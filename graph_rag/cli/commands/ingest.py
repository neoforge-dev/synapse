"""Command for ingesting documents into the graph database."""

import asyncio
import json
import logging  # Add logging import
from collections import defaultdict
from pathlib import Path
from typing import Optional

import typer

from graph_rag.api.dependencies import MockEmbeddingService  # Using Mock for CLI
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

logger = logging.getLogger(__name__)  # Initialize logger
# Configure basic logging if not already configured by application entry point
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def process_and_store_document(
    file_path: Path, metadata: Optional[dict] = None
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
    # Create required dependencies (using mocks/simple versions for CLI)
    # Use settings to get embedding dimension
    embedding_service = MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION)
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

        # Read file content
        content = file_path.read_text()
        document_id = str(file_path)  # Use file path as ID for CLI

        # 1. Basic ingestion (Doc + Chunks)
        await service.ingest_document(
            document_id=document_id,
            content=content,
            metadata=metadata or {},
            generate_embeddings=False,  # Skip embeddings for CLI simplicity for now
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
    file_path: Path = typer.Argument(..., help="Path to the file to ingest"),
    metadata: Optional[str] = typer.Option(
        None, help="JSON string of metadata to attach to the document"
    ),
) -> None:
    """
    Ingest a document into the graph database.

    Args:
        file_path: Path to the file to ingest
        metadata: Optional JSON string of metadata to attach to the document
    """
    # Validate file exists
    if not file_path.exists():
        typer.echo(f"Error: File {file_path} does not exist")
        raise typer.Exit(1)

    # Parse metadata if provided
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            typer.echo("Error: Invalid JSON in metadata")
            raise typer.Exit(1)

    try:
        # Process and store document (now includes graph building)
        await process_and_store_document(file_path, metadata_dict)
        # Updated success message - num_chunks not directly available
        typer.echo(
            f"Successfully processed and stored {file_path} including graph links."
        )
    except Exception as e:
        typer.echo(f"Error ingesting document: {e}")
        raise typer.Exit(1)


def ingest_command(
    file_path: Path = typer.Argument(..., help="Path to the file to ingest"),
    metadata: Optional[str] = typer.Option(
        None, help="JSON string of metadata to attach to the document"
    ),
) -> None:
    """Wrapper function to run the async ingest command."""
    asyncio.run(ingest(file_path=file_path, metadata=metadata))
