import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, MagicMock, AsyncMock

# Removed direct app import
# from graph_rag.api.main import app 
from graph_rag.api.models import QueryResult, ResultItem
from graph_rag.core.interfaces import EntityExtractor
# Removed direct repo import, use dependency injection/mocking
# from graph_rag.infrastructure.repositories.graph_repository import GraphRepository

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# Removed local async_client fixture
# @pytest.fixture(scope="module")
# async def async_client() -> AsyncClient:
#     """Provides an async test client for the FastAPI app."""
#     async with AsyncClient(app=app, base_url="http://testserver") as client:
#         yield client

# --- Test Cases ---

# Use the shared 'test_client' fixture from conftest.py
# Mock dependencies using fixtures or direct patching within tests
async def test_query_success(test_client: AsyncClient):
    """Test successful query processing."""
    payload = {
        "query_text": "Tell me about Alice.",
        "k": 5
    }

    # Mock the dependencies
    mock_entities = [MagicMock(name="Alice")]
    mock_entities[0].name = "Alice"

    mock_results = [
        {
            "chunk_id": "c1",
            "chunk_content": "Alice info...",
            "document_id": "doc1"
        },
        {
            "chunk_id": "c2",
            "chunk_content": "More about Alice...",
            "document_id": "doc2"
        }
    ]

    # Mock the entity extractor dependency function
    mock_entity_extractor = MagicMock(spec=EntityExtractor)
    mock_entity_extractor.extract_entities.return_value = mock_entities

    # Mock the graph repository dependency function
    # Assuming GraphRepository has execute_read
    mock_graph_repository = AsyncMock() # Use AsyncMock for async methods
    mock_graph_repository.execute_read.return_value = mock_results

    # Patch the dependency *getter functions*
    with patch("graph_rag.api.routers.query.get_entity_extractor", return_value=mock_entity_extractor) as mock_get_extractor, \
         patch("graph_rag.api.routers.query.get_graph_repository", return_value=mock_graph_repository) as mock_get_repo:

        response = await test_client.post("/api/v1/query/", json=payload)

        # Verify the mocks were called (on the instance returned by the getter)
        mock_entity_extractor.extract_entities.assert_called_once_with(payload["query_text"])
        mock_graph_repository.execute_read.assert_called_once()

        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert response_data["query"] == payload["query_text"]
        assert len(response_data["results"]) == len(mock_results)
        assert response_data["results"][0]["content"] == mock_results[0]["chunk_content"]
        assert response_data["results"][0]["metadata"]["chunk_id"] == mock_results[0]["chunk_id"]
        assert response_data["results"][0]["metadata"]["document_id"] == mock_results[0]["document_id"]

async def test_query_missing_query_text(test_client: AsyncClient):
    """Test query request missing the required 'query_text' field."""
    payload = {
        # Missing "query_text"
        "k": 5
    }

    response = await test_client.post("/api/v1/query/", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("query_text" in err.get("loc", []) and "missing" in err.get("type", "") for err in response_data.get("detail", []))

async def test_query_no_entities(test_client: AsyncClient):
    """Test query handling when no entities are extracted."""
    payload = {
        "query_text": "This query has no entities",
        "k": 5
    }

    # Mock the entity extractor to return no entities
    mock_entity_extractor = MagicMock(spec=EntityExtractor)
    mock_entity_extractor.extract_entities.return_value = []

    # Mock the graph repository (should not be called)
    mock_graph_repository = AsyncMock()

    # Patch the dependencies
    with patch("graph_rag.api.routers.query.get_entity_extractor", return_value=mock_entity_extractor) as mock_get_extractor, \
         patch("graph_rag.api.routers.query.get_graph_repository", return_value=mock_graph_repository) as mock_get_repo:

        response = await test_client.post("/api/v1/query/", json=payload)

        # Verify the mocks were called
        mock_entity_extractor.extract_entities.assert_called_once_with(payload["query_text"])
        mock_graph_repository.execute_read.assert_not_called()

        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert response_data["query"] == payload["query_text"]
        assert len(response_data["results"]) == 0

async def test_query_graph_error(test_client: AsyncClient):
    """Test query handling when the graph repository raises an exception."""
    payload = {
        "query_text": "Tell me about Alice.",
        "k": 5
    }

    # Mock the entity extractor
    mock_entities = [MagicMock(name="Alice")]
    mock_entities[0].name = "Alice"

    mock_entity_extractor = MagicMock(spec=EntityExtractor)
    mock_entity_extractor.extract_entities.return_value = mock_entities

    # Mock the graph repository to raise an error
    mock_graph_repository = AsyncMock()
    mock_graph_repository.execute_read.side_effect = Exception("Graph query failed")

    # Patch the dependencies
    with patch("graph_rag.api.routers.query.get_entity_extractor", return_value=mock_entity_extractor) as mock_get_extractor, \
         patch("graph_rag.api.routers.query.get_graph_repository", return_value=mock_graph_repository) as mock_get_repo:

        response = await test_client.post("/api/v1/query/", json=payload)

        # Verify the mocks were called
        mock_entity_extractor.extract_entities.assert_called_once_with(payload["query_text"])
        mock_graph_repository.execute_read.assert_called_once()

        # Verify the error response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert "detail" in response_data
        assert "Failed to query graph for context" in response_data["detail"]

# TODO: Add test for query with graph context returned
# TODO: Add test for different config parameters (e.g., testing 'k') 