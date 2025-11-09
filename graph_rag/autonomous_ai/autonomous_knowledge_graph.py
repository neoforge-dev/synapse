"""
Autonomous Knowledge Graph Builder

Core component that combines pattern analysis and schema generation to create
self-configuring knowledge graphs that adapt to enterprise data patterns.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from graph_rag.autonomous_ai.ai_pattern_analyzer import DataPatternAnalyzer, DataPatterns
from graph_rag.autonomous_ai.autonomous_schema_generator import (
    AdaptiveSchemaGenerator,
    GraphSchema,
    SchemaEvolution,
    UsageFeedback,
)
from graph_rag.core.interfaces import GraphRepository
from graph_rag.domain.models import Document, Entity, Relationship

logger = logging.getLogger(__name__)


@dataclass
class AutonomousKGStats:
    """Statistics for autonomous knowledge graph operations."""
    documents_processed: int = 0
    entities_discovered: int = 0
    relationships_inferred: int = 0
    schema_evolutions: int = 0
    performance_improvements: float = 0.0
    last_optimization: datetime | None = None
    confidence_score: float = 0.0


@dataclass
class OptimizationMetrics:
    """Metrics for measuring optimization success."""
    query_performance_improvement: float = 0.0
    storage_efficiency_improvement: float = 0.0
    accuracy_improvement: float = 0.0
    user_satisfaction_score: float = 0.0
    overall_improvement: float = 0.0


class AutonomousKnowledgeGraphBuilder:
    """
    Self-configuring knowledge graph builder that automatically:
    - Analyzes data patterns
    - Generates optimal graph schemas
    - Continuously optimizes based on usage
    - Adapts to new data patterns without human intervention

    This is the core autonomous AI component that transforms assisted
    knowledge graph management into fully autonomous operations.
    """

    def __init__(
        self,
        graph_repository: GraphRepository,
        pattern_analyzer: DataPatternAnalyzer | None = None,
        schema_generator: AdaptiveSchemaGenerator | None = None,
        optimization_interval: timedelta = timedelta(hours=24),
        min_confidence: float = 0.7
    ):
        self.graph_repository = graph_repository
        self.pattern_analyzer = pattern_analyzer or DataPatternAnalyzer(min_confidence=min_confidence)
        self.schema_generator = schema_generator or AdaptiveSchemaGenerator(min_confidence=min_confidence)
        self.optimization_interval = optimization_interval
        self.min_confidence = min_confidence

        # Operational state
        self.current_schema: GraphSchema | None = None
        self.stats = AutonomousKGStats()
        self.usage_metrics: list[dict[str, Any]] = []
        self.last_optimization = datetime.utcnow()

        # Performance tracking
        self.query_performance_history: list[dict[str, Any]] = []
        self.optimization_history: list[OptimizationMetrics] = []

    async def initialize_autonomous_operations(self, initial_documents: list[Document]) -> GraphSchema:
        """
        Initialize autonomous operations by analyzing initial data and generating schema.

        Args:
            initial_documents: Initial document collection for pattern analysis

        Returns:
            Generated initial schema for the knowledge graph
        """
        logger.info(f"Initializing autonomous operations with {len(initial_documents)} documents")

        # Analyze patterns in initial data
        patterns = await self.pattern_analyzer.analyze_full_patterns(initial_documents)

        # Generate initial schema based on patterns
        schema = await self.schema_generator.generate_initial_schema(patterns)

        # Apply schema to graph repository
        await self._apply_schema_to_graph(schema)

        self.current_schema = schema
        self.stats.documents_processed = len(initial_documents)
        self.stats.confidence_score = schema.confidence_score

        logger.info(
            f"Autonomous operations initialized with schema confidence: {schema.confidence_score:.2f}"
        )

        return schema

    async def process_new_documents(
        self,
        documents: list[Document],
        enable_schema_evolution: bool = True
    ) -> dict[str, Any]:
        """
        Process new documents with autonomous pattern recognition and schema evolution.

        Args:
            documents: New documents to process
            enable_schema_evolution: Whether to evolve schema based on new patterns

        Returns:
            Processing results including any schema changes
        """
        logger.info(f"Processing {len(documents)} new documents autonomously")

        processing_start = datetime.utcnow()
        results = {
            "documents_processed": 0,
            "new_entities": 0,
            "new_relationships": 0,
            "schema_changes": None,
            "processing_time": 0.0,
            "confidence_score": 0.0
        }

        try:
            # Process documents with current schema
            for doc in documents:
                await self._process_document_autonomously(doc)
                results["documents_processed"] += 1

            # Analyze new patterns if we have enough new data
            if len(documents) >= 10 and enable_schema_evolution:
                new_patterns = await self.pattern_analyzer.analyze_full_patterns(documents)

                # Check if schema evolution is needed
                evolution_needed = await self._assess_schema_evolution_need(new_patterns)

                if evolution_needed:
                    schema_changes = await self._evolve_schema_autonomously(new_patterns)
                    results["schema_changes"] = schema_changes
                    self.stats.schema_evolutions += 1

            # Update statistics
            self.stats.documents_processed += len(documents)

            processing_time = (datetime.utcnow() - processing_start).total_seconds()
            results["processing_time"] = processing_time
            results["confidence_score"] = self.stats.confidence_score

            logger.info(f"Processed {len(documents)} documents in {processing_time:.2f}s")

        except Exception as e:
            logger.error(f"Error in autonomous document processing: {e}", exc_info=True)
            raise

        return results

    async def _process_document_autonomously(self, document: Document) -> None:
        """Process a single document with autonomous pattern recognition."""

        # Add document to graph
        await self.graph_repository.add_document(document)

        # Process chunks
        for chunk in document.chunks:
            await self.graph_repository.add_chunk(chunk)

            # Extract and process entities autonomously
            entities_data = chunk.metadata.get('entities', [])
            for entity_data in entities_data:
                entity = Entity(
                    id=entity_data['id'],
                    text=entity_data['text'],
                    label=entity_data['label'],
                    metadata=entity_data.get('metadata', {})
                )
                await self.graph_repository.add_entity(entity)
                self.stats.entities_discovered += 1

            # Process relationships autonomously
            relationships_data = chunk.metadata.get('relationships', [])
            for rel_data in relationships_data:
                relationship = Relationship(
                    id=f"{rel_data['source_entity_id']}_{rel_data['label']}_{rel_data['target_entity_id']}",
                    source_entity_id=rel_data['source_entity_id'],
                    target_entity_id=rel_data['target_entity_id'],
                    label=rel_data['label'],
                    metadata={}
                )
                await self.graph_repository.add_relationship(relationship)
                self.stats.relationships_inferred += 1

    async def _assess_schema_evolution_need(self, new_patterns: DataPatterns) -> bool:
        """Assess whether schema evolution is needed based on new patterns."""
        if not self.current_schema:
            return True

        # Compare new patterns with current schema
        current_entity_types = {nt.name for nt in self.current_schema.node_types}
        current_rel_types = {rt.name for rt in self.current_schema.relationship_types}

        new_entity_types = {
            self.schema_generator._normalize_type_name(ep.entity_type)
            for ep in new_patterns.entity_patterns
        }
        new_rel_types = {
            self.schema_generator._normalize_type_name(rp.relationship_type)
            for rp in new_patterns.relationship_patterns
        }

        # Check for new types
        unseen_entity_types = new_entity_types - current_entity_types
        unseen_rel_types = new_rel_types - current_rel_types

        # Evolution needed if we find significant new patterns
        significant_new_patterns = len(unseen_entity_types) >= 2 or len(unseen_rel_types) >= 2

        # Or if overall quality significantly improved
        current_quality = self.current_schema.metadata.get('quality_metrics', {}).get('overall_quality', 0)
        new_quality = new_patterns.quality_metrics.get('overall_quality', 0)
        quality_improvement = new_quality > current_quality + 0.1  # 10% improvement threshold

        evolution_needed = significant_new_patterns or quality_improvement

        if evolution_needed:
            logger.info(
                f"Schema evolution needed: new_entities={len(unseen_entity_types)}, "
                f"new_relationships={len(unseen_rel_types)}, "
                f"quality_improvement={quality_improvement}"
            )

        return evolution_needed

    async def _evolve_schema_autonomously(self, new_patterns: DataPatterns) -> SchemaEvolution:
        """Evolve schema autonomously based on new patterns."""
        logger.info("Evolving schema autonomously based on new patterns")

        # Generate updated schema
        new_schema = await self.schema_generator.generate_initial_schema(new_patterns)

        # Create evolution object (simplified - in practice would be more sophisticated)
        evolution = SchemaEvolution(
            added_elements=[],  # Would populate with actual differences
            modified_elements=[],
            removed_elements=[],
            performance_improvements={"pattern_recognition": 0.15},
            confidence_score=new_schema.confidence_score,
            reasoning="Schema evolved based on new data patterns",
            impact_assessment={"performance_impact": "positive"}
        )

        # Apply new schema if confidence is sufficient
        if new_schema.confidence_score >= self.min_confidence:
            await self._apply_schema_to_graph(new_schema)
            self.current_schema = new_schema
            self.stats.confidence_score = new_schema.confidence_score

            logger.info(f"Schema evolved successfully with confidence {new_schema.confidence_score:.2f}")
        else:
            logger.warning(f"Schema evolution rejected due to low confidence: {new_schema.confidence_score:.2f}")

        return evolution

    async def _apply_schema_to_graph(self, schema: GraphSchema) -> None:
        """Apply schema changes to the graph repository."""
        logger.info("Applying schema to graph repository")

        try:
            # Create indexes
            for index in schema.indexes:
                if index.properties.get("type") == "fulltext":
                    # Create full-text index (Memgraph-specific syntax)
                    query = "CREATE FULLTEXT INDEX ON :Node(text)"
                    await self.graph_repository.execute_query(query)
                elif index.properties.get("type") == "unique":
                    # Create unique constraint
                    node_type = index.properties.get("node_type", "Node")
                    property_name = index.properties.get("property", "id")
                    query = f"CREATE CONSTRAINT ON (n:{node_type}) ASSERT n.{property_name} IS UNIQUE"
                    await self.graph_repository.execute_query(query)

            # Apply constraints
            for constraint in schema.constraints:
                if constraint.properties.get("type") == "unique":
                    node_type = constraint.properties.get("node_type", "Node")
                    property_name = constraint.properties.get("property", "id")
                    query = f"CREATE CONSTRAINT ON (n:{node_type}) ASSERT n.{property_name} IS UNIQUE"
                    await self.graph_repository.execute_query(query)

            logger.info("Schema applied successfully to graph repository")

        except Exception as e:
            logger.error(f"Error applying schema to graph: {e}", exc_info=True)
            # Continue operation even if some schema elements fail

    async def optimize_performance_autonomously(self) -> OptimizationMetrics:
        """
        Perform autonomous performance optimization based on usage patterns.

        Returns:
            Metrics showing optimization improvements
        """
        logger.info("Starting autonomous performance optimization")

        optimization_start = datetime.utcnow()

        # Collect usage feedback
        usage_feedback = await self._collect_usage_feedback()

        # Identify optimization opportunities
        optimization_opportunities = await self._identify_optimization_opportunities(usage_feedback)

        # Apply optimizations
        applied_optimizations = []
        for opportunity in optimization_opportunities:
            try:
                result = await self._apply_optimization(opportunity)
                if result:
                    applied_optimizations.append(result)
            except Exception as e:
                logger.warning(f"Failed to apply optimization {opportunity}: {e}")

        # Measure improvement
        metrics = await self._measure_optimization_impact(applied_optimizations)

        # Update stats
        self.stats.performance_improvements += metrics.overall_improvement
        self.stats.last_optimization = optimization_start
        self.optimization_history.append(metrics)

        optimization_time = (datetime.utcnow() - optimization_start).total_seconds()
        logger.info(
            f"Autonomous optimization completed in {optimization_time:.2f}s, "
            f"overall improvement: {metrics.overall_improvement:.2f}"
        )

        return metrics

    async def _collect_usage_feedback(self) -> UsageFeedback:
        """Collect usage feedback from graph operations."""

        # Get query patterns from recent usage
        query_patterns = []

        # Get performance metrics
        performance_metrics = {}

        # Placeholder implementation - would collect real metrics
        return UsageFeedback(
            query_patterns=query_patterns,
            performance_metrics=performance_metrics,
            error_patterns=[],
            user_feedback=[]
        )

    async def _identify_optimization_opportunities(
        self,
        feedback: UsageFeedback
    ) -> list[dict[str, Any]]:
        """Identify optimization opportunities from usage feedback."""

        opportunities = []

        # Identify missing indexes for slow queries
        # (Placeholder implementation)

        # Identify unused indexes
        # (Placeholder implementation)

        # Identify schema optimizations
        # (Placeholder implementation)

        return opportunities

    async def _apply_optimization(self, opportunity: dict[str, Any]) -> dict[str, Any] | None:
        """Apply a specific optimization."""

        optimization_type = opportunity.get("type")

        if optimization_type == "add_index":
            # Add missing index
            index_query = opportunity.get("query")
            if index_query:
                await self.graph_repository.execute_query(index_query)
                return {"type": "index_added", "query": index_query}

        elif optimization_type == "remove_index":
            # Remove unused index
            drop_query = opportunity.get("query")
            if drop_query:
                await self.graph_repository.execute_query(drop_query)
                return {"type": "index_removed", "query": drop_query}

        return None

    async def _measure_optimization_impact(
        self,
        applied_optimizations: list[dict[str, Any]]
    ) -> OptimizationMetrics:
        """Measure the impact of applied optimizations."""

        # Placeholder implementation - would measure real performance improvements
        metrics = OptimizationMetrics()

        if applied_optimizations:
            # Estimate improvements based on optimization types
            for opt in applied_optimizations:
                if opt["type"] == "index_added":
                    metrics.query_performance_improvement += 0.2  # 20% improvement estimate
                elif opt["type"] == "index_removed":
                    metrics.storage_efficiency_improvement += 0.1  # 10% improvement estimate

            # Calculate overall improvement
            improvements = [
                metrics.query_performance_improvement,
                metrics.storage_efficiency_improvement,
                metrics.accuracy_improvement,
                metrics.user_satisfaction_score
            ]
            metrics.overall_improvement = np.mean([i for i in improvements if i > 0])

        return metrics

    async def get_autonomous_status(self) -> dict[str, Any]:
        """Get current status of autonomous operations."""

        time_since_last_optimization = datetime.utcnow() - (
            self.stats.last_optimization or datetime.utcnow()
        )

        return {
            "schema_version": self.current_schema.version if self.current_schema else None,
            "confidence_score": self.stats.confidence_score,
            "documents_processed": self.stats.documents_processed,
            "entities_discovered": self.stats.entities_discovered,
            "relationships_inferred": self.stats.relationships_inferred,
            "schema_evolutions": self.stats.schema_evolutions,
            "performance_improvements": self.stats.performance_improvements,
            "time_since_last_optimization": time_since_last_optimization.total_seconds(),
            "optimization_needed": time_since_last_optimization > self.optimization_interval,
            "operational_status": "autonomous" if self.current_schema else "initializing"
        }

    async def continuous_optimization_loop(self) -> None:
        """
        Continuous optimization loop that runs in the background.

        This method should be run as a background task to provide
        ongoing autonomous optimization.
        """
        logger.info("Starting continuous autonomous optimization loop")

        while True:
            try:
                # Check if optimization is needed
                status = await self.get_autonomous_status()

                if status["optimization_needed"]:
                    await self.optimize_performance_autonomously()

                # Wait for next optimization cycle
                await asyncio.sleep(3600)  # Check every hour

            except Exception as e:
                logger.error(f"Error in continuous optimization loop: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Continue after error
