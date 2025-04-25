import pytest
from httpx import AsyncClient
from fastapi import status, HTTPException
from unittest.mock import AsyncMock, patch

# Change import
from graph_rag.config import get_settings

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
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_307_TEMPORARY_REDIRECT]

# Test the health check endpoint
# NOTE: This test assumes the lifespan startup was successful *within the test context*.
# If lifespan depends on external services (like Memgraph), this test might need mocking 
# or dependency overrides in the test_client fixture for true isolation.
@pytest.mark.asyncio
async def test_health_check_mocked(integration_test_client: AsyncClient, mock_graph_rag_engine: AsyncMock):
    """Test the health check endpoint using the standard mocked test client.
    We need to explicitly mock the engine's behavior for this client."""
    # Since test_client overrides get_graph_rag_engine with mock_graph_rag_engine,
    # this test now verifies the endpoint works when the mocked dependency is injected.
    # No specific mock setup needed here unless we want to simulate engine errors.
    
    # Ensure the mock engine is considered "initialized" by the health check
    # (The health check might just check for its existence in app.state)
    # If using integration_test_client, the real lifespan runs, so the real engine
    # should be initialized (assuming lifespan succeeds).
    # Let's assume the integration client is now used and lifespan works.
    
    # response = await test_client.get("/health")
    response = await integration_test_client.get("/health")
    # assert response.status_code == status.HTTP_200_OK
    # assert 503 == 200
    assert response.status_code == status.HTTP_200_OK, f"Health check failed: {response.text}"

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
    response = await test_client.get("/", follow_redirects=False) # Don't follow redirects automatically
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

# TODO: Add a test to verify the health check actually checks DB connectivity if that's part of it. 