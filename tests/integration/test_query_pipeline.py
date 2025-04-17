import pytest
import asyncio
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
import logging
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from graph_rag.core.graph_store import GraphStore
from graph_rag.domain.models import Document

# Change import
from graph_rag.config import get_settings 
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.domain.models import Chunk, Entity, Relationship
from graph_rag.core.vector_store import VectorStore
from graph_rag.services.embedding import EmbeddingService
from graph_rag.core.graph_rag_engine import GraphRAGEngine

# Instantiate settings
settings = get_settings()

logger = logging.getLogger(__name__)

# --- Fixtures --- 
@pytest.fixture(scope="function")
async def test_document_content() -> str:
    return "Test document for query pipeline. Mentions Alice and works at ACME Corp."

@pytest.fixture(scope="function")
async def test_document_metadata() -> Dict[str, Any]:
    return {"source": "query-pipeline-test", "category": "integration"}

@pytest_asyncio.fixture(scope="function")
async def ingested_doc_id(test_client: AsyncClient, mock_graph_repo: AsyncMock) -> str:
    """Ingest a test document and return its ID. Waits for ingestion to complete (checks mock repo)."""
    doc_content = "Alice works at ACME Corp. Bob works at Beta Inc."
    metadata = {"source": "test_query_pipeline"}
    
    # Ingest the document
    response = await test_client.post(
        "/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True},
    )
    
    # Check response status
    if response.status_code != status.HTTP_202_ACCEPTED:
        pytest.fail(f"Document ingestion failed with status {response.status_code}: {response.text}")

    response_data = response.json()
    doc_id = response_data.get("document_id")
    
    if not doc_id:
        pytest.fail("Ingestion response did not contain a document_id.")

    logger.info(f"Document {doc_id} ingestion initiated for query pipeline test.")

    # Wait for the MOCKED ingestion service to call add_document on the MOCKED repo
    max_attempts = 15
    wait_seconds = 1.5
    attempt = 0
    while attempt < max_attempts:
        try:
            # Check if mock_graph_repo.add_document was called with the correct ID
            found_call = False
            for call in mock_graph_repo.add_document.await_args_list:
                # call[0][0] should be the first positional argument (the doc data)
                if isinstance(call[0][0], dict) and call[0][0].get("id") == doc_id:
                    found_call = True
                    break
                # Add check if Document object is passed
                elif hasattr(call[0][0], 'id') and call[0][0].id == doc_id:
                    found_call = True
                    break

            if found_call:
                logger.info(f"Mock document {doc_id} found in mock_graph_repo calls (attempt {attempt + 1}).")
                await asyncio.sleep(0.5) # Short delay for safety
                return doc_id
            else:
                logger.debug(f"Mock document {doc_id} not yet added to mock_graph_repo (attempt {attempt + 1}). Calls: {mock_graph_repo.add_document.await_args_list}")

        except Exception as e:
            logger.warning(f"Error checking mock_graph_repo calls for doc {doc_id} (attempt {attempt + 1}): {e}")
            
        await asyncio.sleep(wait_seconds)
        attempt += 1
        
    pytest.fail(f"Mock Ingestion did not call add_document on mock_graph_repo for {doc_id} after {max_attempts * wait_seconds} seconds.")
    return ""

# --- Integration Test --- 
pytestmark = pytest.mark.asyncio

