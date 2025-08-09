import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport


@pytest.mark.asyncio
async def test_search_endpoint_returns_503_when_vector_store_missing(app: FastAPI):
    """When app.state.vector_store is not set and no override is provided,
    the dependency getter should respond with 503.
    Lifespan is intentionally not run to simulate missing initialization.
    """
    # Ensure there is no vector_store on app.state
    if hasattr(app.state, "vector_store"):
        delattr(app.state, "vector_store")

    # Quick sanity print of routes (optional)
    _ = [
        (route.path, route.methods)
        for route in app.routes
        if isinstance(route, APIRoute)
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        payload = {"query": "hello", "search_type": "vector", "limit": 1}
        resp = await client.post("/api/v1/search/", json=payload)
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        body = resp.json()
        assert "detail" in body
        assert "Vector store" in body["detail"].capitalize()
