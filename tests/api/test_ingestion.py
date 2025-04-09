import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

from graph_rag.api.schemas import DocumentIngestRequest, IngestionResponse
from graph_rag.domain.models import Document


@pytest.fixture
def mock_ingestion_service():
    """Fixture to mock the IngestionService."""
    with patch("graph_rag.api.routers.ingestion.get_ingestion_service") as mock_get_service:
        mock_instance = AsyncMock()
        mock_instance.ingest_document_background.return_value = ("doc_id_123", "task_id_456")
        mock_get_service.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_ingest_document_endpoint(
    test_client: AsyncClient,
    mock_ingestion_service: AsyncMock
):
    """Test the document ingestion endpoint."""
    ingest_data = DocumentIngestRequest(
        document_id="test_doc_ingest_1",
        content="This is a test document to ingest.",
        metadata={"source": "ingestion_test"}
    )
    request_payload = {
        "document_id": ingest_data.document_id,
        "content": ingest_data.content,
        "metadata": ingest_data.metadata
    }

    response = await test_client.post("/api/v1/ingestion/documents", json=request_payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data.get("document_id") == "test_doc_ingest_1"
    assert response_data.get("status") == "processing"
    assert "task_id" in response_data


@pytest.mark.asyncio
async def test_ingest_document_handles_endpoint_error(
    test_client: AsyncClient,
    mock_ingestion_service: AsyncMock
):
    """Test that the ingestion endpoint properly handles immediate errors (e.g., during request validation or before queuing task)."""
    with patch("graph_rag.api.routers.ingestion.get_ingestion_service", side_effect=Exception("Service unavailable")):

        response = await test_client.post(
            "/api/v1/ingestion/documents",
            json={
                "content": "Test document content",
                "metadata": {}
            }
        )

    assert response.status_code >= 500
    data = response.json()
    assert "detail" in data