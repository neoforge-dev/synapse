"""
Autonomous Schema Generation System

Generates and evolves graph schemas automatically based on discovered data patterns.
Core component of self-configuring knowledge graphs.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np

from graph_rag.autonomous_ai.ai_pattern_analyzer import (
    DataPatterns,
    EntityPattern,
    RelationshipPattern,
)

logger = logging.getLogger(__name__)


class SchemaElementType(Enum):
    """Types of schema elements."""
    NODE_TYPE = "node_type"
    RELATIONSHIP_TYPE = "relationship_type"
    PROPERTY = "property"
    INDEX = "index"
    CONSTRAINT = "constraint"


@dataclass
class SchemaElement:
    """Individual element of a graph schema."""
    element_type: SchemaElementType
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    indexes: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    source_pattern: str | None = None


@dataclass
class GraphSchema:
    """Complete graph schema definition."""
    node_types: list[SchemaElement]
    relationship_types: list[SchemaElement]
    properties: list[SchemaElement]
    indexes: list[SchemaElement]
    constraints: list[SchemaElement]
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 0.0


@dataclass
class SchemaEvolution:
    """Schema evolution changes and improvements."""
    added_elements: list[SchemaElement]
    modified_elements: list[tuple[SchemaElement, SchemaElement]]  # (old, new)
    removed_elements: list[SchemaElement]
    performance_improvements: dict[str, float]
    confidence_score: float
    reasoning: str
    impact_assessment: dict[str, Any]


@dataclass
class UsageFeedback:
    """Feedback from schema usage for continuous improvement."""
    query_patterns: list[dict[str, Any]]
    performance_metrics: dict[str, float]
    error_patterns: list[dict[str, Any]]
    user_feedback: list[dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AdaptiveSchemaGenerator:
    """
    Generates and evolves graph schemas automatically based on data patterns.

    Key capabilities:
    - Generate initial schemas from data patterns
    - Evolve schemas based on usage feedback
    - Optimize for performance and accuracy
    - Maintain backward compatibility
    """

    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence
        self.schema_history: list[GraphSchema] = []
        self.evolution_history: list[SchemaEvolution] = []

    async def generate_initial_schema(self, patterns: DataPatterns) -> GraphSchema:
        """
        Generate initial graph schema from discovered data patterns.

        Args:
            patterns: Analyzed data patterns from DataPatternAnalyzer

        Returns:
            Generated graph schema with confidence scores
        """
        logger.info("Generating initial graph schema from data patterns")

        # Generate node types from entity patterns
        node_types = await self._generate_node_types(patterns.entity_patterns)

        # Generate relationship types from relationship patterns
        relationship_types = await self._generate_relationship_types(patterns.relationship_patterns)

        # Generate properties based on patterns
        properties = await self._generate_properties(
            patterns.entity_patterns,
            patterns.relationship_patterns
        )

        # Generate recommended indexes
        indexes = await self._generate_indexes(
            node_types,
            relationship_types,
            patterns.document_patterns
        )

        # Generate constraints
        constraints = await self._generate_constraints(
            node_types,
            relationship_types,
            patterns
        )

        # Calculate overall schema confidence
        confidence_score = await self._calculate_schema_confidence(
            node_types, relationship_types, patterns.quality_metrics
        )

        schema = GraphSchema(
            node_types=node_types,
            relationship_types=relationship_types,
            properties=properties,
            indexes=indexes,
            constraints=constraints,
            metadata={
                "source_patterns": {
                    "entity_patterns": len(patterns.entity_patterns),
                    "relationship_patterns": len(patterns.relationship_patterns),
                    "document_count": patterns.document_patterns.get("total_documents", 0)
                },
                "quality_metrics": patterns.quality_metrics,
                "generation_method": "autonomous_pattern_analysis"
            },
            confidence_score=confidence_score
        )

        self.schema_history.append(schema)
        logger.info(f"Generated schema with confidence {confidence_score:.2f}")
        return schema

    async def _generate_node_types(self, entity_patterns: list[EntityPattern]) -> list[SchemaElement]:
        """Generate node types from entity patterns."""
        node_types = []

        for pattern in entity_patterns:
            if pattern.confidence_score < self.min_confidence:
                continue

            # Map entity pattern to node type
            node_type = SchemaElement(
                element_type=SchemaElementType.NODE_TYPE,
                name=self._normalize_type_name(pattern.entity_type),
                properties={
                    "label": pattern.entity_type,
                    "frequency": pattern.frequency,
                    "sample_values": pattern.sample_entities,
                    "characteristic_features": pattern.characteristic_features
                },
                confidence_score=pattern.confidence_score,
                source_pattern=f"entity_pattern_{pattern.entity_type}"
            )

            node_types.append(node_type)

        logger.info(f"Generated {len(node_types)} node types")
        return node_types

    async def _generate_relationship_types(
        self,
        relationship_patterns: list[RelationshipPattern]
    ) -> list[SchemaElement]:
        """Generate relationship types from relationship patterns."""
        relationship_types = []

        for pattern in relationship_patterns:
            if pattern.confidence_score < self.min_confidence:
                continue

            # Map relationship pattern to relationship type
            rel_type = SchemaElement(
                element_type=SchemaElementType.RELATIONSHIP_TYPE,
                name=self._normalize_type_name(pattern.relationship_type),
                properties={
                    "label": pattern.relationship_type,
                    "source_type": pattern.source_type,
                    "target_type": pattern.target_type,
                    "frequency": pattern.frequency,
                    "strength_indicators": pattern.strength_indicators,
                    "context_patterns": pattern.context_patterns
                },
                confidence_score=pattern.confidence_score,
                source_pattern=f"relationship_pattern_{pattern.relationship_type}"
            )

            relationship_types.append(rel_type)

        logger.info(f"Generated {len(relationship_types)} relationship types")
        return relationship_types

    async def _generate_properties(
        self,
        entity_patterns: list[EntityPattern],
        relationship_patterns: list[RelationshipPattern]
    ) -> list[SchemaElement]:
        """Generate property definitions from patterns."""
        properties = []

        # Standard properties for all nodes
        base_properties = [
            SchemaElement(
                element_type=SchemaElementType.PROPERTY,
                name="id",
                properties={"type": "string", "required": True, "unique": True},
                confidence_score=1.0
            ),
            SchemaElement(
                element_type=SchemaElementType.PROPERTY,
                name="text",
                properties={"type": "string", "required": True},
                confidence_score=1.0
            ),
            SchemaElement(
                element_type=SchemaElementType.PROPERTY,
                name="metadata",
                properties={"type": "object", "required": False},
                confidence_score=1.0
            )
        ]

        properties.extend(base_properties)

        # Generate entity-specific properties
        for pattern in entity_patterns:
            for feature in pattern.characteristic_features[:5]:  # Top 5 features
                prop = SchemaElement(
                    element_type=SchemaElementType.PROPERTY,
                    name=f"{pattern.entity_type.lower()}_{feature}",
                    properties={
                        "type": "string",
                        "entity_type": pattern.entity_type,
                        "feature": feature
                    },
                    confidence_score=pattern.confidence_score * 0.8  # Slightly lower confidence
                )
                properties.append(prop)

        return properties

    async def _generate_indexes(
        self,
        node_types: list[SchemaElement],
        relationship_types: list[SchemaElement],
        document_patterns: dict[str, Any]
    ) -> list[SchemaElement]:
        """Generate recommended indexes based on patterns."""
        indexes = []

        # Always index on ID for all node types
        for node_type in node_types:
            index = SchemaElement(
                element_type=SchemaElementType.INDEX,
                name=f"idx_{node_type.name}_id",
                properties={
                    "node_type": node_type.name,
                    "property": "id",
                    "type": "unique"
                },
                confidence_score=1.0
            )
            indexes.append(index)

        # Index on text for full-text search
        text_index = SchemaElement(
            element_type=SchemaElementType.INDEX,
            name="idx_fulltext_search",
            properties={
                "properties": ["text"],
                "type": "fulltext"
            },
            confidence_score=0.9
        )
        indexes.append(text_index)

        # Index on relationship types for frequent traversals
        for rel_type in relationship_types:
            if rel_type.properties.get("frequency", 0) > 10:  # Only for frequent relationships
                index = SchemaElement(
                    element_type=SchemaElementType.INDEX,
                    name=f"idx_{rel_type.name}_type",
                    properties={
                        "relationship_type": rel_type.name,
                        "property": "type"
                    },
                    confidence_score=rel_type.confidence_score
                )
                indexes.append(index)

        return indexes

    async def _generate_constraints(
        self,
        node_types: list[SchemaElement],
        relationship_types: list[SchemaElement],
        patterns: DataPatterns
    ) -> list[SchemaElement]:
        """Generate schema constraints based on patterns."""
        constraints = []

        # Unique constraints on ID
        for node_type in node_types:
            constraint = SchemaElement(
                element_type=SchemaElementType.CONSTRAINT,
                name=f"unique_{node_type.name}_id",
                properties={
                    "node_type": node_type.name,
                    "property": "id",
                    "type": "unique"
                },
                confidence_score=1.0
            )
            constraints.append(constraint)

        # Existence constraints for required properties
        for node_type in node_types:
            constraint = SchemaElement(
                element_type=SchemaElementType.CONSTRAINT,
                name=f"exists_{node_type.name}_text",
                properties={
                    "node_type": node_type.name,
                    "property": "text",
                    "type": "exists"
                },
                confidence_score=0.9
            )
            constraints.append(constraint)

        return constraints

    async def _calculate_schema_confidence(
        self,
        node_types: list[SchemaElement],
        relationship_types: list[SchemaElement],
        quality_metrics: dict[str, float]
    ) -> float:
        """Calculate overall confidence score for the schema."""
        if not node_types and not relationship_types:
            return 0.0

        # Component confidence scores
        node_confidences = [nt.confidence_score for nt in node_types]
        rel_confidences = [rt.confidence_score for rt in relationship_types]

        component_scores = []
        if node_confidences:
            component_scores.append(np.mean(node_confidences))
        if rel_confidences:
            component_scores.append(np.mean(rel_confidences))

        schema_confidence = np.mean(component_scores) if component_scores else 0.0

        # Adjust based on quality metrics
        overall_quality = quality_metrics.get("overall_quality", 0.0)
        adjusted_confidence = (schema_confidence + overall_quality) / 2.0

        return min(1.0, max(0.0, adjusted_confidence))

    def _normalize_type_name(self, name: str) -> str:
        """Normalize type names for consistency."""
        # Convert to uppercase and replace spaces/special chars with underscores
        normalized = name.upper().replace(" ", "_").replace("-", "_")
        # Remove special characters except underscores
        normalized = "".join(c for c in normalized if c.isalnum() or c == "_")
        return normalized

    async def evolve_schema(self, usage_feedback: UsageFeedback) -> SchemaEvolution:
        """
        Evolve schema based on usage feedback and performance metrics.

        Args:
            usage_feedback: Feedback from schema usage

        Returns:
            Schema evolution changes and improvements
        """
        logger.info("Evolving schema based on usage feedback")

        if not self.schema_history:
            raise ValueError("No existing schema to evolve")

        current_schema = self.schema_history[-1]

        # Analyze feedback to identify improvements
        improvements = await self._analyze_improvement_opportunities(
            current_schema, usage_feedback
        )

        # Generate schema evolution
        evolution = await self._generate_schema_evolution(
            current_schema, improvements, usage_feedback
        )

        # Apply evolution if confidence is sufficient
        if evolution.confidence_score >= self.min_confidence:
            new_schema = await self._apply_schema_evolution(current_schema, evolution)
            self.schema_history.append(new_schema)
            self.evolution_history.append(evolution)

            logger.info(f"Schema evolved with confidence {evolution.confidence_score:.2f}")
        else:
            logger.info(f"Schema evolution confidence too low: {evolution.confidence_score:.2f}")

        return evolution

    async def _analyze_improvement_opportunities(
        self,
        schema: GraphSchema,
        feedback: UsageFeedback
    ) -> dict[str, Any]:
        """Analyze feedback to identify improvement opportunities."""
        opportunities = {
            "performance_improvements": [],
            "missing_indexes": [],
            "unused_elements": [],
            "new_patterns": [],
            "constraint_violations": []
        }

        # Analyze query patterns for missing indexes
        for query_pattern in feedback.query_patterns:
            query_pattern.get("type", "")
            frequency = query_pattern.get("frequency", 0)
            performance = query_pattern.get("avg_duration", 0)

            if frequency > 100 and performance > 1000:  # ms
                # Frequent slow query - needs index
                opportunities["missing_indexes"].append({
                    "query_pattern": query_pattern,
                    "suggested_index": self._suggest_index_for_query(query_pattern)
                })

        # Analyze performance metrics for bottlenecks
        slow_operations = []
        for metric_name, value in feedback.performance_metrics.items():
            if "duration" in metric_name.lower() and value > 5000:  # 5+ seconds
                slow_operations.append(metric_name)

        if slow_operations:
            opportunities["performance_improvements"].extend(slow_operations)

        return opportunities

    def _suggest_index_for_query(self, query_pattern: dict[str, Any]) -> dict[str, Any]:
        """Suggest an index to improve query performance."""
        # Placeholder implementation
        return {
            "type": "btree",
            "properties": ["id"],  # Default suggestion
            "estimated_improvement": 0.5
        }

    async def _generate_schema_evolution(
        self,
        current_schema: GraphSchema,
        improvements: dict[str, Any],
        feedback: UsageFeedback
    ) -> SchemaEvolution:
        """Generate schema evolution based on improvements."""
        added_elements = []
        modified_elements = []
        removed_elements = []

        # Add missing indexes
        for missing_index in improvements["missing_indexes"]:
            suggested = missing_index["suggested_index"]
            index_element = SchemaElement(
                element_type=SchemaElementType.INDEX,
                name=f"idx_performance_{len(added_elements)}",
                properties=suggested,
                confidence_score=0.8
            )
            added_elements.append(index_element)

        # Calculate performance improvements (estimated)
        performance_improvements = {}
        if added_elements:
            performance_improvements["query_performance"] = 0.3  # 30% improvement estimate

        # Calculate confidence based on feedback quality
        feedback_quality = self._assess_feedback_quality(feedback)
        confidence_score = min(1.0, feedback_quality * 0.9)

        reasoning = f"Added {len(added_elements)} indexes based on query performance analysis"

        impact_assessment = {
            "performance_impact": "positive",
            "compatibility_impact": "none",
            "maintenance_impact": "low"
        }

        return SchemaEvolution(
            added_elements=added_elements,
            modified_elements=modified_elements,
            removed_elements=removed_elements,
            performance_improvements=performance_improvements,
            confidence_score=confidence_score,
            reasoning=reasoning,
            impact_assessment=impact_assessment
        )

    def _assess_feedback_quality(self, feedback: UsageFeedback) -> float:
        """Assess the quality of usage feedback."""
        quality_factors = []

        # Query pattern richness
        if feedback.query_patterns:
            query_richness = min(1.0, len(feedback.query_patterns) / 50.0)
            quality_factors.append(query_richness)

        # Performance metrics availability
        if feedback.performance_metrics:
            metric_coverage = min(1.0, len(feedback.performance_metrics) / 10.0)
            quality_factors.append(metric_coverage)

        # Error pattern analysis
        if feedback.error_patterns:
            error_richness = min(1.0, len(feedback.error_patterns) / 10.0)
            quality_factors.append(error_richness)

        return np.mean(quality_factors) if quality_factors else 0.0

    async def _apply_schema_evolution(
        self,
        current_schema: GraphSchema,
        evolution: SchemaEvolution
    ) -> GraphSchema:
        """Apply evolution to create new schema version."""
        # Create new schema based on current + evolution
        new_node_types = current_schema.node_types.copy()
        new_relationship_types = current_schema.relationship_types.copy()
        new_properties = current_schema.properties.copy()
        new_indexes = current_schema.indexes.copy()
        new_constraints = current_schema.constraints.copy()

        # Apply additions
        for element in evolution.added_elements:
            if element.element_type == SchemaElementType.NODE_TYPE:
                new_node_types.append(element)
            elif element.element_type == SchemaElementType.RELATIONSHIP_TYPE:
                new_relationship_types.append(element)
            elif element.element_type == SchemaElementType.PROPERTY:
                new_properties.append(element)
            elif element.element_type == SchemaElementType.INDEX:
                new_indexes.append(element)
            elif element.element_type == SchemaElementType.CONSTRAINT:
                new_constraints.append(element)

        # Apply modifications (placeholder)
        for _old_element, _new_element in evolution.modified_elements:
            # Implementation would update existing elements
            pass

        # Apply removals (placeholder)
        for _ in evolution.removed_elements:
            # Implementation would remove elements
            pass

        # Increment version
        current_version = current_schema.version
        major, minor, patch = map(int, current_version.split('.'))
        new_version = f"{major}.{minor}.{patch + 1}"

        return GraphSchema(
            node_types=new_node_types,
            relationship_types=new_relationship_types,
            properties=new_properties,
            indexes=new_indexes,
            constraints=new_constraints,
            metadata={
                **current_schema.metadata,
                "evolution_applied": True,
                "evolution_reasoning": evolution.reasoning,
                "performance_improvements": evolution.performance_improvements
            },
            version=new_version,
            confidence_score=evolution.confidence_score
        )
