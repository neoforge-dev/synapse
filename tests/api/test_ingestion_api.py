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

# Fixture for mocking background tasks (adjust target path as needed)
@pytest.fixture
def mock_background_tasks():
    with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
        yield mock_add_task

# --- Test Cases ---
# Basic success/generation tests are covered by tests/api/test_ingestion.py
# Keep tests focusing on specific API model validation and background task scheduling

@pytest.mark.asyncio
async def test_ingest_document_empty_content(test_client: AsyncClient):
    """Test ingestion attempt with empty content string (should fail validation)."""
    payload = {
        "content": "", # Empty content
        "metadata": {"source": "api-test-empty"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    # We expect a 422 from FastAPI's validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    # Check for Pydantic v2 string_too_short error type
    assert any("content" in err.get("loc", []) and err.get("type") == "string_too_short" for err in response_data.get("detail", []))

@pytest.mark.asyncio
async def test_ingest_document_missing_content(test_client: AsyncClient):
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
async def test_ingest_document_invalid_metadata_type(test_client: AsyncClient):
    """Test ingestion with metadata that is not a dictionary."""
    payload = {
        "content": "Valid content.",
        "metadata": ["not", "a", "dictionary"] # Invalid type
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("metadata" in err.get("loc", []) and ("dict_type" in err.get("type", "") or "is_instance_of" in err.get("type", "")) for err in response_data.get("detail", []))

# --- Background Processing Tests ---

@pytest.fixture
def mock_process_document_task(): # Separate mock for the task function itself
    # Patch the correct location where the background task function is defined
    with patch("graph_rag.api.routers.ingestion.process_document_with_service") as mock_task_func:
        yield mock_task_func

@pytest.mark.asyncio
async def test_background_processing_success(test_client: AsyncClient, mock_background_tasks, mock_process_document_task, mock_ingestion_service: AsyncMock):
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
    args, kwargs = mock_background_tasks.call_args

    # Verify the correct function was passed to add_task
    # The first argument to add_task should be the task function itself
    assert args[0] is mock_process_document_task

    # Verify the arguments passed *to* the background task function
    # These are passed as kwargs to add_task
    assert kwargs['document_id'] == response_data["document_id"]
    assert kwargs['content'] == payload["content"]
    assert kwargs['metadata'] == payload["metadata"]
    # Ensure the mock ingestion service instance from the dependency override is passed
    assert kwargs['ingestion_service'] is mock_ingestion_service

# --- Edge Cases ---

@pytest.mark.asyncio
async def test_ingest_large_document(test_client: AsyncClient, mock_background_tasks):
    """Test ingestion of a large document (API acceptance test)."""
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
async def test_ingest_document_with_special_chars(test_client: AsyncClient, mock_background_tasks):
    """Test ingestion of document with special characters (API acceptance test)."""
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
        ingest_doc(test_client, f"Document {i}") for i in range(5)
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