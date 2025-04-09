"""Tests for graph-specific debugging scenarios."""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import neo4j
from unittest.mock import patch, AsyncMock

from graph_rag.core.debug_tools import GraphDebugger, DebugContext, SystemState
from graph_rag.core.senior_debug_protocol import Investigation, TestFailure
from graph_rag.domain.models import Node, Relationship # Use correct models

@pytest.mark.asyncio
async def test_debug_orphaned_nodes(graph_debugger: GraphDebugger):
    """Test debugging scenario with orphaned nodes."""
    # Create some orphaned nodes directly using the driver from the debugger
    # Ensure the graph_debugger fixture provides access to the driver
    async with graph_debugger.driver.session() as session:
        await session.run("""
            CREATE (n1:TestNode {id: 'orphan1'}),
                   (n2:TestNode {id: 'orphan2'})
        """)

    try:
        # This should trigger orphaned node detection
        structure = await graph_debugger.validate_graph_structure()
        assert "orphaned_nodes" in structure
        # Adjust check based on actual label format if needed
        assert any(node["labels"] == ["TestNode"] for node in structure["orphaned_nodes"])

        # Create a dummy TestFailure object for debugging context
        failure = TestFailure(
            error_type="ValueError",
            error_message="Orphaned nodes detected",
            test_file="test_graph_debugging_scenarios.py",
            test_function="test_debug_orphaned_nodes",
            traceback_info="",
            test_code="",
            timestamp=datetime.now()
        )

        # Debug the issue
        investigation, context = await graph_debugger.debug_test_failure(failure)

        assert isinstance(investigation, Investigation)
        assert isinstance(context, DebugContext)
        assert any(h["type"] == "graph_structure" for h in investigation.hypotheses)

    finally:
        # Cleanup
        async with graph_debugger.driver.session() as session:
            await session.run("MATCH (n:TestNode) DETACH DELETE n")

@pytest.mark.asyncio
async def test_debug_query_performance(graph_debugger: GraphDebugger):
    """Test debugging scenario with query performance issues."""
    # Create test data
    async with graph_debugger.driver.session() as session:
        await session.run("""
            CREATE (n1:PerformanceTest {id: 'perf1'}),
                   (n2:PerformanceTest {id: 'perf2'}),
                   (n3:PerformanceTest {id: 'perf3'}),
                   (n1)-[:RELATES_TO]->(n2),
                   (n2)-[:RELATES_TO]->(n3)
        """)

    try:
        # Execute a potentially problematic query
        query = """
            MATCH (n:PerformanceTest)
            WHERE n.id = 'perf1'
            MATCH (n)-[*1..5]-(m)
            RETURN m
        """

        # Create dummy failure
        failure = TestFailure(
            error_type="TimeoutError",
            error_message="Query performance issue",
            test_file="test_graph_debugging_scenarios.py",
            test_function="test_debug_query_performance",
            traceback_info="",
            test_code=query,
            timestamp=datetime.now()
        )

        # Debug performance issue
        investigation, context = await graph_debugger.debug_test_failure(failure)

        assert isinstance(investigation, Investigation)
        assert isinstance(context, DebugContext)
        assert any(h["type"] == "query_performance" for h in investigation.hypotheses)

        # Test persistent error handling (assuming this method exists on debugger)
        # This might need adaptation based on the actual protocol implementation
        # If handle_persistent_graph_error is part of SeniorDebugProtocol, use that directly
        # For now, assume it might be accessible via debugger or needs a separate test
        # reasoning = await graph_debugger.handle_persistent_graph_error(
        #     Exception("Query still slow"),
        #     2,
        #     query
        # )
        # assert len(reasoning) > 0
        # assert any("Query Performance Analysis" in r for r in reasoning)

    finally:
        # Cleanup
        async with graph_debugger.driver.session() as session:
            await session.run("MATCH (n:PerformanceTest) DETACH DELETE n")

