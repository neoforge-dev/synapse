"""
AI Pattern Analysis System

Core component for autonomous knowledge graph self-configuration.
Analyzes enterprise data patterns to discover optimal graph structures and relationships.
"""

import asyncio
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from graph_rag.core.interfaces import ExtractedEntity, ExtractedRelationship
from graph_rag.domain.models import Document

logger = logging.getLogger(__name__)


@dataclass
class EntityPattern:
    """Discovered entity type pattern with confidence metrics."""
    entity_type: str
    frequency: int
    confidence_score: float
    sample_entities: list[str]
    characteristic_features: list[str]
    co_occurrence_patterns: dict[str, float]


@dataclass
class RelationshipPattern:
    """Discovered relationship pattern between entity types."""
    source_type: str
    target_type: str
    relationship_type: str
    frequency: int
    confidence_score: float
    context_patterns: list[str]
    strength_indicators: dict[str, float]


@dataclass
class DataPatterns:
    """Comprehensive pattern analysis results."""
    entity_patterns: list[EntityPattern]
    relationship_patterns: list[RelationshipPattern]
    document_patterns: dict[str, Any]
    quality_metrics: dict[str, float]
    timestamp: datetime
    confidence_threshold: float = 0.8


class DataPatternAnalyzer:
    """
    Analyzes enterprise data to discover patterns for autonomous knowledge graph configuration.
    
    Uses machine learning techniques to identify:
    - Common entity types and their characteristics
    - Relationship patterns between entities
    - Document structure patterns
    - Quality indicators for pattern confidence
    """

    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.entity_clusters = None
        self.relationship_clusters = None

    async def discover_entity_types(self, documents: list[Document]) -> list[EntityPattern]:
        """
        Discover entity type patterns from document collection.
        
        Args:
            documents: Collection of documents to analyze
            
        Returns:
            List of discovered entity patterns with confidence scores
        """
        logger.info(f"Analyzing entity patterns in {len(documents)} documents")

        # Extract all entities from documents
        all_entities = []
        entity_contexts = {}

        for doc in documents:
            for chunk in doc.chunks:
                # Get entities from chunk (assuming entities are stored in chunk metadata)
                chunk_entities = chunk.metadata.get('entities', [])
                for entity_data in chunk_entities:
                    entity = ExtractedEntity(**entity_data)
                    all_entities.append(entity)

                    # Store context for each entity
                    entity_key = f"{entity.text}:{entity.label}"
                    if entity_key not in entity_contexts:
                        entity_contexts[entity_key] = []
                    entity_contexts[entity_key].append(chunk.text)

        if not all_entities:
            logger.warning("No entities found in documents")
            return []

        # Group entities by label (type)
        entity_groups = defaultdict(list)
        for entity in all_entities:
            entity_groups[entity.label].append(entity)

        # Analyze patterns for each entity type
        entity_patterns = []
        for entity_type, entities in entity_groups.items():
            if len(entities) < 3:  # Skip types with too few examples
                continue

            pattern = await self._analyze_entity_type_pattern(
                entity_type, entities, entity_contexts
            )
            if pattern.confidence_score >= self.min_confidence:
                entity_patterns.append(pattern)

        # Sort by frequency and confidence
        entity_patterns.sort(
            key=lambda p: (p.frequency * p.confidence_score),
            reverse=True
        )

        logger.info(f"Discovered {len(entity_patterns)} entity patterns")
        return entity_patterns

    async def _analyze_entity_type_pattern(
        self,
        entity_type: str,
        entities: list[ExtractedEntity],
        entity_contexts: dict[str, list[str]]
    ) -> EntityPattern:
        """Analyze pattern for a specific entity type."""

        # Basic frequency metrics
        frequency = len(entities)
        entity_texts = [e.text for e in entities]
        unique_entities = list(set(entity_texts))

        # Get contexts for this entity type
        type_contexts = []
        for entity in entities:
            entity_key = f"{entity.text}:{entity.label}"
            type_contexts.extend(entity_contexts.get(entity_key, []))

        # Extract characteristic features using TF-IDF
        if type_contexts:
            try:
                # Fit TF-IDF on contexts
                tfidf_matrix = self.vectorizer.fit_transform(type_contexts)
                feature_names = self.vectorizer.get_feature_names_out()

                # Get top features for this entity type
                mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
                top_indices = np.argsort(mean_scores)[-10:]  # Top 10 features
                characteristic_features = [feature_names[i] for i in top_indices]
            except Exception as e:
                logger.warning(f"Failed to extract features for {entity_type}: {e}")
                characteristic_features = []
        else:
            characteristic_features = []

        # Calculate confidence score based on multiple factors
        # - Frequency (more frequent = higher confidence)
        # - Uniqueness ratio (less redundancy = higher confidence)
        # - Context richness (more context = higher confidence)

        frequency_score = min(1.0, frequency / 100.0)  # Normalize to 0-1
        uniqueness_score = len(unique_entities) / len(entity_texts) if entity_texts else 0
        context_score = min(1.0, len(type_contexts) / (frequency * 2))  # Expect ~2 contexts per entity

        confidence_score = np.mean([frequency_score, uniqueness_score, context_score])

        # Analyze co-occurrence patterns (placeholder for now)
        co_occurrence_patterns = {}

        return EntityPattern(
            entity_type=entity_type,
            frequency=frequency,
            confidence_score=confidence_score,
            sample_entities=unique_entities[:5],  # Top 5 samples
            characteristic_features=characteristic_features,
            co_occurrence_patterns=co_occurrence_patterns
        )

    async def infer_relationship_patterns(
        self,
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship]
    ) -> list[RelationshipPattern]:
        """
        Infer relationship patterns between entity types.
        
        Args:
            entities: List of extracted entities
            relationships: List of extracted relationships
            
        Returns:
            List of relationship patterns with confidence scores
        """
        logger.info(f"Analyzing relationship patterns from {len(relationships)} relationships")

        if not relationships:
            return []

        # Create entity lookup by ID
        entity_lookup = {entity.id: entity for entity in entities}

        # Group relationships by type and entity type pairs
        relationship_groups = defaultdict(list)

        for rel in relationships:
            source_entity = entity_lookup.get(rel.source_entity_id)
            target_entity = entity_lookup.get(rel.target_entity_id)

            if source_entity and target_entity:
                pattern_key = (source_entity.label, target_entity.label, rel.label)
                relationship_groups[pattern_key].append(rel)

        # Analyze patterns for each relationship type
        relationship_patterns = []
        for (source_type, target_type, rel_type), rels in relationship_groups.items():
            if len(rels) < 2:  # Skip patterns with too few examples
                continue

            pattern = await self._analyze_relationship_pattern(
                source_type, target_type, rel_type, rels, entity_lookup
            )
            if pattern.confidence_score >= self.min_confidence:
                relationship_patterns.append(pattern)

        # Sort by frequency and confidence
        relationship_patterns.sort(
            key=lambda p: (p.frequency * p.confidence_score),
            reverse=True
        )

        logger.info(f"Discovered {len(relationship_patterns)} relationship patterns")
        return relationship_patterns

    async def _analyze_relationship_pattern(
        self,
        source_type: str,
        target_type: str,
        relationship_type: str,
        relationships: list[ExtractedRelationship],
        entity_lookup: dict[str, ExtractedEntity]
    ) -> RelationshipPattern:
        """Analyze pattern for a specific relationship type."""

        frequency = len(relationships)

        # Gather context patterns (placeholder for now)
        context_patterns = []

        # Calculate strength indicators
        # - Frequency: how often this relationship occurs
        # - Consistency: how consistent the pattern is
        # - Bidirectionality: whether relationships go both ways

        strength_indicators = {
            "frequency": frequency,
            "consistency": 1.0,  # Placeholder
            "bidirectionality": 0.0  # Placeholder
        }

        # Calculate confidence score
        frequency_score = min(1.0, frequency / 50.0)  # Normalize
        consistency_score = strength_indicators["consistency"]

        confidence_score = np.mean([frequency_score, consistency_score])

        return RelationshipPattern(
            source_type=source_type,
            target_type=target_type,
            relationship_type=relationship_type,
            frequency=frequency,
            confidence_score=confidence_score,
            context_patterns=context_patterns,
            strength_indicators=strength_indicators
        )

    async def analyze_document_patterns(self, documents: list[Document]) -> dict[str, Any]:
        """
        Analyze document structure and content patterns.
        
        Args:
            documents: Collection of documents to analyze
            
        Returns:
            Dictionary containing document pattern analysis results
        """
        logger.info(f"Analyzing document patterns in {len(documents)} documents")

        if not documents:
            return {}

        # Basic document statistics
        doc_lengths = [len(doc.content) for doc in documents]
        chunk_counts = [len(doc.chunks) for doc in documents]

        # Content type analysis
        content_types = Counter()
        for doc in documents:
            content_type = doc.metadata.get('content_type', 'unknown')
            content_types[content_type] += 1

        # Source analysis
        sources = Counter()
        for doc in documents:
            source = doc.metadata.get('source', 'unknown')
            sources[source] += 1

        return {
            "total_documents": len(documents),
            "average_length": np.mean(doc_lengths),
            "median_length": np.median(doc_lengths),
            "average_chunks": np.mean(chunk_counts),
            "content_types": dict(content_types),
            "sources": dict(sources),
            "length_distribution": {
                "min": min(doc_lengths),
                "max": max(doc_lengths),
                "std": np.std(doc_lengths)
            }
        }

    async def calculate_quality_metrics(
        self,
        entity_patterns: list[EntityPattern],
        relationship_patterns: list[RelationshipPattern],
        document_patterns: dict[str, Any]
    ) -> dict[str, float]:
        """
        Calculate overall quality metrics for the pattern analysis.
        
        Returns:
            Dictionary of quality metrics and confidence scores
        """
        metrics = {}

        # Entity pattern quality
        if entity_patterns:
            entity_confidences = [p.confidence_score for p in entity_patterns]
            metrics["entity_pattern_quality"] = np.mean(entity_confidences)
            metrics["entity_pattern_coverage"] = len(entity_patterns)
        else:
            metrics["entity_pattern_quality"] = 0.0
            metrics["entity_pattern_coverage"] = 0

        # Relationship pattern quality
        if relationship_patterns:
            rel_confidences = [p.confidence_score for p in relationship_patterns]
            metrics["relationship_pattern_quality"] = np.mean(rel_confidences)
            metrics["relationship_pattern_coverage"] = len(relationship_patterns)
        else:
            metrics["relationship_pattern_quality"] = 0.0
            metrics["relationship_pattern_coverage"] = 0

        # Document pattern quality
        doc_count = document_patterns.get("total_documents", 0)
        avg_chunks = document_patterns.get("average_chunks", 0)

        if doc_count > 0:
            metrics["document_coverage"] = doc_count
            metrics["document_richness"] = min(1.0, avg_chunks / 10.0)  # Expect ~10 chunks per doc
        else:
            metrics["document_coverage"] = 0
            metrics["document_richness"] = 0.0

        # Overall quality score
        quality_components = [
            metrics["entity_pattern_quality"],
            metrics["relationship_pattern_quality"],
            metrics["document_richness"]
        ]
        metrics["overall_quality"] = np.mean([c for c in quality_components if c > 0])

        return metrics

    async def analyze_full_patterns(self, documents: list[Document]) -> DataPatterns:
        """
        Perform comprehensive pattern analysis on document collection.
        
        Args:
            documents: Collection of documents to analyze
            
        Returns:
            Complete pattern analysis results
        """
        logger.info("Starting comprehensive pattern analysis")

        # Extract entities and relationships from documents
        all_entities = []
        all_relationships = []

        for doc in documents:
            for chunk in doc.chunks:
                # Get entities and relationships from chunk metadata
                chunk_entities = chunk.metadata.get('entities', [])
                chunk_relationships = chunk.metadata.get('relationships', [])

                for entity_data in chunk_entities:
                    all_entities.append(ExtractedEntity(**entity_data))

                for rel_data in chunk_relationships:
                    all_relationships.append(ExtractedRelationship(**rel_data))

        # Run parallel analysis
        entity_task = self.discover_entity_types(documents)
        relationship_task = self.infer_relationship_patterns(all_entities, all_relationships)
        document_task = self.analyze_document_patterns(documents)

        entity_patterns, relationship_patterns, document_patterns = await asyncio.gather(
            entity_task, relationship_task, document_task
        )

        # Calculate quality metrics
        quality_metrics = await self.calculate_quality_metrics(
            entity_patterns, relationship_patterns, document_patterns
        )

        return DataPatterns(
            entity_patterns=entity_patterns,
            relationship_patterns=relationship_patterns,
            document_patterns=document_patterns,
            quality_metrics=quality_metrics,
            timestamp=datetime.utcnow(),
            confidence_threshold=self.min_confidence
        )


