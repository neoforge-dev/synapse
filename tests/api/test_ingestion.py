import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

from graph_rag.api.main import app
from graph_rag.services.ingestion import IngestionResult


@pytest.fixture
def mock_ingestion_service():
    """Fixture to mock the IngestionService."""
    with patch("graph_rag.api.routers.ingestion.IngestionService") as mock_service_cls:
        # Set up the mock instance and its ingest_document method
        mock_instance = AsyncMock()
        mock_service_cls.return_value = mock_instance
        
        # Configure the return value for ingest_document
        mock_instance.ingest_document.return_value = IngestionResult(
            document_id="test-doc-id",
            chunk_ids=["chunk1", "chunk2", "chunk3"]
        )
        
        yield mock_instance


@pytest.mark.asyncio
async def test_ingest_document_endpoint(mock_ingestion_service):
    """Test the document ingestion endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingestion/document",
            json={
                "content": "Test document content",
                "metadata": {"source": "test"},
                "max_tokens_per_chunk": 10
            }
        )
    
    # Verify response
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["document_id"] == "test-doc-id"
    assert len(data["chunk_ids"]) == 3
    assert data["num_chunks"] == 3
    
    # Verify the service was called with correct arguments
    mock_ingestion_service.ingest_document.assert_called_once()
    call_args = mock_ingestion_service.ingest_document.call_args[1]
    assert call_args["content"] == "Test document content"
    assert call_args["metadata"] == {"source": "test"}
    assert call_args["max_tokens_per_chunk"] == 10


@pytest.mark.asyncio
async def test_ingest_document_handles_errors(mock_ingestion_service):
    """Test that the ingestion endpoint properly handles errors."""
    # Configure the mock to raise an exception
    mock_ingestion_service.ingest_document.side_effect = Exception("Test error")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ingestion/document",
            json={
                "content": "Test document content",
                "metadata": {}
            }
        )
    
    # Verify response
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert "detail" in data 