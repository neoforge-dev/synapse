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
from graph_rag.config.settings import Settings # Import Settings
import pytest_asyncio # Import pytest_asyncio

# Instantiate settings
settings = get_settings()

# --- Unit Tests (Mocking Neo4j Driver) ---

@pytest.fixture
def mock_neo4j_driver() -> AsyncDriver:
    driver = AsyncMock(spec=AsyncDriver)
    session = AsyncMock(spec=AsyncSession)
    result = AsyncMock(spec=Result)
    record = AsyncMock(spec=Record) # Mock for record
    
    # Configure mocks
    driver.session.return_value.__aenter__.return_value = session
    session.run.return_value = result
    
    # Configure session methods to be awaitable
    session.execute_write = AsyncMock() 
    session.close = AsyncMock()
    
    # Default result behavior (can be overridden in tests)
    # result.single.return_value = None # Old: Not awaitable
    result.single = AsyncMock() # Make it awaitable
    # Example: Make it return a mock record by default
    mock_record_instance = record(data={'id': 'mock_id'}) # Create a mock record instance
    result.single.return_value = mock_record_instance
    
    result.data.return_value = [] 
    
    # Mock __aexit__ to avoid context manager issues
    driver.session.return_value.__aexit__.return_value = None 
    # session.close.return_value = None # Now handled by AsyncMock
    driver.close = AsyncMock() # Make driver.close awaitable too
    
    return driver

@pytest_asyncio.fixture # Use pytest_asyncio fixture
async def memgraph_store_unit(mock_neo4j_driver) -> MemgraphStore:
    """Provides a MemgraphStore instance with a mocked driver for unit tests."""
    # Patch the driver creation within MemgraphStore
    with patch("graph_rag.data_stores.memgraph_store.AsyncGraphDatabase.driver") as mock_get_driver:
        mock_get_driver.return_value = mock_neo4j_driver
        # Use the global settings instance
        current_settings = get_settings()
        store = MemgraphStore(settings=current_settings) # Correct initialization
        # Simulate connection for unit tests (driver mock handles sessions)
        store._driver = mock_neo4j_driver
        yield store # Yield the store instance
        # return store # Reverted change
        # No explicit close needed as driver is mocked

@pytest.mark.asyncio
async def test_unit_connect_success(mock_neo4j_driver):
    """Unit test successful connection (driver creation)."""
    with patch("graph_rag.data_stores.memgraph_store.AsyncGraphDatabase.driver") as mock_get_driver:
        mock_get_driver.return_value = mock_neo4j_driver
        # Use the global settings instance for initialization
        current_settings = get_settings()
        store = MemgraphStore(settings=current_settings) # Use settings
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
    
    # Mock session and run result
    mock_session = mock_neo4j_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock(spec=Result)
    # Simulate the record data that single() should return
    mock_record_data = {"id": node_id}
    # Configure the async single() method to return the mock data
    async def mock_single():
        return mock_record_data
    mock_result.single = mock_single # Assign the async function directly

    # Configure session.run to return the awaitable mock_result
    mock_session.run = AsyncMock(return_value=mock_result)

    result_id = await memgraph_store_unit.add_node(label, properties)

    assert result_id == node_id
    # Check that session.run was called
    mock_session.run.assert_called_once()
    call_args = mock_session.run.call_args
    assert "MERGE (n:Person {id: $props.id})" in call_args[0][0] # Check query structure
    assert call_args[1]["parameters"]["props"] == properties

@pytest.mark.asyncio
async def test_unit_add_relationship(memgraph_store_unit: MemgraphStore, mock_neo4j_driver):
    """Unit test add_relationship query generation."""
    mock_session = mock_neo4j_driver.session.return_value.__aenter__.return_value
    # Configure execute_write to be awaitable (it's called by the retry decorator)
    mock_session.execute_write = AsyncMock(return_value=None) # Doesn't need a specific result for this test
    # Configure close to be awaitable
    mock_session.close = AsyncMock(return_value=None)

    await memgraph_store_unit.add_relationship("p1", "c1", "WORKS_AT", {"role": "Engineer"})

    # Check that execute_write was called (via the retry mechanism)
    mock_session.execute_write.assert_called_once()
    # Check the arguments passed to the underlying tx.run inside execute_write
    # The execute_write mock receives a function (lambda tx: ...) as its first arg
    transaction_func = mock_session.execute_write.call_args[0][0]
    mock_tx = AsyncMock()
    await transaction_func(mock_tx) # Execute the lambda with a mock transaction

    # Now check the call to tx.run
    mock_tx.run.assert_called_once()
    call_args = mock_tx.run.call_args
    assert "MATCH (a {id: $source_id}), (b {id: $target_id})" in call_args[0][0]
    assert "MERGE (a)-[r:WORKS_AT]->(b)" in call_args[0][0]
    assert call_args[1]["source_id"] == "p1"
    assert call_args[1]["target_id"] == "c1"
    assert call_args[1]["props"] == {"role": "Engineer"}

    # Check session close was called
    mock_session.close.assert_called_once()

# --- Integration Tests (Requires running Memgraph via Docker) ---

@pytest.fixture(scope="session")
async def memgraph_store_integration() -> MemgraphStore:
    """Provides a MemgraphStore connected to the real Docker instance."""
    # Ensure settings point to Docker container
    # Use the global settings instance
    current_settings = get_settings()
    if "localhost" not in current_settings.get_memgraph_uri() and "GITHUB_ACTIONS" not in os.environ:
         pytest.skip("Skipping integration tests that require Docker Memgraph unless explicitly targeting localhost.")
    
    store = MemgraphStore(settings=current_settings) # Correct initialization
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