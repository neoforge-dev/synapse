import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
import asyncio
import uuid
import os
from typing import List, Dict, Any
from datetime import datetime

# Import driver classes for mocking
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, Result, Record
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from graph_rag.data_stores.memgraph_store import MemgraphStore
from graph_rag.config import get_settings
from gqlalchemy import Memgraph
from graph_rag.data_stores.memgraph_store import MemgraphStoreError
from graph_rag.domain.models import Document, Chunk

# Instantiate settings
settings = get_settings()

# --- Unit Tests (Mocking Neo4j Driver) ---

@pytest.fixture
def mock_neo4j_driver() -> AsyncDriver:
    driver = AsyncMock(spec=AsyncDriver)
    session = AsyncMock(spec=AsyncSession)
    result = AsyncMock(spec=Result)
    
    # Configure mocks
    driver.session.return_value.__aenter__.return_value = session
    session.run.return_value = result
    
    # Default result behavior (can be overridden in tests)
    result.single.return_value = None
    result.data.return_value = [] 
    
    # Mock __aexit__ to avoid context manager issues
    driver.session.return_value.__aexit__.return_value = None 
    session.close.return_value = None
    driver.close.return_value = None
    
    return driver

@pytest.fixture
async def memgraph_store_unit(mock_neo4j_driver) -> MemgraphStore:
    """Provides a MemgraphStore instance with a mocked driver for unit tests."""
    # Patch the driver creation within MemgraphStore
    with patch("graph_rag.data_stores.memgraph_store.AsyncGraphDatabase.driver") as mock_get_driver:
        mock_get_driver.return_value = mock_neo4j_driver
        store = MemgraphStore(uri=settings.get_memgraph_uri(), config=settings)
        # Simulate connection for unit tests (driver mock handles sessions)
        store._driver = mock_neo4j_driver
        yield store
        # No explicit close needed as driver is mocked

@pytest.mark.asyncio
async def test_unit_connect_success(mock_neo4j_driver):
    """Unit test successful connection (driver creation)."""
    with patch("graph_rag.data_stores.memgraph_store.AsyncGraphDatabase.driver") as mock_get_driver:
        mock_get_driver.return_value = mock_neo4j_driver
        store = MemgraphStore(uri="bolt://mock", config=settings)
        await store.connect()
        mock_get_driver.assert_called_once()
        mock_neo4j_driver.verify_connectivity.assert_called_once()
        assert store._driver is mock_neo4j_driver
        await store.close()
        mock_neo4j_driver.close.assert_called_once()

@pytest.mark.asyncio
async def test_unit_add_node(memgraph_store_unit: MemgraphStore, mock_neo4j_driver):
    """Unit test add_node query generation and execution."""
    label = "Person"
    node_id = "p1"
    properties = {"id": node_id, "name": "Alice", "age": 30}
    
    # Mock result for write transaction
    mock_session = mock_neo4j_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock(spec=Result)
    mock_session.execute_write.return_value = node_id # Simulate return value
    
    result_id = await memgraph_store_unit.add_node(label, properties)
    
    assert result_id == node_id
    # Check that execute_write was called
    assert mock_session.execute_write.call_count == 1
    # Inspect the query (fragile, but useful for basic check)
    call_args = mock_session.execute_write.call_args
    assert "MERGE (n:Person {id: $props.id})" in call_args[0][1] # Check query structure
    assert call_args[1]["props"] == properties

@pytest.mark.asyncio
async def test_unit_add_relationship(memgraph_store_unit: MemgraphStore, mock_neo4j_driver):
    """Unit test add_relationship query generation."""
    mock_session = mock_neo4j_driver.session.return_value.__aenter__.return_value
    
    await memgraph_store_unit.add_relationship("p1", "c1", "WORKS_AT", {"role": "Engineer"})
    
    assert mock_session.execute_write.call_count == 1
    call_args = mock_session.execute_write.call_args
    assert "MATCH (a {id: $source_id}), (b {id: $target_id})" in call_args[0][1]
    assert "MERGE (a)-[r:WORKS_AT]->(b)" in call_args[0][1]
    assert call_args[1]["source_id"] == "p1"
    assert call_args[1]["target_id"] == "c1"
    assert call_args[1]["props"] == {"role": "Engineer"}

# --- Integration Tests (Requires running Memgraph via Docker) ---

