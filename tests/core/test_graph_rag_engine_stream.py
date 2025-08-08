import asyncio
import pytest
from unittest.mock import AsyncMock

from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.core.interfaces import (
    SearchResultData,
    ChunkData,
    GraphRepository,
    VectorStore,
    EntityExtractor,
)


@pytest.mark.asyncio
async def test_stream_context_vector_returns_results_in_order():
    # Arrange: mock dependencies
    mock_graph_repo = AsyncMock(spec=GraphRepository)
    mock_vector_store = AsyncMock(spec=VectorStore)
    mock_entity_extractor = AsyncMock(spec=EntityExtractor)

    # Prepare vector store to return two results
    r1 = SearchResultData(
        chunk=ChunkData(id="c1", text="chunk1", document_id="d1", embedding=None),
        score=0.9,
        document=None,
    )
    r2 = SearchResultData(
        chunk=ChunkData(id="c2", text="chunk2", document_id="d2", embedding=None),
        score=0.8,
        document=None,
    )
    mock_vector_store.search = AsyncMock(return_value=[r1, r2])

    engine = SimpleGraphRAGEngine(
        graph_store=mock_graph_repo,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
    )

    # Act: collect from async generator
    results = []
    async for item in engine.stream_context("find me", search_type="vector", limit=10):
        results.append(item)

    # Assert
    assert len(results) == 2
    assert results[0].chunk.id == "c1"
    assert results[1].chunk.id == "c2"
    mock_vector_store.search.assert_awaited_once_with(
        "find me", top_k=10, search_type="vector"
    )
