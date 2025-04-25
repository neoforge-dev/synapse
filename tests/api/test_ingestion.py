import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock, MagicMock

from graph_rag.api.schemas import DocumentIngestRequest, IngestionResponse
from graph_rag.services.ingestion import IngestionService
from graph_rag.api.routers.ingestion import process_document_with_service


@pytest.mark.asyncio
async def test_ingest_document_endpoint(
    test_client: AsyncClient, 
    mock_ingestion_service: AsyncMock
):
    """Test the document ingestion endpoint schedules a background task."""
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
    test_client: AsyncClient, mock_ingestion_service: AsyncMock
):
    """Test that endpoint handles validation errors before task scheduling."""
    # Invalid payload (e.g., missing content)
    invalid_payload = {"metadata": {"source": "error_test"}}
    
    response = await test_client.post("/api/v1/ingestion/documents", json=invalid_payload)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY