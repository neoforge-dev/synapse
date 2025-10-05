"""End-to-end test for LLM relationship intelligence features."""

import pytest

from graph_rag.config import get_settings


def test_llm_relationship_settings_exist():
    """Test that LLM relationship settings are properly configured."""
    settings = get_settings()

    # Verify settings exist with proper defaults
    assert hasattr(settings, 'enable_llm_relationships')
    assert hasattr(settings, 'llm_rel_min_confidence')

    # Verify defaults are reasonable
    assert settings.enable_llm_relationships is False  # Safe default
    assert settings.llm_rel_min_confidence == 0.7  # Reasonable confidence threshold
    assert 0.0 <= settings.llm_rel_min_confidence <= 1.0  # Valid range


def test_ask_request_has_relationship_controls():
    """Test that AskRequest model has LLM relationship control flags."""
    from graph_rag.api.models import AskRequest

    # Test with relationship persistence enabled
    request = AskRequest(
        text="test question",
        extract_relationships_persist=True,
        extract_relationships_dry_run=False
    )

    assert request.extract_relationships_persist is True
    assert request.extract_relationships_dry_run is False

    # Test with dry-run enabled
    request_dry = AskRequest(
        text="test question",
        extract_relationships_persist=False,
        extract_relationships_dry_run=True
    )

    assert request_dry.extract_relationships_persist is False
    assert request_dry.extract_relationships_dry_run is True


def test_api_propagates_relationship_flags():
    """Test that API properly propagates relationship flags to engine config."""
    from unittest.mock import AsyncMock

    from graph_rag.api.models import AskRequest

    # Create request with relationship controls
    ask_request = AskRequest(
        text="test query",
        extract_relationships_persist=True,
        extract_relationships_dry_run=False
    )

    # Mock engine that captures config
    captured_config = {}

    async def mock_query(query_text, config=None):
        captured_config.update(config or {})
        from graph_rag.core.graph_rag_engine import QueryResult
        return QueryResult(answer="mock answer")

    mock_engine = AsyncMock()
    mock_engine.query = mock_query

    # Simulate router processing
    from graph_rag.api.routers.core_business_operations import create_core_business_operations_router
    router = create_core_business_operations_router()

    # Find and call the ask endpoint
    for route in router.routes:
        if hasattr(route, 'path') and route.path == '/ask':
            ask_func = route.endpoint
            import asyncio
            asyncio.run(ask_func(ask_request, mock_engine))
            break

    # Verify relationship flags are propagated
    assert "extract_relationships_persist" in captured_config
    assert "extract_relationships_dry_run" in captured_config
    assert captured_config["extract_relationships_persist"] is True
    assert captured_config["extract_relationships_dry_run"] is False


@pytest.mark.asyncio
async def test_llm_relationship_intelligence_integration():
    """Integration test showing complete LLM relationship intelligence workflow."""
    from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
    from graph_rag.core.interfaces import (
        ChunkData,
        EntityExtractor,
        ExtractedEntity,
        ExtractionResult,
        GraphRepository,
        SearchResultData,
        VectorStore,
    )
    from graph_rag.domain.models import Entity as DomainEntity

    # Mock components that demonstrate the workflow
    class MockGraphRepo(GraphRepository):
        def __init__(self):
            self.persisted_relationships = []

        async def search_entities_by_properties(self, props, limit=1):
            # Return entities that exist in the graph
            name = props.get("name", "unknown")
            return [DomainEntity(id=f"id_{name}", name=name, type="Person", properties=props)]

        async def add_relationship(self, relationship):
            self.persisted_relationships.append(relationship)

        # Minimal required implementations
        async def execute_query(self, query, params=None): return []
        async def add_document(self, doc): pass
        async def get_document_by_id(self, doc_id): return None
        async def get_entity_by_id(self, entity_id): return None
        async def add_chunk(self, chunk): pass
        async def add_chunks(self, chunks): pass
        async def get_chunk_by_id(self, chunk_id): return None
        async def get_chunks_by_document_id(self, doc_id): return []
        async def add_entity(self, entity): pass
        async def get_neighbors(self, entity_id, depth=1): return [], []
        async def update_node_properties(self, node_id, props): pass
        async def delete_document(self, doc_id): return True
        async def link_chunk_to_entities(self, chunk_id, entity_ids): pass

    class MockVectorStore(VectorStore):
        async def search(self, query_text, top_k=5, search_type="vector"):
            chunk = ChunkData(id="c1", text="Alice knows Bob", document_id="d1", metadata={})
            return [SearchResultData(chunk=chunk, score=0.9)]
        async def add_chunks(self, chunks): pass
        async def search_similar_chunks(self, query_vector, limit=10, threshold=None): return []
        async def get_chunk_by_id(self, chunk_id): return None
        async def delete_chunks(self, chunk_ids): pass
        async def delete_store(self): pass

    class MockEntityExtractor(EntityExtractor):
        async def extract_from_text(self, text, context=None):
            entities = [
                ExtractedEntity(id="alice", label="Person", text="Alice", name="Alice"),
                ExtractedEntity(id="bob", label="Person", text="Bob", name="Bob")
            ]
            return ExtractionResult(entities=entities, relationships=[])

    class MockLLMService:
        async def extract_entities_relationships(self, text, config=None):
            # Return a high-confidence relationship
            relationships = [{
                "source_name": "Alice",
                "target_name": "Bob",
                "type": "KNOWS",
                "confidence": 0.95
            }]
            return [], relationships

    # Set up engine with LLM relationships enabled
    repo = MockGraphRepo()
    vector_store = MockVectorStore()
    extractor = MockEntityExtractor()
    engine = SimpleGraphRAGEngine(
        graph_store=repo,
        vector_store=vector_store,
        entity_extractor=extractor
    )
    engine._llm_service = MockLLMService()

    # Enable LLM relationships in engine settings
    import graph_rag.core.graph_rag_engine as eng_module
    original_enabled = eng_module.settings.enable_llm_relationships
    original_confidence = eng_module.settings.llm_rel_min_confidence

    try:
        eng_module.settings.enable_llm_relationships = True
        eng_module.settings.llm_rel_min_confidence = 0.8

        # Execute query with relationship persistence enabled
        config = {
            "k": 1,
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": True
        }

        chunks, graph_context = await engine._retrieve_and_build_context(
            "Who knows whom?", config
        )

        # Verify relationship was persisted (confidence 0.95 > threshold 0.8)
        assert len(repo.persisted_relationships) == 1
        relationship = repo.persisted_relationships[0]
        assert relationship.properties["extractor"] == "llm"
        assert relationship.properties["confidence"] == 0.95

        # Verify counters were updated
        assert config.get("llm_relations_inferred_total", 0) >= 1
        assert config.get("llm_relations_persisted_total", 0) >= 1

    finally:
        # Restore original settings
        eng_module.settings.enable_llm_relationships = original_enabled
        eng_module.settings.llm_rel_min_confidence = original_confidence
