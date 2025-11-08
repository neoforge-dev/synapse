import os
from collections.abc import AsyncIterator

os.environ.setdefault("SKIP_SPACY_IMPORT", "1")

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from graph_rag.api.dependencies import MockEmbeddingService, get_advanced_features_service
from graph_rag.api.routers.advanced_features import create_advanced_features_router
from graph_rag.core.interfaces import ChunkData
from graph_rag.domain.models import Chunk, Document, Entity, Relationship
from graph_rag.infrastructure.graph_stores.mock_graph_store import MockGraphRepository
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
from graph_rag.services.advanced_features import AdvancedFeaturesService


@pytest.fixture
async def advanced_features_service() -> AsyncIterator[AdvancedFeaturesService]:
    """Create an advanced features service with representative graph data."""
    repo = MockGraphRepository()

    # Documents and chunks
    document = Document(
        id="doc:strategic-ai",
        content="Strategic AI consolidation blueprint",
        metadata={"topics": ["AI Strategy", "Enterprise Graphs"]},
    )
    await repo.add_document(document)

    chunk = Chunk(
        id="chunk:overview",
        text="AI strategy consolidation delivers measurable enterprise value.",
        document_id=document.id,
        metadata={"section": "overview", "score": 0.88},
    )
    await repo.add_chunk(chunk)

    # Entities
    topic_entity = Entity(
        id="entity:ai-strategy",
        type="Topic",
        name="AI Strategy",
        properties={"category": "strategy", "confidence": 0.91},
    )
    leader_entity = Entity(
        id="entity:enterprise-leadership",
        type="Persona",
        name="Enterprise Leadership",
        properties={"department": "Executive"},
    )
    repo.add_entity(topic_entity)
    repo.add_entity(leader_entity)

    # Relationships
    repo._relationships["rel:chunk-topic"] = Relationship(  # type: ignore[attr-defined]
        id="rel:chunk-topic",
        type="MENTIONS_TOPIC",
        source_id=chunk.id,
        target_id=topic_entity.id,
        properties={"weight": 0.82},
    )
    repo._relationships["rel:topic-persona"] = Relationship(  # type: ignore[attr-defined]
        id="rel:topic-persona",
        type="RESOLVES_FOR",
        source_id=topic_entity.id,
        target_id=leader_entity.id,
        properties={"strength": 0.73},
    )
    repo._relationships["rel:doc-chunk"] = Relationship(  # type: ignore[attr-defined]
        id="rel:doc-chunk",
        type="CONTAINS",
        source_id=document.id,
        target_id=chunk.id,
        properties={},
    )

    # Vector store with matching chunk
    embedding_service = MockEmbeddingService(dimension=8)
    vector_store = SimpleVectorStore(embedding_service)
    await vector_store.add_chunks(
        [
            ChunkData(
                id=chunk.id,
                text=chunk.text,
                document_id=chunk.document_id,
                metadata={
                    "document_id": chunk.document_id,
                    "section": "overview",
                    "score": 0.88,
                },
            )
        ]
    )

    service = AdvancedFeaturesService(graph_repo=repo, vector_store=vector_store)
    yield service


@pytest.mark.asyncio
async def test_graph_stats_reflects_graph_topology(advanced_features_service: AdvancedFeaturesService):
    stats = await advanced_features_service.graph_stats()

    assert stats.total_nodes >= 4  # document, chunk, and two entities
    assert stats.total_relationships >= 2
    assert stats.graph_density > 0.0
    assert stats.connected_components == 1
    assert stats.node_types["Topic"] >= 1


@pytest.mark.asyncio
async def test_graph_analysis_filters_by_query(advanced_features_service: AdvancedFeaturesService):
    result = await advanced_features_service.analyze_graph(
        query="strategy",
        depth=2,
        include_entities=True,
        include_relationships=True,
    )

    entity_names = {entity["name"].lower() for entity in result.entities}
    assert any("strategy" in name for name in entity_names)
    assert result.analysis_metrics["entities_analyzed"] == len(result.entities)
    assert result.analysis_metrics["relationships_analyzed"] == len(result.relationships)


@pytest.mark.asyncio
async def test_hot_take_analysis_scores_content(advanced_features_service: AdvancedFeaturesService):
    response = await advanced_features_service.analyze_hot_take(
        content="AI dominated transformations spark industry debate! Massive ROI plus governance risks.",
        platform="linkedin",
        analysis_depth="comprehensive",
    )

    assert 0.0 <= response.controversy_score <= 1.0
    assert response.viral_potential >= 0.2
    assert "risk_assessment" in response.dict()
    assert response.engagement_prediction["expected"] > 0


@pytest.mark.asyncio
async def test_brand_safety_detects_risky_language(advanced_features_service: AdvancedFeaturesService):
    assessment = await advanced_features_service.check_brand_safety(
        content="Exploit regulatory loopholes and crush competitors mercilessly.",
        safety_level="strict",
    )

    assert assessment.safety_score < 0.6
    categories = {category["category"] for category in assessment.risk_categories}
    assert "compliance" in categories or "ethics" in categories
    assert assessment.compliance_status in {"review", "high_risk"}


@pytest.mark.asyncio
async def test_chunk_analysis_returns_real_metadata(advanced_features_service: AdvancedFeaturesService):
    analysis = await advanced_features_service.get_chunk_analysis("chunk:overview")

    assert analysis.chunk_id == "chunk:overview"
    assert analysis.parent_document == "doc:strategic-ai"
    assert analysis.embedding_quality > 0
    assert analysis.semantic_density > 0
    assert analysis.relationships_count >= 1


@pytest.mark.asyncio
async def test_advanced_features_router_uses_service(advanced_features_service: AdvancedFeaturesService):
    app = FastAPI()
    app.include_router(create_advanced_features_router(), prefix="/advanced")

    async def _override_service() -> AdvancedFeaturesService:
        return advanced_features_service

    app.dependency_overrides[get_advanced_features_service] = _override_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/advanced/graph/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_nodes"] >= 4
    assert payload["node_types"].get("Topic", 0) >= 1
