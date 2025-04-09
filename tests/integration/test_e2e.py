import pytest
import httpx
import time
import os
from typing import Dict, Any, List
import asyncio
import uuid

# Base URL for the running API service
# Assumes it's running on localhost:8000 as per docker-compose
BASE_URL = os.getenv("INTEGRATION_TEST_BASE_URL", "http://localhost:8000/api/v1")

# --- Helper Functions ---

async def wait_for_service(url: str, timeout: int = 30):
    """Wait for the API service to be available."""
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{url.replace('/api/v1','/')}/health") # Use health endpoint
                if response.status_code == 200:
                    print(f"Service {url} is up!")
                    return True
            except httpx.RequestError as e:
                print(f"Service {url} not up yet ({e}), waiting...")
            await asyncio.sleep(2)
    raise TimeoutError(f"Service {url} did not become available within {timeout} seconds.")

async def ingest_test_document(client: httpx.AsyncClient, doc_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to ingest a document."""
    response = await client.post(
        f"{BASE_URL}/ingestion/document",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    response.raise_for_status() # Raise exception for non-2xx status
    return response.json()

async def search_keyword(client: httpx.AsyncClient, query: str, limit: int = 5) -> Dict[str, Any]:
    """Helper for keyword search."""
    response = await client.post(
        f"{BASE_URL}/search/chunks/keyword",
        json={"query": query, "limit": limit}
    )
    response.raise_for_status()
    return response.json()

async def search_vector(client: httpx.AsyncClient, query: str, limit: int = 5) -> Dict[str, Any]:
    """Helper for vector search."""
    response = await client.post(
        f"{BASE_URL}/search/chunks/vector",
        json={"query": query, "limit": limit}
    )
    response.raise_for_status()
    return response.json()

# --- Test Fixtures ---

@pytest.fixture(scope="session")
async def http_client() -> httpx.AsyncClient:
    """Provides an HTTPX client for the test session."""
    # Optional: Wait for service to be ready before starting tests
    # Requires importing asyncio
    # import asyncio
    # await wait_for_service(BASE_URL)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client

# --- Test Cases ---

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_keyword_search(http_client: httpx.AsyncClient):
    """Verify ingestion and subsequent keyword search."""
    doc_content = "Integration testing involves blue widgets."
    metadata = {"source": "integration_test", "color": "blue"}
    
    # Ingest
    ingest_result = await ingest_test_document(http_client, doc_content, metadata)
    assert "document_id" in ingest_result
    assert ingest_result["num_chunks"] > 0
    
    # Allow some time for potential indexing/consistency
    await asyncio.sleep(1)
    
    # Keyword Search
    search_term = "widgets"
    search_results = await search_keyword(http_client, search_term)
    
    assert search_results["query"] == search_term
    assert len(search_results["results"]) > 0
    found_match = any(search_term in r["content"] for r in search_results["results"])
    assert found_match, f"Keyword '{search_term}' not found in search results: {search_results['results']}"
    # Check if the source document id matches
    assert search_results["results"][0]["document_id"] == ingest_result["document_id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_vector_search(http_client: httpx.AsyncClient):
    """Verify ingestion and subsequent vector similarity search."""
    doc_content = "Semantic search looks for meaning, like finding vehicles when asked about cars."
    metadata = {"source": "integration_test", "topic": "search"}
    query = "automobiles"
    
    # Ingest
    ingest_result = await ingest_test_document(http_client, doc_content, metadata)
    assert "document_id" in ingest_result
    assert ingest_result["num_chunks"] > 0
    
    # Allow some time for potential indexing/consistency and embedding calculation
    await asyncio.sleep(2) 
    
    # Vector Search
    search_results = await search_vector(http_client, query)
    
    assert search_results["query"] == query
    assert len(search_results["results"]) > 0, "Vector search returned no results."
    
    # Basic check: the content should be somewhat related
    # A more robust check would involve comparing scores or specific content fragments
    assert "cars" in search_results["results"][0]["content"], "Top vector search result content doesn't seem related."
    assert search_results["results"][0]["score"] > 0.5, "Vector search score is unexpectedly low."
    assert search_results["results"][0]["document_id"] == ingest_result["document_id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_nonexistent_term(http_client: httpx.AsyncClient):
    """Verify searches for unlikely terms return empty results."""
    query = "zzzyyyxxx_nonexistent_term_qwerty"
    
    # Keyword Search
    keyword_results = await search_keyword(http_client, query)
    assert keyword_results["query"] == query
    assert len(keyword_results["results"]) == 0
    
    # Vector Search
    vector_results = await search_vector(http_client, query)
    assert vector_results["query"] == query
    # Vector search might still return *something* based on similarity, 
    # but unlikely to be highly relevant for a truly random string.
    # Depending on threshold, it might be empty or contain low-scoring results.
    assert isinstance(vector_results["results"], list) # Just ensure it returns a list 

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_delete(http_client: httpx.AsyncClient):
    """Verify ingestion and subsequent deletion."""
    doc_content = "This document is created solely for deletion testing."
    metadata = {"source": "integration_test_delete"}
    
    # 1. Ingest
    ingest_result = await ingest_test_document(http_client, doc_content, metadata)
    doc_id = ingest_result["document_id"]
    assert doc_id is not None
    assert ingest_result["num_chunks"] > 0
    initial_chunk_ids = ingest_result["chunk_ids"]
    
    # Optional: Verify document exists via GET (requires GET endpoint)
    # get_response = await http_client.get(f"/documents/{doc_id}")
    # assert get_response.status_code == 200
    
    # 2. Delete
    delete_response = await http_client.delete(f"/documents/{doc_id}")
    assert delete_response.status_code == 204
    
    # 3. Verify Deletion
    # Attempt to GET the deleted document - should be 404
    get_response_after_delete = await http_client.get(f"/documents/{doc_id}")
    assert get_response_after_delete.status_code == 404
    
    # Attempt to GET chunks for the deleted document - should be empty
    get_chunks_response = await http_client.get(f"/chunks/by_document/{doc_id}")
    assert get_chunks_response.status_code == 200
    assert len(get_chunks_response.json()) == 0
    
    # Optional: Attempt keyword search for content - should not find deleted chunks
    await asyncio.sleep(1) # Allow time for potential consistency
    keyword_search_response = await search_keyword(http_client, "deletion testing")
    found_deleted = any(c["chunk_id"] in initial_chunk_ids for c in keyword_search_response["results"])
    assert not found_deleted, "Search found chunks that should have been deleted."

@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_nonexistent(http_client: httpx.AsyncClient):
    """Test deleting a non-existent document ID."""
    non_existent_id = f"non-existent-id-{uuid.uuid4()}"
    delete_response = await http_client.delete(f"/documents/{non_existent_id}")
    assert delete_response.status_code == 404 