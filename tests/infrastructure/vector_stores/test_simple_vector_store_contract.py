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
    assert all(
        isinstance(r.chunk.id, str) and isinstance(r.chunk.text, str) for r in results
    )

    # Keyword search path
    kw_results = await store.search("beta", top_k=5, search_type="keyword")
    assert isinstance(kw_results, list)
    assert all(isinstance(r, SearchResultData) for r in kw_results)
    # Score is float and chunk present
    assert all(isinstance(r.score, float) for r in kw_results)


@pytest.mark.asyncio
async def test_faiss_vector_store_persistence(tmp_path):
    from graph_rag.infrastructure.vector_stores.faiss_vector_store import (
        FaissVectorStore,
    )

    dim = 8
    path = tmp_path / "faiss"
    store = FaissVectorStore(path=str(path), embedding_dimension=dim)

    # Prepare two chunks with explicit embeddings
    emb_a = [1.0] + [0.0] * (dim - 1)
    emb_b = [0.0, 1.0] + [0.0] * (dim - 2)
    chunks = [
        ChunkData(id="c1", text="alpha", document_id="d1", embedding=emb_a),
        ChunkData(id="c2", text="beta", document_id="d2", embedding=emb_b),
    ]
    await store.add_chunks(chunks)

    # Query with a vector close to c1
    results = await store.search_similar_chunks(emb_a, limit=1)
    assert results and results[0].chunk.id == "c1"

    # Recreate store from disk and query again
    store2 = FaissVectorStore(path=str(path), embedding_dimension=dim)
    results2 = await store2.search_similar_chunks(emb_a, limit=1)
    assert results2 and results2[0].chunk.id == "c1"

    # Meta file should contain version key set to 2
    meta = (path / "meta.json").read_text()
    import json as _json

    meta_obj = _json.loads(meta)
    assert meta_obj.get("version") == 2


@pytest.mark.asyncio
async def test_faiss_vector_store_delete_and_rebuild(tmp_path):
    from graph_rag.infrastructure.vector_stores.faiss_vector_store import (
        FaissVectorStore,
    )

    dim = 8
    path = tmp_path / "faiss_del"
    store = FaissVectorStore(path=str(path), embedding_dimension=dim)

    emb_a = [1.0] + [0.0] * (dim - 1)
    emb_b = [0.0, 1.0] + [0.0] * (dim - 2)
    chunks = [
        ChunkData(id="c1", text="alpha", document_id="d1", embedding=emb_a),
        ChunkData(id="c2", text="beta", document_id="d2", embedding=emb_b),
    ]
    await store.add_chunks(chunks)

    # Ensure both are searchable initially
    res_a = await store.search_similar_chunks(emb_a, limit=2)
    assert any(r.chunk.id == "c1" for r in res_a)
    assert any(r.chunk.id == "c2" for r in res_a)

    # Delete c1 and verify it's removed
    await store.delete_chunks(["c1"])
    res_after = await store.search_similar_chunks(emb_a, limit=2)
    assert not any(r.chunk.id == "c1" for r in res_after)
    assert any(r.chunk.id == "c2" for r in res_after)

    # Reload from disk and verify deletion persists
    store2 = FaissVectorStore(path=str(path), embedding_dimension=dim)
    res_after_reload = await store2.search_similar_chunks(emb_a, limit=2)
    assert not any(r.chunk.id == "c1" for r in res_after_reload)
    # c2 should still be present
    assert any(r.chunk.id == "c2" for r in res_after_reload)
