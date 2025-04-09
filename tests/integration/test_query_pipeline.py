import pytest
import asyncio
from httpx import AsyncClient
from fastapi import status
import logging
from typing import Dict, Any

# Assuming GraphRepository is needed for verification/setup
from graph_rag.data_stores.memgraph_store import MemgraphStore
from graph_rag.config.settings import settings

logger = logging.getLogger(__name__)

# Helper function to ingest a document (could be shared)
async def ingest_test_document(client: AsyncClient, doc_content: str, metadata: Dict[str, Any]) -> str:
    """Helper to ingest a document via API and wait for basic processing."""
    # Use the actual API endpoint for ingestion
    response = await client.post(
        "/api/v1/ingestion/documents", # Adjust if endpoint differs
        json={"content": doc_content, "metadata": metadata}
    )
    response.raise_for_status()
    doc_id = response.json()["document_id"]

    # Basic wait logic - replace with more robust check if needed
    # In a real scenario, might need to query a status endpoint or DB directly
    await asyncio.sleep(5) # Simple wait for processing to likely complete
    return doc_id


@pytest.mark.asyncio
async def test_basic_query(test_client: AsyncClient):
    """
    Test the basic query endpoint.
    1. Ingest a known document.
    2. Query for information related to the document.
    3. Assert the response contains relevant context (e.g., chunk content).
    """
    # 1. Ingest a known document
    doc_content = "The Eiffel Tower is located in Paris, the capital of France."
    metadata = {"source": "query-test-basic"}
    try:
        doc_id = await ingest_test_document(test_client, doc_content, metadata)
        logger.info(f"Ingested document {doc_id} for query test.")
    except Exception as e:
        pytest.fail(f"Failed to ingest test document: {e}")

    # 2. Query the endpoint
    query_text = "Where is the Eiffel Tower?"
    logger.info(f"Submitting query: '{query_text}'")
    response = await test_client.post(
        "/api/v1/query",
        json={
            "query_text": query_text,
            "k": 5  # Request up to 5 results
        }
    )

    # 3. Assertions
    assert response.status_code == status.HTTP_200_OK, f"Expected 200 OK, got {response.status_code}. Response: {response.text}"

    response_data = response.json()

    # Verify response structure
    assert "query" in response_data, "Response should contain 'query'"
    assert "results" in response_data, "Response should contain 'results'"
    assert isinstance(response_data["results"], list), "'results' should be a list"
    
    # Verify query text is returned correctly
    assert response_data["query"] == query_text, "Response should echo the query text"

    # Check if we got any results
    assert len(response_data["results"]) > 0, "Expected at least one result"

    # Verify result structure
    first_result = response_data["results"][0]
    assert "content" in first_result, "Result should contain 'content'"
    assert "metadata" in first_result, "Result should contain 'metadata'"
    assert "chunk_id" in first_result["metadata"], "Result metadata should contain 'chunk_id'"
    assert "document_id" in first_result["metadata"], "Result metadata should contain 'document_id'"

    # Check if the content contains relevant information
    assert "Paris" in first_result["content"], "Result content missing expected entity 'Paris'"
    assert "Eiffel Tower" in first_result["content"], "Result content missing expected entity 'Eiffel Tower'"

    logger.info(f"Query successful, received relevant context: {first_result['content']}")

@pytest.mark.asyncio
async def test_query_no_entities(test_client: AsyncClient):
    """Test query handling when no entities are found in the query."""
    query_text = "This is a query with no named entities"
    response = await test_client.post(
        "/api/v1/query",
        json={
            "query_text": query_text,
            "k": 5
        }
    )

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    
    assert response_data["query"] == query_text
    assert len(response_data["results"]) == 0, "Expected no results for query with no entities"

@pytest.mark.asyncio
async def test_query_invalid_request(test_client: AsyncClient):
    """Test query endpoint with invalid request format."""
    # Missing query_text
    response = await test_client.post(
        "/api/v1/query",
        json={
            "k": 5
        }
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("query_text" in err.get("loc", []) for err in response_data["detail"])

# Add more tests later for different query types, edge cases, etc. 