@pytest.mark.asyncio
async def test_debug_relationship_patterns(graph_debugger: GraphDebugger):
    """Test debugging scenario with relationship pattern issues."""
    # Create test data with potential relationship issues
    async with graph_debugger.driver.session() as session:
        await session.run("""
            CREATE (n1:PatternTest {id: 'pat1'}),
                   (n2:PatternTest {id: 'pat2'}),
                   (n3:PatternTest {id: 'pat3'}),
                   (n1)-[:INVALID_REL]->(n2),
                   (n2)-[:INVALID_REL]->(n3),
                   (n3)-[:INVALID_REL]->(n1)
        """)

    try:
        # Create dummy failure
        failure = TestFailure(
            error_type="SchemaError",
            error_message="Invalid relationship pattern",
            test_file="test_graph_debugging_scenarios.py",
            test_function="test_debug_relationship_patterns",
            traceback_info="",
            test_code="",
            timestamp=datetime.now()
        )

        # Debug relationship pattern issue
        investigation, context = await graph_debugger.debug_test_failure(failure)

        assert isinstance(investigation, Investigation)
        assert isinstance(context, DebugContext)

        # Check for graph-specific hypotheses
        graph_hypotheses = [h for h in investigation.hypotheses
                          if h["type"] in ["graph_structure", "query_performance"]]
        assert len(graph_hypotheses) > 0

        # Test state capture
        state = await graph_debugger.capture_system_state()
        assert "PatternTest" in state.node_counts
        assert "INVALID_REL" in state.relationship_counts

    finally:
        # Cleanup
        async with graph_debugger.driver.session() as session:
            await session.run("MATCH (n:PatternTest) DETACH DELETE n")

@pytest.mark.asyncio
async def test_debug_transaction_issues(graph_debugger: GraphDebugger):
    """Test debugging scenario with transaction issues."""
    try:
        # Start a transaction (using the driver directly)
        async with graph_debugger.driver.session() as session:
            async with session.begin_transaction() as tx:
                # Create some test data
                await tx.run("CREATE (n:TransactionTest {id: 'tx1'})")

                # Simulate a transaction error
                try:
                    # This might cause a constraint violation or other issue
                    await tx.run("CREATE (n:TransactionTest {id: 'tx1'})") # Duplicate ID
                    await tx.commit()
                    pytest.fail("Transaction should have failed")
                except Exception as e:
                    await tx.rollback() # Ensure rollback on error
                    # Debug the transaction issue
                    failure = TestFailure(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        test_file="test_graph_debugging_scenarios.py",
                        test_function="test_debug_transaction_issues",
                        traceback_info="", # Populate if possible
                        test_code="tx.run(...)",
                        timestamp=datetime.now()
                    )
                    investigation, context = await graph_debugger.debug_test_failure(failure)

                    assert isinstance(investigation, Investigation)
                    assert isinstance(context, DebugContext)

                    # Check for transaction-specific hypotheses (adapt check as needed)
                    assert any("transaction" in h["description"].lower()
                              for h in investigation.hypotheses)

    finally:
        # Cleanup
        async with graph_debugger.driver.session() as session:
            await session.run("MATCH (n:TransactionTest) DETACH DELETE n")

@pytest.mark.asyncio
async def test_debug_index_issues(graph_debugger: GraphDebugger):
    """Test debugging scenario with index issues."""
    try:
        # Create test data without proper index
        async with graph_debugger.driver.session() as session:
            await session.run("""
                CREATE (n1:IndexTest {id: 'idx1', value: 1}),
                       (n2:IndexTest {id: 'idx2', value: 2}),
                       (n3:IndexTest {id: 'idx3', value: 3})
            """)

        # Execute a query that would benefit from an index
        query = """
            MATCH (n:IndexTest)
            WHERE n.value > 1
            RETURN n
        """

        # Create dummy failure
        failure = TestFailure(
            error_type="PerformanceWarning",
            error_message="Query might need index",
            test_file="test_graph_debugging_scenarios.py",
            test_function="test_debug_index_issues",
            traceback_info="",
            test_code=query,
            timestamp=datetime.now()
        )

        # Debug potential index issue
        investigation, context = await graph_debugger.debug_test_failure(failure)

        assert isinstance(investigation, Investigation)
        assert isinstance(context, DebugContext)

        # Check for index-related hypotheses
        assert any("index" in h["description"].lower()
                  for h in investigation.hypotheses)

        # Test query performance analysis
        performance = await graph_debugger.analyze_query_performance(query)
        assert "plan" in performance
        assert "stats" in performance

    finally:
        # Cleanup
        async with graph_debugger.driver.session() as session:
            await session.run("MATCH (n:IndexTest) DETACH DELETE n")

# Helper to create dummy TestFailure objects
def create_dummy_failure(test_name: str, error_message: str) -> TestFailure:
    return TestFailure(
        error_type="DummyError",
        error_message=error_message,
        test_file="test_graph_debugging_scenarios.py",
        test_function=test_name,
        traceback_info="",
        test_code="",
        timestamp=datetime.now()
    ) 