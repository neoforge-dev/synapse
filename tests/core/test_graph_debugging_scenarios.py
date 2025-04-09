"""Tests for graph-specific debugging scenarios."""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import neo4j

from graph_rag.core.debug_tools import GraphDebugger, DebugContext
from graph_rag.core.senior_debug_protocol import Investigation

@pytest.mark.asyncio
async def test_debug_orphaned_nodes(graph_debugger: GraphDebugger):
    """Test debugging scenario with orphaned nodes."""
    # Create some orphaned nodes
    await graph_debugger.driver.session().run("""
        CREATE (n1:TestNode {id: 'orphan1'}),
               (n2:TestNode {id: 'orphan2'})
    """)
    
    try:
        # This should trigger orphaned node detection
        structure = await graph_debugger.validate_graph_structure()
        assert "orphaned_nodes" in structure
        assert any(node["label"] == ["TestNode"] for node in structure["orphaned_nodes"])
        
        # Debug the issue
        investigation, context = await graph_debugger.debug_test_failure(
            Exception("Orphaned nodes detected"),
            "test_graph_debugging_scenarios.py",
            "test_debug_orphaned_nodes"
        )
        
        assert isinstance(investigation, Investigation)
        assert isinstance(context, DebugContext)
        assert any(h["type"] == "graph_structure" for h in investigation.hypotheses)
        
    finally:
        # Cleanup
        await graph_debugger.driver.session().run("""
            MATCH (n:TestNode)
            DELETE n
        """)

@pytest.mark.asyncio
async def test_debug_query_performance(graph_debugger: GraphDebugger):
    """Test debugging scenario with query performance issues."""
    # Create test data
    await graph_debugger.driver.session().run("""
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
        
        # Debug performance issue
        investigation, context = await graph_debugger.debug_test_failure(
            Exception("Query performance issue"),
            "test_graph_debugging_scenarios.py",
            "test_debug_query_performance"
        )
        
        assert isinstance(investigation, Investigation)
        assert isinstance(context, DebugContext)
        assert any(h["type"] == "query_performance" for h in investigation.hypotheses)
        
        # Test persistent error handling
        reasoning = await graph_debugger.handle_persistent_graph_error(
            Exception("Query still slow"),
            2,
            query
        )
        
        assert len(reasoning) > 0
        assert any("Query Performance Analysis" in r for r in reasoning)
        
    finally:
        # Cleanup
        await graph_debugger.driver.session().run("""
            MATCH (n:PerformanceTest)
            DETACH DELETE n
        """)

@pytest.mark.asyncio
async def test_debug_relationship_patterns(graph_debugger: GraphDebugger):
    """Test debugging scenario with relationship pattern issues."""
    # Create test data with potential relationship issues
    await graph_debugger.driver.session().run("""
        CREATE (n1:PatternTest {id: 'pat1'}),
               (n2:PatternTest {id: 'pat2'}),
               (n3:PatternTest {id: 'pat3'}),
               (n1)-[:INVALID_REL]->(n2),
               (n2)-[:INVALID_REL]->(n3),
               (n3)-[:INVALID_REL]->(n1)
    """)
    
    try:
        # Debug relationship pattern issue
        investigation, context = await graph_debugger.debug_test_failure(
            Exception("Invalid relationship pattern"),
            "test_graph_debugging_scenarios.py",
            "test_debug_relationship_patterns"
        )
        
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
        await graph_debugger.driver.session().run("""
            MATCH (n:PatternTest)
            DETACH DELETE n
        """)

@pytest.mark.asyncio
async def test_debug_transaction_issues(graph_debugger: GraphDebugger):
    """Test debugging scenario with transaction issues."""
    try:
        # Start a transaction
        session = graph_debugger.driver.session()
        tx = session.begin_transaction()
        
        # Create some test data
        tx.run("CREATE (n:TransactionTest {id: 'tx1'})")
        
        # Simulate a transaction error
        try:
            tx.run("CREATE (n:TransactionTest {id: 'tx2'})")
            raise Exception("Transaction conflict")
        except Exception as e:
            # Debug the transaction issue
            investigation, context = await graph_debugger.debug_test_failure(
                e,
                "test_graph_debugging_scenarios.py",
                "test_debug_transaction_issues"
            )
            
            assert isinstance(investigation, Investigation)
            assert isinstance(context, DebugContext)
            
            # Check for transaction-specific hypotheses
            assert any("transaction" in h["description"].lower() 
                      for h in investigation.hypotheses)
            
    finally:
        # Cleanup
        await graph_debugger.driver.session().run("""
            MATCH (n:TransactionTest)
            DELETE n
        """)

@pytest.mark.asyncio
async def test_debug_index_issues(graph_debugger: GraphDebugger):
    """Test debugging scenario with index issues."""
    try:
        # Create test data without proper index
        await graph_debugger.driver.session().run("""
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
        
        # Debug potential index issue
        investigation, context = await graph_debugger.debug_test_failure(
            Exception("Query might need index"),
            "test_graph_debugging_scenarios.py",
            "test_debug_index_issues"
        )
        
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
        await graph_debugger.driver.session().run("""
            MATCH (n:IndexTest)
            DELETE n
        """) 