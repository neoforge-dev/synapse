"""Command for ingesting documents into the graph database."""

import asyncio
import json
import logging  # Add logging import
from collections import defaultdict
from pathlib import Path
from typing import Optional, Any

import typer
import yaml

from graph_rag.api.dependencies import (
    MockEmbeddingService,  # Using Mock by default for CLI
)
from graph_rag.config import Settings
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.core.interfaces import (
    ExtractedEntity,
    ExtractedRelationship,
)  # Import ExtractionResult too
from graph_rag.core.knowledge_graph_builder import SimpleKnowledgeGraphBuilder
from graph_rag.domain.models import Chunk, Entity
from graph_rag.infrastructure.document_processor.simple_processor import (
    SimpleDocumentProcessor,
)
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
from graph_rag.models import ProcessedDocument
from graph_rag.services.ingestion import IngestionService
from graph_rag.utils.identity import derive_document_id

logger = logging.getLogger(__name__)  # Initialize logger
# Configure basic logging if not already configured by application entry point
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def process_and_store_document(
    file_path: Path,
    metadata: Optional[dict] = None,
    enable_embeddings: bool = False,
) -> None:
    """
    Process and store a document, extract entities, and build graph links.

    Args:
        file_path: Path to the file to process
        metadata: Optional metadata dictionary to attach to the document
    """
    # Initialize components
    settings = Settings()
    repo = MemgraphGraphRepository(settings)
    processor = SimpleDocumentProcessor()
    extractor = SpacyEntityExtractor()
    builder = SimpleKnowledgeGraphBuilder(graph_store=repo)  # Initialize builder
    # Create required dependencies (using mock embeddings by default for speed/portability)
    # Optionally switch to real embeddings when enabled
    try:
        if enable_embeddings:
            # Prefer sentence-transformers via service factory; fallback to mock on failure
            from graph_rag.services.embedding import (
                SentenceTransformerEmbeddingService,
            )

            embedding_service = SentenceTransformerEmbeddingService(
                model_name=settings.vector_store_embedding_model
            )
        else:
            raise RuntimeError("Embeddings disabled")
    except Exception:
        # Fallback to constant mock embeddings
        # Use a small dimension for speed
        embedding_service = MockEmbeddingService(dimension=10)

    vector_store = SimpleVectorStore(embedding_service=embedding_service)

    try:
        # Connect to database
        await repo.connect()

        # Create ingestion service - Corrected signature
        service = IngestionService(
            document_processor=processor,
            entity_extractor=extractor,
            graph_store=repo,
            embedding_service=embedding_service,  # Provide the created service
            # chunk_splitter=processor,  # Removed incorrect argument
            vector_store=vector_store,  # Provide the created store
        )

        # Read file content and derive stable document_id
        content = file_path.read_text()
        derived_id, id_source, _ = derive_document_id(file_path, content, metadata or {})
        document_id = derived_id
        # Attach id_source for observability
        meta_with_id = dict(metadata or {})
        meta_with_id.setdefault("id_source", id_source)

        # 1. Basic ingestion (Doc + Chunks)
        await service.ingest_document(
            document_id=document_id,
            content=content,
            metadata=meta_with_id,
            generate_embeddings=enable_embeddings,
        )

        # 2. Retrieve chunks
        chunk_objects: list[Chunk] = await repo.get_chunks_by_document_id(document_id)
        if not chunk_objects:
            logger.warning(
                f"No chunks found for document {document_id} after ingestion, skipping entity linking."
            )
            return  # Return early if no chunks

        # 3. Extract Entities chunk by chunk
        all_entities_dict: dict[str, ExtractedEntity] = {}
        all_relationships: list[ExtractedRelationship] = []
        # Map Chunk ID -> List of ExtractedEntity IDs in that chunk
        chunk_to_entity_ids: dict[str, list[str]] = defaultdict(list)

        logger.info(
            f"Extracting entities from {len(chunk_objects)} chunks for doc {document_id}..."
        )

        extraction_tasks = []
        chunk_map = {
            chunk.id: chunk for chunk in chunk_objects
        }  # For associating results back to chunks
        for chunk_id, chunk in chunk_map.items():
            if chunk.text and not chunk.text.isspace():
                # Pass chunk_id for context/mapping
                extraction_tasks.append(
                    (chunk_id, extractor.extract_from_text(chunk.text))
                )
            else:
                logger.debug(f"Skipping empty chunk {chunk_id} for entity extraction.")

        if extraction_tasks:
            # Await all extraction tasks
            results_with_ids = await asyncio.gather(
                *[task[1] for task in extraction_tasks]
            )
            original_chunk_ids = [task[0] for task in extraction_tasks]

            for i, result in enumerate(results_with_ids):
                chunk_id_for_result = original_chunk_ids[i]
                entity_ids_in_chunk = []
                for entity in result.entities:
                    if entity.id not in all_entities_dict:
                        all_entities_dict[entity.id] = entity
                    # Store the link
                    entity_ids_in_chunk.append(entity.id)

                if entity_ids_in_chunk:
                    chunk_to_entity_ids[chunk_id_for_result].extend(entity_ids_in_chunk)

                # Aggregate relationships if any extractor ever produces them
                all_relationships.extend(result.relationships)

        final_entities = list(all_entities_dict.values())
        logger.info(
            f"Extracted {len(final_entities)} unique entities for doc {document_id}."
        )

        # 4. Build KG Links (Entities + Relationships)
        logger.info(f"Building knowledge graph links for doc {document_id}...")
        domain_entities = [
            Entity(id=e.id, name=e.name, type=e.label, metadata=e.metadata)
            for e in final_entities
        ]
        # Assuming builder.build primarily adds entities/relationships nodes/edges
        processed_doc_for_graph = ProcessedDocument(
            id=document_id,
            content=content,
            chunks=chunk_objects,
            entities=domain_entities,
            relationships=[],  # Pass empty domain relationships
        )
        # This call might just add entity nodes if that's how builder/repo is implemented
        await builder.build(processed_doc_for_graph)
        logger.info(f"Completed graph node/relationship additions for {document_id}.")

        # 5. Explicitly link Chunks to the Entities they mention
        logger.info(f"Linking chunks to mentioned entities for doc {document_id}...")
        link_tasks = []
        for chunk_id, entity_ids in chunk_to_entity_ids.items():
            if entity_ids:
                # Ensure unique IDs before linking
                unique_entity_ids = list(set(entity_ids))
                logger.debug(
                    f"Linking chunk {chunk_id} to entities: {unique_entity_ids}"
                )
                # Assume repo has link_chunk_to_entities method
                link_tasks.append(
                    repo.link_chunk_to_entities(chunk_id, unique_entity_ids)
                )

        if link_tasks:
            await asyncio.gather(*link_tasks)
            logger.info(
                f"Completed linking {len(chunk_to_entity_ids)} chunks to entities for doc {document_id}."
            )
        else:
            logger.info(f"No chunk-entity links to create for doc {document_id}.")

        # Original result is still useful for reporting
        # Return None as the main success indicator is no exception

    except Exception as e:
        logger.error(f"Error during CLI processing for {file_path}: {e}", exc_info=True)
        # Reraise the exception to be caught by the typer command handler
        raise
    finally:
        await repo.close()
        # Return the original ingestion result if it exists, otherwise None
        # The calling function checks for exceptions, not the return value now.
        # return ingestion_result


