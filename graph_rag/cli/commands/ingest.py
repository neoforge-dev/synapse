"""Command for ingesting documents into the graph database."""
import json
from pathlib import Path
import typer
from typing import Optional
import asyncio

from graph_rag.config.settings import Settings
from graph_rag.core.document_processor import SimpleDocumentProcessor
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.services.ingestion import IngestionService

# Import necessary for creating dependencies
from graph_rag.api.dependencies import MockEmbeddingService
from graph_rag.infrastructure.vector_stores import SimpleVectorStore

async def process_and_store_document(
    file_path: Path,
    metadata: Optional[dict] = None
) -> None:
    """
    Process and store a document in the graph database.
    
    Args:
        file_path: Path to the file to process
        metadata: Optional metadata dictionary to attach to the document
    """
    # Initialize components
    settings = Settings()
    repo = MemgraphGraphRepository(settings)
    processor = SimpleDocumentProcessor()
    extractor = SpacyEntityExtractor()
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
            embedding_service=embedding_service, # Provide the created service
            # chunk_splitter=processor,  # Removed incorrect argument
            vector_store=vector_store # Provide the created store
        )

        # Read file content
        content = file_path.read_text()

        # Process and store document
        result = await service.ingest_document(
            document_id=str(file_path),
            content=content,
            metadata=metadata or {},
            generate_embeddings=False  # Skip embeddings for now
        )

        return result
    finally:
        await repo.close()

async def ingest(
    file_path: Path = typer.Argument(..., help="Path to the file to ingest"),
    metadata: Optional[str] = typer.Option(None, help="JSON string of metadata to attach to the document")
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
        # Process and store document
        result = await process_and_store_document(file_path, metadata_dict)
        typer.echo(f"Successfully ingested {file_path} (document ID: {result.document_id}, chunks: {result.num_chunks})")
    except Exception as e:
        typer.echo(f"Error ingesting document: {e}")
        raise typer.Exit(1)

def ingest_command(
    file_path: Path = typer.Argument(..., help="Path to the file to ingest"),
    metadata: Optional[str] = typer.Option(None, help="JSON string of metadata to attach to the document")
) -> None:
    """Wrapper function to run the async ingest command."""
    asyncio.run(ingest(file_path=file_path, metadata=metadata)) 