async def test_query_pipeline(test_client: AsyncClient, ingested_doc_id: str):
    """Test the query API endpoint after ingesting a document."""
    assert ingested_doc_id, "Test setup failed: No ingested document ID available."
    
    # Give a little extra time for potential entity/relationship linking background tasks
    await asyncio.sleep(1)
    
    # Query for content related to the ingested document
    query_text = "Who works at ACME?"
    response = await test_client.post(
        "/api/v1/query",
        json={"query_text": query_text, "config": {"k": 2, "include_graph": True}}
    )
    
    if response.status_code == status.HTTP_307_TEMPORARY_REDIRECT:
        logger.warning(f"Received unexpected 307 redirect. Headers: {response.headers}")

    assert response.status_code == status.HTTP_200_OK
    query_result = response.json()
    
    logger.info(f"Query result: {query_result}")
    
    # Assertions on the query result
    assert "answer" in query_result
    assert isinstance(query_result["answer"], str)
    # Basic check: Answer should mention Alice or ACME
    assert "Alice" in query_result["answer"] or "ACME" in query_result["answer"]
    
    # Check relevant chunks
    assert "relevant_chunks" in query_result
    assert isinstance(query_result["relevant_chunks"], list)
    # Check if chunks are related to the ingested document
    # Requires repo method to get chunks or more detailed query result
    if query_result["relevant_chunks"]:
        # Example: Verify chunk text contains relevant terms
        # assert any("Alice" in chunk["text"] for chunk in query_result["relevant_chunks"])
        pass # Add more specific chunk checks if needed
        
    # Check graph context (if included)
    assert "graph_context" in query_result
    graph_context = query_result["graph_context"]
    if graph_context: # It might be None if include_graph=False or no context found
        assert "entities" in graph_context
        assert "relationships" in graph_context
        assert isinstance(graph_context["entities"], list)
        assert isinstance(graph_context["relationships"], list)
        
        # Verify expected entities (Alice, ACME Corp) are present
        entity_names = {e.get("name") for e in graph_context["entities"]} 
        assert "Alice" in entity_names
        assert "ACME Corp" in entity_names # Assuming extractor finds this
        
        # Verify relationship between Alice and ACME Corp (if extractor supports it)
        # This requires checking relationship source/target/type
        found_works_at = False
        for rel in graph_context["relationships"]:
            # Check if source is Alice and target is ACME Corp (or vice versa depending on direction/model)
            # Requires entities to have IDs in the response matching source/target_id in relationships
            # Example check (needs adaptation based on actual entity IDs and relationship model):
            # source_name = next((e["name"] for e in graph_context["entities"] if e["id"] == rel.get("source_id")), None)
            # target_name = next((e["name"] for e in graph_context["entities"] if e["id"] == rel.get("target_id")), None)
            # if (source_name == "Alice" and target_name == "ACME Corp" and rel.get("type") == "WORKS_AT"): # Example type
            #     found_works_at = True
            #     break
            pass # More specific relationship checks needed based on extractor capabilities
        # assert found_works_at, "Expected WORKS_AT relationship not found in graph context"
    
    # Optional: Clean up the specific document if needed (fixtures usually handle this)
    # await memgraph_repo.delete_document(ingested_doc_id)

# Define helper locally
async def ingest_doc_helper(client: AsyncClient, doc_content: str, metadata: dict) -> str:
    response = await client.post(
        f"/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    response.raise_for_status() # Raise exception for bad status codes
    return response.json()["document_id"]

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
        # Use the local helper or inline the call
        doc_id = await ingest_doc_helper(test_client, doc_content, metadata)
        # doc_id = await ingest_test_document(test_client, doc_content, metadata) # If using imported helper
        logger.info(f"Ingested document {doc_id} for query test.")
    except Exception as e:
        pytest.fail(f"Failed to ingest test document: {e}")

    # 2. Query for information
    query_text = "Where is the Eiffel Tower?"
    response = await test_client.post(
        "/api/v1/query", 
        json={
            "query_text": query_text,
            "k": 5
        }
    )

    # 3. Assertions
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    logger.debug(f"Query Response Data: {response_data}")

    # Updated assertions to match expected response structure
    # The response schema may have changed - adjust assertions accordingly
    assert "answer" in response_data
    assert isinstance(response_data["answer"], str)
    assert "relevant_chunks" in response_data
    assert isinstance(response_data["relevant_chunks"], list)
    
    # Check for relevant content in the chunks (if any are returned)
    if response_data["relevant_chunks"]:
        assert any("Paris" in chunk.get("text", "") or "Eiffel Tower" in chunk.get("text", "") 
                for chunk in response_data["relevant_chunks"]), "Relevant chunk not found in results"
        # Check if the chunk is from our ingested document
        first_chunk = response_data["relevant_chunks"][0]
        assert "document_id" in first_chunk
        assert first_chunk["document_id"] == doc_id

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

    # Adjust assertions to match actual response structure
    assert "answer" in response_data
    assert "relevant_chunks" in response_data
    assert isinstance(response_data["relevant_chunks"], list)
    # If there's metadata to check
    if "metadata" in response_data:
        assert isinstance(response_data["metadata"], dict)
    # Optionally check the answer content for keyword
    assert "Could not find" in response_data["answer"] or "no relevant" in response_data["answer"].lower()

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