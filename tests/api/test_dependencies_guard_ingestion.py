import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingestion_requires_ingestion_service(app, test_client: AsyncClient):
    # Clear override for get_ingestion_service to hit main.py getter
    from graph_rag.api.main import get_ingestion_service as main_get_ingestion

    if main_get_ingestion in app.dependency_overrides:
        del app.dependency_overrides[main_get_ingestion]

    # Remove service from state to trigger 503
    if hasattr(app.state, "ingestion_service"):
        app.state.ingestion_service = None

    payload = {"content": "hello world", "metadata": {}}
    resp = await test_client.post("/api/v1/ingestion/documents", json=payload)
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "ingestion service" in resp.json().get("detail", "").lower()
