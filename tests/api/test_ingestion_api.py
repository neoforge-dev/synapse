import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock
import logging

# Assuming your FastAPI app instance is accessible for testing
# If main.app isn't directly importable, adjust how you get the app
# Might need a fixture in conftest.py to provide the app instance
from graph_rag.api.main import app 

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio 

@pytest.fixture(scope="module")
async def async_client() -> AsyncClient:
    """Provides an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

@pytest.fixture
def mock_graph_repository():
    """Fixture to mock the GraphRepository."""
    with patch("graph_rag.infrastructure.repositories.graph_repository.GraphRepository") as mock_repo_cls:
        mock_instance = AsyncMock()
        mock_repo_cls.return_value = mock_instance
        yield mock_instance

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_ingest_document_success(mock_graph_repository):
    """Test successful ingestion of a document via the API."""
    payload = {
        "content": "This is a test document about Alice and Bob.",
        "metadata": {"source": "api-test", "category": "testing"},
        "document_id": "test-doc-api-01"
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["message"] == "Document ingestion started"
    assert response_data["document_id"] == "test-doc-api-01"
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    # TODO: Verify side effects (e.g., check mock graph/vector stores if possible 
    #       or use dependency overrides during testing)

@pytest.mark.asyncio
async def test_ingest_document_generate_id(mock_graph_repository):
    """Test ingestion when document_id is not provided (should be generated)."""
    payload = {
        "content": "Another test document.",
        "metadata": {"source": "api-test-genid"}
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["message"] == "Document ingestion started"
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    assert response_data["document_id"].startswith("doc-")

@pytest.mark.asyncio
async def test_ingest_document_empty_content(mock_graph_repository):
    """Test ingestion attempt with empty content string."""
    payload = {
        "content": "", # Empty content
        "metadata": {"source": "api-test-empty"}
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_data = response.json()
    assert "detail" in response_data

@pytest.mark.asyncio
async def test_ingest_document_missing_content(mock_graph_repository):
    """Test ingestion request missing the required 'content' field."""
    payload = { 
        "metadata": {"source": "api-test-missing"}
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("content" in err.get("loc", []) and "missing" in err.get("type", "") for err in response_data.get("detail", []))

@pytest.mark.asyncio
async def test_ingest_document_invalid_metadata_type(async_client: AsyncClient):
    """Test ingestion with metadata that is not a dictionary."""
    payload = { 
        "content": "Valid content.",
        "metadata": ["not", "a", "dictionary"] # Invalid type
    }
    
    response = await async_client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("metadata" in err.get("loc", []) and "dict_type" in err.get("type", "") for err in response_data.get("detail", []))

# --- Background Processing Tests ---

@pytest.mark.asyncio
async def test_background_processing_success(async_client: AsyncClient):
    """Test successful background processing of a document."""
    with patch("graph_rag.api.routers.ingestion.process_document") as mock_process:
        mock_process.return_value = None  # Background task doesn't return
        
        payload = {
            "content": "Test document for background processing.",
            "metadata": {"source": "test-bg"}
        }
        
        response = await async_client.post("/api/v1/ingestion/documents", json=payload)
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["status"] == "processing"
        assert "task_id" in response_data
        
        # Verify background task was scheduled
        mock_process.assert_called_once()

@pytest.mark.asyncio
async def test_background_processing_error_handling(async_client: AsyncClient):
    """Test error handling in background processing."""
    with patch("graph_rag.api.routers.ingestion.process_document") as mock_process:
        mock_process.side_effect = Exception("Test background error")
        
        payload = {
            "content": "Test document with processing error.",
            "metadata": {"source": "test-error"}
        }
        
        response = await async_client.post("/api/v1/ingestion/documents", json=payload)
        
        # API should still return 202 as the error is in background
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["status"] == "processing"
        
        # Verify error was logged
        assert any(
            "Test background error" in record.getMessage()
            for record in logging.getLogger("graph_rag.api.routers.ingestion").records
        )

# --- Edge Cases ---

@pytest.mark.asyncio
async def test_ingest_large_document(mock_graph_repository):
    """Test ingestion of a large document."""
    large_content = "Test " * 10000  # 50KB document
    payload = {
        "content": large_content,
        "metadata": {"source": "test-large"}
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    assert response_data["document_id"].startswith("doc-")

@pytest.mark.asyncio
async def test_ingest_document_with_special_chars(mock_graph_repository):
    """Test ingestion of document with special characters."""
    special_content = "Test document with special chars: \n\t\r\b\f\\\"'"
    payload = {
        "content": special_content,
        "metadata": {"source": "test-special"}
    }
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    assert response_data["document_id"].startswith("doc-")

# --- Concurrent Processing ---

@pytest.mark.asyncio
async def test_concurrent_ingestion(async_client: AsyncClient):
    """Test concurrent ingestion of multiple documents."""
    import asyncio
    
    async def ingest_doc(content: str):
        payload = {
            "content": content,
            "metadata": {"source": "test-concurrent"}
        }
        return await async_client.post("/api/v1/ingestion/documents", json=payload)
    
    # Create multiple ingestion tasks
    tasks = [
        ingest_doc(f"Document {i}") for i in range(5)
    ]
    
    # Run all tasks concurrently
    responses = await asyncio.gather(*tasks)
    
    # Verify all requests were accepted
    for response in responses:
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["status"] == "processing"
        assert "task_id" in response_data

# TODO: Add tests that mock dependencies (doc_processor, extractor, builder) 
#       to verify they are called correctly and handle their potential errors.
#       This requires using FastAPI's dependency overrides feature. 