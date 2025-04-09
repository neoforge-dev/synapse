import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock
import logging
import asyncio

# Assuming your FastAPI app instance is accessible for testing
# If main.app isn't directly importable, adjust how you get the app
# Might need a fixture in conftest.py to provide the app instance
# from graph_rag.api.main import app # Remove direct app import

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_graph_repository():
    """Fixture to mock the GraphRepository."""
    # Update patch target if necessary (check where GraphRepository is used)
    with patch("graph_rag.api.routers.ingestion.get_graph_repository") as mock_get_repo:
        mock_instance = AsyncMock()
        mock_get_repo.return_value = mock_instance
        yield mock_instance

# Fixture for mocking background tasks (adjust target path as needed)
@pytest.fixture
def mock_background_tasks():
    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        yield mock_add_task

# --- Test Cases ---

@pytest.mark.asyncio
async def test_ingest_document_success(test_client: AsyncClient, mock_graph_repository: AsyncMock, mock_background_tasks):
    """Test successful ingestion of a document via the API using the shared test_client."""
    payload = {
        "content": "This is a test document about Alice and Bob.",
        "metadata": {"source": "api-test", "category": "testing"},
        "document_id": "test-doc-api-01"
    }

    # Use the test_client fixture provided by conftest.py
    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["message"] == "Document ingestion started"
    assert response_data["document_id"] == "test-doc-api-01"
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    mock_background_tasks.assert_called_once() # Verify background task was added

@pytest.mark.asyncio
async def test_ingest_document_generate_id(test_client: AsyncClient, mock_graph_repository: AsyncMock, mock_background_tasks):
    """Test ingestion when document_id is not provided (should be generated)."""
    payload = {
        "content": "Another test document.",
        "metadata": {"source": "api-test-genid"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["message"] == "Document ingestion started"
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    assert response_data["document_id"].startswith("doc-")
    mock_background_tasks.assert_called_once()

@pytest.mark.asyncio
async def test_ingest_document_empty_content(test_client: AsyncClient, mock_graph_repository: AsyncMock):
    """Test ingestion attempt with empty content string."""
    payload = {
        "content": "", # Empty content
        "metadata": {"source": "api-test-empty"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_data = response.json()
    assert "detail" in response_data

@pytest.mark.asyncio
async def test_ingest_document_missing_content(test_client: AsyncClient, mock_graph_repository: AsyncMock):
    """Test ingestion request missing the required 'content' field."""
    payload = {
        "metadata": {"source": "api-test-missing"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("content" in err.get("loc", []) and "missing" in err.get("type", "") for err in response_data.get("detail", []))

@pytest.mark.asyncio
async def test_ingest_document_invalid_metadata_type(test_client: AsyncClient): # Removed mock repo as it's not used
    """Test ingestion with metadata that is not a dictionary."""
    payload = {
        "content": "Valid content.",
        "metadata": ["not", "a", "dictionary"] # Invalid type
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("metadata" in err.get("loc", []) and "dict_type" in err.get("type", "") for err in response_data.get("detail", []))

# --- Background Processing Tests ---
# Note: Testing the *actual* execution requires more complex setup (e.g., running worker)
# These tests verify the API endpoint schedules the task correctly.

@pytest.fixture
def mock_process_document_task(): # Separate mock for the task function itself
    with patch("graph_rag.api.routers.ingestion.process_document_background") as mock_task_func:
        yield mock_task_func

@pytest.mark.asyncio
async def test_background_processing_success(test_client: AsyncClient, mock_background_tasks, mock_process_document_task):
    """Test successful scheduling of background processing."""
    payload = {
        "content": "Test document for background processing.",
        "metadata": {"source": "test-bg"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["status"] == "processing"
    assert "task_id" in response_data

    # Verify BackgroundTasks.add_task was called
    mock_background_tasks.assert_called_once()
    # Verify the correct function was passed to add_task
    args, kwargs = mock_background_tasks.call_args
    assert args[0] == mock_process_document_task # Check if the mocked task func was the target
    # Optionally, check args passed to the background task function
    assert kwargs['document_id'] == response_data["document_id"]
    assert kwargs['content'] == payload["content"]

# Background error handling is tricky to test directly here without executing the task.
# We assume the API endpoint itself works; error logging happens within process_document_background.
# @pytest.mark.asyncio
# async def test_background_processing_error_handling(test_client: AsyncClient, mock_background_tasks, mock_process_document_task):
#     """Test API response when background task might error (logging happens in task)."""
#     mock_process_document_task.side_effect = Exception("Simulated background error")

#     payload = {
#         "content": "Test document with potential processing error.",
#         "metadata": {"source": "test-error"}
#     }

#     response = await test_client.post("/api/v1/ingestion/documents", json=payload)

#     # API should still return 202 as the error is in background
#     assert response.status_code == status.HTTP_202_ACCEPTED
#     mock_background_tasks.assert_called_once()
#     # Verification of logging would happen if the task actually ran & raised.

# --- Edge Cases ---

@pytest.mark.asyncio
async def test_ingest_large_document(test_client: AsyncClient, mock_graph_repository: AsyncMock, mock_background_tasks):
    """Test ingestion of a large document."""
    large_content = "Test " * 10000  # ~50KB document
    payload = {
        "content": large_content,
        "metadata": {"source": "test-large"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    assert response_data["document_id"].startswith("doc-")
    mock_background_tasks.assert_called_once()

@pytest.mark.asyncio
async def test_ingest_document_with_special_chars(test_client: AsyncClient, mock_graph_repository: AsyncMock, mock_background_tasks):
    """Test ingestion of document with special characters."""
    special_content = "Test document with special chars: \n\t\r\b\f\\\"'"
    payload = {
        "content": special_content,
        "metadata": {"source": "test-special"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    assert response_data["document_id"].startswith("doc-")
    mock_background_tasks.assert_called_once()

# --- Concurrent Processing ---

@pytest.mark.asyncio
async def test_concurrent_ingestion(test_client: AsyncClient, mock_background_tasks):
    """Test concurrent ingestion requests to the API endpoint."""

    async def ingest_doc(client: AsyncClient, content: str):
        payload = {
            "content": content,
            "metadata": {"source": "test-concurrent"}
        }
        return await client.post("/api/v1/ingestion/documents", json=payload)

    # Create multiple ingestion tasks
    tasks = [
        ingest_doc(test_client, f"Document {i}") for i in range(5) # Pass test_client
    ]

    # Run all tasks concurrently
    responses = await asyncio.gather(*tasks)

    # Verify all requests were accepted
    for response in responses:
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["status"] == "processing"
        assert "task_id" in response_data

    # Verify background tasks were added for each request
    assert mock_background_tasks.call_count == 5

# TODO: Add tests that mock dependencies (doc_processor, extractor, builder)
#       within the process_document_background task itself, if needed for finer-grained checks.
#       This might require more intricate patching or dependency injection into the task. 