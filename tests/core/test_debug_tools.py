"""Tests for debugging tools."""

import logging
from datetime import datetime
from pathlib import Path

import pytest

# Setup logger for this test module
logger = logging.getLogger(__name__)

from graph_rag.core.debug_tools import DebugContext, GraphDebugger, SystemState

# Use the concrete implementation from conftest.py


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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_query_performance(graph_debugger: GraphDebugger):
    """Test query performance analysis."""
    query = "MATCH (n) RETURN n LIMIT 1"
    result = await graph_debugger.analyze_query_performance(query)

    assert isinstance(result, dict)
    assert result["query"] == f"PROFILE {query}"
    assert "plan" in result
    assert "stats" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_graph_structure(graph_debugger: GraphDebugger):
    """Test graph structure validation."""
    result = await graph_debugger.validate_graph_structure()

    assert isinstance(result, dict)
    assert "orphaned_nodes" in result
    assert "connected_components" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_debug_context(graph_debugger: GraphDebugger):
    """Test creating debug context."""
    context = await graph_debugger.create_debug_context(
        error_type="State Transition Error",
        test_file="test_ingest_command.py",
        test_function="test_document_ingestion",
        error_message="Document nodes created but relationships missing",
    )

    assert isinstance(context, DebugContext)
    assert context.error_type == "State Transition Error"
    assert context.test_file == "test_ingest_command.py"
    assert context.test_function == "test_document_ingestion"
    assert isinstance(context.system_state, SystemState)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_load_debug_context(
    graph_debugger: GraphDebugger, tmp_path: Path
):
    """Test saving and loading debug context."""
    # Create context
    context = await graph_debugger.create_debug_context(
        error_type="Integration Error",
        test_file="test_query_pipeline.py",
        test_function="test_query_execution",
        error_message="Query returns incorrect context",
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


@pytest.mark.asyncio
async def test_capture_system_state_integration(graph_debugger: GraphDebugger):
    """Test capturing system state with actual data."""
    created_ids = [
        "doc-debug-integ-1",
        "doc-debug-integ-2",
        "ent-debug-integ-1",
        "ent-debug-integ-2",
    ]
    try:
        async with graph_debugger.driver.session() as session:
            # Ensure required indices exist for this test
            # Memgraph < 2.10 doesn't support IF NOT EXISTS, handle errors
            indices_to_ensure = [
                "CREATE INDEX ON :Document(id);",
                "CREATE INDEX ON :Chunk(id);",  # Assuming capture_system_state might look for this too
                "CREATE INDEX ON :Person(id);",
                "CREATE INDEX ON :Organisation(id);",
            ]
            for index_query in indices_to_ensure:
                try:
                    await session.run(index_query)
                except Exception as e:
                    # Ignore errors indicating index already exists
                    if (
                        "index already exists" in str(e).lower()
                        or "multiple indices for label" in str(e).lower()
                    ):  # Memgraph >= 2.10
                        logger.warning(
                            f"Index creation skipped (already exists): {index_query} - {e}"
                        )
                    else:
                        raise  # Re-raise unexpected errors

            # Create test data
            await session.run("""
                CREATE (d1:Document {id: 'doc-debug-integ-1', content: 'Debug integ doc 1'}),
                       (d2:Document {id: 'doc-debug-integ-2', content: 'Debug integ doc 2'}),
                       (e1:Person {id: 'ent-debug-integ-1', name: 'Debug Integ Person 1'}),
                       (e2:Organisation {id: 'ent-debug-integ-2', name: 'Debug Integ Org 2'})
            """)
            await session.run("""
                MATCH (d:Document {id: 'doc-debug-integ-1'}), (e:Person {id: 'ent-debug-integ-1'})
                CREATE (d)-[:CONTAINS {score: 0.9}]->(e);
            """)
            await session.run("""
                MATCH (d:Document {id: 'doc-debug-integ-2'}), (e:Organisation {id: 'ent-debug-integ-2'})
                CREATE (d)-[:CONTAINS {score: 0.8}]->(e);
            """)

        # Run the test logic
        state = await graph_debugger.capture_system_state()

        assert isinstance(state, SystemState)
        assert "Document" in state.node_counts
        assert "Person" in state.node_counts
        assert "Organisation" in state.node_counts
        assert state.node_counts["Document"] >= 2
        assert state.node_counts["Person"] >= 1
        assert state.node_counts["Organisation"] >= 1

        assert "CONTAINS" in state.relationship_counts
        assert state.relationship_counts["CONTAINS"] >= 2

        # Check if expected indices exist (Memgraph format :Label(property))
        # Note: SHOW INDEX INFO might return different details based on Memgraph version
        # We check for the presence of indices on the core labels/properties
        def index_exists(label, prop):
            return any(
                idx.get("label") == label and idx.get("property") == prop
                for idx in state.indexes
            )

        # Log the retrieved indexes for debugging
        logger.info(f"Retrieved indexes: {state.indexes}")

        assert index_exists("Document", "id")  # Check for :Document(id)
        assert index_exists("Chunk", "id")  # Check for :Chunk(id)
        # assert index_exists("Person", "id")  # Optionally check others if needed/guaranteed
        # assert index_exists("Organisation", "id")

    finally:
        # Cleanup data created specifically for this test
        async with graph_debugger.driver.session() as session:
            await session.run(
                """
                MATCH (n) WHERE n.id IN $ids
                DETACH DELETE n
            """,
                ids=created_ids,
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_query_performance_integration(graph_debugger: GraphDebugger):
    """Test query performance analysis with actual data."""
    query = "MATCH (d:Document {id: 'doc-debug-1'})-[:CONTAINS]->(p:Person) RETURN d, p"
    result = await graph_debugger.analyze_query_performance(query)

    assert isinstance(result, dict)
    assert result["query"] == f"PROFILE {query}"
    assert "plan" in result
    assert "stats" in result
    assert "nodes_created" in result["stats"]  # Example stat check


@pytest.mark.integration
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
