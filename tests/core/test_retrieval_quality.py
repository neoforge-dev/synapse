import pytest

from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.core.interfaces import (
    ChunkData,
    EntityExtractor as EntityExtractorProto,
    ExtractionResult,
    GraphRepository as GraphRepositoryProto,
    SearchResultData,
    VectorStore as VectorStoreProto,
)


class _StubVectorStore(VectorStoreProto):
    def __init__(self, vector_results, keyword_results):
        self._vec = vector_results
        self._kw = keyword_results

    async def add_chunks(self, chunks):  # pragma: no cover
        return None

    async def search_similar_chunks(self, query_vector, limit=10, threshold=None):  # pragma: no cover
        return []

    async def get_chunk_by_id(self, chunk_id):  # pragma: no cover
        return None

    async def delete_chunks(self, chunk_ids):  # pragma: no cover
        return None

    async def delete_store(self):  # pragma: no cover
        return None

    async def search(self, query_text: str, top_k: int = 5, search_type: str = "vector"):
        data = self._kw if search_type == "keyword" else self._vec
        return data[:top_k]


class _StubEntityExtractor(EntityExtractorProto):
    async def extract_from_text(self, text: str, context=None) -> ExtractionResult:
        return ExtractionResult(entities=[], relationships=[])


class _StubGraphRepo(GraphRepositoryProto):
    async def execute_query(self, query, params=None):  # pragma: no cover
        return []

    async def add_document(self, document):  # pragma: no cover
        return None

    async def get_document_by_id(self, document_id):  # pragma: no cover
        return None

    async def get_entity_by_id(self, entity_id):  # pragma: no cover
        return None

    async def add_chunk(self, chunk):  # pragma: no cover
        return None

    async def add_chunks(self, chunks):  # pragma: no cover
        return None

    async def get_chunk_by_id(self, chunk_id):  # pragma: no cover
        return None

    async def get_chunks_by_document_id(self, document_id):  # pragma: no cover
        return []

    async def add_entity(self, entity):  # pragma: no cover
        return None

    async def add_relationship(self, relationship):  # pragma: no cover
        return None

    async def get_neighbors(self, entity_id: str, depth: int = 1):  # pragma: no cover
        return [], []

    async def update_node_properties(self, node_id, properties):  # pragma: no cover
        return None

    async def delete_document(self, document_id: str) -> bool:  # pragma: no cover
        return True

    async def link_chunk_to_entities(self, chunk_id: str, entity_ids):  # pragma: no cover
        return None


def _sr(id_: str, text: str, score: float) -> SearchResultData:
    cd = ChunkData(id=id_, text=text, document_id="doc", metadata={}, score=score)
    return SearchResultData(chunk=cd, score=score)


@pytest.mark.asyncio
async def test_no_answer_min_score_blocks_low_scores():
    vec = [_sr("A", "alpha", 0.2)]
    kw = []
    vs = _StubVectorStore(vec, kw)
    repo = _StubGraphRepo()
    ex = _StubEntityExtractor()
    engine = SimpleGraphRAGEngine(graph_store=repo, vector_store=vs, entity_extractor=ex)

    result = await engine.query("q", config={"k": 3, "include_graph": False, "no_answer_min_score": 0.5})
    assert result is not None
    assert result.relevant_chunks == []
    assert "Could not find relevant information" in result.answer


@pytest.mark.asyncio
async def test_hybrid_blending_and_dedupe():
    vec = [_sr("A", "alpha", 0.4), _sr("B", "bravo", 0.1)]
    kw = [_sr("A", "alpha", 0.1), _sr("C", "charlie", 0.5)]
    vs = _StubVectorStore(vec, kw)
    repo = _StubGraphRepo()
    ex = _StubEntityExtractor()
    engine = SimpleGraphRAGEngine(graph_store=repo, vector_store=vs, entity_extractor=ex)

    chunks, _ = await engine._retrieve_and_build_context(
        "q",
        config={"k": 3, "include_graph": False, "blend_vector_weight": 1.0, "blend_keyword_weight": 1.0},
    )
    ids = [c.chunk.id for c in chunks]
    assert "A" in ids and "C" in ids
    assert ids.count("A") == 1
