import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock
from graph_rag.core.interfaces import SearchResultData, ChunkData, DocumentData
from pydantic_core import ValidationError

# from graph_rag.api.main import app # No longer needed, use test_client fixture
from graph_rag.api.schemas import (
    SearchQueryRequest, SearchQueryResponse, SearchResultSchema, 
    ChunkResultSchema, DocumentResultSchema
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
    
    # Prepare mock engine response (List[SearchResultData])
    mock_chunk = ChunkData(id="key_chunk1", text="Keyword result 1", document_id="doc_key1")
    mock_doc = DocumentData(id="doc_key1", content="Mock document content", metadata={"source": "keyword_test"})
    mock_engine_results = [
        SearchResultData(chunk=mock_chunk, score=0.95, document=mock_doc)
    ]
    
    mock_graph_rag_engine.retrieve_context.return_value = mock_engine_results
    mock_graph_rag_engine.reset_mock() # Clear previous calls
    mock_graph_rag_engine.retrieve_context.return_value = mock_engine_results

    # Prepare request payload
    request_payload = SearchQueryRequest(
        query=query_text,
        search_type="keyword",
        limit=limit
    ).model_dump()

    response = await test_client.post("/api/v1/search/query", json=request_payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["query"] == query_text
    assert response_data["search_type"] == "keyword"
    assert len(response_data["results"]) == len(mock_engine_results)
    # Check structure of the first result (SearchResultSchema)
    first_result = response_data["results"][0]
    assert first_result["score"] == 0.95
    assert isinstance(first_result["chunk"], dict)
    assert first_result["chunk"]["id"] == mock_chunk.id
    assert first_result["chunk"]["text"] == mock_chunk.text
    assert isinstance(first_result["document"], dict)
    assert first_result["document"]["id"] == mock_doc.id
    assert first_result["document"]["metadata"] == mock_doc.metadata

    mock_graph_rag_engine.retrieve_context.assert_awaited_once_with(
        query=query_text, search_type="keyword", limit=limit
    )

@pytest.mark.asyncio
async def test_unified_search_vector(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test the unified search endpoint with search_type='vector'."""
    query_text = "test vector query"
    limit = 3
    
    # Prepare mock engine response
    mock_chunk_vec = ChunkData(id="vec_chunk1", text="Vector result 1", document_id="doc_vec1")
    mock_engine_results_vec = [
        SearchResultData(chunk=mock_chunk_vec, score=0.88, document=None) # Test case without document
    ]
    
    mock_graph_rag_engine.retrieve_context.return_value = mock_engine_results_vec
    mock_graph_rag_engine.reset_mock()
    mock_graph_rag_engine.retrieve_context.return_value = mock_engine_results_vec

    request_payload = SearchQueryRequest(
        query=query_text,
        search_type="vector",
        limit=limit
    ).model_dump()

    response = await test_client.post("/api/v1/search/query", json=request_payload)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["search_type"] == "vector"
    assert len(response_data["results"]) == 1
    first_result = response_data["results"][0]
    assert first_result["score"] == 0.88
    assert first_result["chunk"]["id"] == mock_chunk_vec.id
    assert first_result["document"] is None # Check document is None as per mock

    mock_graph_rag_engine.retrieve_context.assert_awaited_once_with(
        query=query_text, search_type="vector", limit=limit
    )

@pytest.mark.asyncio
async def test_unified_search_engine_error(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test handling of errors raised by the GraphRAGEngine during search."""
    query_text = "query causing engine error"
    search_type = "keyword"
    limit = 5
    error_message = "Simulated engine search error"
    
    mock_graph_rag_engine.retrieve_context.side_effect = Exception(error_message)
    mock_graph_rag_engine.reset_mock()
    mock_graph_rag_engine.retrieve_context.side_effect = Exception(error_message)

    request_payload = SearchQueryRequest(
        query=query_text,
        search_type=search_type,
        limit=limit
    ).model_dump()

    response = await test_client.post("/api/v1/search/query", json=request_payload)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Check detail message (might depend on exact exception handling in the router)
    assert "internal server error" in response.json()["detail"]

    mock_graph_rag_engine.retrieve_context.assert_awaited_once_with(
        query=query_text, search_type=search_type, limit=limit
    )

@pytest.mark.asyncio
async def test_unified_search_invalid_search_type(
    test_client: AsyncClient, mock_graph_rag_engine: AsyncMock
):
    """Test unified search with an invalid search_type value."""
    with pytest.raises(ValidationError) as excinfo:
        SearchQueryRequest(
            query="test query",
            search_type="invalid_type", # Use an invalid type
            limit=5
        )
    assert "search_type" in str(excinfo.value) # Check that the error is related to search_type
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

    # Test with zero limit
    with pytest.raises(ValidationError) as excinfo_zero:
        SearchQueryRequest(query="limit test", search_type="vector", limit=0)
    assert "limit" in str(excinfo_zero.value)

    # Test with very large limit (should ideally be capped by service/config, but test API validation)
    # Assuming API doesn't impose its own large cap, let's test if it passes validation
    # mock_search_service.search_chunks.return_value = [] # Need to mock for the call to succeed
    # response = await client.get("/api/v1/search/chunks/vector", params={"query": "limit test", "limit": 9999})
    # assert response.status_code == status.HTTP_200_OK # Or 422 if API caps input

    # TODO: Add test for invalid limit for vector search if needed 