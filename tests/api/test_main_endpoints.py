import pytest
from httpx import AsyncClient
from fastapi import status

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
async def test_health_check_main(test_client: AsyncClient):
    """Test the health check endpoint directly via main app test client."""
    # This uses the same test_client fixture from conftest
    # which should have the necessary mocks (engine, driver) set in app state
    response = await test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}

# Add tests for failure cases later (e.g., lifespan fails to connect DB)
# This would require manipulating app.state or using dependency overrides
# to simulate the failure condition before calling the endpoint. 