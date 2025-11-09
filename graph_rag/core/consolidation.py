"""Core interfaces and models for experiment consolidation and deduplication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class SimilarityThreshold(Enum):
    """Predefined similarity thresholds for different consolidation scenarios."""

    EXACT_MATCH = 0.95  # Near-identical content
    HIGH_SIMILARITY = 0.80  # Default consolidation threshold
    MEDIUM_SIMILARITY = 0.60  # Pattern detection threshold
    LOW_SIMILARITY = 0.40  # Loose relationship threshold


class MetricType(Enum):
    """Types of success metrics that can be extracted from experimental documents."""

    PERFORMANCE_IMPROVEMENT = "performance_improvement"  # e.g., "39,092x improvement"
    PERCENTAGE_GAIN = "percentage_gain"  # e.g., "95.9% code reduction"
    THROUGHPUT_METRIC = "throughput_metric"  # e.g., "18,483 messages/second"
    COST_REDUCTION = "cost_reduction"  # e.g., "$200K savings"
    TIME_SAVINGS = "time_savings"  # e.g., "40% faster development"
    ENGAGEMENT_METRIC = "engagement_metric"  # e.g., "4-6% engagement rate"


class SuccessMetric(BaseModel):
    """A quantifiable success metric extracted from experimental content."""

    metric_type: MetricType
    value: float
    unit: str  # e.g., "x", "%", "messages/second", "$", "hours"
    context: str  # Brief description of what this metric represents
    source_location: str  # Where in the document this metric was found
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in metric extraction accuracy")


class ArchitecturalPattern(BaseModel):
    """An architectural or design pattern identified in experimental content."""

    pattern_name: str
    description: str
    benefits: list[str]
    challenges: list[str]
    use_cases: list[str]
    evidence_strength: float = Field(ge=0.0, le=1.0, description="Strength of supporting evidence")
    supporting_metrics: list[SuccessMetric] = Field(default_factory=list)


class ConsolidationCandidate(BaseModel):
    """A document or content piece that's a candidate for consolidation."""

    document_id: str
    file_path: str
    content_hash: str
    title: str
    content_preview: str = Field(max_length=500, description="First 500 chars of content")
    extracted_metrics: list[SuccessMetric] = Field(default_factory=list)
    architectural_patterns: list[ArchitecturalPattern] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    content_type: str = "experimental"  # e.g., "experimental", "draft", "final", "brief"


class SimilarityMatch(BaseModel):
    """A similarity match between two consolidation candidates."""

    candidate_a: ConsolidationCandidate
    candidate_b: ConsolidationCandidate
    similarity_score: float = Field(ge=0.0, le=1.0)
    matching_sections: list[str] = Field(default_factory=list, description="Sections with high similarity")
    differing_sections: list[str] = Field(default_factory=list, description="Sections with notable differences")
    overlap_percentage: float = Field(ge=0.0, le=1.0, description="Percentage of content that overlaps")


class ConsolidatedExperiment(BaseModel):
    """The result of consolidating multiple similar experimental documents."""

    consolidated_id: str
    title: str
    summary: str
    source_candidates: list[ConsolidationCandidate]
    best_practices: list[str] = Field(default_factory=list)
    proven_metrics: list[SuccessMetric] = Field(default_factory=list)
    architectural_patterns: list[ArchitecturalPattern] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence_ranking: float = Field(ge=0.0, le=1.0, description="Overall strength of evidence")
    consolidation_confidence: float = Field(ge=0.0, le=1.0, description="Confidence in consolidation quality")
    created_at: datetime = Field(default_factory=datetime.now)


class ConsolidationReport(BaseModel):
    """A comprehensive report of the consolidation process and results."""

    total_candidates_analyzed: int
    similarity_matches_found: int
    experiments_consolidated: list[ConsolidatedExperiment]
    high_value_patterns: list[ArchitecturalPattern]
    top_performing_metrics: list[SuccessMetric]
    recommendations: list[str]
    processing_summary: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)


@runtime_checkable
class SimilarityDetector(Protocol):
    """Protocol for detecting content similarity between documents."""

    async def calculate_similarity(
        self,
        content_a: str,
        content_b: str,
        comparison_method: str = "semantic"
    ) -> float:
        """Calculate similarity score between two content pieces.

        Args:
            content_a: First content piece
            content_b: Second content piece
            comparison_method: Method to use ("semantic", "textual", "structural")

        Returns:
            Similarity score between 0.0 and 1.0
        """
        ...

    async def find_similar_sections(
        self,
        content_a: str,
        content_b: str,
        threshold: float = 0.8
    ) -> list[tuple[str, str]]:
        """Find sections with high similarity between documents.

        Returns:
            List of (section_a, section_b) tuples that are similar
        """
        ...


