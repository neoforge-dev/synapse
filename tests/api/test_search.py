import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

from graph_rag.api.main import app
from graph_rag.services.search import SearchResult

# Define sample results for mocking
SAMPLE_SEARCH_RESULTS = [
    SearchResult(chunk_id="chunk1", document_id="doc1", content="Result 1", score=0.9),
    SearchResult(chunk_id="chunk2", document_id="doc1", content="Result 2", score=0.8),
]

@pytest.fixture
def mock_search_service():
    """Fixture to mock the SearchService, covering both search types."""
    with patch("graph_rag.api.routers.search.SearchService") as mock_service_cls:
        mock_instance = AsyncMock()
        mock_service_cls.return_value = mock_instance
        
        # Configure return values for both methods
        mock_instance.search_chunks.return_value = SAMPLE_SEARCH_RESULTS
        mock_instance.search_chunks_by_similarity.return_value = SAMPLE_SEARCH_RESULTS
        
        yield mock_instance


# --- Keyword Search Endpoint Tests --- 

@pytest.mark.asyncio
async def test_search_chunks_keyword_endpoint(mock_search_service):
    """Test the keyword chunk search endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search/chunks/keyword", # Updated endpoint path
            json={
                "query": "test query",
                "limit": 5
            }
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["query"] == "test query"
    assert len(data["results"]) == len(SAMPLE_SEARCH_RESULTS)
    assert data["results"][0]["chunk_id"] == "chunk1"
    assert data["results"][1]["chunk_id"] == "chunk2"
    
    mock_search_service.search_chunks.assert_called_once_with(query="test query", limit=5)
    mock_search_service.search_chunks_by_similarity.assert_not_called()


@pytest.mark.asyncio
async def test_search_chunks_keyword_handles_service_error(mock_search_service):
    mock_search_service.search_chunks.side_effect = Exception("Service error")
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search/chunks/keyword",
            json={"query": "error query"}
        )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_search_chunks_keyword_handles_invalid_limit(mock_search_service):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response_high = await client.post(
            "/api/v1/search/chunks/keyword",
            json={"query": "test", "limit": 200}
        )
        assert response_high.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_low = await client.post(
            "/api/v1/search/chunks/keyword",
            json={"query": "test", "limit": 0}
        )
        assert response_low.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# --- Vector Search Endpoint Tests --- 

@pytest.mark.asyncio
async def test_search_chunks_vector_endpoint(mock_search_service):
    """Test the vector chunk search endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search/chunks/vector",
            json={
                "query": "similar query",
                "limit": 7
            }
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["query"] == "similar query"
    assert len(data["results"]) == len(SAMPLE_SEARCH_RESULTS)
    assert data["results"][0]["chunk_id"] == "chunk1"
    assert data["results"][1]["chunk_id"] == "chunk2"
    
    mock_search_service.search_chunks_by_similarity.assert_called_once_with(query="similar query", limit=7)
    mock_search_service.search_chunks.assert_not_called()


@pytest.mark.asyncio
async def test_search_chunks_vector_handles_service_error(mock_search_service):
    mock_search_service.search_chunks_by_similarity.side_effect = Exception("Vector Service error")
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search/chunks/vector",
            json={"query": "error query"}
        )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_search_chunks_vector_handles_invalid_limit(mock_search_service):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response_high = await client.post(
            "/api/v1/search/chunks/vector",
            json={"query": "test", "limit": 200}
        )
        assert response_high.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_low = await client.post(
            "/api/v1/search/chunks/vector",
            json={"query": "test", "limit": 0}
        )
        assert response_low.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY 