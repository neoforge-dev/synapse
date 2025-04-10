"""Debugging tools for GraphRAG system."""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from pathlib import Path

from neo4j import GraphDatabase
from pydantic import BaseModel

from graph_rag.core.senior_debug_protocol import (
    SeniorDebugProtocol,
    TestFailure,
    Investigation
)

logger = logging.getLogger(__name__)

class SystemState(BaseModel):
    """Represents the current state of the system."""
    timestamp: datetime
    node_counts: Dict[str, int]
    relationship_counts: Dict[str, int]
    indexes: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    active_queries: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]

class DebugContext(BaseModel):
    """Context for debugging operations."""
    error_type: str
    test_file: str
    test_function: str
    error_message: str
    system_state: SystemState
    hypotheses: List[Dict[str, Any]]
    verification_steps: List[Dict[str, Any]]
    resolution: Optional[Dict[str, Any]] = None

class GraphDebugger:
    """Tools for debugging graph-based operations."""

    def __init__(self, driver: GraphDatabase.driver):
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.senior_protocol = None

    def initialize_senior_protocol(self, test_file: str, test_function: str):
        """Initialize the Senior Developer Debugging Protocol."""
        self.senior_protocol = SeniorDebugProtocol(test_file, test_function)
        return self.senior_protocol

    async def capture_system_state(self) -> SystemState:
        """Capture current state of the graph database."""
        async with self.driver.session() as session:
            # Get node counts by label
            result = await session.run("""
                MATCH (n)
                RETURN labels(n) as label, count(*) as count
            """)
            node_counts = await result.data()

            # Get relationship counts by type
            result = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
            """)
            rel_counts = await result.data()

            # Get index information
            result = await session.run("SHOW INDEX INFO")
            indexes = await result.data()

            # Get constraint information
            result = await session.run("SHOW CONSTRAINT INFO")
            constraints = await result.data()

            # Get active queries
            result = await session.run("SHOW TRANSACTIONS")
            active_queries = await result.data()

            # Get performance metrics
            result = await session.run("""
                CALL db.stats.retrieve("ALL")
                YIELD section, map
                RETURN section, map
            """)
            performance = await result.data()

            return SystemState(
                timestamp=datetime.utcnow(),
                node_counts={item['label'][0]: item['count'] for item in node_counts},
                relationship_counts={item['type']: item['count'] for item in rel_counts},
                indexes=indexes,
                constraints=constraints,
                active_queries=active_queries,
                performance_metrics={item['section']: item['map'] for item in performance}
            )

    async def analyze_query_performance(self, query: str) -> Dict[str, Any]:
        """Analyze performance of a specific query."""
        async with self.driver.session() as session:
            result = await session.run(f"PROFILE {query}")
            profile = await result.consume()
            return {
                "query": f"PROFILE {query}",
                "plan": profile.profile,
                "stats": profile.counters
            }

    async def validate_graph_structure(self) -> Dict[str, Any]:
        """Validate the structure of the graph database."""
        async with self.driver.session() as session:
            # Check for orphaned nodes
            result = await session.run("""
                MATCH (n)
                WHERE NOT (n)--()
                RETURN labels(n) as label, count(*) as count
            """)
            orphaned = await result.data()

            # Check for disconnected components
            result = await session.run("""
                CALL gds.wcc.stream('myGraph')
                YIELD nodeId, componentId
                RETURN componentId, count(*) as size
                ORDER BY size DESC
            """)
            components = await result.data()

            return {
                "orphaned_nodes": orphaned,
                "connected_components": components
            }

    async def trace_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Trace a specific transaction's operations."""
        async with self.driver.session() as session:
            result = await session.run("""
                SHOW TRANSACTION $txId
                YIELD *
            """, txId=transaction_id)
            return await result.data()

    async def create_debug_context(
        self,
        error_type: str,
        test_file: str,
        test_function: str,
        error_message: str
    ) -> DebugContext:
        """Create a new debugging context."""
        system_state = await self.capture_system_state()
        
        return DebugContext(
            error_type=error_type,
            test_file=test_file,
            test_function=test_function,
            error_message=error_message,
            system_state=system_state,
            hypotheses=[],
            verification_steps=[],
            resolution=None
        )

    async def save_debug_context(self, context: DebugContext, path: Path) -> None:
        """Save debugging context to a file."""
        with open(path, 'w') as f:
            f.write(context.json(indent=2))

    async def load_debug_context(self, path: Path) -> DebugContext:
        """Load debugging context from a file."""
        with open(path, 'r') as f:
            return DebugContext.parse_raw(f.read())

    async def debug_test_failure(
        self,
        error: Exception,
        test_file: str,
        test_function: str
    ) -> Tuple[Investigation, DebugContext]:
        """Debug a test failure using both Senior Protocol and Graph Debugging."""
        # Initialize senior protocol if not already done
        if not self.senior_protocol:
            self.initialize_senior_protocol(test_file, test_function)
        
        # Use senior protocol for analysis
        failure = self.senior_protocol.observe_failure(error)
        failure = self.senior_protocol.analyze_test_case(failure)
        investigation = self.senior_protocol.create_investigation(failure)
        
        # Generate hypotheses
        hypotheses = self.senior_protocol.generate_hypotheses(investigation)
        investigation.hypotheses = hypotheses
        
        # Create graph-specific debug context
        debug_context = self.create_debug_context(
            error_type=type(error).__name__,
            test_file=test_file,
            test_function=test_function,
            error_message=str(error)
        )
        
        # Add graph-specific hypotheses
        graph_hypotheses = [
            {
                "type": "graph_structure",
                "description": "Graph structure or relationship issues",
                "confidence": 0.7,
                "verification_steps": [
                    "Check for orphaned nodes",
                    "Verify relationship patterns",
                    "Validate graph constraints"
                ]
            },
            {
                "type": "query_performance",
                "description": "Query performance or optimization issues",
                "confidence": 0.6,
                "verification_steps": [
                    "Profile query execution",
                    "Check index usage",
                    "Analyze query plan"
                ]
            }
        ]
        
        investigation.hypotheses.extend(graph_hypotheses)
        debug_context.hypotheses = investigation.hypotheses
        
        return investigation, debug_context

    async def handle_persistent_graph_error(
        self,
        error: Exception,
        count: int,
        query: Optional[str] = None
    ) -> List[str]:
        """Handle persistent graph-related errors."""
        if count >= 2:
            reasoning = self.senior_protocol.handle_persistent_error(error, count)
            
            # Add graph-specific reasoning
            if query:
                performance = await self.analyze_query_performance(query)
                reasoning.append(
                    f"Query Performance Analysis:\n"
                    f"Review the query execution plan and performance metrics:\n"
                    f"{performance}"
                )
            
            structure = await self.validate_graph_structure()
            reasoning.append(
                f"Graph Structure Analysis:\n"
                f"Review the graph structure and connectivity:\n"
                f"{structure}"
            )
            
            return reasoning
        return [] 