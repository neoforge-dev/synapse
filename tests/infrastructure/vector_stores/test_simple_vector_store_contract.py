import pytest
from graph_rag.api.dependencies import MockEmbeddingService
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
from graph_rag.core.interfaces import ChunkData, SearchResultData


@pytest.mark.asyncio
async def test_simple_vector_store_search_contract():
    emb = MockEmbeddingService(dimension=8)
    store = SimpleVectorStore(embedding_service=emb)

    # Ingest two chunks without embeddings to exercise embedding path
    chunks = [
        ChunkData(id="c1", text="alpha beta", document_id="d1"),
        ChunkData(id="c2", text="beta gamma", document_id="d2"),
    ]
    await store.ingest_chunks(chunks)

    # Vector search path
    results = await store.search("alpha", top_k=5, search_type="vector")
    assert isinstance(results, list)
    assert all(isinstance(r, SearchResultData) for r in results)
    assert all(isinstance(r.score, float) for r in results)
    assert all(isinstance(r.chunk.id, str) and isinstance(r.chunk.text, str) for r in results)

    # Keyword search path
    kw_results = await store.search("beta", top_k=5, search_type="keyword")
    assert isinstance(kw_results, list)
    assert all(isinstance(r, SearchResultData) for r in kw_results)
    # Score is float and chunk present
    assert all(isinstance(r.score, float) for r in kw_results)
