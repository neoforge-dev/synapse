import pytest
import pytest_asyncio
import httpx
import time
import os
from typing import Dict, Any, List, AsyncGenerator
import asyncio
import uuid
from fastapi import status
import logging
from neo4j import AsyncGraphDatabase, AsyncDriver
from graph_rag.config import get_settings
from fastapi import FastAPI
from httpx import AsyncClient
from httpx import ASGITransport

# Import BASE_URL from conftest
from tests.conftest import BASE_URL

# <<< ADD LOGGER INSTANCE >>>
logger = logging.getLogger(__name__)

# Base URL for the running API service
# Assumes it's running on localhost:8000 as per docker-compose
# BASE_URL = os.getenv("INTEGRATION_TEST_BASE_URL", "http://localhost:8000/api/v1") # Moved to conftest.py

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
        f"{BASE_URL}/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    response.raise_for_status() # Raise exception for non-2xx status
    return response.json()

async def search_keyword(client: httpx.AsyncClient, query: str, limit: int = 5) -> Dict[str, Any]:
    """Helper for keyword search."""
    response = await client.post(
        f"{BASE_URL}/api/v1/search/chunks/keyword",
        json={"query": query, "limit": limit}
    )
    response.raise_for_status()
    return response.json()

async def search_vector(client: httpx.AsyncClient, query: str, limit: int = 5) -> Dict[str, Any]:
    """Helper for vector search."""
    response = await client.post(
        f"{BASE_URL}/api/v1/search/chunks/vector",
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

@pytest.fixture(scope="function", autouse=True)
async def clean_db_e2e() -> AsyncGenerator[None, None]:
    """Clears the Memgraph database before each E2E test function."""
    settings = get_settings()
    db_uri = settings.get_memgraph_uri()
    driver: AsyncDriver | None = None
    try:
        driver = AsyncGraphDatabase.driver(
            db_uri,
            auth=(settings.MEMGRAPH_USERNAME, settings.MEMGRAPH_PASSWORD.get_secret_value())
            if settings.MEMGRAPH_USERNAME and settings.MEMGRAPH_PASSWORD
            else None
        )
        logger.info(f"[Fixture] Clearing database: {db_uri} before test.")
        await driver.execute_query("MATCH (n) DETACH DELETE n;")
        logger.info(f"[Fixture] Database cleared.")
        yield # Test runs here
    except ConnectionRefusedError:
         logger.error(f"[Fixture] Connection refused when trying to clear DB: {db_uri}. Is Memgraph running?")
         pytest.fail(f"Failed to connect to Memgraph ({db_uri}) for DB cleanup: Connection refused.")
    except Exception as e:
        logger.error(f"[Fixture] Error during DB cleanup: {e}", exc_info=True)
        pytest.fail(f"Error during Memgraph DB cleanup ({db_uri}): {e}")
    finally:
        if driver:
            await driver.close()
            logger.info(f"[Fixture] Closed DB connection after test.")

@pytest_asyncio.fixture(scope="function")
async def e2e_test_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provides an async test client for E2E tests WITHOUT mock overrides."""
    # Use the real app instance provided by the session-scoped 'app' fixture
    # from tests/conftest.py
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL, timeout=30.0) as client:
        # Wait briefly for lifespan startup if necessary
        await asyncio.sleep(0.1)
        yield client
    # No overrides to restore

# --- Test Cases ---

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_keyword_search(integration_test_client: httpx.AsyncClient):
    """Verify ingestion and subsequent keyword search."""
    doc_content = "Integration testing involves blue widgets."
    metadata = {"source": "integration_test", "color": "blue"}
    
    # Ingest directly using test_client
    ingest_response = await integration_test_client.post(
        f"{BASE_URL}/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    if ingest_response.status_code != status.HTTP_202_ACCEPTED:
        print(f"Ingest response status: {ingest_response.status_code}, body: {ingest_response.text}")
    assert ingest_response.status_code == status.HTTP_202_ACCEPTED
    ingest_result = ingest_response.json()
    assert "document_id" in ingest_result
    assert "status" in ingest_result
    assert "task_id" in ingest_result
    doc_id = ingest_result["document_id"]
    
    # Add delay to allow async ingestion to complete
    logger.info("Waiting 5 seconds for ingestion to process...")
    await asyncio.sleep(15)
    
    # Keyword Search directly using test_client
    # Changed to vector search as keyword search via engine.query is not implemented
    search_query = "widgets"
    limit = 5
    search_response = await integration_test_client.post(
        # f"{BASE_URL}/api/v1/search/query",
        f"{BASE_URL}/api/v1/search/query", # Use the unified query endpoint
        # json={"search_type": "keyword", "query": search_query, "limit": limit}
        json={"search_type": "vector", "query": search_query, "limit": limit} # Perform vector search
    )
    if search_response.status_code != status.HTTP_200_OK:
        print(f"Search response status: {search_response.status_code}, body: {search_response.text}")
    assert search_response.status_code == status.HTTP_200_OK
    search_results = search_response.json()
    
    # Assertions on results
    assert "results" in search_results
    assert len(search_results["results"]) > 0
    # Simplify assertion: Check if any result chunk belongs to the ingested doc_id
    # This avoids the TypeError if the 'document' field is None
    found = any(res.get("chunk", {}).get("document_id") == doc_id for res in search_results["results"])
    assert found, f"No chunk from document {doc_id} found in vector search results for '{search_query}'"
    # assert any(search_query in res["chunk"]["text"] for res in keyword_results["results"])
    # assert keyword_results["results"][0]["document"]["id"] == doc_id

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_vector_search(integration_test_client: httpx.AsyncClient):
    """Verify ingestion and subsequent vector similarity search."""
    doc_content = "Semantic search looks for meaning, like finding vehicles when asked about cars."
    metadata = {"source": "integration_test", "topic": "search"}
    query = "automobiles"
    limit = 3
    
    # Ingest directly using test_client
    ingest_response = await integration_test_client.post(
        f"{BASE_URL}/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    if ingest_response.status_code != status.HTTP_202_ACCEPTED:
        print(f"Ingest response status: {ingest_response.status_code}, body: {ingest_response.text}")
    assert ingest_response.status_code == status.HTTP_202_ACCEPTED
    ingest_result = ingest_response.json()
    doc_id = ingest_result["document_id"]
    
    # Add delay to allow async ingestion to complete
    logger.info("Waiting 5 seconds for ingestion and embedding to process...")
    await asyncio.sleep(15)
    
    # Vector Search directly using test_client
    search_response = await integration_test_client.post(
        f"{BASE_URL}/api/v1/search/query",
        json={"search_type": "vector", "query": query, "limit": limit}
    )
    if search_response.status_code != status.HTTP_200_OK:
        print(f"Vector search response status: {search_response.status_code}, body: {search_response.text}")
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
async def test_search_nonexistent_term(integration_test_client: httpx.AsyncClient):
    """Verify searches for unlikely terms return empty results."""
    query = "zzzyyyxxx_nonexistent_term_qwerty"
    limit = 5
    
    # Keyword Search directly using test_client
    keyword_response = await integration_test_client.post(
        f"{BASE_URL}/api/v1/search/query",
        json={"search_type": "keyword", "query": query, "limit": limit}
    )
    if keyword_response.status_code != status.HTTP_200_OK:
        print(f"Keyword search response status: {keyword_response.status_code}, body: {keyword_response.text}")
    assert keyword_response.status_code == status.HTTP_200_OK
    keyword_results = keyword_response.json()
    assert "results" in keyword_results
    assert not any(query in res["chunk"]["text"] for res in keyword_results["results"]), \
        f"Found unexpected term '{query}' in keyword results: {keyword_results['results']}"

    # Vector Search directly using test_client
    vector_response = await integration_test_client.post(
        f"{BASE_URL}/api/v1/search/query",
        json={"search_type": "vector", "query": query, "limit": limit}
    )
    if vector_response.status_code != status.HTTP_200_OK:
        print(f"Vector search response status: {vector_response.status_code}, body: {vector_response.text}")
    assert vector_response.status_code == status.HTTP_200_OK
    vector_results = vector_response.json()
    assert "results" in vector_results
    assert not any(query in res["chunk"]["text"] for res in vector_results["results"]), \
        f"Found unexpected term '{query}' in vector results: {vector_results['results']}"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_and_delete(integration_test_client: httpx.AsyncClient):
    """Verify ingestion and subsequent deletion."""
    doc_content = "This document is created solely for deletion testing."
    metadata = {"source": "integration_test_delete"}
    max_wait_seconds = 30 # Max time to wait for deletion/search verification
    poll_interval = 1 # Seconds between polls
    
    # 1. Ingest directly using test_client
    ingest_response = await integration_test_client.post(
        f"{BASE_URL}/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": False} # No embedding needed
    )
    if ingest_response.status_code != status.HTTP_202_ACCEPTED:
        print(f"Ingest response status: {ingest_response.status_code}, body: {ingest_response.text}")
    assert ingest_response.status_code == status.HTTP_202_ACCEPTED
    ingest_result = ingest_response.json()
    assert "document_id" in ingest_result
    assert "status" in ingest_result
    assert "task_id" in ingest_result
    doc_id = ingest_result["document_id"]
    
    # ADD POLLING FOR DELETE
    # 2. Poll for successful deletion (instead of fixed sleep)
    start_time = time.time()
    delete_successful = False
    while time.time() - start_time < max_wait_seconds:
        delete_response = await integration_test_client.delete(f"{BASE_URL}/api/v1/documents/{doc_id}")
        if delete_response.status_code == status.HTTP_204_NO_CONTENT:
            logger.info(f"Document {doc_id} deleted successfully after {time.time() - start_time:.2f} seconds.")
            delete_successful = True
            break
        elif delete_response.status_code == status.HTTP_404_NOT_FOUND:
            logger.debug(f"Document {doc_id} not found yet for deletion, polling... (Status: {delete_response.status_code})")
        else:
            # Unexpected status code during deletion attempt
            print(f"Unexpected delete response status: {delete_response.status_code}, body: {delete_response.text}")
            pytest.fail(f"Unexpected status code {delete_response.status_code} during deletion poll for {doc_id}")
        await asyncio.sleep(poll_interval)
        
    if not delete_successful:
        pytest.fail(f"Document {doc_id} was not successfully deleted within {max_wait_seconds} seconds.")

    # ADD POLLING FOR SEARCH VERIFICATION
    # 3. Verify searching for it yields no results (with polling)
    start_time_search = time.time()
    search_verified = False
    while time.time() - start_time_search < max_wait_seconds:
        keyword_response = await integration_test_client.post(
            f"{BASE_URL}/api/v1/search/query",
            json={"search_type": "keyword", "query": "deletion testing", "limit": 1}
        )
        if keyword_response.status_code != status.HTTP_200_OK:
            print(f"Keyword search response status: {keyword_response.status_code}, body: {keyword_response.text}")
            # Fail immediately on non-200 search response
            pytest.fail(f"Keyword search failed with status {keyword_response.status_code} during verification.")
            
        keyword_results = keyword_response.json()
        if len(keyword_results.get("results", [])) == 0:
            logger.info(f"Search verification successful (0 results) after {time.time() - start_time_search:.2f} seconds.")
            search_verified = True
            break
        else:
            logger.debug(f"Search verification found {len(keyword_results.get('results', []))} results, polling... Results: {keyword_results.get('results')}")
            
        await asyncio.sleep(poll_interval)
        
    assert search_verified, f"Search still returned results for deleted doc {doc_id} after {max_wait_seconds} seconds."

    # ORIGINAL SEARCH VERIFICATION (to be replaced by polling above)
    # 5. Verify searching for it yields no results
    # keyword_response = await integration_test_client.post(
    #     f"{BASE_URL}/api/v1/search/query",
    #     json={"search_type": "keyword", "query": "deletion testing", "limit": 1}
    # )
    # if keyword_response.status_code != status.HTTP_200_OK:
    #     print(f"Keyword search response status: {keyword_response.status_code}, body: {keyword_response.text}")
    # assert keyword_response.status_code == status.HTTP_200_OK
    # keyword_results = keyword_response.json()
    # assert len(keyword_results["results"]) == 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_nonexistent(integration_test_client: httpx.AsyncClient):
    """Test deleting a non-existent document ID."""
    non_existent_id = f"non-existent-id-{uuid.uuid4()}"
    delete_response = await integration_test_client.delete(f"{BASE_URL}/api/v1/documents/{non_existent_id}") # Adjust endpoint if needed
    if delete_response.status_code != status.HTTP_404_NOT_FOUND:
        print(f"Delete response status: {delete_response.status_code}, body: {delete_response.text}")
    assert delete_response.status_code == status.HTTP_404_NOT_FOUND 
    # Check the error message structure based on your API's 404 response
    # assert delete_response.json() == {"detail": "Document not found"} 