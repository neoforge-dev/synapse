import pytest

from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore


class DummyEmbedding:
    def get_embedding_dimension(self):
        return 4

    async def encode(self, texts):
        # simple deterministic embeddings
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]


@pytest.mark.asyncio
async def test_bm25_keyword_search_basic():
    vs = SimpleVectorStore(DummyEmbedding())
    # add simple chunks
    from graph_rag.core.interfaces import ChunkData

    chunks = [
        ChunkData(id="a", text="Apples and oranges", document_id="d1"),
        ChunkData(id="b", text="Bananas and apples", document_id="d2"),
        ChunkData(id="c", text="Grapes only", document_id="d3"),
    ]
    await vs.add_chunks(chunks)

    res = await vs.keyword_search("apples", k=2)
    ids = [r[0].id for r in res]
    assert ids[0] in {"a", "b"}
    assert len(res) == 2


@pytest.mark.asyncio
async def test_bm25_respects_deletion():
    vs = SimpleVectorStore(DummyEmbedding())
    from graph_rag.core.interfaces import ChunkData

    chunks = [
        ChunkData(id="x", text="alpha beta", document_id="dx"),
        ChunkData(id="y", text="beta gamma", document_id="dy"),
    ]
    await vs.add_chunks(chunks)
    await vs.delete_chunks(["x"])
    res = await vs.keyword_search("alpha", k=5)
    assert len(res) == 0
