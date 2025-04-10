import pytest
from fastapi.testclient import TestClient
# Remove app import if not directly used for fixture creation
# from graph_rag.api.main import app 
from httpx import AsyncClient, Response, ASGITransport
from fastapi import status
from unittest.mock import AsyncMock
from graph_rag.domain.models import Document
import uuid
from datetime import datetime, timezone

# Remove the locally defined fixture - use the one from conftest.py
# @pytest.fixture
# async def test_client() -> AsyncClient:
#     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
#         yield client

@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient, mock_graph_rag_engine: AsyncMock, mock_neo4j_driver: AsyncMock):
    """Test the health check endpoint."""
    # Ensure mocks are injected by adding them to the signature
    response = await test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_create_document(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test creating a document through the API."""
    doc_data = {
        "id": "test_doc_api_1",
        "content": "This is a test document from the API",
        "metadata": {"source": "api_test"}
    }
    
    # Setup mock behavior for the repository interaction used by the endpoint
    mock_graph_repo.add_document.reset_mock()
    mock_graph_repo.add_document.return_value = None # add_document likely returns None on success

    response = await test_client.post("/api/v1/documents/", json=doc_data)
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert "id" in response_data
    created_id = response_data["id"]
    # assert created_id == doc_data["id"] # Old assertion - ID is now generated
    # Assert that the created_id is a valid UUID string
    try:
        uuid.UUID(created_id, version=4)
        assert True
    except ValueError:
        assert False, f"Returned ID '{created_id}' is not a valid UUID4"

    # Verify the correct repository method was called
    # Check that add_document was called once
    mock_graph_repo.add_document.assert_awaited_once()
    # Inspect the arguments passed to the mock
    call_args = mock_graph_repo.add_document.call_args
    assert isinstance(call_args.args[0], Document) # Check if a Document object was passed
    assert call_args.args[0].content == doc_data["content"] # Check content
    assert call_args.args[0].metadata == doc_data["metadata"] # Check metadata

@pytest.mark.asyncio
async def test_get_document(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test retrieving a document through the API."""
    doc_id = "test_doc_api_2"
    doc_content = "This is another test document from the API"
    doc_metadata = {"retrieval_test": True}
    
    # Mock the specific method called by the GET endpoint in the document router
    # Assume it's get_document_by_id
    mock_graph_repo.get_document_by_id.reset_mock()
    
    # Prepare the mock return value (the domain object)
    mock_return_document = Document(
        id=doc_id,
        type="Document",
        content=doc_content,
        metadata=doc_metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Configure the mock to return the awaitable result directly
    # instead of using side_effect for simple return cases.
    mock_graph_repo.get_document.return_value = mock_return_document
    mock_graph_repo.get_document.side_effect = None

    # Reset and configure get_document_by_id just in case, although it seems unused by the endpoint
    mock_graph_repo.get_document_by_id.reset_mock()
    mock_graph_repo.get_document_by_id.return_value = mock_return_document
    mock_graph_repo.get_document_by_id.side_effect = None

    response = await test_client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == doc_id
    assert response_data["content"] == doc_content
    # Assuming DocumentResponse maps metadata correctly
    assert response_data["metadata"] == doc_metadata

# Remove the hallucinated function below
# @pytest.mark.asyncio
# def test_ingest_document_endpoint(
#     test_client: AsyncClient,
#     mock_graph_repo: AsyncMock,
#     mock_graph_rag_engine: AsyncMock,
#     mock_neo4j_driver: AsyncMock
# ):
#     # Implementation of the test_ingest_document_endpoint function
#     # This function is not provided in the original file or the code block
#     # It's assumed to exist as it's called in the test_ingest_document_endpoint function
#     pass 