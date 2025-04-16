import pytest
import asyncio
from httpx import AsyncClient
from fastapi import status
import logging
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Change import
from graph_rag.config import get_settings 
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.domain.models import Document, Chunk, Entity, Relationship
from graph_rag.core.vector_store import VectorStore
from graph_rag.services.embedding import EmbeddingService
from graph_rag.core.graph_rag_engine import GraphRAGEngine

# Instantiate settings
settings = get_settings()

logger = logging.getLogger(__name__)

# --- Fixtures --- 
@pytest.fixture(scope="module")
async def test_document_content() -> str:
    return "Test document for query pipeline. Mentions Alice and works at ACME Corp."

@pytest.fixture(scope="module")
async def test_document_metadata() -> Dict[str, Any]:
    return {"source": "query-pipeline-test", "category": "integration"}

@pytest.fixture(scope="module")
async def ingested_doc_id(test_client: AsyncClient, test_document_content: str, test_document_metadata: Dict[str, Any], memgraph_repo) -> str:
    """Ingests a document and waits for it to appear, returning its ID."""
    response = await test_client.post(
        "/api/v1/ingestion/documents",
        json={"content": test_document_content, "metadata": test_document_metadata}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    doc_id = response.json()["document_id"]

    # Wait for document to appear in DB
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        # Use direct repo check
        doc = await memgraph_repo.get_document_by_id(doc_id)
        if doc is not None:
            logger.info(f"Document {doc_id} found in DB for query pipeline test.")
            return doc_id # Return the found ID
        await asyncio.sleep(1) 
        attempt += 1
        
    pytest.fail(f"Document {doc_id} did not appear in database after ingestion.")
    return ""

# --- Integration Test --- 
pytestmark = pytest.mark.asyncio

async def test_query_pipeline(test_client: AsyncClient, ingested_doc_id: str, memgraph_repo):
    """Test the query API endpoint after ingesting a document."""
    assert ingested_doc_id, "Test setup failed: No ingested document ID available."
    
    # Give a little extra time for potential entity/relationship linking background tasks
    await asyncio.sleep(1)
    
    # Query for content related to the ingested document
    query_text = "Who works at ACME?"
    response = await test_client.post(
        "/api/v1/query/", 
        json={"query_text": query_text, "config": {"k": 2, "include_graph": True}}
    )
    
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

    assert "query_text" in response_data
    assert response_data["query_text"] == query_text
    assert "results" in response_data
    assert len(response_data["results"]) > 0
    # Check if relevant content is in the results
    assert any("Paris" in chunk["text"] or "Eiffel Tower" in chunk["text"] 
               for chunk in response_data["results"]), "Relevant chunk not found in results"
    assert response_data["results"][0]["document"]["id"] == doc_id

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

    # Adjust assertion based on actual response structure
    # Assuming the API returns the original query text and empty results
    # assert "query_text" in response_data # Original assertion - incorrect
    assert "answer" in response_data
    assert "relevant_chunks" in response_data
    assert len(response_data["relevant_chunks"]) == 0
    # Optionally check the answer content if it's consistent
    # assert "Could not find relevant information" in response_data["answer"]

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