"""Test that retrieval quality toggles properly propagate from API to engine."""

from unittest.mock import AsyncMock

import pytest

from graph_rag.api.models import AskRequest
from graph_rag.core.graph_rag_engine import QueryResult


@pytest.mark.asyncio
async def test_ask_request_search_type_propagates_to_engine():
    """Test that search_type parameter propagates from API to engine."""
    # Arrange
    ask_request = AskRequest(
        text="test query",
        k=5,
        search_type="keyword",  # This should propagate to the engine
        blend_vector_weight=0.0,
        blend_keyword_weight=1.0,
    )

    # Mock engine that captures the config passed to it
    captured_config = {}

    async def mock_query(query_text, config=None):
        captured_config.update(config or {})
        return QueryResult(answer="mock answer")

    mock_engine = AsyncMock()
    mock_engine.query = mock_query

    # Act
    from graph_rag.api.routers.core_business_operations import create_core_business_operations_router
    router = create_core_business_operations_router()

    # We need to manually call the ask function with our mocked engine
    # Since we can't easily test the dependency injection in isolation
    for route in router.routes:
        if hasattr(route, 'path') and route.path == '/ask':
            ask_func = route.endpoint
            await ask_func(ask_request, mock_engine)
            break

    # Assert
    assert "search_type" in captured_config
    assert captured_config["search_type"] == "keyword"


@pytest.mark.asyncio
async def test_ask_request_all_retrieval_toggles_propagate():
    """Test that all retrieval quality toggles propagate correctly."""
    # Arrange
    ask_request = AskRequest(
        text="test query",
        k=3,
        search_type="vector",
        blend_vector_weight=0.7,
        blend_keyword_weight=0.3,
        no_answer_min_score=0.5,
        rerank=True,
        mmr_lambda=0.6,
    )

    captured_config = {}

    async def mock_query(query_text, config=None):
        captured_config.update(config or {})
        return QueryResult(answer="mock answer")

    mock_engine = AsyncMock()
    mock_engine.query = mock_query

    # Act
    from graph_rag.api.routers.core_business_operations import create_core_business_operations_router
    router = create_core_business_operations_router()

    for route in router.routes:
        if hasattr(route, 'path') and route.path == '/ask':
            ask_func = route.endpoint
            await ask_func(ask_request, mock_engine)
            break

    # Assert
    expected_config_keys = [
        "search_type",
        "blend_vector_weight",
        "blend_keyword_weight",
        "no_answer_min_score",
        "rerank",
        "mmr_lambda",
    ]

    for key in expected_config_keys:
        assert key in captured_config, f"Missing {key} in engine config"

    assert captured_config["search_type"] == "vector"
    assert captured_config["blend_vector_weight"] == 0.7
    assert captured_config["blend_keyword_weight"] == 0.3
    assert captured_config["no_answer_min_score"] == 0.5
    assert captured_config["rerank"] is True
    assert captured_config["mmr_lambda"] == 0.6
