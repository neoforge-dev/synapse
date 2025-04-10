import pytest
from fastapi.testclient import TestClient
from graph_rag.api.main import app
from httpx import AsyncClient, Response, ASGITransport
from fastapi import status
from unittest.mock import AsyncMock

@pytest.fixture
async def test_client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_health_check(test_client: AsyncClient):
    """Test the health check endpoint."""
    response = await test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_create_document(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test creating a document through the API."""
    doc_data = {
        "id": "test_doc_api_1",
        "content": "This is a test document from the API",
        "metadata": {"source": "api_test"}
    }
    
    async def mock_save(doc):
        return doc.id
    mock_graph_repo.save_document.side_effect = mock_save
    mock_graph_repo.reset_mock()
    mock_graph_repo.save_document.side_effect = mock_save

    response = await test_client.post("/api/v1/documents/", json=doc_data)
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert "id" in response_data
    created_id = response_data["id"]

    mock_graph_repo.save_document.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_document(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test retrieving a document through the API."""
    doc_id = "test_doc_api_2"
    doc_content = "This is another test document from the API"
    doc_metadata = {"retrieval_test": True}
    
    from graph_rag.domain.models import Document
    from datetime import datetime, timezone
    async def mock_get(id_to_get):
        if id_to_get == doc_id:
            return Document(
                id=doc_id, 
                content=doc_content, 
                metadata=doc_metadata,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
                )
        return None
    mock_graph_repo.get_document.side_effect = mock_get
    mock_graph_repo.reset_mock()
    mock_graph_repo.get_document.side_effect = mock_get
    
    response = await test_client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == doc_id
    assert data["content"] == doc_content
    assert data["metadata"] == doc_metadata
    mock_graph_repo.get_document.assert_awaited_once_with(doc_id) 