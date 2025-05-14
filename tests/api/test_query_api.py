from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient

# Import QueryResult from where it is defined, GraphContext is a Tuple
from graph_rag.core.graph_rag_engine import QueryResult as DomainQueryResult
from graph_rag.core.interfaces import GraphRAGEngine

# Import domain models and core models needed for mocking engine response
from graph_rag.domain.models import Chunk, Entity, Relationship

# Removed direct app import
# from graph_rag.api.main import app
# Removed API QueryResult model, using QueryResponse
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


# --- Fixtures (if specific mocking needed beyond conftest) ---
@pytest.fixture
def mock_query_engine() -> AsyncMock:
    engine_mock = AsyncMock(spec=GraphRAGEngine)

    # Define a sample successful response structure
    async def mock_query_success(query_text, k):
        mock_entities = [Entity(id="e1", type="Person", properties={"name": "Alice"})]
        mock_relationships = []  # Empty list for this example
        return DomainQueryResult(
            answer=f"Answer for {query_text}",
            relevant_chunks=[
                Chunk(id="c1", text="Chunk 1 content", document_id="d1", metadata={}),
                Chunk(id="c2", text="Chunk 2 content", document_id="d2", metadata={}),
            ],
            graph_context=(mock_entities, mock_relationships),  # Use Tuple structure
            metadata={"query_time_ms": 123},
        )

    engine_mock.query.side_effect = mock_query_success
    return engine_mock


# --- Test Cases ---


