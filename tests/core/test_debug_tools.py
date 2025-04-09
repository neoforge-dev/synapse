"""Tests for debugging tools."""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from graph_rag.core.debug_tools import GraphDebugger, SystemState, DebugContext
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository

@pytest.mark.asyncio
async def test_capture_system_state(graph_debugger: GraphDebugger):
    """Test capturing system state."""
    state = await graph_debugger.capture_system_state()
    
    assert isinstance(state, SystemState)
    assert isinstance(state.timestamp, datetime)
    assert isinstance(state.node_counts, dict)
    assert isinstance(state.relationship_counts, dict)
    assert isinstance(state.indexes, list)
    assert isinstance(state.constraints, list)
    assert isinstance(state.active_queries, list)
    assert isinstance(state.performance_metrics, dict)

@pytest.mark.asyncio
async def test_analyze_query_performance(graph_debugger: GraphDebugger):
    """Test query performance analysis."""
    query = "MATCH (n) RETURN n LIMIT 1"
    result = await graph_debugger.analyze_query_performance(query)
    
    assert isinstance(result, dict)
    assert result["query"] == query
    assert "plan" in result
    assert "stats" in result

@pytest.mark.asyncio
async def test_validate_graph_structure(graph_debugger: GraphDebugger):
    """Test graph structure validation."""
    result = await graph_debugger.validate_graph_structure()
    
    assert isinstance(result, dict)
    assert "orphaned_nodes" in result
    assert "connected_components" in result

@pytest.mark.asyncio
async def test_create_debug_context(graph_debugger: GraphDebugger):
    """Test creating debug context."""
    context = graph_debugger.create_debug_context(
        error_type="State Transition Error",
        test_file="test_ingest_command.py",
        test_function="test_document_ingestion",
        error_message="Document nodes created but relationships missing"
    )
    
    assert isinstance(context, DebugContext)
    assert context.error_type == "State Transition Error"
    assert context.test_file == "test_ingest_command.py"
    assert context.test_function == "test_document_ingestion"
    assert isinstance(context.system_state, SystemState)

@pytest.mark.asyncio
async def test_save_and_load_debug_context(
    graph_debugger: GraphDebugger,
    tmp_path: Path
):
    """Test saving and loading debug context."""
    # Create context
    context = graph_debugger.create_debug_context(
        error_type="Integration Error",
        test_file="test_query_pipeline.py",
        test_function="test_query_execution",
        error_message="Query returns incorrect context"
    )
    
    # Save context
    save_path = tmp_path / "debug_context.json"
    await graph_debugger.save_debug_context(context, save_path)
    
    # Load context
    loaded_context = await graph_debugger.load_debug_context(save_path)
    
    assert isinstance(loaded_context, DebugContext)
    assert loaded_context.error_type == context.error_type
    assert loaded_context.test_file == context.test_file
    assert loaded_context.test_function == context.test_function
    assert loaded_context.error_message == context.error_message

@pytest.fixture
async def graph_debugger(graph_repository: GraphRepository) -> GraphDebugger:
    """Fixture for GraphDebugger instance using the shared GraphRepository."""
    # The GraphRepository instance from conftest provides the driver
    return GraphDebugger(graph_repository.driver)

@pytest.fixture(scope="module", autouse=True)
async def setup_debug_test_data(graph_repository: GraphRepository):
    """Set up specific graph data for debug tools tests."""
    try:
        # Create nodes
        await graph_repository.execute_query("""
            CREATE (d1:Document {id: 'doc-debug-1', content: 'Debug test doc 1'}),
                   (d2:Document {id: 'doc-debug-2', content: 'Debug test doc 2'}),
                   (e1:Entity {id: 'ent-debug-1', name: 'Debug Entity 1'}),
                   (e2:Entity {id: 'ent-debug-2', name: 'Debug Entity 2'}),
                   (q1:Query {id: 'q-debug-1', text: 'Debug query 1'})
        """)
        
        # Create relationships
        await graph_repository.execute_query("""
            MATCH (d:Document {id: 'doc-debug-1'}), (e:Entity {id: 'ent-debug-1'})
            CREATE (d)-[:CONTAINS {score: 0.9}]->(e);
            
            MATCH (d:Document {id: 'doc-debug-2'}), (e:Entity {id: 'ent-debug-2'})
            CREATE (d)-[:CONTAINS {score: 0.8}]->(e);

            MATCH (q:Query {id: 'q-debug-1'}), (d:Document {id: 'doc-debug-1'})
            CREATE (q)-[:RETRIEVED]->(d);
        """)
        
        # Create necessary indices (if not already covered by global setup)
        await graph_repository.execute_query("""
            CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.id);
            CREATE INDEX IF NOT EXISTS FOR (n:Query) ON (n.id);
        """)
        
        yield # Let tests run
        
    finally:
        # Cleanup: Remove only the data created by this fixture
        await graph_repository.execute_query("""
            MATCH (n) WHERE n.id STARTS WITH 'doc-debug-' OR 
                           n.id STARTS WITH 'ent-debug-' OR 
                           n.id STARTS WITH 'q-debug-'
            DETACH DELETE n
        """)

@pytest.mark.asyncio
async def test_capture_system_state_integration(graph_debugger: GraphDebugger):
    """Test capturing system state with actual data."""
    state = await graph_debugger.capture_system_state()
    
    assert isinstance(state, SystemState)
    assert "Document" in state.node_counts
    assert "Entity" in state.node_counts
    assert "Query" in state.node_counts
    assert state.node_counts["Document"] >= 2  # Includes other test data potentially
    assert state.node_counts["Entity"] >= 2
    assert state.node_counts["Query"] >= 1
    
    assert "CONTAINS" in state.relationship_counts
    assert "RETRIEVED" in state.relationship_counts
    assert state.relationship_counts["CONTAINS"] >= 2
    assert state.relationship_counts["RETRIEVED"] >= 1

    # Check if expected indices exist (adjust based on actual index names)
    index_names = [idx['name'] for idx in state.indexes]
    assert "index_document_id" in index_names # From global setup
    assert "index_chunk_id" in index_names    # From global setup
    assert "index_entity_id" in index_names   # From local setup
    assert "index_query_id" in index_names    # From local setup

@pytest.mark.asyncio
async def test_analyze_query_performance_integration(graph_debugger: GraphDebugger):
    """Test query performance analysis with actual data."""
    query = "MATCH (d:Document {id: 'doc-debug-1'})-[:CONTAINS]->(e:Entity) RETURN d, e"
    result = await graph_debugger.analyze_query_performance(query)
    
    assert isinstance(result, dict)
    assert result["query"] == f"PROFILE {query}" # PROFILE is prepended by the tool
    assert "plan" in result
    assert "stats" in result
    assert "nodes_created" in result["stats"] # Example stat check

@pytest.mark.asyncio
async def test_validate_graph_structure_integration(graph_debugger: GraphDebugger):
    """Test graph structure validation with actual data."""
    # Note: This test assumes the test data creates a connected component
    # and might need adjustments based on broader test setup/cleanup.
    result = await graph_debugger.validate_graph_structure()
    
    assert isinstance(result, dict)
    assert "orphaned_nodes" in result
    assert "connected_components" in result
    # Potentially assert specific counts if setup guarantees no orphans
    # assert not any(item['count'] > 0 for item in result['orphaned_nodes']) 