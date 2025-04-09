import pytest
import asyncio
from httpx import AsyncClient
from fastapi import status
import logging
from typing import Dict, Any

from graph_rag.api.main import app
from graph_rag.config import settings
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository
from graph_rag.domain.models import Document, Chunk

# Configure logging for tests
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
async def test_client():
    """Provides an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(scope="module")
async def graph_repository():
    """Provides a test graph repository instance."""
    repo = GraphRepository(
        uri=settings.memgraph_uri,
        username=settings.memgraph_username,
        password=settings.memgraph_password
    )
    yield repo
    # Cleanup after tests
    await repo.close()

async def ingest_test_document(client: AsyncClient, doc_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to ingest a document."""
    response = await client.post(
        "/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata}
    )
    response.raise_for_status()
    return response.json()

# --- Integration Tests ---

@pytest.mark.asyncio
async def test_document_ingestion_pipeline(test_client: AsyncClient, graph_repository: GraphRepository):
    """Test complete document ingestion pipeline with database verification."""
    # 1. Ingest document
    doc_content = "Test document for integration testing. Contains some entities like Alice and Bob."
    metadata = {"source": "integration-test", "category": "test"}
    
    response = await ingest_test_document(test_client, doc_content, metadata)
    doc_id = response["document_id"]
    task_id = response["task_id"]
    
    assert response["status"] == "processing"
    assert doc_id.startswith("doc-")
    
    # 2. Wait for background processing (with timeout)
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        # Check if document exists in database
        doc = await graph_repository.get_document(doc_id)
        if doc is not None:
            break
        await asyncio.sleep(1)  # Wait 1 second between checks
        attempt += 1
    
    assert doc is not None, "Document not found in database after ingestion"
    assert doc.content == doc_content
    assert doc.metadata == metadata
    
    # 3. Verify chunks were created
    chunks = await graph_repository.get_chunks_by_document(doc_id)
    assert len(chunks) > 0, "No chunks created for document"
    
    # 4. Verify document-chunk relationships
    for chunk in chunks:
        assert chunk.document_id == doc_id
        assert chunk.content in doc_content  # Chunk content should be part of document

@pytest.mark.asyncio
async def test_concurrent_ingestion_integration(test_client: AsyncClient, graph_repository: GraphRepository):
    """Test concurrent document ingestion with database verification."""
    async def ingest_and_verify(content: str, metadata: Dict[str, Any]):
        # Ingest document
        response = await ingest_test_document(test_client, content, metadata)
        doc_id = response["document_id"]
        
        # Wait for processing
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            doc = await graph_repository.get_document(doc_id)
            if doc is not None:
                break
            await asyncio.sleep(1)
            attempt += 1
        
        assert doc is not None, f"Document {doc_id} not found in database"
        assert doc.content == content
        return doc_id
    
    # Create multiple ingestion tasks
    tasks = [
        ingest_and_verify(
            f"Concurrent test document {i}",
            {"source": "concurrent-test", "index": i}
        )
        for i in range(3)
    ]
    
    # Run all tasks concurrently
    doc_ids = await asyncio.gather(*tasks)
    
    # Verify all documents exist and have chunks
    for doc_id in doc_ids:
        doc = await graph_repository.get_document(doc_id)
        assert doc is not None
        
        chunks = await graph_repository.get_chunks_by_document(doc_id)
        assert len(chunks) > 0

@pytest.mark.asyncio
async def test_large_document_ingestion_integration(test_client: AsyncClient, graph_repository: GraphRepository):
    """Test ingestion of a large document with database verification."""
    # Create a large document (100KB)
    large_content = "Large test document. " * 5000
    metadata = {"source": "large-doc-test", "size": "100KB"}
    
    response = await ingest_test_document(test_client, large_content, metadata)
    doc_id = response["document_id"]
    
    # Wait for processing
    max_attempts = 15  # Give more time for large document
    attempt = 0
    while attempt < max_attempts:
        doc = await graph_repository.get_document(doc_id)
        if doc is not None:
            break
        await asyncio.sleep(1)
        attempt += 1
    
    assert doc is not None, "Large document not found in database"
    assert doc.content == large_content
    
    # Verify chunks
    chunks = await graph_repository.get_chunks_by_document(doc_id)
    assert len(chunks) > 0
    
    # Verify chunk content
    reconstructed_content = " ".join(chunk.content for chunk in chunks)
    assert reconstructed_content == large_content

@pytest.mark.asyncio
async def test_error_handling_integration(test_client: AsyncClient, graph_repository: GraphRepository):
    """Test error handling during ingestion with database verification."""
    # Test with invalid content (empty)
    response = await test_client.post(
        "/api/v1/ingestion/documents",
        json={"content": "", "metadata": {"source": "error-test"}}
    )
    
    # Should still return 202 as processing is async
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    doc_id = response_data["document_id"]
    
    # Wait and verify document was not created
    await asyncio.sleep(2)  # Give some time for processing
    doc = await graph_repository.get_document(doc_id)
    assert doc is None, "Empty document should not be created" 