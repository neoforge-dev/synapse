import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock, call
import logging
import asyncio
from fastapi import FastAPI
from fastapi import BackgroundTasks
from graph_rag.services.ingestion import IngestionService, process_document_with_service
from graph_rag.core.models import Document

# Assuming your FastAPI app instance is accessible for testing
# If main.app isn't directly importable, adjust how you get the app
# Might need a fixture in conftest.py to provide the app instance
# from graph_rag.api.main import app # Remove direct app import

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# Fixture for mocking background tasks (adjust target path as needed)
# @pytest.fixture
# def mock_background_tasks():
#     mock = MagicMock(spec=BackgroundTasks)
#     mock.add_task = MagicMock() # Mock the add_task method
#     return mock

# Mock the background task function itself
@pytest.fixture
def mock_process_document_task():
    # Use AsyncMock if process_document_with_service is async
    return AsyncMock(name="process_document_with_service") 

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

@pytest.mark.asyncio
async def test_background_processing_success(
    test_client: AsyncClient,
    mock_process_document_task: AsyncMock,
    mock_ingestion_service: AsyncMock,
    mock_background_tasks: AsyncMock,
):
    """Test successful scheduling of background processing."""
    payload = {
        "content": "Test document for background processing.",
        "metadata": {"source": "test-bg"}
    }

    # Reset mocks before the call
    mock_process_document_task.reset_mock()
    mock_background_tasks.add_task.reset_mock()

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED # Expect 202
    response_data = response.json()
    assert response_data["status"] == "processing"
    assert "task_id" in response_data
    doc_id = response_data["document_id"]
    assert doc_id.startswith("doc-")

    # Verify BackgroundTasks.add_task was called with our mocked task function
    # and the correct arguments (service, doc_id, content, metadata)
    mock_background_tasks.add_task.assert_called_once()
    # Get the actual arguments add_task was called with
    args, kwargs = mock_background_tasks.add_task.call_args
    # The first argument should be the task function (our mock)
    assert args[0] == mock_process_document_task
    # The subsequent arguments should be the ones passed to the task
    assert args[1] == mock_ingestion_service  # The IngestionService instance
    assert args[2] == doc_id                  # The generated document ID
    assert args[3] == payload["content"]      # The document content
    assert args[4] == payload["metadata"]     # The document metadata

@pytest.mark.asyncio
async def test_ingest_large_document(test_client: AsyncClient):
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
    assert response_data["document_id"].startswith("doc-")

    # No assertion on mock_process_document_task here

@pytest.mark.asyncio
async def test_ingest_document_with_special_chars(test_client: AsyncClient):
    """Test ingestion of document with special characters (API acceptance test)."""
    special_content = "Test document with special chars: \\n\\t\\r\\b\\f\\\"\\\'" # Corrected escaping again
    payload = {
        "content": special_content,
        "metadata": {"source": "test-special"}
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["status"] == "processing"
    assert response_data["document_id"].startswith("doc-")

    # No assertion on mock_process_document_task here

# --- Concurrent Processing ---

@pytest.mark.asyncio
async def test_concurrent_ingestion(test_client: AsyncClient):
    """Test concurrent ingestion requests to the API endpoint."""

    async def ingest_doc(client: AsyncClient, content: str):
        payload = {
            "content": content,
            "metadata": {"source": "test-concurrent"}
        }
        return await client.post("/api/v1/ingestion/documents", json=payload)

    # Reset mock before calls - Removed, handled by fixture scope now
    # mock_process_document_task.reset_mock() # Remove this line

    # Make multiple concurrent requests
    tasks = [ingest_doc(test_client, f"Document {i}") for i in range(3)]
    responses = await asyncio.gather(*tasks)

    # Check responses
    doc_ids = set()
    for response in responses:
        assert response.status_code == status.HTTP_202_ACCEPTED
        response_data = response.json()
        assert response_data["status"] == "processing"
        doc_id = response_data["document_id"]
        assert doc_id.startswith("doc-")
        doc_ids.add(doc_id)

    # Ensure unique document IDs were generated
    assert len(doc_ids) == 3

    # We don't assert mock_process_document_task call count here,
    # as individual calls might overlap or finish at different times.
    # The main check is that the API accepted all requests.

# TODO: Add tests that mock dependencies (doc_processor, extractor, builder)
#       within the process_document_background task itself, if needed for finer-grained checks.
#       This might require more intricate patching or dependency injection into the task. 