@runtime_checkable
class MetricsExtractor(Protocol):
    """Protocol for extracting quantifiable success metrics from content."""

    async def extract_metrics(self, content: str) -> list[SuccessMetric]:
        """Extract quantifiable metrics from text content.

        Args:
            content: Text content to analyze

        Returns:
            List of extracted success metrics
        """
        ...

    async def extract_performance_numbers(self, content: str) -> list[SuccessMetric]:
        """Extract performance improvement numbers like '39,092x' or '95.9%'.

        Args:
            content: Text content to analyze

        Returns:
            List of performance-related metrics
        """
        ...


@runtime_checkable
class PatternRecognizer(Protocol):
    """Protocol for recognizing architectural and design patterns."""

    async def identify_patterns(self, content: str) -> list[ArchitecturalPattern]:
        """Identify architectural patterns mentioned in content.

        Args:
            content: Text content to analyze

        Returns:
            List of identified architectural patterns
        """
        ...

    async def extract_best_practices(self, content: str) -> list[str]:
        """Extract best practices and proven approaches.

        Args:
            content: Text content to analyze

        Returns:
            List of identified best practices
        """
        ...


@runtime_checkable
class EvidenceRanker(Protocol):
    """Protocol for ranking ideas and patterns by evidence strength."""

    async def rank_by_evidence(
        self,
        consolidated_experiments: list[ConsolidatedExperiment]
    ) -> list[ConsolidatedExperiment]:
        """Rank consolidated experiments by strength of supporting evidence.

        Args:
            consolidated_experiments: List of experiments to rank

        Returns:
            List sorted by evidence strength (highest first)
        """
        ...

    async def calculate_evidence_score(
        self,
        metrics: list[SuccessMetric],
        patterns: list[ArchitecturalPattern]
    ) -> float:
        """Calculate overall evidence strength score.

        Args:
            metrics: Success metrics as evidence
            patterns: Architectural patterns as evidence

        Returns:
            Evidence strength score between 0.0 and 1.0
        """
        ...


class ExperimentConsolidator(ABC):
    """Abstract base class for experiment consolidation engines."""

    @abstractmethod
    async def discover_candidates(
        self,
        search_path: str,
        file_patterns: list[str] = None
    ) -> list[ConsolidationCandidate]:
        """Discover documents that are candidates for consolidation.

        Args:
            search_path: Directory path to search for candidates
            file_patterns: Optional list of file patterns to match

        Returns:
            List of consolidation candidates
        """
        ...

    @abstractmethod
    async def find_similar_documents(
        self,
        candidates: list[ConsolidationCandidate],
        similarity_threshold: float = SimilarityThreshold.HIGH_SIMILARITY.value
    ) -> list[SimilarityMatch]:
        """Find documents with high content similarity.

        Args:
            candidates: List of candidates to compare
            similarity_threshold: Minimum similarity score for matches

        Returns:
            List of similarity matches above threshold
        """
        ...

    @abstractmethod
    async def consolidate_experiments(
        self,
        similarity_matches: list[SimilarityMatch]
    ) -> list[ConsolidatedExperiment]:
        """Consolidate similar documents into unified experiments.

        Args:
            similarity_matches: Similarity matches to consolidate

        Returns:
            List of consolidated experiments
        """
        ...

    @abstractmethod
    async def generate_report(
        self,
        candidates: list[ConsolidationCandidate],
        consolidated_experiments: list[ConsolidatedExperiment]
    ) -> ConsolidationReport:
        """Generate a comprehensive consolidation report.

        Args:
            candidates: Original candidates analyzed
            consolidated_experiments: Results of consolidation

        Returns:
            Detailed consolidation report
        """
        ...

    async def run_full_consolidation(
        self,
        search_path: str,
        similarity_threshold: float = SimilarityThreshold.HIGH_SIMILARITY.value,
        file_patterns: list[str] = None
    ) -> ConsolidationReport:
        """Run the complete consolidation pipeline.

        Args:
            search_path: Directory to search for experimental documents
            similarity_threshold: Minimum similarity for consolidation
            file_patterns: Optional file patterns to match

        Returns:
            Complete consolidation report
        """
        # Discover candidates
        candidates = await self.discover_candidates(search_path, file_patterns)

        # Find similar documents
        similarity_matches = await self.find_similar_documents(candidates, similarity_threshold)

        # Consolidate experiments
        consolidated_experiments = await self.consolidate_experiments(similarity_matches)

        # Generate report
        report = await self.generate_report(candidates, consolidated_experiments)

        return report
