"""Test graceful fallbacks when Memgraph is unavailable."""

from unittest.mock import patch

import pytest

from graph_rag.api.dependencies import create_graph_repository
from graph_rag.config import Settings
from graph_rag.infrastructure.graph_stores.mock_graph_store import MockGraphRepository


def test_graph_repository_graceful_fallback_when_disabled():
    """Test that MockGraphRepository is used when graph is disabled."""
    settings = Settings(disable_graph=True)
    repo = create_graph_repository(settings)
    assert isinstance(repo, MockGraphRepository)


def test_graph_repository_fallback_when_memgraph_unavailable():
    """Test fallback to MockGraphRepository when Memgraph connection fails."""
    # Mock the availability check
    with patch('graph_rag.api.dependencies._MEMGRAPH_AVAILABLE', False):
        settings = Settings(disable_graph=False)
        repo = create_graph_repository(settings)
        assert isinstance(repo, MockGraphRepository)


@pytest.mark.asyncio
async def test_mock_graph_repository_basic_operations():
    """Test that MockGraphRepository implements required operations."""
    from graph_rag.models import Chunk, Document

    repo = MockGraphRepository()

    # Test document operations
    doc = Document(
        id="test-doc",
        content="Test content",
        metadata={"title": "Test"}
    )

    await repo.add_document(doc)
    retrieved_doc = await repo.get_document("test-doc")
    assert retrieved_doc is not None
    assert retrieved_doc.id == "test-doc"

    # Test chunk operations
    chunk = Chunk(
        id="test-chunk",
        document_id="test-doc",
        content="Test chunk content",
        embedding=[0.1, 0.2, 0.3]
    )

    await repo.add_chunk(chunk)
    retrieved_chunk = await repo.get_chunk("test-chunk")
    assert retrieved_chunk is not None
    assert retrieved_chunk.id == "test-chunk"

    # Test health check
    health = await repo.health_check()
    assert health["status"] == "healthy"
    assert health["type"] == "mock"


def test_environment_variable_controls_graph_disable():
    """Test that SYNAPSE_DISABLE_GRAPH controls graph functionality."""
    import os

    # Test with environment variable set
    with patch.dict(os.environ, {'SYNAPSE_DISABLE_GRAPH': 'true'}):
        settings = Settings()
        assert settings.disable_graph is True

        repo = create_graph_repository(settings)
        assert isinstance(repo, MockGraphRepository)


@pytest.mark.asyncio
async def test_vector_only_mode_still_works():
    """Test that vector operations work even when graph is disabled."""
    from graph_rag.api.dependencies import create_embedding_service, create_vector_store
    from graph_rag.config import get_settings

    settings = get_settings()
    settings.disable_graph = True

    # Create components for vector-only mode
    embedding_service = create_embedding_service(settings)
    vector_store = create_vector_store(settings)

    # These should work without graph
    assert embedding_service is not None
    assert vector_store is not None

    # Test basic vector operations
    test_texts = ["Hello world", "Test document"]
    embeddings = await embedding_service.encode(test_texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0
