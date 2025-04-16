# tests/test_e2e_mvp.py
import pytest
import os
import logging
from typing import Dict, Any
import pymgclient as mgclient
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import asyncio
import uuid
from httpx import AsyncClient, Timeout
from fastapi import status

from graph_rag.config import get_settings
from graph_rag.stores.memgraph_store import MemgraphStore
from graph_rag.infrastructure.vector_stores import SimpleVectorStore
from graph_rag.core.entity_extractor import SpacyEntityExtractor, MockEntityExtractor
from graph_rag.core.document_processor import SimpleDocumentProcessor, SentenceSplitter
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.models import Document, Chunk, Entity, Relationship
from graph_rag.api.main import app
from graph_rag.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

# --- Test Configuration --- 
MEMGRAPH_HOST = os.getenv("MEMGRAPH_HOST", "127.0.0.1")
MEMGRAPH_PORT = int(os.getenv("MEMGRAPH_PORT", 7687))

requires_memgraph = pytest.mark.skipif(
    not os.getenv("RUN_MEMGRAPH_TESTS", False),
    reason="Set RUN_MEMGRAPH_TESTS=true environment variable to run Memgraph integration tests"
)

# Helper to check connection (copied from test_memgraph_store)
def check_memgraph_connection(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT) -> bool:
    try:
        conn = mgclient.connect(host=host, port=port)
        conn.close()
        return True
    except Exception:
        return False

if not check_memgraph_connection():
    pytest.skip("Cannot connect to Memgraph, skipping all MVP E2E tests.", allow_module_level=True)

# --- Fixtures --- 

@pytest.fixture(scope="module")
def graph_store() -> MemgraphStore:
    store = MemgraphStore(
        host=MEMGRAPH_HOST,
        port=MEMGRAPH_PORT
        # Add other settings if needed based on your .env or defaults
    )
    # Clear DB at the start of the module tests
    try:
        store._execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Cleared Memgraph for E2E tests.")
    except Exception as e:
        pytest.skip(f"Could not clear Memgraph DB for E2E tests: {e}")
    yield store
    store.close()

@pytest.fixture(scope="module")
def vector_store() -> SimpleVectorStore:
    # Use the model configured in settings if possible, else default
    model = get_settings().vector_store_embedding_model
    return SimpleVectorStore(embedding_model_name=model)

@pytest.fixture(scope="module")
def entity_extractor() -> SpacyEntityExtractor:
    # Use spacy for a more realistic E2E test
    try:
        return SpacyEntityExtractor(model_name=get_settings().entity_extractor_model)
    except RuntimeError as e:
        pytest.skip(f"Skipping E2E test needing Spacy: {e}")

@pytest.fixture(scope="module")
def doc_processor() -> SimpleDocumentProcessor:
    # TODO: Make splitter configurable
    return SimpleDocumentProcessor(splitter=SentenceSplitter())

@pytest.fixture(scope="module")
def kg_builder(graph_store: MemgraphStore) -> PersistentKnowledgeGraphBuilder:
    return PersistentKnowledgeGraphBuilder(graph_store=graph_store)

@pytest.fixture(scope="module")
def rag_engine(
    graph_store: MemgraphStore,
    vector_store: SimpleVectorStore,
    entity_extractor: SpacyEntityExtractor
) -> SimpleGraphRAGEngine:
    return SimpleGraphRAGEngine(
        graph_store=graph_store,
        vector_store=vector_store,
        entity_extractor=entity_extractor
    )

@pytest.fixture
def mock_neo4j_driver():
    """Fixture to mock the Neo4j driver."""
    driver = AsyncMock()
    session = AsyncMock()
    driver.session.return_value = session
    return driver

@pytest.fixture
def mock_embedding_service():
    """Mock the EmbeddingService class methods globally for service tests."""
    with patch('graph_rag.services.embedding.EmbeddingService', autospec=True) as mock_emb_service:
        # Mock the encode method
        def mock_encode(texts):
            if isinstance(texts, str):
                return np.random.rand(EMBEDDING_DIM).tolist()
            else:
                return [np.random.rand(EMBEDDING_DIM).tolist() for _ in texts]
        
        mock_emb_service.encode.side_effect = mock_encode
        mock_emb_service._get_model.return_value = MagicMock() # Mock the internal model loading
        mock_emb_service.get_embedding_dim.return_value = EMBEDDING_DIM
        yield mock_emb_service