@pytest.fixture(scope="session")
async def memgraph_store_integration() -> MemgraphStore:
    """Provides a MemgraphStore connected to the real Docker instance."""
    # Ensure settings point to Docker container
    if "localhost" in settings.get_memgraph_uri() and "GITHUB_ACTIONS" not in os.environ:
         pytest.skip("Skipping integration tests that require Docker Memgraph unless explicitly targeting localhost.")
    
    store = MemgraphStore(uri=settings.get_memgraph_uri(), config=settings)
    await store.connect()
    # Apply constraints and clean up before tests
    try:
        await store.execute_write("MATCH (n) DETACH DELETE n")
        await store.apply_schema_constraints()
    except Exception as e:
        pytest.fail(f"Failed to clean/setup Memgraph for integration tests: {e}")
        
    yield store
    
    # Cleanup after tests
    await store.execute_write("MATCH (n) DETACH DELETE n")
    await store.close()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_connection(memgraph_store_integration: MemgraphStore):
    """Test connectivity to the real Memgraph instance."""
    assert memgraph_store_integration._driver is not None
    # Simple query to test connection
    result = await memgraph_store_integration.execute_read("RETURN 1")
    assert result == [1]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_add_and_get_node(memgraph_store_integration: MemgraphStore):
    """Test adding and retrieving a node from the real Memgraph."""
    label = "City"
    node_id = "city-sf"
    properties = {"id": node_id, "name": "San Francisco", "country": "USA"}
    
    added_id = await memgraph_store_integration.add_node(label, properties)
    assert added_id == node_id
    
    retrieved_node = await memgraph_store_integration.get_node_by_id(node_id)
    assert retrieved_node is not None
    # Memgraph might add internal properties, only check ours
    assert retrieved_node.get("id") == node_id
    assert retrieved_node.get("name") == "San Francisco"
    assert retrieved_node.get("country") == "USA"
    # Check label implicitly via get_node_by_id implementation (if it includes labels)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_add_relationship(memgraph_store_integration: MemgraphStore):
    """Test adding a relationship between two nodes."""
    # Add nodes first
    await memgraph_store_integration.add_node("Person", {"id": "p-int-1", "name": "Dev1"})
    await memgraph_store_integration.add_node("Project", {"id": "proj-int-a", "name": "GraphRAG"})
    
    # Add relationship
    await memgraph_store_integration.add_relationship("p-int-1", "proj-int-a", "WORKS_ON", {"since": 2024})
    
    # Verify relationship exists
    query = "MATCH (:Person {id: $p_id})-[:WORKS_ON {since: $since}]->(:Project {id: $proj_id}) RETURN COUNT(*) > 0"
    result = await memgraph_store_integration.execute_read(query, {"p_id": "p-int-1", "proj_id": "proj-int-a", "since": 2024})
    assert result == [True]

# TODO: Add integration tests for query_subgraph, detect_communities, schema constraints, transactions, error handling/retries. 

@pytest.fixture
def mock_mgclient():
    """Mocks the mgclient connection and cursor."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    with patch('mgclient.connect', return_value=mock_conn) as mock_connect:
        yield mock_connect, mock_conn, mock_cursor

@pytest.fixture
def memgraph_store(mock_mgclient):
    """Provides a MemgraphStore instance with mocked mgclient."""
    # Pass dummy config values since mgclient is mocked
    return MemgraphStore(
        host="mockhost", 
        port=1234, 
        user="mockuser", 
        password="mockpass"
    )

@pytest.mark.asyncio
async def test_add_document_success(memgraph_store, mock_mgclient):
    """Test successful document addition."""
    mock_connect, mock_conn, mock_cursor = mock_mgclient
    doc = Document(id="doc1", content="Test", metadata={})
    
    await memgraph_store.add_document(doc)
    
    # Assert connect was called
    # mock_connect.assert_called_once_with(host="mockhost", port=1234, user="mockuser", password="mockpass")
    # Assert execute was called with correct query parts
    assert mock_cursor.execute.call_count == 1
    args, kwargs = mock_cursor.execute.call_args
    assert "MERGE (d:Document {id: $id})" in args[0]
    assert args[1]["id"] == "doc1"
    # Assert commit was called
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

@pytest.mark.asyncio
async def test_add_chunk_success(memgraph_store, mock_mgclient):
    mock_connect, mock_conn, mock_cursor = mock_mgclient
    chunk = Chunk(id="chunk1", document_id="doc1", content="Chunk text", embedding=[0.1])

    await memgraph_store.add_chunk(chunk)

    assert mock_cursor.execute.call_count == 1
    args, kwargs = mock_cursor.execute.call_args
    assert "MATCH (d:Document {id: $doc_id})" in args[0]
    assert "MERGE (c:Chunk {id: $chunk_id})" in args[0]
    assert "MERGE (d)-[:CONTAINS]->(c)" in args[0]
    assert args[1]["chunk_id"] == "chunk1"
    assert args[1]["doc_id"] == "doc1"
    mock_conn.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_document_by_id_found(memgraph_store, mock_mgclient):
    mock_connect, mock_conn, mock_cursor = mock_mgclient
    mock_cursor.fetchall.return_value = [("doc1", "Content", {"key": "value"}, datetime.now(), datetime.now())]
    # Mock description for column names
    mock_cursor.description = [("id",), ("content",), ("metadata",), ("created_at",), ("updated_at",)]

    doc = await memgraph_store.get_document_by_id("doc1")

    assert doc is not None
    assert doc.id == "doc1"
    assert doc.content == "Content"
    assert doc.metadata == {"key": "value"}
    assert mock_cursor.execute.call_count == 1
    args, kwargs = mock_cursor.execute.call_args
    assert "MATCH (d:Document {id: $id})" in args[0]

@pytest.mark.asyncio
async def test_get_document_by_id_not_found(memgraph_store, mock_mgclient):
    mock_connect, mock_conn, mock_cursor = mock_mgclient
    mock_cursor.fetchall.return_value = [] # Simulate not found
    mock_cursor.description = [("id",), ("content",), ("metadata",), ("created_at",), ("updated_at",)]

    doc = await memgraph_store.get_document_by_id("doc_nonexistent")

    assert doc is None

@pytest.mark.asyncio
async def test_add_document_connection_error(memgraph_store, mock_mgclient):
    mock_connect, mock_conn, mock_cursor = mock_mgclient
    # Simulate connection error
    mock_connect.side_effect = mgclient.Error("Connection failed")
    doc = Document(id="doc_err", content="Error test", metadata={})

    with pytest.raises(mgclient.Error):
        await memgraph_store.add_document(doc)
    
    # Assert connection was attempted
    # mock_connect.assert_called_once()
    # Assert execute, commit, close were NOT called
    mock_cursor.execute.assert_not_called()
    mock_conn.commit.assert_not_called()
    mock_conn.close.assert_not_called() # Connection wasn't successfully opened to be closed 