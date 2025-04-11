import pytest
import httpx
import time
import os
from typing import Dict, Any, List
import asyncio
import uuid
from fastapi import status

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
async def test_ingest_and_keyword_search(test_client: httpx.AsyncClient):
    """Verify ingestion and subsequent keyword search."""
    doc_content = "Integration testing involves blue widgets."
    metadata = {"source": "integration_test", "color": "blue"}
    
    # Ingest directly using test_client
    ingest_response = await test_client.post(
        f"{BASE_URL}/ingestion/document",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    assert ingest_response.status_code == status.HTTP_200_OK
    ingest_result = ingest_response.json()
    assert "document_id" in ingest_result
    assert "chunk_ids" in ingest_result
    doc_id = ingest_result["document_id"]
    
    # Keyword Search directly using test_client
    search_query = "widgets"
    limit = 5
    search_response = await test_client.post(
        f"{BASE_URL}/search/chunks/keyword",
        json={"query": search_query, "limit": limit}
    )
    assert search_response.status_code == status.HTTP_200_OK
    keyword_results = search_response.json()
    
    # Assertions on results
    assert "results" in keyword_results
    assert len(keyword_results["results"]) > 0
    assert any(search_query in res["chunk"]["text"] for res in keyword_results["results"])
    assert keyword_results["results"][0]["document"]["id"] == doc_id

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_vector_search(test_client: httpx.AsyncClient):
    """Verify ingestion and subsequent vector similarity search."""
    doc_content = "Semantic search looks for meaning, like finding vehicles when asked about cars."
    metadata = {"source": "integration_test", "topic": "search"}
    query = "automobiles"
    limit = 3
    
    # Ingest directly using test_client
    ingest_response = await test_client.post(
        f"{BASE_URL}/ingestion/document",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    assert ingest_response.status_code == status.HTTP_200_OK
    ingest_result = ingest_response.json()
    doc_id = ingest_result["document_id"]
    
    # Vector Search directly using test_client
    search_response = await test_client.post(
        f"{BASE_URL}/search/chunks/vector",
        json={"query": query, "limit": limit}
    )
    assert search_response.status_code == status.HTTP_200_OK
    vector_results = search_response.json()
    
    # Assertions on results
    assert "results" in vector_results
    assert len(vector_results["results"]) > 0
    assert len(vector_results["results"]) <= limit
    # Check if related content is found (specific assertion depends on embedding model)
    assert any("cars" in res["chunk"]["text"] or "vehicles" in res["chunk"]["text"] for res in vector_results["results"])
    assert vector_results["results"][0]["document"]["id"] == doc_id
    assert "score" in vector_results["results"][0]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_nonexistent_term(test_client: httpx.AsyncClient):
    """Verify searches for unlikely terms return empty results."""
    query = "zzzyyyxxx_nonexistent_term_qwerty"
    limit = 5
    
    # Keyword Search directly using test_client
    keyword_response = await test_client.post(
        f"{BASE_URL}/search/chunks/keyword",
        json={"query": query, "limit": limit}
    )
    assert keyword_response.status_code == status.HTTP_200_OK
    keyword_results = keyword_response.json()
    assert "results" in keyword_results
    assert len(keyword_results["results"]) == 0

    # Vector Search directly using test_client
    vector_response = await test_client.post(
        f"{BASE_URL}/search/chunks/vector",
        json={"query": query, "limit": limit}
    )
    assert vector_response.status_code == status.HTTP_200_OK
    vector_results = vector_response.json()
    assert "results" in vector_results
    assert len(vector_results["results"]) == 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_delete(test_client: httpx.AsyncClient):
    """Verify ingestion and subsequent deletion."""
    doc_content = "This document is created solely for deletion testing."
    metadata = {"source": "integration_test_delete"}
    
    # 1. Ingest directly using test_client
    ingest_response = await test_client.post(
        f"{BASE_URL}/ingestion/document",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": False} # No embedding needed
    )
    assert ingest_response.status_code == status.HTTP_200_OK
    ingest_result = ingest_response.json()
    doc_id = ingest_result["document_id"]
    assert doc_id is not None

    # 2. Verify existence (optional - depends on having a GET /document/{id} endpoint)
    # get_response = await test_client.get(f"{BASE_URL}/documents/{doc_id}")
    # assert get_response.status_code == status.HTTP_200_OK

    # 3. Delete directly using test_client
    delete_response = await test_client.delete(f"{BASE_URL}/documents/{doc_id}")
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {"message": "Document deleted successfully"} # Or similar success message

    # 4. Verify deletion (optional - depends on GET endpoint)
    # get_response_after_delete = await test_client.get(f"{BASE_URL}/documents/{doc_id}")
    # assert get_response_after_delete.status_code == status.HTTP_404_NOT_FOUND

    # 5. Verify searching for it yields no results
    keyword_response = await test_client.post(
        f"{BASE_URL}/search/chunks/keyword",
        json={"query": "deletion testing", "limit": 1}
    )
    assert keyword_response.status_code == status.HTTP_200_OK
    keyword_results = keyword_response.json()
    assert len(keyword_results["results"]) == 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_nonexistent(test_client: httpx.AsyncClient):
    """Test deleting a non-existent document ID."""
    non_existent_id = f"non-existent-id-{uuid.uuid4()}"
    delete_response = await test_client.delete(f"{BASE_URL}/documents/{non_existent_id}") # Adjust endpoint if needed
    assert delete_response.status_code == status.HTTP_404_NOT_FOUND 
    # Check the error message structure based on your API's 404 response
    # assert delete_response.json() == {"detail": "Document not found"} 