@pytest.fixture
def client(mock_neo4j_driver, mock_embedding_service):
    """Create a test client with mocked dependencies."""
    with patch('graph_rag.stores.memgraph_store.MemgraphStore', return_value=mock_neo4j_driver):
        with patch('graph_rag.services.embedding.EmbeddingService', return_value=mock_embedding_service):
            return app.test_client()

# --- E2E Test --- 

@requires_memgraph
def test_mvp_ingest_and_query_flow(
    doc_processor: SimpleDocumentProcessor,
    entity_extractor: SpacyEntityExtractor,
    kg_builder: PersistentKnowledgeGraphBuilder,
    vector_store: SimpleVectorStore,
    rag_engine: SimpleGraphRAGEngine
):
    """Tests ingesting a document and querying related information."""
    
    # 1. Ingestion
    doc_content = "Alice lives in Wonderland. Bob works for Acme Corp in London."
    doc_id = "e2e-doc-1"
    doc = Document(id=doc_id, content=doc_content, metadata={"source": "e2e_test"})
    
    # Chunking
    chunks: List[Chunk] = doc_processor.process_document(doc)
    assert len(chunks) > 0
    logger.info(f"E2E: Created {len(chunks)} chunks.")
    
    # Embedding & Vector Store Add
    vector_store.add_chunks(chunks)
    logger.info(f"E2E: Added chunks to vector store.")
    
    # Entity Extraction
    processed_doc: ProcessedDocument = entity_extractor.extract(doc) # Extractor now works on Document
    assert len(processed_doc.entities) > 0
    entity_names = {e.name for e in processed_doc.entities}
    assert "Alice" in entity_names
    assert "Wonderland" in entity_names
    assert "Bob" in entity_names
    assert "Acme Corp" in entity_names
    assert "London" in entity_names
    logger.info(f"E2E: Extracted {len(processed_doc.entities)} entities: {entity_names}")
    
    # KG Building (Simplified - add entities directly, PersistentKGBuilder needs async)
    # In a real scenario, this would be orchestrated, potentially via API calls or a service method.
    # For this test, we manually add to the graph store used by the engine.
    try:
        kg_builder.graph_store.add_entities_and_relationships(processed_doc.entities, [])
        logger.info(f"E2E: Added {len(processed_doc.entities)} entities to graph store.")
        # TODO: Add relationship extraction/addition if implemented
        # TODO: Add chunk nodes and links if needed by query strategy
    except Exception as e:
        pytest.fail(f"E2E: Failed to add entities to graph store: {e}")

    # --- Wait briefly for potential indexing --- 
    import time
    time.sleep(1) 

    # 2. Query
    query = "Where does Alice live?"
    logger.info(f"E2E: Executing query: '{query}'")
    result = rag_engine.query(query, config={"k": 2, "include_graph": True})
    
    # Verification
    assert result is not None
    assert isinstance(result.answer, str)
    assert len(result.relevant_chunks) > 0
    assert "Wonderland" in result.answer # Check if answer reflects context
    logger.info(f"E2E: Query answer: {result.answer}")
    
    # Check graph context
    assert result.graph_context is not None
    graph_entities, graph_rels = result.graph_context
    assert len(graph_entities) > 0
    graph_entity_names = {e.name for e in graph_entities}
    logger.info(f"E2E: Graph context entities found: {graph_entity_names}")
    assert "Alice" in graph_entity_names
    assert "Wonderland" in graph_entity_names # Alice's neighbor
    # Bob might be included if linked to Alice or found via property search
    # assert "Bob" in graph_entity_names 
    
    # --- Query 2 --- 
    query2 = "Who works for Acme?"
    logger.info(f"E2E: Executing query: '{query2}'")
    result2 = rag_engine.query(query2, config={"k": 2, "include_graph": True})
    
    assert result2 is not None
    assert "Bob" in result2.answer
    assert result2.graph_context is not None
    graph_entities2, _ = result2.graph_context
    graph_entity_names2 = {e.name for e in graph_entities2}
    logger.info(f"E2E: Graph context entities found: {graph_entity_names2}")
    assert "Bob" in graph_entity_names2
    assert "Acme Corp" in graph_entity_names2
    # assert "London" in graph_entity_names2 # Neighbor of Acme? Depends on relationships

    logger.info("E2E MVP test completed successfully.") 