class GraphPatternRecognizer:
    """
    Advanced pattern recognition for graph structures and optimization opportunities.
    
    Analyzes existing graph structures to identify:
    - Optimization opportunities
    - Structural anomalies
    - Performance bottlenecks
    - Expansion patterns
    """

    def __init__(self, min_pattern_frequency: int = 5):
        self.min_pattern_frequency = min_pattern_frequency

    async def discover_patterns(self, graph_data: Any) -> dict[str, Any]:
        """
        Discover patterns in existing graph structure.
        
        Args:
            graph_data: Current graph data and metrics
            
        Returns:
            Dictionary containing discovered patterns and recommendations
        """
        logger.info("Discovering graph structure patterns")

        patterns = {
            "structural_patterns": await self._analyze_structural_patterns(graph_data),
            "performance_patterns": await self._analyze_performance_patterns(graph_data),
            "growth_patterns": await self._analyze_growth_patterns(graph_data),
            "optimization_opportunities": await self._identify_optimization_opportunities(graph_data)
        }

        return patterns

    async def _analyze_structural_patterns(self, graph_data: Any) -> dict[str, Any]:
        """Analyze structural patterns in the graph."""
        # Placeholder implementation
        return {
            "node_degree_distribution": {},
            "clustering_coefficient": 0.0,
            "centrality_patterns": {},
            "community_structure": {}
        }

    async def _analyze_performance_patterns(self, graph_data: Any) -> dict[str, Any]:
        """Analyze performance patterns and bottlenecks."""
        # Placeholder implementation
        return {
            "query_hotspots": [],
            "performance_bottlenecks": [],
            "indexing_opportunities": []
        }

    async def _analyze_growth_patterns(self, graph_data: Any) -> dict[str, Any]:
        """Analyze growth and evolution patterns."""
        # Placeholder implementation
        return {
            "growth_rate": 0.0,
            "expansion_areas": [],
            "scaling_challenges": []
        }

    async def _identify_optimization_opportunities(self, graph_data: Any) -> list[dict[str, Any]]:
        """Identify specific optimization opportunities."""
        # Placeholder implementation
        return [
            {
                "type": "indexing",
                "description": "Add index for frequently queried relationship type",
                "impact_score": 0.8,
                "implementation_complexity": "low"
            }
        ]