# Use the shared 'test_client' fixture from conftest.py
# Mock dependencies using fixtures or direct patching within tests
@pytest.mark.asyncio
async def test_query_success(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test successful query processing using the mocked engine from conftest."""
    payload = {"query_text": "Tell me about Alice.", "k": 5}

    # Configure the mock engine from conftest fixture for this test
    async def mock_query_specific(query_text, k=None, config=None):
        (
            k if k is not None else (config.get("k") if config else 5)
        )  # Handle both ways k might be passed
        return DomainQueryResult(
            answer=f"Mocked answer about {query_text}",
            relevant_chunks=[
                Chunk(
                    id="alice_c1",
                    text="Alice lives here.",
                    document_id="doc_alice",
                    properties={"score": 0.9},
                ),
            ],
            graph_context=None,  # Keep as None for this specific test case
            metadata={"source": "mock_engine"},
        )

    mock_graph_rag_engine.query.side_effect = mock_query_specific
    mock_graph_rag_engine.reset_mock()  # Reset before call if needed
    mock_graph_rag_engine.query.side_effect = mock_query_specific

    response = await test_client.post("/api/v1/query", json=payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["answer"] == "Mocked answer about Tell me about Alice."
    assert len(response_data["relevant_chunks"]) == 1
    assert response_data["relevant_chunks"][0]["id"] == "alice_c1"
    assert response_data["relevant_chunks"][0]["text"] == "Alice lives here."
    assert response_data["relevant_chunks"][0]["score"] == 0.9
    assert response_data["graph_context"] is None
    mock_graph_rag_engine.query.assert_awaited_once_with(
        payload["query_text"], config={"k": payload["k"]}
    )


@pytest.mark.asyncio
async def test_query_success_with_graph_context(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test successful query processing including graph context."""
    payload = {"query_text": "Who is connected to Bob?", "k": 2}

    # Configure mock engine to return graph context
    mock_entities = [
        Entity(id="bob", type="Person", properties={"name": "Bob"}),
        Entity(id="carol", type="Person", properties={"name": "Carol"}),
    ]
    mock_relationships = [
        Relationship(id="rel1", type="FRIENDS", source_id="bob", target_id="carol")
    ]

    async def mock_query_with_graph(query_text, k=None, config=None):
        (
            k if k is not None else (config.get("k") if config else 2)
        )  # Handle both ways k might be passed
        return DomainQueryResult(
            answer=f"Mocked answer about {query_text} graph.",
            relevant_chunks=[
                Chunk(
                    id="bob_c1",
                    text="Bob info",
                    document_id="d_bob",
                    properties={"score": 0.85},
                )
            ],
            graph_context=(mock_entities, mock_relationships),
            metadata={"source": "mock_engine_graph"},
        )

    mock_graph_rag_engine.query.side_effect = mock_query_with_graph
    mock_graph_rag_engine.reset_mock()
    mock_graph_rag_engine.query.side_effect = mock_query_with_graph

    response = await test_client.post("/api/v1/query", json=payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert (
        response_data["answer"] == "Mocked answer about Who is connected to Bob? graph."
    )
    assert len(response_data["relevant_chunks"]) == 1
    assert response_data["relevant_chunks"][0]["id"] == "bob_c1"
    assert response_data["relevant_chunks"][0]["score"] == 0.85
    assert response_data["graph_context"] is not None
    assert isinstance(response_data["graph_context"], dict)  # API model is a dict
    assert len(response_data["graph_context"].get("entities", [])) == 2
    assert len(response_data["graph_context"].get("relationships", [])) == 1
    # Check if the content matches (simplified check)
    assert response_data["graph_context"]["entities"][0]["id"] == "bob"
    assert response_data["graph_context"]["relationships"][0]["id"] == "rel1"

    mock_graph_rag_engine.query.assert_awaited_once_with(
        payload["query_text"], config={"k": payload["k"]}
    )


@pytest.mark.asyncio
async def test_query_engine_error(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test handling of errors raised by the GraphRAGEngine during query."""
    payload = {"query_text": "Query that causes error.", "k": 3}

    # Configure mock engine to raise an exception
    error_message = "Simulated engine failure"

    async def raise_exception(*args, **kwargs):
        raise Exception(error_message)

    mock_graph_rag_engine.query.side_effect = raise_exception
    mock_graph_rag_engine.reset_mock()  # Reset before call
    mock_graph_rag_engine.query.side_effect = raise_exception

    response = await test_client.post("/api/v1/query", json=payload)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()
    assert "detail" in response_data
    assert error_message in response_data["detail"]
    mock_graph_rag_engine.query.assert_awaited_once_with(
        payload["query_text"], config={"k": payload["k"]}
    )


@pytest.mark.asyncio
async def test_query_invalid_request_missing_text(test_client: AsyncClient):
    """Test query endpoint with missing query_text."""
    payload = {"k": 5}  # Missing query_text

    response = await test_client.post("/api/v1/query", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_query_invalid_request_bad_k_type(test_client: AsyncClient):
    """Test query endpoint with non-integer k."""
    payload = {
        "query_text": "Valid query",
        "k": "five",  # Invalid type for k
    }

    response = await test_client.post("/api/v1/query", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_query_missing_query_text(test_client: AsyncClient):
    """Test query request missing the required 'query_text' field."""
    payload = {
        # Missing "query_text"
        "k": 5
    }

    response = await test_client.post("/api/v1/query", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any(
        "query_text" in err.get("loc", []) and "missing" in err.get("type", "")
        for err in response_data.get("detail", [])
    )


@pytest.mark.asyncio
async def test_query_no_entities(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test query processing when the engine finds no relevant entities."""
    payload = {"query_text": "This query has no relevant entities.", "k": 5}

    # Configure mock engine to return a result indicating no entities were relevant
    async def mock_query_no_entities(query_text, k=None, config=None):
        k if k is not None else (config.get("k") if config else 5)
        return DomainQueryResult(
            answer="Could not find relevant information based on entities.",
            relevant_chunks=[],  # No chunks if no entities were used
            graph_context=None,
            metadata={"source": "mock_engine_no_entities"},
        )

    mock_graph_rag_engine.query.side_effect = mock_query_no_entities
    mock_graph_rag_engine.reset_mock()  # Reset before call
    mock_graph_rag_engine.query.side_effect = mock_query_no_entities

    response = await test_client.post("/api/v1/query", json=payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "Could not find relevant information" in response_data["answer"]
    assert len(response_data["relevant_chunks"]) == 0
    assert response_data["graph_context"] is None
    mock_graph_rag_engine.query.assert_awaited_once_with(
        payload["query_text"], config={"k": payload["k"]}
    )


# TODO: Add test for query with graph context returned
# TODO: Add test for different config parameters (e.g., testing 'k')