@pytest.mark.asyncio
async def test_query_endpoint(client):
    """Test the query endpoint with a simple question."""
    # Mock the response from the graph store
    mock_result = AsyncMock()
    mock_result.data.return_value = [
        {"c": {"id": "chunk1", "text": "Test chunk 1"}},
        {"c": {"id": "chunk2", "text": "Test chunk 2"}}
    ]
    client.application.extensions['graph_store'].session.return_value.run.return_value = mock_result

    # Make a request to the query endpoint
    response = await client.post('/query', json={'query': 'What is the test about?'})
    
    # Check the response
    assert response.status_code == 200
    data = await response.get_json()
    assert 'answer' in data
    assert 'relevant_chunks' in data
    assert 'graph_context' in data
    assert 'metadata' in data
    assert len(data['relevant_chunks']) == 2

@pytest.mark.asyncio
async def test_query_endpoint_with_entities(client):
    """Test the query endpoint with a question that should extract entities."""
    # Mock the response from the graph store
    mock_result = AsyncMock()
    mock_result.data.return_value = [
        {"c": {"id": "chunk1", "text": "Test chunk 1"}},
        {"c": {"id": "chunk2", "text": "Test chunk 2"}}
    ]
    client.application.extensions['graph_store'].session.return_value.run.return_value = mock_result

    # Make a request to the query endpoint
    response = await client.post('/query', json={'query': 'Tell me about Alice and Bob'})
    
    # Check the response
    assert response.status_code == 200
    data = await response.get_json()
    assert 'answer' in data
    assert 'relevant_chunks' in data
    assert 'graph_context' in data
    assert 'metadata' in data
    assert len(data['relevant_chunks']) == 2
    assert 'entities' in data['metadata']
    assert len(data['metadata']['entities']) > 0

@pytest.mark.asyncio
async def test_query_endpoint_error_handling(client):
    """Test error handling in the query endpoint."""
    # Mock an error from the graph store
    client.application.extensions['graph_store'].session.return_value.run.side_effect = Exception("Test error")

    # Make a request to the query endpoint
    response = await client.post('/query', json={'query': 'What is the test about?'})
    
    # Check the error response
    assert response.status_code == 500
    data = await response.get_json()
    assert 'error' in data
    assert 'Test error' in data['error'] 

# Instantiate settings
settings = get_settings()

# API base URL (consider moving to a shared config or fixture)
API_BASE_URL = f"http://{settings.api_host}:{settings.api_port}"

# Configure timeout for API requests
TIMEOUT = Timeout(10.0, connect=5.0) # 10 second overall timeout

# Helper to check Memgraph connection
async def check_memgraph_connection():
    # This check ideally uses the actual connection logic or a minimal client connection
    # For now, assume connection check relies on fixture availability or test setup
    # In a real scenario, might use mgclient or neo4j driver directly
    try:
        # Replace with actual connection check if possible
        # Example using mgclient (if installed and configured)
        import mgclient
        conn = mgclient.connect(host=settings.MEMGRAPH_HOST, port=settings.MEMGRAPH_PORT)
        conn.close()
        return True
    except Exception:
        return False

# Mark all tests as async and integration
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

@pytest.fixture(scope="module", autouse=True)
async def skip_if_memgraph_unavailable():
    """Skips tests in this module if Memgraph is not reachable."""
    if not await check_memgraph_connection():
        pytest.skip("Cannot connect to Memgraph, skipping all MVP E2E tests.")

