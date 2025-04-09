import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, MagicMock

from graph_rag.api.main import app # Assuming app is accessible
from graph_rag.core.graph_rag_engine import QueryResult
from graph_rag.models import Chunk

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio 

@pytest.fixture(scope="module")
async def async_client() -> AsyncClient:
    """Provides an async test client for the FastAPI app."""
    # Use dependency overrides here if needed to inject mock engine for specific tests
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

# --- Test Cases --- 

async def test_query_success(async_client: AsyncClient):
    """Test successful query processing."""
    payload = {
        "query_text": "Tell me about Alice.",
        "config": {"k": 5}
    }
    
    # --- Mocking the RAG Engine --- 
    # We need to mock the rag_engine dependency within the API for this test
    # This assumes the engine dependency is setup correctly in main.py and query.py
    mock_engine_result = QueryResult(
        answer="Alice is a test entity.",
        relevant_chunks=[
            Chunk(id="c1", text="Alice info...", document_id="doc1", metadata={}),
            Chunk(id="c2", text="More about Alice...", document_id="doc2", metadata={})
        ],
        graph_context=None, # Keep it simple for now
        metadata={"source": "mock_engine"}
    )
    
    # Use FastAPI's dependency overrides to inject a mock engine
    # Note: Adjust the path `graph_rag.api.routers.query.get_rag_engine` if your dependency setup differs
    # This assumes `get_rag_engine` is the dependency function used in the router
    # If the dependency is directly on the class, the path might be different.
    # Let's assume `get_rag_engine` is defined in `main.py` and used by the router factory.
    # Path needs adjustment based on where get_rag_engine is defined and used.
    # Assuming it's defined in main.py and accessible via the request state mechanism:
    
    # Simpler approach for testing: Patch the actual engine instance used by the API
    # This is less ideal than dependency override but easier if override setup is complex.
    # Patch target should be the instance created during lifespan, often in app.state
    with patch("graph_rag.api.main.app.state.rag_engine", new_callable=MagicMock) as mock_engine:
        mock_engine.query.return_value = mock_engine_result
        
        response = await async_client.post("/api/v1/query/", json=payload)
        
        # Verify the mock was called
        mock_engine.query.assert_called_once_with(
            query_text=payload["query_text"],
            config=payload["config"]
        )

    # --- Assertions --- 
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    assert response_data["answer"] == mock_engine_result.answer
    assert len(response_data["relevant_chunks"]) == len(mock_engine_result.relevant_chunks)
    assert response_data["relevant_chunks"][0]["id"] == mock_engine_result.relevant_chunks[0].id
    assert response_data["relevant_chunks"][0]["text"] == mock_engine_result.relevant_chunks[0].text
    assert response_data["graph_context"] is None
    assert response_data["metadata"] == mock_engine_result.metadata
    
async def test_query_missing_query_text(async_client: AsyncClient):
    """Test query request missing the required 'query_text' field."""
    payload = { 
        # Missing "query_text"
        "config": {}
    }
    
    response = await async_client.post("/api/v1/query/", json=payload)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("query_text" in err.get("loc", []) and "missing" in err.get("type", "") for err in response_data.get("detail", []))

async def test_query_engine_error(async_client: AsyncClient):
    """Test query handling when the RAG engine raises an exception."""
    payload = {
        "query_text": "Query that causes error",
        "config": {}
    }

    error_message = "Engine processing failed spectacularly!"
    # Patch the engine instance to raise an error
    with patch("graph_rag.api.main.app.state.rag_engine", new_callable=MagicMock) as mock_engine:
        mock_engine.query.side_effect = RuntimeError(error_message)
        
        response = await async_client.post("/api/v1/query/", json=payload)
        
        mock_engine.query.assert_called_once_with(
            query_text=payload["query_text"],
            config=payload["config"]
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()
    assert "detail" in response_data
    assert "Failed to process query" in response_data["detail"]
    # The specific error message might be included depending on the exception handler
    # assert error_message in response_data["detail"]
    assert response_data.get("error_type") == "RuntimeError"

# TODO: Add test for query with graph context returned
# TODO: Add test for different config parameters (e.g., testing 'k') 