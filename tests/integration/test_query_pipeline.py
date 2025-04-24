import pytest
import asyncio
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
import logging
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from graph_rag.core.interfaces import (
    GraphRepository, EntityExtractor, EmbeddingService, VectorStore, DocumentProcessor
)
from graph_rag.services.embedding import SentenceTransformerEmbeddingService
from graph_rag.domain.models import Document

# Change import
from graph_rag.config import get_settings 
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.domain.models import Chunk, Entity, Relationship
from graph_rag.core.graph_rag_engine import GraphRAGEngine, QueryResult

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

# Fixture to provide the mock graph rag engine (potentially overridden in specific tests)
@pytest.fixture(scope="function")
async def mock_graph_rag_engine() -> AsyncMock:
    # Basic setup, can be overridden by test functions
    mock = AsyncMock(spec=SimpleGraphRAGEngine) # Use spec
    default_result = QueryResult(
        answer="Default fallback answer",
        relevant_chunks=[],
        graph_context=None,
        metadata={'source': 'mock_pipeline_fixture'}
    )
    mock.query.return_value = default_result
    return mock

# --- Integration Test --- 
pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_query_pipeline(test_client: AsyncClient, ingested_doc_id: str, mock_graph_rag_engine: AsyncMock):
    """Test the full query pipeline with specific entities."""
    # Mock the engine's query method
    async def mock_specific_query(query_text: str, k: int | None = None, config: dict | None = None) -> QueryResult:
        # Simulate returning specific results based on the query
        if "Eiffel Tower" in query_text:
            return QueryResult(
                query=query_text,
                answer="The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France.",
                context=["Mock context 1", "Mock context 2"],
                nodes=["node1", "node2"], # Sample node IDs
                llm_info={"model": "mock_llm", "tokens_used": 50}
            )
        return QueryResult(query=query_text, answer="No specific result found.", context=[], nodes=[], llm_info={})

    mock_graph_rag_engine.query.side_effect = mock_specific_query # Assign the async function directly

    # Send a request to the endpoint
    response = await test_client.post("/api/v1/query", json={"query_text": "Tell me about the Eiffel Tower", "k": 5})

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Tell me about the Eiffel Tower"
    assert "Eiffel Tower" in data["answer"]
    assert isinstance(data["context"], list)
    assert isinstance(data["nodes"], list)
    assert data["llm_info"]["model"] == "mock_llm"

    # Verify the mock was called correctly (using await for async mock)
    mock_graph_rag_engine.query.assert_awaited_once_with("Tell me about the Eiffel Tower", k=5)

@pytest.mark.asyncio
async def test_basic_query(test_client: AsyncClient, mock_graph_rag_engine: AsyncMock):
    """Test a basic query without complex entity extraction."""
    async def mock_eiffel_query(query_text: str, k: int | None = None, config: dict | None = None) -> QueryResult:
        return QueryResult(
            query=query_text,
            answer="Mock answer for Eiffel Tower query.",
            context=["Mock context: Eiffel Tower"],
            nodes=["eiffel_node"],
            llm_info={"model": "mock_basic", "tokens_used": 20}
        )

    mock_graph_rag_engine.query.side_effect = mock_eiffel_query

    response = await test_client.post("/api/v1/query", json={"query_text": "What is the Eiffel Tower?", "k": 3})

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "What is the Eiffel Tower?"
    assert "Mock answer" in data["answer"]
    mock_graph_rag_engine.query.assert_awaited_once_with("What is the Eiffel Tower?", k=3)

@pytest.mark.asyncio
async def test_query_no_entities(test_client: AsyncClient, mock_graph_rag_engine: AsyncMock):
    """Test a query that might not yield specific entities or graph results."""
    async def mock_no_entity_query(query_text: str, k: int | None = None, config: dict | None = None) -> QueryResult:
        return QueryResult(
            query=query_text,
            answer="No specific graph entities found, providing general info.",
            context=["General context 1", "General context 2"],
            nodes=[],
            llm_info={"model": "mock_general", "tokens_used": 30}
        )

    mock_graph_rag_engine.query.side_effect = mock_no_entity_query

    response = await test_client.post("/api/v1/query", json={"query_text": "What is the weather like?", "k": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "What is the weather like?"
    assert "No specific graph entities found" in data["answer"]
    assert data["nodes"] == []
    mock_graph_rag_engine.query.assert_awaited_once_with("What is the weather like?", k=10)

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

# Define helper locally
async def ingest_doc_helper(client: AsyncClient, doc_content: str, metadata: dict) -> str:
    response = await client.post(
        f"/api/v1/ingestion/documents",
        json={"content": doc_content, "metadata": metadata, "generate_embeddings": True}
    )
    response.raise_for_status() # Raise exception for bad status codes
    return response.json()["document_id"]