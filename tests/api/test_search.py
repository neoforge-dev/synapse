from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient
from pydantic_core import ValidationError

# from graph_rag.api.main import app # No longer needed, use test_client fixture
from graph_rag.api.schemas import (
    SearchQueryRequest,
)

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# --- Test Cases for Unified Search Endpoint ---


@pytest.mark.asyncio
async def test_unified_search_keyword(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test the unified search endpoint with search_type='keyword'."""
    query_text = "test keyword query"
    limit = 5

    # No need to set return_value here, the fixture uses a side_effect
    # mock_graph_rag_engine.query.return_value = mock_query_result # REMOVED
    mock_graph_rag_engine.reset_mock()  # Keep reset_mock

    # Prepare request payload
    request_payload = SearchQueryRequest(
        query=query_text, search_type="keyword", limit=limit
    ).model_dump()

    response = await test_client.post("/api/v1/search/query", json=request_payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["query"] == query_text
    assert response_data["search_type"] == "keyword"
    # Check against the mock engine side_effect from conftest.py
    assert len(response_data["results"]) == 1
    first_result = response_data["results"][0]
    assert first_result["score"] == 0.0
    assert isinstance(first_result["chunk"], dict)
    assert first_result["chunk"]["id"] == "key_chunk1"  # From conftest mock_query
    assert first_result["chunk"]["text"] == "Keyword result"  # From conftest mock_query
    assert (
        first_result["chunk"]["document_id"] == "doc_key1"
    )  # From conftest mock_query
    # Check document from mock_get_document in conftest.py
    assert first_result["document"] is not None
    assert first_result["document"]["id"] == "doc_key1"
    assert first_result["document"]["metadata"] == {"topic": "keyword"}

    # Validate LLM response and graph context from conftest mock_query
    assert response_data["llm_response"] == "Mock keyword response"
    assert response_data["graph_context"] == "Mock keyword context"

    # Check that the mock engine was called correctly
    mock_graph_rag_engine.query.assert_awaited_once_with(
        query_text,
        config={
            "k": limit,
            "search_type": "keyword",
            "include_graph": False,  # Default used by router when calling engine
        },
    )


@pytest.mark.asyncio
async def test_unified_search_vector(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test the unified search endpoint with search_type='vector'."""
    query_text = "test vector query"
    limit = 3

    # No need to set return_value here, the fixture uses a side_effect
    # mock_graph_rag_engine.query.return_value = mock_query_result_vec # REMOVED
    mock_graph_rag_engine.reset_mock()  # Keep reset_mock

    request_payload = SearchQueryRequest(
        query=query_text, search_type="vector", limit=limit
    ).model_dump()

    response = await test_client.post("/api/v1/search/query", json=request_payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()

    assert response_data["query"] == query_text
    assert response_data["search_type"] == "vector"
    # Check against the mock engine side_effect from conftest.py
    assert len(response_data["results"]) == 1
    first_result = response_data["results"][0]
    assert first_result["score"] == 0.0
    assert isinstance(first_result["chunk"], dict)
    assert first_result["chunk"]["id"] == "vec_chunk1"  # From conftest mock_query
    assert first_result["chunk"]["text"] == "Vector result"  # From conftest mock_query
    assert (
        first_result["chunk"]["document_id"] == "doc_vec1"
    )  # From conftest mock_query
    # Check document from mock_get_document in conftest.py
    assert first_result["document"] is not None
    assert first_result["document"]["id"] == "doc_vec1"
    assert first_result["document"]["metadata"] == {"topic": "vector"}

    # Validate LLM response and graph context from conftest mock_query
    assert response_data["llm_response"] == "Mock vector response"
    assert response_data["graph_context"] == "Mock vector context"

    mock_graph_rag_engine.query.assert_awaited_once_with(
        query_text,
        config={
            "k": limit,
            "search_type": "vector",
            "include_graph": False,  # Default used by router when calling engine
        },
    )


@pytest.mark.asyncio
async def test_unified_search_engine_error(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test handling of errors raised by the GraphRAGEngine during search."""
    query_text = "query causing engine error"
    search_type = "keyword"
    limit = 5
    error_message = "Simulated engine query error"

    mock_graph_rag_engine.query.side_effect = Exception(error_message)
    mock_graph_rag_engine.reset_mock()

    request_payload = SearchQueryRequest(
        query=query_text, search_type=search_type, limit=limit
    ).model_dump()

    response = await test_client.post("/api/v1/search/query", json=request_payload)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Check detail message (might depend on exact exception handling in the router)
    # Updated to check for the specific error detail used in the endpoint
    assert "Search failed due to an internal server error." in response.json()["detail"]

    mock_graph_rag_engine.query.assert_awaited_once_with(
        query_text,  # Pass query_text positionally
        config={"k": limit, "search_type": search_type, "include_graph": False},
    )


@pytest.mark.asyncio
async def test_unified_search_invalid_search_type(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test unified search with an invalid search_type value."""
    with pytest.raises(ValidationError) as excinfo:
        SearchQueryRequest(
            query="test query",
            search_type="invalid_type",  # Use an invalid type
            limit=5,
        )
    assert "String should match pattern" in str(excinfo.value)
    assert "vector|keyword" in str(excinfo.value)
    # No need to call the endpoint, validation happens on model creation


@pytest.mark.asyncio
async def test_unified_search_invalid_limit(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test unified search with invalid limit values."""
    # Test with negative limit
    with pytest.raises(ValidationError) as excinfo_neg:
        SearchQueryRequest(query="limit test", search_type="keyword", limit=-1)
    assert "limit" in str(excinfo_neg.value)
    # Add assertion for ValidationError message detail
    assert "Input should be greater than 0" in str(excinfo_neg.value)

    # Test with zero limit
    with pytest.raises(ValidationError) as excinfo_zero:
        SearchQueryRequest(query="limit test", search_type="vector", limit=0)
    assert "limit" in str(excinfo_zero.value)
    # Add assertion for ValidationError message detail
    assert "Input should be greater than 0" in str(excinfo_zero.value)

    # Test with very large limit (should ideally be capped by service/config, but test API validation)
    # Assuming API doesn't impose its own large cap, let's test if it passes validation
    # mock_search_service.search_chunks.return_value = [] # Need to mock for the call to succeed
    # response = await client.get("/api/v1/search/chunks/vector", params={"query": "limit test", "limit": 9999})
    # assert response.status_code == status.HTTP_200_OK # Or 422 if API caps input

    # TODO: Add test for invalid limit for vector search if needed