async def ingest(
    file_path: Path = typer.Argument(
        ..., help="Path to the file or directory to ingest"
    ),
    metadata: Optional[str] = typer.Option(
        None, help="JSON string of metadata to attach to the document"
    ),
    embeddings: bool = typer.Option(
        False,
        "--embeddings/--no-embeddings",
        help="Generate and store embeddings during ingestion (default: off)",
    ),
) -> None:
    """
    Ingest a document into the graph database.

    Args:
        file_path: Path to the file to ingest
        metadata: Optional JSON string of metadata to attach to the document
    """
    # Validate path exists
    if not file_path.exists():
        typer.echo(f"Error: File {file_path} does not exist")
        raise typer.Exit(1)

    # Parse metadata if provided and merge with any front matter
    metadata_dict: dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            typer.echo("Error: Invalid JSON in metadata")
            raise typer.Exit(1)

    def parse_front_matter(path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return {}
        # YAML front matter block
        if text.startswith("---\n"):
            end_idx = text.find("\n---\n", 4)
            if end_idx == -1:
                return {}
            fm_text = text[4:end_idx]
            try:
                raw = yaml.safe_load(fm_text) or {}
                data = raw if isinstance(raw, dict) else {}
                # Normalize common Obsidian/Markdown keys
                normalized: dict = dict(data)

                def _ensure_list(value: Any) -> list:
                    if value is None:
                        return []
                    if isinstance(value, list):
                        return [str(v) for v in value]
                    if isinstance(value, str):
                        # split on commas or spaces with '#'
                        if "," in value:
                            return [s.strip() for s in value.split(",") if s.strip()]
                        if "#" in value:
                            return [s.strip().lstrip("#") for s in value.split() if s.strip()]
                        return [value.strip()] if value.strip() else []
                    return [str(value)]

                # tags/Topics -> topics
                if "tags" in data and data.get("tags") is not None:
                    normalized["topics"] = _ensure_list(data.get("tags"))
                if "Topics" in data and data.get("Topics") is not None:
                    topics = _ensure_list(data.get("Topics"))
                    normalized["topics"] = list({*(normalized.get("topics", [])), *topics})

                # aliases passthrough normalization
                if "aliases" in data and data.get("aliases") is not None:
                    normalized["aliases"] = _ensure_list(data.get("aliases"))

                # dates mapping if present
                for k in ("created", "created_at"):
                    if k in data and data.get(k):
                        normalized["created_at"] = str(data.get(k))
                        break
                for k in ("updated", "updated_at", "last_edited_time", "Last edited time"):
                    if k in data and data.get(k):
                        normalized["updated_at"] = str(data.get(k))
                        break

                return normalized
            except Exception as fm_err:
                logger.warning(f"Failed to parse YAML front matter in {path}: {fm_err}")
                return {}

        # Notion Markdown export: parse leading property table if present
        try:
            lines = text.splitlines()
            # Look for a table header in first ~20 lines
            window = [ln.strip() for ln in lines[:20] if ln.strip()]
            if len(window) >= 3 and "|" in window[0] and "|" in window[1] and set(window[1]) <= set("|- :"):
                # Parse rows of the form: | Property | Value |
                props: dict[str, str] = {}
                for row in window[2:]:
                    if "|" not in row:
                        break
                    # Normalize a markdown table row like: | Key | Value |
                    row_norm = row.strip().strip("|")
                    cols = [c.strip() for c in row_norm.split("|")]
                    # Filter out empty columns
                    cols = [c for c in cols if c]
                    if len(cols) < 2:
                        continue
                    key, value = cols[0], cols[1]
                    if key:
                        props[key] = value

                # Normalize similar to YAML
                normalized: dict[str, Any] = {}

                def _ensure_list(value: Any) -> list:
                    if value is None:
                        return []
                    if isinstance(value, list):
                        return [str(v) for v in value]
                    if isinstance(value, str):
                        if "," in value:
                            return [s.strip().lstrip("#") for s in value.split(",") if s.strip()]
                        if "#" in value:
                            return [s.strip().lstrip("#") for s in value.split() if s.strip()]
                        return [value.strip()] if value.strip() else []
                    return [str(value)]

                # Tags / properties
                for k in ("Tags", "tags", "Topics"):
                    if k in props:
                        normalized["topics"] = _ensure_list(props[k])
                        break
                for k in ("Aliases", "aliases"):
                    if k in props:
                        normalized["aliases"] = _ensure_list(props[k])
                        break
                for k in ("Created", "Created time", "created", "created_at"):
                    if k in props:
                        normalized["created_at"] = props[k]
                        break
                for k in ("Last edited time", "Updated", "updated", "updated_at"):
                    if k in props:
                        normalized["updated_at"] = props[k]
                        break

                # Include any other simple scalar properties
                for k, v in props.items():
                    if k not in ("Tags", "tags", "Topics", "Aliases", "aliases", "Created", "Created time", "Last edited time", "Updated", "created", "created_at", "updated", "updated_at"):
                        normalized[k.lower().replace(" ", "_")] = v

                return normalized
        except Exception as table_err:
            logger.warning(f"Failed to parse Notion property table in {path}: {table_err}")
            return {}

        return {}

    try:
        processed_count = 0
        if file_path.is_dir():
            # Walk directory for markdown/text-like files
            for path in sorted(file_path.rglob("*")):
                if (
                    path.is_file()
                    and not path.name.startswith(".")
                    and ".obsidian" not in path.parts
                    and path.suffix.lower() in {".md", ".markdown", ".txt"}
                ):
                    fm = parse_front_matter(path)
                    merged_meta = {**fm, **metadata_dict}
                    # Call with embeddings flag when supported; fall back to 2-arg call for backward-compat in tests
                    try:
                        await process_and_store_document(
                            path, merged_meta, enable_embeddings=embeddings
                        )
                    except TypeError:
                        await process_and_store_document(path, merged_meta)
                    processed_count += 1
            if processed_count == 0:
                typer.echo("No eligible files found to ingest.")
                raise typer.Exit(1)
            typer.echo(
                f"Successfully processed and stored {processed_count} files from {file_path}."
            )
        else:
            # Single file
            fm = parse_front_matter(file_path)
            merged_meta = {**fm, **metadata_dict}
            try:
                await process_and_store_document(
                    file_path, merged_meta, enable_embeddings=embeddings
                )
            except TypeError:
                await process_and_store_document(file_path, merged_meta)
            typer.echo(
                f"Successfully processed and stored {file_path} including graph links."
            )
    except Exception as e:
        typer.echo(f"Error ingesting document(s): {e}")
        raise typer.Exit(1)


def ingest_command(
    file_path: Path = typer.Argument(..., help="Path to the file to ingest"),
    metadata: Optional[str] = typer.Option(
        None, help="JSON string of metadata to attach to the document"
    ),
) -> None:
    """Wrapper function to run the async ingest command."""
    asyncio.run(ingest(file_path=file_path, metadata=metadata))
