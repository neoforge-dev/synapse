import pytest

from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.core.interfaces import (
    ChunkData,
    ExtractedEntity,
    ExtractionResult,
    SearchResultData,
)
from graph_rag.core.interfaces import (
    EntityExtractor as EntityExtractorProto,
)
from graph_rag.core.interfaces import (
    GraphRepository as GraphRepositoryProto,
)
from graph_rag.core.interfaces import (
    VectorStore as VectorStoreProto,
)
from graph_rag.domain.models import Entity as DomainEntity


class _StubVectorStore(VectorStoreProto):
    def __init__(self):
        cd = ChunkData(id="c1", text="alpha", document_id="d1", metadata={}, score=0.9)
        self._out = [SearchResultData(chunk=cd, score=0.9)]

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
        return self._out[:top_k]


class _StubEntityExtractor(EntityExtractorProto):
    async def extract_from_text(self, text: str, context=None) -> ExtractionResult:
        # Two entities: alice (Person), bob (Person)
        e1 = ExtractedEntity(id="e_alice", label="Person", text="alice", name="alice")
        e2 = ExtractedEntity(id="e_bob", label="Person", text="bob", name="bob")
        return ExtractionResult(entities=[e1, e2], relationships=[])


class _StubGraphRepo(GraphRepositoryProto):
    def __init__(self):
        self.cypher_calls: list[tuple[str, dict]] = []

    async def execute_query(self, query, params=None):
        self.cypher_calls.append((query, params or {}))
        return []

    # Minimal implementations used by engine paths
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

    async def get_neighbors(self, entity_id: str, depth: int = 1):
        # No extra neighbors; engine still keeps seeds
        return [], []

    async def update_node_properties(self, node_id, properties):  # pragma: no cover
        return None

    async def delete_document(self, document_id: str) -> bool:  # pragma: no cover
        return True

    async def link_chunk_to_entities(self, chunk_id: str, entity_ids):  # pragma: no cover
        return None

    # Custom helper used by engine but not in Protocol
    async def search_entities_by_properties(self, props: dict, limit: int = 1):
        # Return a DomainEntity matching the requested name/type
        name = props.get("name")
        label = props.get("type")
        ent = DomainEntity(id=f"id_{name}", name=name, type=label, properties={"name": name})
        return [ent]


class _LLMStub:
    async def extract_entities_relationships(self, text: str, config=None):
        # Two duplicates above threshold and one low-confidence
        rels = [
            {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.95},
            {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.90},
            {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.10},
        ]
        return [], rels


@pytest.mark.asyncio
async def test_llm_relationship_persist_gating_and_dedupe(monkeypatch):
    repo = _StubGraphRepo()
    vs = _StubVectorStore()
    ex = _StubEntityExtractor()
    engine = SimpleGraphRAGEngine(graph_store=repo, vector_store=vs, entity_extractor=ex)
    # Patch LLM service with our stub
    engine._llm_service = _LLMStub()
    # Patch settings used in engine module
    import graph_rag.core.graph_rag_engine as engmod

    engmod.settings.enable_llm_relationships = True
    engmod.settings.llm_rel_min_confidence = 0.8

    config = {
        "k": 2,
        "include_graph": True,
        "extract_relationships": True,
        "extract_relationships_persist": True,
    }

    chunks, graph_ctx = await engine._retrieve_and_build_context("who knows whom?", config)
    # One MERGE expected despite duplicates; low-confidence skipped
    assert len(repo.cypher_calls) == 1
    cypher, params = repo.cypher_calls[0]
    assert "MERGE" in cypher and params["props"]["extractor"] == "llm"
    # Counters present
    assert config.get("llm_relations_inferred_total", 0) >= 1
    assert config.get("llm_relations_persisted_total", 0) >= 1
