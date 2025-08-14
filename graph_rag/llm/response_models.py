"""Enhanced response models for LLM services with confidence scoring."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfidenceLevel(Enum):
    """Confidence levels for LLM responses."""
    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"            # 0.7-0.89
    MEDIUM = "medium"        # 0.5-0.69
    LOW = "low"              # 0.3-0.49
    VERY_LOW = "very_low"    # 0.0-0.29


@dataclass
class ConfidenceMetrics:
    """Detailed confidence metrics for an LLM response."""

    # Overall confidence score (0.0 to 1.0)
    overall_score: float

    # Confidence level classification
    level: ConfidenceLevel

    # Context-based confidence metrics
    context_coverage: float  # How well context covers the query (0.0-1.0)
    context_relevance: float  # How relevant retrieved context is (0.0-1.0)

    # LLM uncertainty indicators
    uncertainty_indicators: list[str] = field(default_factory=list)

    # Source quality metrics
    source_count: int = 0
    source_quality_score: float = 0.0

    # Answer quality indicators
    answer_completeness: float = 0.0  # How complete the answer appears (0.0-1.0)
    factual_consistency: float = 0.0  # Consistency with source material (0.0-1.0)

    # Metadata
    reasoning: str | None = None  # Human-readable confidence reasoning


@dataclass
class EnhancedLLMResponse:
    """Enhanced LLM response with confidence scoring and metadata."""

    # Core response
    text: str

    # Confidence metrics
    confidence: ConfidenceMetrics

    # Token usage and performance
    input_tokens: int | None = None
    output_tokens: int | None = None
    processing_time: float | None = None

    # Response metadata
    model_name: str | None = None
    temperature: float | None = None

    # Quality indicators
    has_hallucination_risk: bool = False
    requires_verification: bool = False


class ConfidenceCalculator:
    """Calculates confidence scores for LLM responses."""

    # Uncertainty phrases that indicate lower confidence
    UNCERTAINTY_PATTERNS = [
        r"(?i)\b(might|may|could|perhaps|possibly|likely|probably|seems?|appears?)\b",
        r"(?i)\b(i think|i believe|in my opinion|it's possible|it's likely)\b",
        r"(?i)\b(not (entirely )?sure|uncertain|unclear|ambiguous)\b",
        r"(?i)\b(based on limited information|insufficient information)\b",
        r"(?i)\b(cannot be certain|hard to say|difficult to determine)\b"
    ]

    # Confidence phrases that indicate higher certainty
    CONFIDENCE_PATTERNS = [
        r"(?i)\b(definitely|certainly|clearly|obviously|undoubtedly)\b",
        r"(?i)\b(according to|based on|as stated in|documented in)\b",
        r"(?i)\b(research shows|studies indicate|evidence suggests)\b"
    ]

    @classmethod
    def calculate_confidence(
        cls,
        answer_text: str,
        context_chunks: list[Any],
        query: str,
        context_texts: list[str] | None = None
    ) -> ConfidenceMetrics:
        """Calculate comprehensive confidence metrics for an answer."""

        # 1. Analyze uncertainty indicators in the answer
        uncertainty_score = cls._analyze_uncertainty_indicators(answer_text)

        # 2. Calculate context quality metrics
        context_coverage = cls._calculate_context_coverage(query, context_texts or [])
        context_relevance = cls._calculate_context_relevance(query, context_texts or [])

        # 3. Assess source quality
        source_count = len(context_chunks)
        source_quality = cls._assess_source_quality(context_chunks)

        # 4. Evaluate answer completeness
        answer_completeness = cls._evaluate_answer_completeness(answer_text, query)

        # 5. Check factual consistency
        factual_consistency = cls._check_factual_consistency(answer_text, context_texts or [])

        # 6. Calculate overall confidence score
        overall_score = cls._calculate_overall_score(
            uncertainty_score,
            context_coverage,
            context_relevance,
            source_quality,
            answer_completeness,
            factual_consistency
        )

        # 7. Determine confidence level
        level = cls._score_to_level(overall_score)

        # 8. Extract uncertainty indicators
        uncertainty_indicators = cls._extract_uncertainty_phrases(answer_text)

        # 9. Generate reasoning
        reasoning = cls._generate_confidence_reasoning(
            overall_score, uncertainty_indicators, context_coverage, source_count
        )

        return ConfidenceMetrics(
            overall_score=overall_score,
            level=level,
            context_coverage=context_coverage,
            context_relevance=context_relevance,
            uncertainty_indicators=uncertainty_indicators,
            source_count=source_count,
            source_quality_score=source_quality,
            answer_completeness=answer_completeness,
            factual_consistency=factual_consistency,
            reasoning=reasoning
        )

    @classmethod
    def _analyze_uncertainty_indicators(cls, text: str) -> float:
        """Analyze uncertainty indicators in the text. Returns 0.0-1.0 (higher = less uncertain)."""
        uncertainty_count = 0
        confidence_count = 0

        # Count uncertainty patterns
        for pattern in cls.UNCERTAINTY_PATTERNS:
            uncertainty_count += len(re.findall(pattern, text))

        # Count confidence patterns
        for pattern in cls.CONFIDENCE_PATTERNS:
            confidence_count += len(re.findall(pattern, text))

        # Calculate uncertainty score (0.0 = very uncertain, 1.0 = very confident)
        total_indicators = uncertainty_count + confidence_count
        if total_indicators == 0:
            return 0.7  # Neutral confidence if no indicators

        confidence_ratio = confidence_count / total_indicators
        uncertainty_penalty = min(uncertainty_count * 0.1, 0.5)  # Cap penalty at 50%

        return max(0.0, confidence_ratio - uncertainty_penalty)

    @classmethod
    def _calculate_context_coverage(cls, query: str, context_texts: list[str]) -> float:
        """Calculate how well the context covers the query topics."""
        if not context_texts or not query:
            return 0.0

        query_words = set(query.lower().split())
        context_words = set()
        for text in context_texts:
            context_words.update(text.lower().split())

        if not query_words:
            return 0.0

        # Calculate overlap ratio
        overlap = len(query_words.intersection(context_words))
        coverage = overlap / len(query_words)

        # Boost for longer context (more comprehensive)
        context_length_boost = min(len(' '.join(context_texts)) / 1000, 0.2)

        return min(1.0, coverage + context_length_boost)

    @classmethod
    def _calculate_context_relevance(cls, query: str, context_texts: list[str]) -> float:
        """Calculate relevance of context to the query."""
        if not context_texts or not query:
            return 0.0

        # Simple relevance based on keyword density
        query_keywords = query.lower().split()
        total_relevance = 0.0

        for text in context_texts:
            text_lower = text.lower()
            keyword_matches = sum(1 for keyword in query_keywords if keyword in text_lower)
            text_relevance = keyword_matches / len(query_keywords) if query_keywords else 0.0
            total_relevance += text_relevance

        return min(1.0, total_relevance / len(context_texts))

    @classmethod
    def _assess_source_quality(cls, chunks: list[Any]) -> float:
        """Assess the quality of source chunks."""
        if not chunks:
            return 0.0

        quality_score = 0.0
        for chunk in chunks:
            # Basic quality indicators
            chunk_score = 0.5  # Base score

            # Longer chunks generally have more context
            if hasattr(chunk, 'content') and len(chunk.content) > 200:
                chunk_score += 0.2

            # Chunks with metadata (titles, authors) are higher quality
            if hasattr(chunk, 'metadata') and chunk.metadata:
                if chunk.metadata.get('title'):
                    chunk_score += 0.1
                if chunk.metadata.get('author'):
                    chunk_score += 0.1

            quality_score += min(1.0, chunk_score)

        return quality_score / len(chunks)

    @classmethod
    def _evaluate_answer_completeness(cls, answer: str, query: str) -> float:
        """Evaluate how complete the answer appears."""
        if not answer or not query:
            return 0.0

        # Basic completeness indicators
        completeness = 0.5  # Base score

        # Longer answers are generally more complete
        if len(answer) > 100:
            completeness += 0.2

        # Answers that address query keywords are more complete
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        keyword_coverage = len(query_words.intersection(answer_words)) / len(query_words)
        completeness += keyword_coverage * 0.3

        return min(1.0, completeness)

    @classmethod
    def _check_factual_consistency(cls, answer: str, context_texts: list[str]) -> float:
        """Check factual consistency between answer and context."""
        if not context_texts or not answer:
            return 0.5  # Neutral if can't check

        # Simple consistency check based on word overlap
        answer_words = set(answer.lower().split())
        context_words = set()
        for text in context_texts:
            context_words.update(text.lower().split())

        if not answer_words:
            return 0.5

        overlap = len(answer_words.intersection(context_words))
        consistency = overlap / len(answer_words)

        return min(1.0, consistency)

    @classmethod
    def _calculate_overall_score(
        cls,
        uncertainty_score: float,
        context_coverage: float,
        context_relevance: float,
        source_quality: float,
        answer_completeness: float,
        factual_consistency: float
    ) -> float:
        """Calculate weighted overall confidence score."""

        # Weighted average of all factors
        weights = {
            'uncertainty': 0.25,      # LLM's own confidence indicators
            'coverage': 0.20,         # How well context covers query
            'relevance': 0.20,        # How relevant context is
            'source_quality': 0.15,   # Quality of source material
            'completeness': 0.10,     # Answer completeness
            'consistency': 0.10       # Factual consistency
        }

        overall = (
            uncertainty_score * weights['uncertainty'] +
            context_coverage * weights['coverage'] +
            context_relevance * weights['relevance'] +
            source_quality * weights['source_quality'] +
            answer_completeness * weights['completeness'] +
            factual_consistency * weights['consistency']
        )

        return min(1.0, max(0.0, overall))

    @classmethod
    def _score_to_level(cls, score: float) -> ConfidenceLevel:
        """Convert numerical score to confidence level."""
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    @classmethod
    def _extract_uncertainty_phrases(cls, text: str) -> list[str]:
        """Extract specific uncertainty phrases found in the text."""
        found_phrases = []
        for pattern in cls.UNCERTAINTY_PATTERNS:
            matches = re.findall(pattern, text)
            found_phrases.extend(matches)
        return found_phrases

    @classmethod
    def _generate_confidence_reasoning(
        cls,
        score: float,
        uncertainty_indicators: list[str],
        context_coverage: float,
        source_count: int
    ) -> str:
        """Generate human-readable confidence reasoning."""

        level = cls._score_to_level(score)

        reasons = []

        # Add score-based reasoning
        if level == ConfidenceLevel.VERY_HIGH:
            reasons.append("High confidence based on strong context coverage and clear source material")
        elif level == ConfidenceLevel.HIGH:
            reasons.append("Good confidence with solid supporting evidence")
        elif level == ConfidenceLevel.MEDIUM:
            reasons.append("Moderate confidence with adequate supporting information")
        elif level == ConfidenceLevel.LOW:
            reasons.append("Lower confidence due to limited context or uncertainty indicators")
        else:
            reasons.append("Very low confidence - answer may be unreliable")

        # Add specific factors
        if uncertainty_indicators:
            reasons.append(f"Uncertainty indicators detected: {', '.join(uncertainty_indicators[:3])}")

        if context_coverage < 0.5:
            reasons.append("Limited context coverage for the query")

        if source_count == 0:
            reasons.append("No source material available")
        elif source_count == 1:
            reasons.append("Based on single source")
        else:
            reasons.append(f"Based on {source_count} sources")

        return ". ".join(reasons) + "."
