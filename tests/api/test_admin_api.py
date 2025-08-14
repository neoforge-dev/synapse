from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_vector_stats_endpoint(test_client: AsyncClient, mock_vector_store: AsyncMock):
    mock_vector_store.stats.return_value = {"vectors": 42, "rows": 42}
    resp = await test_client.get("/api/v1/admin/vector/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("vectors") == 42


async def test_vector_rebuild_endpoint(test_client: AsyncClient, mock_vector_store: AsyncMock):
    mock_vector_store.rebuild_index.return_value = None
    resp = await test_client.post("/api/v1/admin/vector/rebuild")
    assert resp.status_code == 202
    body = resp.json()
    assert body.get("status") == "ok"


async def test_integrity_check_endpoint(test_client: AsyncClient, mock_graph_repo: AsyncMock, mock_vector_store: AsyncMock):
    # Mock graph repo count
    mock_graph_repo.execute_query.return_value = [{"n": 10}]
    mock_vector_store.stats.return_value = {"vectors": 8}
    resp = await test_client.get("/api/v1/admin/integrity/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("graph_chunks") == 10
    assert data.get("vectors") == 8
    assert data.get("warnings")
