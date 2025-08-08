import asyncio
import json
import os

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_search_stream_keyword_flag_enabled(app, test_client: AsyncClient, mock_graph_rag_engine: AsyncMock):
    os.environ["SYNAPSE_ENABLE_KEYWORD_STREAMING"] = "true"

    async def gen():
        from graph_rag.core.interfaces import ChunkData
        yield ChunkData(id="k1", text="kw1", document_id="d1")

    mock_graph_rag_engine.stream_context = AsyncMock(return_value=gen())

    payload = {"query": "kw", "search_type": "keyword", "limit": 1}
    results = []
    async with test_client.stream("POST", "/api/v1/search/query?stream=true", json=payload) as resp:
        assert resp.status_code == 200
        async for line in resp.aiter_lines():
            if line:
                results.append(json.loads(line))

    assert results and results[0]["chunk"]["id"] == "k1"

    # Cleanup env
    del os.environ["SYNAPSE_ENABLE_KEYWORD_STREAMING"]
