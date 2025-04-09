import pytest
import asyncio
from pathlib import Path
import tempfile
import json
from typing import Dict, Any
import logging

from graph_rag.cli.commands.ingest import process_and_store_document
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository
from graph_rag.core.document_processor import SimpleDocumentProcessor
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.config import settings

logger = logging.getLogger(__name__)

@pytest.fixture
def test_document() -> str:
    """Create a test document with known entities."""
    return """
    The Eiffel Tower is a wrought-iron lattice tower in Paris, France.
    It was designed by Gustave Eiffel and completed in 1889.
    The tower is 330 meters tall and is the most-visited paid monument in the world.
    """

@pytest.fixture
def test_metadata() -> Dict[str, Any]:
    """Create test metadata."""
    return {
        "source": "test",
        "type": "factual",
        "language": "en"
    }

@pytest.fixture
async def graph_repository():
    """Create a GraphRepository instance for testing."""
    repo = GraphRepository(
        uri=f"bolt://{settings.memgraph_host}:{settings.memgraph_port}",
        user=settings.memgraph_user,
        password=settings.memgraph_password.get_secret_value() if settings.memgraph_password else None
    )
    yield repo
    await repo.close()

@pytest.mark.asyncio
async def test_process_and_store_document(
    test_document: str,
    test_metadata: Dict[str, Any],
    graph_repository: GraphRepository
):
    """Test the complete document ingestion pipeline."""
    # Create a temporary file with the test document
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(test_document)
        file_path = Path(f.name)
    
    try:
        # Initialize components
        doc_processor = SimpleDocumentProcessor()
        entity_extractor = SpacyEntityExtractor()
        
        # Process and store the document
        await process_and_store_document(
            file_path,
            test_metadata,
            graph_repository,
            doc_processor,
            entity_extractor
        )
        
        # Verify document was stored
        result = await graph_repository.execute_read(
            "MATCH (d:Document) RETURN d.id as id, d.metadata as metadata"
        )
        assert len(result) == 1
        assert result[0]["metadata"] == test_metadata
        
        # Verify chunks were created and linked
        result = await graph_repository.execute_read(
            """
            MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
            RETURN count(c) as chunk_count
            """
        )
        assert result[0]["chunk_count"] > 0
        
        # Verify entities were extracted and linked
        result = await graph_repository.execute_read(
            """
            MATCH (c:Chunk)-[:MENTIONS]->(e:Entity)
            RETURN count(DISTINCT e) as entity_count
            """
        )
        assert result[0]["entity_count"] > 0
        
        # Verify specific entities were extracted
        result = await graph_repository.execute_read(
            """
            MATCH (e:Entity)
            WHERE e.text IN ['Eiffel Tower', 'Paris', 'Gustave Eiffel']
            RETURN e.text as text
            """
        )
        extracted_entities = {r["text"] for r in result}
        assert "Eiffel Tower" in extracted_entities
        assert "Paris" in extracted_entities
        assert "Gustave Eiffel" in extracted_entities
        
    finally:
        # Clean up
        file_path.unlink()
        
        # Clean up the graph
        await graph_repository.execute_read(
            "MATCH (n) DETACH DELETE n"
        )

@pytest.mark.asyncio
async def test_process_and_store_document_error_handling(
    graph_repository: GraphRepository
):
    """Test error handling in the document ingestion pipeline."""
    # Create a non-existent file path
    file_path = Path("/nonexistent/file.txt")
    
    # Initialize components
    doc_processor = SimpleDocumentProcessor()
    entity_extractor = SpacyEntityExtractor()
    
    # Attempt to process and store the document
    with pytest.raises(SystemExit):
        await process_and_store_document(
            file_path,
            {},
            graph_repository,
            doc_processor,
            entity_extractor
        )

@pytest.mark.asyncio
async def test_process_and_store_document_invalid_metadata(
    test_document: str,
    graph_repository: GraphRepository
):
    """Test handling of invalid metadata."""
    # Create a temporary file with the test document
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(test_document)
        file_path = Path(f.name)
    
    try:
        # Initialize components
        doc_processor = SimpleDocumentProcessor()
        entity_extractor = SpacyEntityExtractor()
        
        # Process and store the document with invalid metadata
        await process_and_store_document(
            file_path,
            {"invalid": object()},  # Invalid metadata (non-serializable)
            graph_repository,
            doc_processor,
            entity_extractor
        )
        
        # Verify document was stored with empty metadata
        result = await graph_repository.execute_read(
            "MATCH (d:Document) RETURN d.metadata as metadata"
        )
        assert result[0]["metadata"] == {}
        
    finally:
        # Clean up
        file_path.unlink()
        
        # Clean up the graph
        await graph_repository.execute_read(
            "MATCH (n) DETACH DELETE n"
        ) 