async def ingest_document(client: AsyncClient, content: str, metadata: dict) -> str:
    """Helper function to ingest a document via the API."""
    response = await client.post(
        f"{API_BASE_URL}/api/v1/ingestion/documents", 
        json={"content": content, "metadata": metadata},
        timeout=TIMEOUT
    )
    response.raise_for_status() # Raise exception for non-2xx responses
    return response.json()["document_id"]

async def wait_for_doc_in_db(doc_id: str, repo) -> bool:
    """Waits for a document to appear in the database."""
    for _ in range(10): # Wait up to 10 seconds
        # Use repo fixture passed to the test function
        doc = await repo.get_document_by_id(doc_id)
        if doc:
            return True
        await asyncio.sleep(1)
    return False

async def test_e2e_mvp_pipeline(test_client: AsyncClient, memgraph_repo):
    """Tests the Minimum Viable Product end-to-end flow: Ingest -> Query."""
    doc_content = f"E2E Test MVP {uuid.uuid4()}. Key entity: E2E_COMPANY. Another: E2E_PERSON."
    doc_metadata = {"source": "e2e-mvp", "test_run_id": str(uuid.uuid4())}
    
    # 1. Ingestion
    print(f"\n[E2E] Ingesting document...")
    try:
        doc_id = await ingest_document(test_client, doc_content, doc_metadata)
        print(f"[E2E] Document ingestion requested. Document ID: {doc_id}")
    except Exception as e:
        pytest.fail(f"[E2E] Document ingestion failed: {e}")

    # 2. Verification (Wait for DB update)
    print(f"[E2E] Waiting for document {doc_id} to appear in Memgraph...")
    # Pass the memgraph_repo fixture here
    assert await wait_for_doc_in_db(doc_id, memgraph_repo), \
        f"[E2E] Document {doc_id} did not appear in Memgraph after waiting."
    print(f"[E2E] Document {doc_id} confirmed in Memgraph.")
    # Optional: Add checks for chunks/entities if repo methods exist
    # chunks = await memgraph_repo.get_chunks_by_document_id(doc_id)
    # assert chunks, f"[E2E] No chunks found for document {doc_id}"
    # print(f"[E2E] Found {len(chunks)} chunks for document {doc_id}.")

    # 3. Querying
    query = "What key entities are mentioned?"
    print(f"[E2E] Querying API: '{query}'")
    try:
        response = await test_client.post(
            f"{API_BASE_URL}/api/v1/query/",
            json={"query_text": query, "config": {"include_graph": True}}, 
            timeout=TIMEOUT
        )
        response.raise_for_status()
        query_result = response.json()
        print(f"[E2E] Query successful. Result: {query_result}")
    except Exception as e:
        pytest.fail(f"[E2E] Query request failed: {e}")

    # 4. Assertions on Query Result
    assert "answer" in query_result, "[E2E] Query result missing 'answer' field."
    assert isinstance(query_result["answer"], str)
    # Check if expected entities are mentioned in the answer or context
    assert "E2E_COMPANY" in query_result["answer"] or \
           any("E2E_COMPANY" in c.get("text", "") for c in query_result.get("relevant_chunks", [])), \
           "[E2E] Expected entity E2E_COMPANY not found in answer or relevant chunks."
    assert "E2E_PERSON" in query_result["answer"] or \
           any("E2E_PERSON" in c.get("text", "") for c in query_result.get("relevant_chunks", [])), \
           "[E2E] Expected entity E2E_PERSON not found in answer or relevant chunks."

    # Optional: Check graph context if included and populated
    if query_result.get("graph_context"):
        entities = query_result["graph_context"].get("entities", [])
        entity_names = {e.get("name") for e in entities}
        print(f"[E2E] Graph context entities found: {entity_names}")
        assert "E2E_COMPANY" in entity_names, "[E2E] E2E_COMPANY not found in graph context entities."
        assert "E2E_PERSON" in entity_names, "[E2E] E2E_PERSON not found in graph context entities."

    print(f"[E2E] MVP Pipeline Test Completed Successfully.") 