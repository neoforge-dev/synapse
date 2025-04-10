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
from graph_rag.config import get_settings

settings = get_settings()

# Configure logging for CLI
logging.basicConfig(
    level=settings.api_log_level.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Typer app for ingest commands
# app = typer.Typer(help="Commands for ingesting documents into the knowledge graph.")

async def make_api_request(
    method: str,
    url: str,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Make an HTTP request to the API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                files=files,
                headers=headers or {}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error making API request: {str(e)}")
        raise typer.Exit(1)

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
        chunks = await doc_processor.process_document(content)
        
        # Store document
        await graph_repository.add_document({
            "id": doc_id,
            "content": content,
            "metadata": metadata_dict
        })
        
        # Process and store each chunk
        for chunk in chunks:
            # Generate chunk ID
            chunk_id = str(uuid.uuid4())
            
            # Extract entities from chunk
            entities = await entity_extractor.extract_entities(chunk.text)
            
            # Store chunk
            await graph_repository.add_chunk({
                "id": chunk_id,
                "text": chunk.text,
                "document_id": doc_id,
                "embedding": None  # TODO: Add embedding support
            })
            
            # Store entities and create relationships
            entity_ids = []
            for entity in entities:
                entity_id = str(uuid.uuid4())
                await graph_repository.add_entity({
                    "id": entity_id,
                    "label": entity.label,
                    "text": entity.text
                })
                entity_ids.append(entity_id)
            
            # Link chunk to entities
            if entity_ids:
                await graph_repository.link_chunk_to_entities(chunk_id, entity_ids)
        
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

    graph_repository = MemgraphRepository(
        uri=f"bolt://{local_settings.MEMGRAPH_HOST}:{local_settings.MEMGRAPH_PORT}",
        user=local_settings.MEMGRAPH_USERNAME,
        password=local_settings.MEMGRAPH_PASSWORD.get_secret_value() if local_settings.MEMGRAPH_PASSWORD else None
    )
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

# Removed if __name__ == "__main__" block 