import pytest
from httpx import AsyncClient
from fastapi import status

# Import settings if needed to check against response
from graph_rag.config.settings import settings

# Test the root endpoint
@pytest.mark.asyncio
async def test_read_root(test_client: AsyncClient):
    response = await test_client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "OK"
    assert data["app_name"] == settings.APP_NAME
    assert data["version"] == settings.APP_VERSION

# Test the health check endpoint
# NOTE: This test assumes the lifespan startup was successful *within the test context*.
# If lifespan depends on external services (like Memgraph), this test might need mocking 
# or dependency overrides in the test_client fixture for true isolation.
@pytest.mark.asyncio
async def test_health_check_success(test_client: AsyncClient):
    # TODO: This needs proper mocking/dependency override for DB check
    # For now, assume lifespan initialized components in app.state correctly
    # and mock the DB check implicitly by assuming it passes if no exception.
    
    # --- Mocking Setup (Illustrative - Requires More Setup) ---
    # This is complex - requires overriding dependencies in the fixture
    # or using a mocking library like pytest-mock. Let's skip full
    # mocking for now and test the basic path assuming components are 'available'
    # in app.state and the DB check (if implemented fully) passes.
    # 
    # Example using app dependency overrides (in conftest.py fixture):
    # 
    # async def override_get_memgraph_store():
    #     mock_store = AsyncMock(spec=MemgraphStore)
    #     mock_store.execute_read = AsyncMock(return_value=[1]) # Mock DB check
    #     return mock_store
    # 
    # app.dependency_overrides[deps.get_memgraph_store] = override_get_memgraph_store
    # ... other overrides ...
    # yield client # in fixture
    # app.dependency_overrides = {} # cleanup
    # --- End Mocking Setup --- 

    try:
        response = await test_client.get("/health")
        # If the basic checks in the /health endpoint pass (components exist in state)
        # and the mocked DB check passes, we expect 200 OK.
        assert response.status_code == status.HTTP_200_OK 
        assert response.json() == {"status": "healthy"}
    except Exception as e:
        pytest.fail(f"Health check failed unexpectedly: {e}")

# Add tests for failure cases later (e.g., lifespan fails to connect DB)
# This would require manipulating app.state or using dependency overrides
# to simulate the failure condition before calling the endpoint. 