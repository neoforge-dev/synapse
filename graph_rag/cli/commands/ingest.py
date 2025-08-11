"""Command for ingesting documents into the graph database."""

import asyncio
import json
import logging  # Add logging import
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional, Any
import fnmatch

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
    replace_existing: bool = True,
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
        derived_id, id_source, _ = derive_document_id(
            file_path, content, metadata or {}
        )
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
            replace_existing=replace_existing,
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

        # Build a minimal structured result for CLI reporting
        result_payload: dict[str, Any] = {
            "document_id": document_id,
            "num_chunks": len(chunk_objects),
            "id_source": id_source,
            "path": str(file_path),
            "embeddings": bool(enable_embeddings),
            "replace_existing": bool(replace_existing),
        }
        topics = (meta_with_id or {}).get("topics")
        if isinstance(topics, list):
            result_payload["topics"] = topics
        return result_payload

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
    meta: list[str] = typer.Option(
        None,
        "--meta",
        help="Additional metadata entries as key=value (repeatable)",
    ),
    meta_file: Optional[Path] = typer.Option(
        None,
        "--meta-file",
        help="Path to YAML or JSON file with metadata to merge",
    ),
    embeddings: bool = typer.Option(
        False,
        "--embeddings/--no-embeddings",
        help="Generate and store embeddings during ingestion (default: off)",
    ),
    replace: bool = typer.Option(
        True,
        "--replace/--no-replace",
        help=(
            "When re-ingesting an existing document ID, delete old chunks/vectors "
            "before adding new ones (idempotent)."
        ),
    ),
    include: list[str] = typer.Option(
        None,
        "--include",
        help="Glob pattern to include (repeatable). Defaults to all supported files.",
    ),
    exclude: list[str] = typer.Option(
        None,
        "--exclude",
        help="Glob pattern to exclude (repeatable). Applied after include filters.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be ingested and exit"
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON output (with --dry-run)"
    ),
    read_stdin: bool = typer.Option(
        False, "--stdin", help="Read document content from STDIN; ignores file path"
    ),
    json_summary: bool = typer.Option(
        False,
        "--json-summary",
        help="With --json for directories, include a summary with totals",
    ),
) -> None:
    """
    Ingest a document into the graph database.

    Args:
        file_path: Path to the file to ingest
        metadata: Optional JSON string of metadata to attach to the document
    """
    # Validate path exists unless reading from stdin
    if not read_stdin and not file_path.exists():
        typer.echo(f"Error: File {file_path} does not exist")
        raise typer.Exit(1)

    # Parse metadata sources: front matter (per file), meta-file, --meta kv, JSON string
    def _parse_meta_file(path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            typer.echo(f"Error: Failed to read meta-file {path}: {e}")
            raise typer.Exit(1)
        try:
            if path.suffix.lower() in {".yaml", ".yml"}:
                obj = yaml.safe_load(text) or {}
            elif path.suffix.lower() == ".json":
                obj = json.loads(text)
            else:
                # Try YAML first, then JSON
                try:
                    obj = yaml.safe_load(text) or {}
                except Exception:
                    obj = json.loads(text)
            return obj if isinstance(obj, dict) else {}
        except Exception as e:
            typer.echo(f"Error: Invalid meta-file {path}: {e}")
            raise typer.Exit(1)

    def _parse_meta_kv(items: list[str] | None) -> dict:
        result: dict[str, Any] = {}
        if not items:
            return result
        for it in items:
            if "=" not in it:
                typer.echo(
                    f"Warning: Ignoring malformed --meta '{it}', expected key=value"
                )
                continue
            key, value = it.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            result[key] = value
        return result

    metadata_from_file: dict = _parse_meta_file(meta_file) if meta_file else {}
    metadata_from_kv: dict = _parse_meta_kv(meta)
    metadata_json: dict = {}
    if metadata:
        try:
            metadata_json = json.loads(metadata)
        except json.JSONDecodeError:
            # Maintain backward-compatible error message expected by tests
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
                            return [
                                s.strip().lstrip("#")
                                for s in value.split()
                                if s.strip()
                            ]
                        return [value.strip()] if value.strip() else []
                    return [str(value)]

                # tags/Topics -> topics
                if "tags" in data and data.get("tags") is not None:
                    normalized["topics"] = _ensure_list(data.get("tags"))
                if "Topics" in data and data.get("Topics") is not None:
                    topics = _ensure_list(data.get("Topics"))
                    normalized["topics"] = list(
                        {*(normalized.get("topics", [])), *topics}
                    )

                # aliases passthrough normalization
                if "aliases" in data and data.get("aliases") is not None:
                    normalized["aliases"] = _ensure_list(data.get("aliases"))

                # dates mapping if present
                for k in ("created", "created_at"):
                    if k in data and data.get(k):
                        normalized["created_at"] = str(data.get(k))
                        break
                for k in (
                    "updated",
                    "updated_at",
                    "last_edited_time",
                    "Last edited time",
                ):
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
            if (
                len(window) >= 3
                and "|" in window[0]
                and "|" in window[1]
                and set(window[1]) <= set("|- :")
            ):
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
                            return [
                                s.strip().lstrip("#")
                                for s in value.split(",")
                                if s.strip()
                            ]
                        if "#" in value:
                            return [
                                s.strip().lstrip("#")
                                for s in value.split()
                                if s.strip()
                            ]
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
                    if k not in (
                        "Tags",
                        "tags",
                        "Topics",
                        "Aliases",
                        "aliases",
                        "Created",
                        "Created time",
                        "Last edited time",
                        "Updated",
                        "created",
                        "created_at",
                        "updated",
                        "updated_at",
                    ):
                        normalized[k.lower().replace(" ", "_")] = v

                return normalized
        except Exception as table_err:
            logger.warning(
                f"Failed to parse Notion property table in {path}: {table_err}"
            )
            return {}

        return {}

    def _match_globs(root: Path, candidate: Path) -> bool:
        # Build a posix relative path for matching
        try:
            rel = candidate.relative_to(root)
        except Exception:
            rel = candidate
        rel_posix = rel.as_posix()
        # Includes
        if include:
            if not any(fnmatch.fnmatch(rel_posix, pat) for pat in include):
                return False
        # Excludes
        if exclude:
            if any(fnmatch.fnmatch(rel_posix, pat) for pat in exclude):
                return False
        return True

    def _merge_metadata(front_matter: dict) -> dict:
        # Merge order: front matter < meta-file < --meta < --metadata JSON
        merged = {
            **(front_matter or {}),
            **metadata_from_file,
            **metadata_from_kv,
            **metadata_json,
        }
        return merged

    try:
        # Special case: --stdin reads content and stores to a temp file for processing
        if read_stdin:
            content = sys.stdin.read()
            if dry_run:
                # Simulate a path for ID derivation
                synthetic_path = Path("stdin://document")
                derived_id, id_source, _ = derive_document_id(
                    synthetic_path, content, {}
                )
                plan = [
                    {
                        "path": str(synthetic_path),
                        "document_id": derived_id,
                        "id_source": id_source,
                    }
                ]
                output = (
                    json.dumps(plan, ensure_ascii=False)
                    if as_json
                    else f"1 document(s) would be ingested. First id={derived_id} (source={id_source})."
                )
                typer.echo(output)
                return
            # Persist stdin to a temporary file to reuse pipeline
            tmp_dir = Path(typer.get_app_dir("synapse"))
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = tmp_dir / "stdin_ingest.md"
            tmp_file.write_text(content, encoding="utf-8")
            fm = parse_front_matter(tmp_file)
            merged_meta = _merge_metadata(fm)
            try:
                res = await process_and_store_document(
                    tmp_file,
                    merged_meta,
                    enable_embeddings=embeddings,
                    replace_existing=replace,
                )
            except TypeError:
                res = await process_and_store_document(tmp_file, merged_meta)
            if as_json:
                payload = res if isinstance(res, dict) else {"path": str(tmp_file)}
                typer.echo(json.dumps(payload, ensure_ascii=False))
            else:
                typer.echo(
                    "Successfully processed STDIN content including graph links."
                )
            return

        processed_count = 0
        if file_path.is_dir():
            candidates: list[Path] = []
            for path in sorted(file_path.rglob("*")):
                if (
                    path.is_file()
                    and not path.name.startswith(".")
                    and ".obsidian" not in path.parts
                    and not any("assets" in part.lower() for part in path.parts)
                    and path.suffix.lower() in {".md", ".markdown", ".txt"}
                    and _match_globs(file_path, path)
                ):
                    candidates.append(path)

            if dry_run:
                plan: list[dict[str, Any]] = []
                for p in candidates:
                    try:
                        text = p.read_text(encoding="utf-8")
                    except Exception:
                        text = ""
                    fm = parse_front_matter(p)
                    merged_meta = _merge_metadata(fm)
                    doc_id, id_source, _ = derive_document_id(p, text, merged_meta)
                    plan.append(
                        {
                            "path": str(p),
                            "document_id": doc_id,
                            "id_source": id_source,
                            "topics": merged_meta.get("topics", []),
                        }
                    )
                output = (
                    json.dumps(plan, ensure_ascii=False)
                    if as_json
                    else f"{len(plan)} document(s) would be ingested."
                )
                typer.echo(output)
                return

            results_payload: list[dict[str, Any]] = [] if as_json else None
            succeeded = 0
            failed = 0
            for path in candidates:
                fm = parse_front_matter(path)
                merged_meta = _merge_metadata(fm)
                try:
                    try:
                        res = await process_and_store_document(
                            path,
                            merged_meta,
                            enable_embeddings=embeddings,
                            replace_existing=replace,
                        )
                    except TypeError:
                        res = await process_and_store_document(path, merged_meta)
                    if as_json:
                        # Expect dict-like from implementation/tests; fallback minimal
                        item = res if isinstance(res, dict) else {"path": str(path)}
                        # Add status for per-file outcome
                        if isinstance(item, dict) and "status" not in item:
                            item = {**item, "status": "ok"}
                        results_payload.append(item)
                    succeeded += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to ingest {path}: {e}", exc_info=True)
                    if as_json:
                        results_payload.append(
                            {
                                "path": str(path),
                                "error": str(e),
                                "status": "error",
                            }
                        )
                    # Continue processing other files in directory mode
                    continue
                finally:
                    processed_count += 1
            if processed_count == 0:
                typer.echo("No eligible files found to ingest.")
                raise typer.Exit(1)
            if as_json:
                if json_summary:
                    summary_obj = {
                        "files": results_payload,
                        "summary": {
                            "processed": processed_count,
                            "succeeded": succeeded,
                            "failed": failed,
                        },
                    }
                    typer.echo(json.dumps(summary_obj, ensure_ascii=False))
                else:
                    typer.echo(json.dumps(results_payload, ensure_ascii=False))
            else:
                # Preserve existing success message expected by tests
                if failed == 0:
                    typer.echo(
                        f"Successfully processed and stored {processed_count} files from {file_path}."
                    )
                else:
                    typer.echo(
                        f"Processed {processed_count} files from {file_path} ({succeeded} succeeded, {failed} failed)."
                    )
        else:
            # Single file
            if dry_run:
                try:
                    text = file_path.read_text(encoding="utf-8")
                except Exception:
                    text = ""
                fm = parse_front_matter(file_path)
                merged_meta = _merge_metadata(fm)
                doc_id, id_source, _ = derive_document_id(file_path, text, merged_meta)
                plan = [
                    {
                        "path": str(file_path),
                        "document_id": doc_id,
                        "id_source": id_source,
                        "topics": merged_meta.get("topics", []),
                    }
                ]
                output = (
                    json.dumps(plan, ensure_ascii=False)
                    if as_json
                    else f"1 document(s) would be ingested. id={doc_id} (source={id_source})."
                )
                typer.echo(output)
                return

            fm = parse_front_matter(file_path)
            merged_meta = _merge_metadata(fm)
            try:
                res = await process_and_store_document(
                    file_path,
                    merged_meta,
                    enable_embeddings=embeddings,
                    replace_existing=replace,
                )
            except TypeError:
                res = await process_and_store_document(file_path, merged_meta)
            if as_json:
                payload = res if isinstance(res, dict) else {"path": str(file_path)}
                typer.echo(json.dumps(payload, ensure_ascii=False))
            else:
                typer.echo(
                    f"Successfully processed and stored {file_path} including graph links."
                )
    except Exception as e:
        # Emit structured error if --json was requested
        if as_json:
            err = {"error": str(e)}
            try:
                typer.echo(json.dumps(err, ensure_ascii=False))
            except Exception:
                typer.echo('{"error":"ingest failed"}')
        else:
            typer.echo(f"Error ingesting document(s): {e}")
        raise typer.Exit(1)


def ingest_command(
    file_path: Path = typer.Argument(..., help="Path to the file to ingest"),
    metadata: Optional[str] = typer.Option(
        None, help="JSON string of metadata to attach to the document"
    ),
    meta: list[str] = typer.Option(
        None,
        "--meta",
        help="Additional metadata entries as key=value (repeatable)",
    ),
    meta_file: Optional[Path] = typer.Option(
        None,
        "--meta-file",
        help="Path to YAML or JSON file with metadata to merge",
    ),
    embeddings: bool = typer.Option(
        False,
        "--embeddings/--no-embeddings",
        help="Generate and store embeddings during ingestion (default: off)",
    ),
    replace: bool = typer.Option(
        True,
        "--replace/--no-replace",
        help=(
            "When re-ingesting an existing document ID, delete old chunks/vectors "
            "before adding new ones (idempotent)."
        ),
    ),
    include: list[str] = typer.Option(
        None,
        "--include",
        help="Glob pattern to include (repeatable). Defaults to all supported files.",
    ),
    exclude: list[str] = typer.Option(
        None,
        "--exclude",
        help="Glob pattern to exclude (repeatable). Applied after include filters.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be ingested and exit"
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON output (with --dry-run)"
    ),
    read_stdin: bool = typer.Option(
        False, "--stdin", help="Read document content from STDIN; ignores file path"
    ),
    json_summary: bool = typer.Option(
        False,
        "--json-summary",
        help="With --json for directories, include a summary with totals",
    ),
) -> None:
    """Wrapper function to run the async ingest command with options."""
    asyncio.run(
        ingest(
            file_path=file_path,
            metadata=metadata,
            meta=meta,
            meta_file=meta_file,
            embeddings=embeddings,
            replace=replace,
            include=include,
            exclude=exclude,
            dry_run=dry_run,
            as_json=as_json,
            read_stdin=read_stdin,
            json_summary=json_summary,
        )
    )
