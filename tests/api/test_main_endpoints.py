from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import AsyncClient

# Change import
from graph_rag.config import get_settings
from graph_rag.core.interfaces import (
    GraphRAGEngine,
)

# Instantiate settings
settings = get_settings()


# Test the root endpoint
@pytest.mark.asyncio
async def test_read_root(test_client: AsyncClient):
    response = await test_client.get("/")
    # Assuming root redirects or returns a simple message
    # Adjust assertion based on actual root endpoint behavior
    # Example: assert response.status_code == status.HTTP_200_OK
    # Example: assert "message" in response.json()
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_307_TEMPORARY_REDIRECT,
    ]


# Test the health check endpoint
# NOTE: This test assumes the lifespan startup was successful *within the test context*.
# If lifespan depends on external services (like Memgraph), this test might need mocking
# or dependency overrides in the test_client fixture for true isolation.
@pytest.mark.asyncio
async def test_health_check_mocked(test_client: AsyncClient, app: FastAPI, mocker):
    """Test the health check endpoint with mocked dependencies."""
    # Ensure app.state has a mocked engine, as the main.py dependency getter checks state.
    mock_engine = MagicMock(spec=GraphRAGEngine)
    # Mock specific methods if the health check calls them
    # mock_engine.check_status.return_value = True

    # Directly set the engine on the app state for this test
    app.state.graph_rag_engine = mock_engine

    # Remove previous patching attempts for getters
    # mocker.patch("graph_rag.api.main.get_graph_rag_engine", return_value=mock_engine)
    # mocker.patch("graph_rag.api.main.get_graph_repository", return_value=mock_repo)
    # mocker.patch("graph_rag.api.main.get_vector_store", return_value=mock_vector_store)
    # mocker.patch("graph_rag.api.main.get_entity_extractor", return_value=mock_entity_extractor)
    # mocker.patch("graph_rag.api.main.get_llm", return_value=mock_llm)

    try:
        response = await test_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        # Add assertion for response body if needed based on health_check logic
        # Example: Check structure assuming health_check returns {"status": "ok", "dependencies": [...]}
        # response_json = response.json()
        # assert response_json.get("status") == "ok"
        # assert "graph_rag_engine" in response_json.get("dependencies", [])
    finally:
        # Clean up state modification
        if hasattr(app.state, "graph_rag_engine"):
            del app.state.graph_rag_engine  # Or set back to None if appropriate


@pytest.mark.asyncio
async def test_health_check_main(integration_test_client: AsyncClient):
    """Test the health check endpoint directly via main app test client,
    relying on the application lifespan to initialize dependencies."""
    # This uses the integration_test_client which should allow the lifespan
    # startup event to run and initialize the real engine (or fail if it can't).
    response = await integration_test_client.get("/health")
    # Assert based on the expected outcome of the *real* initialization
    # Assuming successful initialization in the test environment
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "dependencies": ["graph_rag_engine"]}


@pytest.mark.asyncio
async def test_root_redirect(test_client: AsyncClient):
    """Test the root endpoint redirects to /docs."""
    response = await test_client.get(
        "/", follow_redirects=False
    )  # Don't follow redirects automatically
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "/docs"


# Add more tests for other main endpoints if necessary
# e.g., testing error handling, different dependency states


@pytest.mark.asyncio
async def test_health_check_engine_failure(integration_test_client: AsyncClient, app):
    """Test health check reports failure if engine initialization failed (simulated)."""
    # Simulate engine initialization failure by setting it to None in app state
    # This needs to happen *after* the lifespan tries to run but *before* the request
    # This is tricky with integration_test_client. A different approach might be needed
    # to reliably test this state, e.g., by mocking the engine *creation* within lifespan.
    # For now, let's assume a scenario where the dependency getter *would* raise 503.

    # Alternative: Mock the dependency getter used by the health endpoint for this specific test
    # This requires knowing exactly which getter is used (`get_graph_rag_engine` from main.py)
    from graph_rag.api.main import get_graph_rag_engine as main_get_engine

    async def mock_failed_engine_getter():
        raise HTTPException(status_code=503, detail="Simulated engine failure")

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[main_get_engine] = mock_failed_engine_getter

    try:
        response = await integration_test_client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        # assert response.json() == {"detail": "Simulated engine failure"} # Or check against actual 503 detail if possible
        response_data = response.json()
        assert response_data.get("detail") == "Simulated engine failure"
    finally:
        # Restore original overrides
        app.dependency_overrides = original_overrides


@pytest.mark.asyncio
async def test_readiness_checks_dependencies_ok(test_client: AsyncClient, app: FastAPI, mock_graph_repo, mock_vector_store):
    """Readiness should return 200 when dependency probes succeed."""
    # Ensure mocks are wired
    app.state.graph_repository = mock_graph_repo
    app.state.vector_store = mock_vector_store
    app.state.graph_rag_engine = object()
    app.state.ingestion_service = object()
    # Probes: graph_repo.get_document_by_id returns None by default; treat as OK
    # Vector store: add a get_vector_store_size that returns 0
    try:
        mock_vector_store.get_vector_store_size.return_value = 0  # type: ignore[attr-defined]
    except Exception:
        pass

    resp = await test_client.get("/ready")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data.get("status") == "ready"


@pytest.mark.asyncio
async def test_readiness_reports_failure_on_dep_error(test_client: AsyncClient, app: FastAPI, mock_graph_repo, mock_vector_store):
    """Readiness should return 503 when a dependency probe fails."""
    app.state.graph_repository = mock_graph_repo
    app.state.vector_store = mock_vector_store
    app.state.graph_rag_engine = object()
    app.state.ingestion_service = object()
    # Make graph ping fail
    async def _boom(_id: str):
        raise RuntimeError("DB down")

    mock_graph_repo.get_document_by_id.side_effect = _boom
    resp = await test_client.get("/ready")
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = resp.json()
    assert body.get("status") == "not ready"


# TODO: Add a test to verify the health check actually checks DB connectivity if that's part of it.
