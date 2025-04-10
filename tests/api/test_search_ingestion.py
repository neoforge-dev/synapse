import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock # Use AsyncMock for async methods
import json

# Import Schemas and core data structures
from graph_rag.api import schemas
from graph_rag.core.interfaces import SearchResultData, ChunkData, DocumentData
from graph_rag.api import dependencies as deps # To override engine dependency
from graph_rag.api.main import app # Import app for dependency override

# --- Mocks --- 
# Override the engine dependency for tests in this module
@pytest_asyncio.fixture(autouse=True) # Apply automatically to all tests in module
def override_engine_dependency(mock_graph_rag_engine):
    app.dependency_overrides[deps.get_graph_rag_engine] = lambda: mock_graph_rag_engine
    yield
    # Clear overrides after tests in this module run
    app.dependency_overrides = {}

# --- Ingestion Tests --- 
@pytest.mark.asyncio
async def test_ingest_document_success(test_client: AsyncClient, mock_graph_rag_engine):
    payload = {"content": "Test document content.", "metadata": {"source": "test"}}
    response = await test_client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    # Check that the engine method was called correctly
    mock_graph_rag_engine.process_and_store_document.assert_called_once_with(
        doc_content="Test document content.", metadata={"source": "test"}
    )
    # Response body might have placeholder ID, check status field
    assert response.json()["status"] == "processing started"

@pytest.mark.asyncio
async def test_ingest_document_empty_content(test_client: AsyncClient):
    payload = {"content": " ", "metadata": {"source": "test"}}
    response = await test_client.post("/api/v1/ingestion/documents", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

# --- Search Tests --- 
@pytest.mark.asyncio
async def test_search_batch_success(test_client: AsyncClient, mock_graph_rag_engine):
    payload = {"query": "find me", "search_type": "vector", "limit": 2}
    response = await test_client.post("/api/v1/search/query?stream=false", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["query"] == "find me"
    assert data["search_type"] == "vector"
    assert len(data["results"]) == 2
    assert data["results"][0]["chunk"]["id"] == "chunk_0"
    assert data["results"][0]["score"] == 0.9
    assert data["results"][1]["chunk"]["id"] == "chunk_1"
    assert data["results"][1]["score"] == 0.8
    # Check that stream_context was called on the mock engine
    # Note: Direct assertion on async generator calls is tricky, 
    # but we verify the output which implies it was called.
    # mock_graph_rag_engine.stream_context.assert_called_once() # Might not work as expected

@pytest.mark.asyncio
async def test_search_stream_success(test_client: AsyncClient, mock_graph_rag_engine):
    payload = {"query": "find me", "search_type": "vector", "limit": 1}
    
    results = []
    async with test_client.stream("POST", "/api/v1/search/query?stream=true", json=payload) as response:
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/x-ndjson"
        async for line in response.aiter_lines():
            if line:
                results.append(json.loads(line))

    assert len(results) == 1
    assert results[0]["chunk"]["id"] == "chunk_0"
    assert results[0]["score"] == 0.9

@pytest.mark.asyncio
async def test_search_no_results(test_client: AsyncClient, mock_graph_rag_engine):
    payload = {"query": "find nothing", "search_type": "keyword", "limit": 5}
    response = await test_client.post("/api/v1/search/query?stream=false", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["query"] == "find nothing"
    assert data["search_type"] == "keyword"
    assert len(data["results"]) == 0

@pytest.mark.asyncio
async def test_search_invalid_type(test_client: AsyncClient):
    payload = {"query": "test", "search_type": "invalid", "limit": 1}
    response = await test_client.post("/api/v1/search/query?stream=false", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY # Validation error from Pydantic 