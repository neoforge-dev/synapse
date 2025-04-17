"""CLI command for document ingestion."""
import logging
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import uuid
import typer
import httpx
import os

from graph_rag.config import get_settings
from graph_rag.cli.config import cli_config
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.core.document_processor import SimpleDocumentProcessor
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.core.interfaces import DocumentData
from graph_rag.domain.models import Document, Chunk, Entity, Relationship
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository

settings = get_settings()

# Configure logging for CLI
logging.basicConfig(
    level=settings.api_log_level.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Typer app for ingest commands
# app = typer.Typer(help="Commands for ingesting documents into the knowledge graph.")

async def process_and_store_document(
    file_path: Path,
    metadata_dict: Dict[str, Any],
    graph_repository: MemgraphRepository,
    doc_processor: SimpleDocumentProcessor,
    entity_extractor: SpacyEntityExtractor
) -> None:
    """Process a document and store it in the graph database."""
    try:
        # Read document content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Process document into chunks
        chunks = await doc_processor.chunk_document(DocumentData(id=doc_id, content=content, metadata=metadata_dict))
        
        # Store document
        await graph_repository.add_document(Document(
            id=doc_id,
            content=content,
            metadata=metadata_dict
        ))
        
        # Process and store each chunk
        for chunk in chunks:
            # Generate chunk ID
            chunk_id = str(uuid.uuid4())
            
            # Extract entities from chunk using the new method
            extraction_result = await entity_extractor.extract_from_text(
                chunk.text,
                context={"chunk_id": chunk_id, "doc_id": doc_id}
            )
            entities = extraction_result.entities # Get ExtractedEntity objects
            
            # Store chunk
            await graph_repository.add_chunk(Chunk(
                id=chunk_id,
                text=chunk.text,
                document_id=doc_id,
                embedding=None  # TODO: Add embedding support
            ))
            
            # Store entities and create relationships
            entity_ids = []
            for entity in entities:
                # entity is now ExtractedEntity from interfaces
                entity_id = str(uuid.uuid4())
                await graph_repository.add_node(Entity(
                    id=entity_id, # Use generated UUID
                    name=entity.text,
                    type=entity.label, # Use label field from ExtractedEntity
                    properties={"original_text": entity.text, "label": entity.label} # Store original text/label as properties
                ))
                entity_ids.append(entity_id)
            
            # Link chunk to entities
            if entity_ids:
                for entity_id in entity_ids:
                    rel = Relationship(
                        id=str(uuid.uuid4()),
                        source_id=chunk_id,
                        target_id=entity_id,
                        type="MENTIONS",
                        properties={}
                    )
                    await graph_repository.add_relationship(rel)
        
        typer.echo(f"Successfully ingested document {doc_id}")
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        typer.echo(f"Error processing document: {str(e)}", err=True)
        raise typer.Exit(1)

# @app.command() # Removed decorator
def ingest(
    # ctx: typer.Context, # Keep context removed if decorator is removed
    file_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the document file to ingest"
    ),
    metadata: Optional[str] = typer.Option(
        None,
        "--metadata",
        help="JSON string of additional metadata"
    )
) -> None:
    """Ingest a document into the knowledge graph."""

    # Parse metadata if provided
    metadata_dict: Dict[str, Any] = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in metadata")
            typer.echo("Error: Invalid JSON in metadata", err=True)
            raise typer.Exit(1)
    
    # Initialize components
    # Import settings here to ensure it loads correctly in CLI context
    from graph_rag.config.settings import Settings
    try:
        local_settings = Settings()
    except Exception as e:
        logger.error(f"Failed to load settings for ingest command: {e}", exc_info=True)
        typer.echo(f"Error: Could not load settings - {e}", err=True)
        raise typer.Exit(1)

    # Initialize Neo4j Driver first
    driver = None
    try:
        from neo4j import AsyncGraphDatabase # Import here
        driver = AsyncGraphDatabase.driver(
            local_settings.get_memgraph_uri(),
            auth=(local_settings.MEMGRAPH_USERNAME, local_settings.MEMGRAPH_PASSWORD.get_secret_value() if local_settings.MEMGRAPH_PASSWORD else None)
        )
        # Optional: Add a connectivity check here if needed for CLI robustness
        # asyncio.run(driver.verify_connectivity()) 
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j driver: {e}", exc_info=True)
        typer.echo(f"Error: Could not connect to the database - {e}", err=True)
        raise typer.Exit(1)

    # Initialize repository with the driver instance
    graph_repository = MemgraphRepository(driver=driver)
    doc_processor = SimpleDocumentProcessor()
    entity_extractor = SpacyEntityExtractor()
    
    # Run the async processing
    asyncio.run(process_and_store_document(
        file_path,
        metadata_dict,
        graph_repository,
        doc_processor,
        entity_extractor
    ))

    # Close the driver when done
    if driver:
        asyncio.run(driver.close())

# Removed if __name__ == "__main__" block 