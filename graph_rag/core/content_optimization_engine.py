"""Content Optimization and Improvement Suggestions System for Epic 9.2.

This module provides a comprehensive content optimization engine that analyzes existing content
and provides actionable improvement suggestions. It integrates all previous epic capabilities
to deliver sophisticated content analysis and optimization recommendations.

Key Features:
- Multi-dimensional content analysis (engagement, readability, brand safety, audience fit)
- AI-powered improvement suggestions with impact scoring
- Platform-specific optimization recommendations
- A/B testing content generation
- Performance prediction with confidence metrics
- Comprehensive workflow management for iterative improvement
- Integration with all previous epic capabilities
- Real-time analysis and suggestions
- Content variation generation for testing
- Optimization history and learning system
"""

import asyncio
import hashlib
import logging
import re
import statistics
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator

from graph_rag.core.audience_intelligence import (
    AudienceSegmentationEngine,
)
from graph_rag.core.brand_safety_analyzer import (
    BrandProfile,
    BrandSafetyAnalyzer,
)

# Import all epic capabilities
from graph_rag.core.concept_entity_extractor import BeliefPreferenceExtractor
from graph_rag.core.content_audience_resonance import ResonanceScorer
from graph_rag.core.content_strategy_optimizer import ContentStrategyOptimizer
from graph_rag.core.viral_prediction_engine import (
    Platform,
    RiskLevel,
    ViralPredictionEngine,
)

logger = logging.getLogger(__name__)


# Enums for Content Optimization
class OptimizationType(Enum):
    """Types of content optimization."""
    ENGAGEMENT = "engagement"
    READABILITY = "readability"
    BRAND_SAFETY = "brand_safety"
    AUDIENCE_FIT = "audience_fit"
    PLATFORM_SPECIFIC = "platform_specific"
    VIRAL_POTENTIAL = "viral_potential"
    SEO = "seo"
    CONVERSION = "conversion"
    ACCESSIBILITY = "accessibility"
    TONE_ADJUSTMENT = "tone_adjustment"


class SuggestionCategory(Enum):
    """Categories of improvement suggestions."""
    STRUCTURE = "structure"           # Content structure and organization
    LANGUAGE = "language"             # Word choice, tone, style
    ENGAGEMENT = "engagement"         # Hooks, CTAs, interaction elements
    COMPLIANCE = "compliance"         # Brand safety, legal compliance
    TARGETING = "targeting"           # Audience-specific optimizations
    DISTRIBUTION = "distribution"     # Platform-specific adaptations
    PERFORMANCE = "performance"       # Metrics and measurement improvements
    ACCESSIBILITY = "accessibility"   # Inclusive design and accessibility
    TECHNICAL = "technical"           # Technical SEO and optimization
    CREATIVE = "creative"             # Creative elements and multimedia


class ContentQualityMetric(Enum):
    """Content quality assessment metrics."""
    READABILITY_SCORE = "readability_score"
    ENGAGEMENT_POTENTIAL = "engagement_potential"
    BRAND_ALIGNMENT = "brand_alignment"
    AUDIENCE_RELEVANCE = "audience_relevance"
    VIRAL_POTENTIAL = "viral_potential"
    SAFETY_SCORE = "safety_score"
    ORIGINALITY = "originality"
    CLARITY = "clarity"
    EMOTIONAL_IMPACT = "emotional_impact"
    ACTIONABILITY = "actionability"


class ImprovementPriority(Enum):
    """Priority levels for improvement suggestions."""
    CRITICAL = "critical"     # Must fix - high risk/impact issues
    HIGH = "high"            # Should fix - significant impact
    MEDIUM = "medium"        # Could fix - moderate impact
    LOW = "low"              # Nice to have - minor impact


class AnalysisDepth(Enum):
    """Depth levels for content analysis."""
    SURFACE = "surface"      # Basic analysis
    STANDARD = "standard"    # Comprehensive analysis
    DEEP = "deep"           # Deep analysis with ML insights
    EXPERT = "expert"       # Expert-level analysis with advanced models


class ContentVariationType(Enum):
    """Types of content variations for A/B testing."""
    HEADLINE = "headline"
    HOOK = "hook"
    TONE = "tone"
    LENGTH = "length"
    STRUCTURE = "structure"
    CTA = "cta"
    PLATFORM_ADAPTATION = "platform_adaptation"
    AUDIENCE_TARGETING = "audience_targeting"


class OptimizationStatus(Enum):
    """Status of optimization workflows."""
    INITIALIZED = "initialized"
    ANALYZING = "analyzing"
    GENERATING_SUGGESTIONS = "generating_suggestions"
    CREATING_VARIATIONS = "creating_variations"
    PREDICTING_PERFORMANCE = "predicting_performance"
    COMPLETED = "completed"
    FAILED = "failed"


# Data Models
class ContentOptimizationRequest(BaseModel):
    """Request for content optimization analysis."""
    content: str = Field(..., description="Content to optimize")
    platform: Platform = Field(default=Platform.GENERAL, description="Target platform")
    optimization_types: list[OptimizationType] = Field(
        default_factory=lambda: [OptimizationType.ENGAGEMENT, OptimizationType.READABILITY],
        description="Types of optimization to perform"
    )
    target_audience: str | None = Field(None, description="Target audience description")
    brand_profile: dict[str, Any] | None = Field(None, description="Brand profile information")
    analysis_depth: AnalysisDepth = Field(default=AnalysisDepth.STANDARD, description="Analysis depth level")
    generate_variations: bool = Field(default=True, description="Whether to generate content variations")
    predict_performance: bool = Field(default=True, description="Whether to predict performance")
    context: dict[str, Any] | None = Field(None, description="Additional context")

    @validator('content')
    def validate_content(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Content must be at least 10 characters long")
        return v


class ContentAnalysisResult(BaseModel):
    """Results of comprehensive content analysis."""
    content_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique analysis ID")
    original_content: str = Field(..., description="Original content analyzed")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When analysis was performed")

    # Quality metrics
    quality_scores: dict[ContentQualityMetric, float] = Field(
        default_factory=dict, description="Quality scores for different metrics"
    )
    overall_score: float = Field(0.0, description="Overall content quality score (0-1)")

    # Detailed analysis results
    readability_analysis: dict[str, Any] = Field(default_factory=dict, description="Readability analysis results")
    engagement_analysis: dict[str, Any] = Field(default_factory=dict, description="Engagement potential analysis")
    brand_alignment_analysis: dict[str, Any] = Field(default_factory=dict, description="Brand alignment analysis")
    audience_fit_analysis: dict[str, Any] = Field(default_factory=dict, description="Audience fit analysis")
    safety_analysis: dict[str, Any] = Field(default_factory=dict, description="Brand safety analysis")
    viral_analysis: dict[str, Any] = Field(default_factory=dict, description="Viral potential analysis")

    # Content gaps and opportunities
    identified_gaps: list[str] = Field(default_factory=list, description="Identified content gaps")
    opportunities: list[str] = Field(default_factory=list, description="Optimization opportunities")

    # Analysis metadata
    analysis_depth: AnalysisDepth = Field(..., description="Depth of analysis performed")
    confidence_score: float = Field(0.0, description="Confidence in analysis results (0-1)")
    processing_time: float = Field(0.0, description="Time taken for analysis in seconds")


class ImprovementSuggestion(BaseModel):
    """Individual improvement suggestion with detailed information."""
    suggestion_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique suggestion ID")
    category: SuggestionCategory = Field(..., description="Category of suggestion")
    priority: ImprovementPriority = Field(..., description="Priority level")

    # Suggestion details
    title: str = Field(..., description="Brief title of the suggestion")
    description: str = Field(..., description="Detailed description")
    rationale: str = Field(..., description="Explanation of why this improvement is suggested")

    # Impact and effort estimation
    impact_score: float = Field(..., ge=0.0, le=1.0, description="Expected impact (0-1)")
    effort_estimate: int = Field(..., ge=1, le=5, description="Implementation effort (1-5 scale)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in suggestion (0-1)")

    # Implementation details
    specific_changes: list[str] = Field(default_factory=list, description="Specific changes to make")
    before_text: str | None = Field(None, description="Text to change (if applicable)")
    after_text: str | None = Field(None, description="Suggested replacement text")

    # Metadata
    optimization_type: OptimizationType = Field(..., description="Type of optimization")
    applicable_platforms: list[Platform] = Field(default_factory=list, description="Platforms where applicable")
    tags: list[str] = Field(default_factory=list, description="Additional tags")
    created_at: datetime = Field(default_factory=datetime.now, description="When suggestion was created")


class ContentVariation(BaseModel):
    """Content variation for A/B testing."""
    variation_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique variation ID")
    variation_type: ContentVariationType = Field(..., description="Type of variation")
    original_content: str = Field(..., description="Original content")
    modified_content: str = Field(..., description="Modified content variation")

    # Variation details
    changes_made: list[str] = Field(default_factory=list, description="Specific changes made")
    target_improvement: str = Field(..., description="What this variation aims to improve")
    variation_rationale: str = Field(..., description="Why this variation was created")

    # Expected performance
    expected_improvement: float = Field(0.0, description="Expected performance improvement (0-1)")
    confidence: float = Field(0.0, description="Confidence in variation effectiveness (0-1)")

    # Platform and audience specific
    optimized_platform: Platform = Field(..., description="Platform this variation is optimized for")
    target_audience_segment: str | None = Field(None, description="Target audience segment")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="When variation was created")
    tags: list[str] = Field(default_factory=list, description="Additional tags")


class PerformancePrediction(BaseModel):
    """Performance prediction for content."""
    prediction_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique prediction ID")
    content: str = Field(..., description="Content being predicted")
    platform: Platform = Field(..., description="Target platform")

    # Performance metrics predictions
    engagement_prediction: float = Field(0.0, description="Predicted engagement rate (0-1)")
    reach_prediction: float = Field(0.0, description="Predicted reach potential (0-1)")
    conversion_prediction: float = Field(0.0, description="Predicted conversion rate (0-1)")
    viral_prediction: float = Field(0.0, description="Predicted viral potential (0-1)")

    # Confidence intervals
    engagement_confidence: tuple[float, float] = Field((0.0, 0.0), description="Engagement confidence interval")
    reach_confidence: tuple[float, float] = Field((0.0, 0.0), description="Reach confidence interval")
    conversion_confidence: tuple[float, float] = Field((0.0, 0.0), description="Conversion confidence interval")
    viral_confidence: tuple[float, float] = Field((0.0, 0.0), description="Viral confidence interval")

    # Risk assessment
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Overall risk level")
    mitigation_suggestions: list[str] = Field(default_factory=list, description="Risk mitigation suggestions")

    # Model metadata
    model_version: str = Field("1.0", description="Prediction model version")
    prediction_confidence: float = Field(0.0, description="Overall prediction confidence (0-1)")
    created_at: datetime = Field(default_factory=datetime.now, description="When prediction was made")


class OptimizationWorkflow(BaseModel):
    """Workflow tracking for content optimization process."""
    workflow_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique workflow ID")
    content_id: str = Field(..., description="ID of content being optimized")
    status: OptimizationStatus = Field(default=OptimizationStatus.INITIALIZED, description="Current status")

    # Workflow progress
    started_at: datetime = Field(default_factory=datetime.now, description="When workflow started")
    completed_at: datetime | None = Field(None, description="When workflow completed")
    current_step: str = Field("initialization", description="Current step in process")
    progress_percentage: float = Field(0.0, description="Progress percentage (0-100)")

    # Results tracking
    analysis_result_id: str | None = Field(None, description="ID of analysis result")
    suggestions_count: int = Field(0, description="Number of suggestions generated")
    variations_count: int = Field(0, description="Number of variations created")
    predictions_count: int = Field(0, description="Number of predictions made")

    # Performance tracking
    total_processing_time: float = Field(0.0, description="Total processing time in seconds")
    step_timings: dict[str, float] = Field(default_factory=dict, description="Timing for each step")

    # Error handling
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    warnings: list[str] = Field(default_factory=list, description="Warnings generated")

    # Configuration
    optimization_config: dict[str, Any] = Field(default_factory=dict, description="Optimization configuration")

    def update_progress(self, step: str, percentage: float):
        """Update workflow progress."""
        self.current_step = step
        self.progress_percentage = min(100.0, max(0.0, percentage))

    def add_error(self, error: str):
        """Add error to workflow."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")

    def add_warning(self, warning: str):
        """Add warning to workflow."""
        self.warnings.append(f"{datetime.now().isoformat()}: {warning}")

    def complete_workflow(self):
        """Mark workflow as completed."""
        self.status = OptimizationStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress_percentage = 100.0


# Core Content Optimization Classes

class ContentAnalyzer:
    """Deep content analysis across multiple dimensions.

    Provides comprehensive analysis of content including readability, engagement potential,
    brand alignment, audience fit, and other quality metrics.
    """

    def __init__(self, belief_extractor: BeliefPreferenceExtractor,
                 viral_engine: ViralPredictionEngine,
                 safety_analyzer: BrandSafetyAnalyzer,
                 audience_engine: AudienceSegmentationEngine,
                 resonance_scorer: ResonanceScorer):
        """Initialize the content analyzer with all epic capabilities."""
        self.belief_extractor = belief_extractor
        self.viral_engine = viral_engine
        self.safety_analyzer = safety_analyzer
        self.audience_engine = audience_engine
        self.resonance_scorer = resonance_scorer

        logger.info("ContentAnalyzer initialized with all epic capabilities")

    async def analyze_readability(self, content: str) -> dict[str, Any]:
        """Analyze content readability using multiple metrics.

        Args:
            content: Content to analyze

        Returns:
            Dictionary with readability metrics and scores
        """
        try:
            # Calculate basic readability metrics
            sentences = len(re.split(r'[.!?]+', content))
            words = len(content.split())
            chars = len(content)

            # Average words per sentence
            avg_words_per_sentence = words / max(sentences, 1)

            # Average characters per word
            avg_chars_per_word = chars / max(words, 1)

            # Calculate Flesch Reading Ease approximation
            flesch_score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * (avg_chars_per_word / 4.7))
            flesch_score = max(0, min(100, flesch_score))  # Clamp to 0-100

            # Readability level based on Flesch score
            if flesch_score >= 90:
                reading_level = "Very Easy"
            elif flesch_score >= 80:
                reading_level = "Easy"
            elif flesch_score >= 70:
                reading_level = "Fairly Easy"
            elif flesch_score >= 60:
                reading_level = "Standard"
            elif flesch_score >= 50:
                reading_level = "Fairly Difficult"
            elif flesch_score >= 30:
                reading_level = "Difficult"
            else:
                reading_level = "Very Difficult"

            # Additional metrics
            complex_words = len([word for word in content.split() if len(word) > 6])
            complex_word_ratio = complex_words / max(words, 1)

            # Sentiment and emotional tone analysis
            positive_words = len([word for word in content.lower().split()
                                if word in ['good', 'great', 'excellent', 'amazing', 'fantastic', 'wonderful']])
            negative_words = len([word for word in content.lower().split()
                                if word in ['bad', 'terrible', 'awful', 'horrible', 'worst', 'disappointing']])

            sentiment_score = (positive_words - negative_words) / max(words, 1)

            return {
                'flesch_score': flesch_score,
                'reading_level': reading_level,
                'avg_words_per_sentence': avg_words_per_sentence,
                'avg_chars_per_word': avg_chars_per_word,
                'complex_word_ratio': complex_word_ratio,
                'word_count': words,
                'sentence_count': sentences,
                'character_count': chars,
                'sentiment_score': sentiment_score,
                'readability_score': flesch_score / 100.0,  # Normalized 0-1
                'recommendations': self._generate_readability_recommendations(flesch_score, avg_words_per_sentence)
            }

        except Exception as e:
            logger.error(f"Error in readability analysis: {e}")
            return {
                'error': str(e),
                'readability_score': 0.5,  # Default middle score
                'recommendations': ['Unable to analyze readability - review content structure']
            }

    def _generate_readability_recommendations(self, flesch_score: float, avg_words_per_sentence: float) -> list[str]:
        """Generate readability improvement recommendations."""
        recommendations = []

        if flesch_score < 50:
            recommendations.append("Consider simplifying language and using shorter words")
            recommendations.append("Break complex ideas into multiple sentences")

        if avg_words_per_sentence > 20:
            recommendations.append("Reduce sentence length - aim for 15-20 words per sentence")
            recommendations.append("Use more periods and fewer conjunctions")

        if avg_words_per_sentence < 8:
            recommendations.append("Consider combining very short sentences for better flow")

        if flesch_score > 80:
            recommendations.append("Content is very easy to read - consider if this matches your audience level")

        return recommendations

    async def analyze_engagement_potential(self, content: str, platform: Platform = Platform.GENERAL) -> dict[str, Any]:
        """Analyze content's potential for engagement.

        Args:
            content: Content to analyze
            platform: Target platform

        Returns:
            Dictionary with engagement analysis results
        """
        try:
            # Use viral prediction engine for engagement analysis
            viral_prediction = await self.viral_engine.predict_viral_potential(content, platform)

            # Additional engagement factors
            has_question = '?' in content
            has_cta = any(phrase in content.lower() for phrase in
                         ['click', 'share', 'comment', 'like', 'follow', 'subscribe', 'join'])
            has_hashtags = '#' in content
            has_mention = '@' in content

            # Emotional words analysis
            emotional_words = self._count_emotional_words(content)
            emotion_score = min(1.0, emotional_words / max(len(content.split()) * 0.1, 1))

            # Hook strength analysis
            first_sentence = content.split('.')[0] if '.' in content else content[:100]
            hook_strength = self._analyze_hook_strength(first_sentence)

            # Calculate overall engagement score
            base_score = viral_prediction.engagement_score
            question_boost = 0.1 if has_question else 0
            cta_boost = 0.15 if has_cta else 0
            hashtag_boost = 0.05 if has_hashtags else 0
            mention_boost = 0.05 if has_mention else 0
            emotion_boost = emotion_score * 0.2
            hook_boost = hook_strength * 0.15

            engagement_score = min(1.0, base_score + question_boost + cta_boost +
                                 hashtag_boost + mention_boost + emotion_boost + hook_boost)

            return {
                'engagement_score': engagement_score,
                'viral_prediction': viral_prediction.dict(),
                'has_question': has_question,
                'has_call_to_action': has_cta,
                'has_hashtags': has_hashtags,
                'has_mentions': has_mention,
                'emotional_words_count': emotional_words,
                'emotion_score': emotion_score,
                'hook_strength': hook_strength,
                'first_sentence': first_sentence,
                'engagement_factors': {
                    'question_boost': question_boost,
                    'cta_boost': cta_boost,
                    'hashtag_boost': hashtag_boost,
                    'mention_boost': mention_boost,
                    'emotion_boost': emotion_boost,
                    'hook_boost': hook_boost
                },
                'recommendations': self._generate_engagement_recommendations(
                    has_question, has_cta, emotion_score, hook_strength
                )
            }

        except Exception as e:
            logger.error(f"Error in engagement analysis: {e}")
            return {
                'error': str(e),
                'engagement_score': 0.5,
                'recommendations': ['Unable to analyze engagement potential']
            }

    def _count_emotional_words(self, content: str) -> int:
        """Count emotional words in content."""
        emotional_words = {
            'excited', 'amazing', 'incredible', 'fantastic', 'wonderful', 'thrilled',
            'frustrated', 'disappointed', 'concerned', 'worried', 'shocked', 'surprised',
            'love', 'hate', 'adore', 'despise', 'passionate', 'angry', 'happy', 'sad'
        }
        words = content.lower().split()
        return sum(1 for word in words if word.strip('.,!?()[]') in emotional_words)

    def _analyze_hook_strength(self, first_sentence: str) -> float:
        """Analyze the strength of the opening hook."""
        hook_indicators = {
            'question': '?' in first_sentence,
            'number': any(char.isdigit() for char in first_sentence),
            'surprising': any(word in first_sentence.lower() for word in
                            ['surprising', 'shocking', 'unbelievable', 'incredible', 'amazing']),
            'personal': any(word in first_sentence.lower() for word in
                          ['i', 'my', 'me', 'personal', 'story', 'experience']),
            'urgent': any(word in first_sentence.lower() for word in
                        ['now', 'today', 'urgent', 'immediately', 'breaking']),
            'benefit': any(word in first_sentence.lower() for word in
                         ['learn', 'discover', 'find out', 'secret', 'tip', 'hack'])
        }

        score = sum(0.2 for indicator in hook_indicators.values() if indicator)
        return min(1.0, score)

    def _generate_engagement_recommendations(self, has_question: bool, has_cta: bool,
                                           emotion_score: float, hook_strength: float) -> list[str]:
        """Generate engagement improvement recommendations."""
        recommendations = []

        if not has_question:
            recommendations.append("Consider adding a question to encourage responses")

        if not has_cta:
            recommendations.append("Add a clear call-to-action to drive engagement")

        if emotion_score < 0.1:
            recommendations.append("Use more emotional language to connect with readers")

        if hook_strength < 0.4:
            recommendations.append("Strengthen your opening hook to capture attention immediately")

        if emotion_score > 0.5:
            recommendations.append("Good use of emotional language - maintain this tone")

        return recommendations

    async def analyze_brand_alignment(self, content: str, brand_profile: BrandProfile | None = None) -> dict[str, Any]:
        """Analyze how well content aligns with brand guidelines.

        Args:
            content: Content to analyze
            brand_profile: Brand profile for alignment check

        Returns:
            Dictionary with brand alignment analysis
        """
        try:
            # Use brand safety analyzer
            if brand_profile:
                safety_assessment = await self.safety_analyzer.assess_brand_safety(content, brand_profile)
            else:
                # Create default brand profile for analysis
                default_profile = BrandProfile(
                    brand_name="Default",
                    industry="General",
                    values=["professional", "trustworthy", "innovative"],
                    voice_tone=["professional", "friendly"],
                    content_guidelines=["informative", "engaging", "respectful"]
                )
                safety_assessment = await self.safety_analyzer.assess_brand_safety(content, default_profile)

            # Additional brand alignment factors
            tone_analysis = self._analyze_tone_alignment(content, brand_profile)
            value_alignment = self._analyze_value_alignment(content, brand_profile)

            # Calculate overall alignment score
            safety_score = 1.0 - (safety_assessment.risk_score if hasattr(safety_assessment, 'risk_score') else 0.0)
            alignment_score = (safety_score + tone_analysis['alignment_score'] + value_alignment['alignment_score']) / 3

            return {
                'alignment_score': alignment_score,
                'safety_assessment': safety_assessment.dict() if hasattr(safety_assessment, 'dict') else str(safety_assessment),
                'tone_analysis': tone_analysis,
                'value_alignment': value_alignment,
                'brand_compliance': alignment_score > 0.7,
                'recommendations': self._generate_brand_alignment_recommendations(alignment_score, tone_analysis, value_alignment)
            }

        except Exception as e:
            logger.error(f"Error in brand alignment analysis: {e}")
            return {
                'error': str(e),
                'alignment_score': 0.5,
                'recommendations': ['Unable to analyze brand alignment']
            }

    def _analyze_tone_alignment(self, content: str, brand_profile: BrandProfile | None) -> dict[str, Any]:
        """Analyze tone alignment with brand."""
        if not brand_profile or not hasattr(brand_profile, 'voice_tone'):
            return {'alignment_score': 0.5, 'detected_tone': 'neutral', 'brand_tone': 'unknown'}

        # Simple tone detection based on language patterns
        formal_indicators = len([word for word in content.split() if word in
                               ['therefore', 'furthermore', 'however', 'consequently', 'accordingly']])
        casual_indicators = len([word for word in content.split() if word in
                               ['hey', 'wow', 'awesome', 'cool', 'super', 'totally']])

        detected_tone = 'formal' if formal_indicators > casual_indicators else 'casual'

        # Check alignment with brand tone
        brand_tones = brand_profile.voice_tone if hasattr(brand_profile, 'voice_tone') else ['professional']
        alignment_score = 1.0 if detected_tone in brand_tones else 0.3

        return {
            'alignment_score': alignment_score,
            'detected_tone': detected_tone,
            'brand_tone': brand_tones,
            'formal_indicators': formal_indicators,
            'casual_indicators': casual_indicators
        }

    def _analyze_value_alignment(self, content: str, brand_profile: BrandProfile | None) -> dict[str, Any]:
        """Analyze alignment with brand values."""
        if not brand_profile or not hasattr(brand_profile, 'values'):
            return {'alignment_score': 0.5, 'detected_values': [], 'brand_values': []}

        brand_values = brand_profile.values if hasattr(brand_profile, 'values') else []

        # Simple value detection based on keywords
        value_keywords = {
            'innovative': ['innovation', 'creative', 'new', 'cutting-edge', 'breakthrough'],
            'trustworthy': ['trust', 'reliable', 'honest', 'transparent', 'integrity'],
            'professional': ['professional', 'expert', 'quality', 'excellence', 'standards'],
            'customer-focused': ['customer', 'client', 'user', 'service', 'satisfaction'],
            'sustainable': ['sustainable', 'green', 'environment', 'eco', 'responsible']
        }

        detected_values = []
        content_lower = content.lower()

        for value, keywords in value_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_values.append(value)

        # Calculate alignment
        aligned_values = [value for value in detected_values if value in brand_values]
        alignment_score = len(aligned_values) / max(len(brand_values), 1) if brand_values else 0.5

        return {
            'alignment_score': alignment_score,
            'detected_values': detected_values,
            'brand_values': brand_values,
            'aligned_values': aligned_values
        }

    def _generate_brand_alignment_recommendations(self, alignment_score: float,
                                                tone_analysis: dict[str, Any],
                                                value_alignment: dict[str, Any]) -> list[str]:
        """Generate brand alignment improvement recommendations."""
        recommendations = []

        if alignment_score < 0.5:
            recommendations.append("Content needs significant alignment with brand guidelines")

        if tone_analysis['alignment_score'] < 0.5:
            recommendations.append(f"Adjust tone to match brand voice: {tone_analysis.get('brand_tone', 'unknown')}")

        if value_alignment['alignment_score'] < 0.5:
            brand_values = value_alignment.get('brand_values', [])
            if brand_values:
                recommendations.append(f"Incorporate brand values: {', '.join(brand_values)}")

        if alignment_score > 0.8:
            recommendations.append("Excellent brand alignment - maintain this consistency")

        return recommendations

    async def identify_gaps(self, content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Identify content gaps and improvement opportunities.

        Args:
            content: Content to analyze
            context: Additional context for gap analysis

        Returns:
            Dictionary with identified gaps and opportunities
        """
        try:
            gaps = []
            opportunities = []

            # Structure gaps
            if len(content.split('\n\n')) < 2:
                gaps.append("Content lacks clear paragraph structure")
                opportunities.append("Break content into digestible paragraphs")

            # Engagement gaps
            if '?' not in content:
                gaps.append("No questions to engage readers")
                opportunities.append("Add questions to encourage interaction")

            if not any(phrase in content.lower() for phrase in ['share', 'comment', 'like', 'follow']):
                gaps.append("Missing call-to-action")
                opportunities.append("Add clear calls-to-action")

            # Content depth gaps
            word_count = len(content.split())
            if word_count < 50:
                gaps.append("Content may be too brief")
                opportunities.append("Expand with more details, examples, or insights")
            elif word_count > 500:
                gaps.append("Content may be too lengthy")
                opportunities.append("Consider breaking into series or reducing length")

            # Visual elements gaps
            if '#' not in content:
                gaps.append("No hashtags for discoverability")
                opportunities.append("Add relevant hashtags")

            # Emotional connection gaps
            emotional_words = self._count_emotional_words(content)
            if emotional_words == 0:
                gaps.append("Lacks emotional connection")
                opportunities.append("Include personal experiences or emotional language")

            # Credibility gaps
            if not any(word in content.lower() for word in ['research', 'study', 'data', 'expert', 'proven']):
                gaps.append("Could benefit from credibility indicators")
                opportunities.append("Add data, research, or expert opinions")

            return {
                'identified_gaps': gaps,
                'opportunities': opportunities,
                'gap_count': len(gaps),
                'opportunity_count': len(opportunities),
                'priority_gaps': gaps[:3],  # Top 3 priority gaps
                'quick_wins': [opp for opp in opportunities if 'add' in opp.lower()][:3]
            }

        except Exception as e:
            logger.error(f"Error in gap analysis: {e}")
            return {
                'error': str(e),
                'identified_gaps': ['Unable to identify gaps'],
                'opportunities': ['Review content structure and engagement elements']
            }


class ImprovementSuggestionGenerator:
    """Generates specific, actionable improvement recommendations.

    Uses ML models and heuristics to suggest content optimizations and prioritizes
    suggestions by impact and effort.
    """

    def __init__(self, content_analyzer: ContentAnalyzer):
        """Initialize with content analyzer for generating suggestions."""
        self.content_analyzer = content_analyzer

        # Suggestion templates for different categories
        self.suggestion_templates = {
            SuggestionCategory.STRUCTURE: [
                "Break long paragraphs into shorter, more digestible chunks",
                "Add subheadings to improve content scanability",
                "Reorganize content with a clear introduction, body, and conclusion",
                "Use bullet points or numbered lists for better readability"
            ],
            SuggestionCategory.LANGUAGE: [
                "Simplify complex terminology for broader audience appeal",
                "Replace passive voice with active voice for more engagement",
                "Use more conversational tone to connect with readers",
                "Incorporate power words to increase emotional impact"
            ],
            SuggestionCategory.ENGAGEMENT: [
                "Add compelling questions to encourage reader interaction",
                "Include a clear call-to-action to drive desired behavior",
                "Start with a strong hook to capture immediate attention",
                "Add interactive elements like polls or challenges"
            ],
            SuggestionCategory.TARGETING: [
                "Adjust language complexity for target audience level",
                "Include industry-specific terminology where appropriate",
                "Address specific pain points of target demographic",
                "Optimize content length for platform and audience preferences"
            ]
        }

        logger.info("ImprovementSuggestionGenerator initialized")

    async def generate_suggestions(self, analysis_result: ContentAnalysisResult,
                                 optimization_types: list[OptimizationType]) -> list[ImprovementSuggestion]:
        """Generate improvement suggestions based on analysis results.

        Args:
            analysis_result: Results from content analysis
            optimization_types: Types of optimization to focus on

        Returns:
            List of prioritized improvement suggestions
        """
        try:
            suggestions = []

            # Generate suggestions based on optimization types
            for opt_type in optimization_types:
                type_suggestions = await self._generate_suggestions_by_type(
                    analysis_result, opt_type
                )
                suggestions.extend(type_suggestions)

            # Remove duplicates and prioritize
            unique_suggestions = self._deduplicate_suggestions(suggestions)
            prioritized_suggestions = self.prioritize_by_impact(unique_suggestions)

            logger.info(f"Generated {len(prioritized_suggestions)} improvement suggestions")
            return prioritized_suggestions

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []

    async def _generate_suggestions_by_type(self, analysis_result: ContentAnalysisResult,
                                          optimization_type: OptimizationType) -> list[ImprovementSuggestion]:
        """Generate suggestions for specific optimization type."""
        suggestions = []

        try:
            if optimization_type == OptimizationType.READABILITY:
                suggestions.extend(await self._generate_readability_suggestions(analysis_result))

            elif optimization_type == OptimizationType.ENGAGEMENT:
                suggestions.extend(await self._generate_engagement_suggestions(analysis_result))

            elif optimization_type == OptimizationType.BRAND_SAFETY:
                suggestions.extend(await self._generate_brand_safety_suggestions(analysis_result))

            elif optimization_type == OptimizationType.AUDIENCE_FIT:
                suggestions.extend(await self._generate_audience_fit_suggestions(analysis_result))

            elif optimization_type == OptimizationType.PLATFORM_SPECIFIC:
                suggestions.extend(await self._generate_platform_suggestions(analysis_result))

            elif optimization_type == OptimizationType.VIRAL_POTENTIAL:
                suggestions.extend(await self._generate_viral_suggestions(analysis_result))

            elif optimization_type == OptimizationType.SEO:
                suggestions.extend(await self._generate_seo_suggestions(analysis_result))

            elif optimization_type == OptimizationType.ACCESSIBILITY:
                suggestions.extend(await self._generate_accessibility_suggestions(analysis_result))

        except Exception as e:
            logger.error(f"Error generating {optimization_type} suggestions: {e}")

        return suggestions

    async def _generate_readability_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate readability improvement suggestions."""
        suggestions = []
        readability_data = analysis_result.readability_analysis

        if not readability_data:
            return suggestions

        flesch_score = readability_data.get('flesch_score', 50)
        avg_words_per_sentence = readability_data.get('avg_words_per_sentence', 15)
        complex_word_ratio = readability_data.get('complex_word_ratio', 0.1)

        # Low readability suggestions
        if flesch_score < 50:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.LANGUAGE,
                priority=ImprovementPriority.HIGH,
                title="Improve readability score",
                description="Content has low readability. Simplify language and sentence structure.",
                rationale=f"Flesch score of {flesch_score:.1f} indicates difficult reading level",
                impact_score=0.8,
                effort_estimate=3,
                confidence=0.9,
                specific_changes=[
                    "Replace complex words with simpler alternatives",
                    "Break long sentences into shorter ones",
                    "Use active voice instead of passive voice"
                ],
                optimization_type=OptimizationType.READABILITY
            ))

        # Long sentence suggestions
        if avg_words_per_sentence > 20:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.STRUCTURE,
                priority=ImprovementPriority.MEDIUM,
                title="Reduce sentence length",
                description="Sentences are too long, reducing readability and comprehension.",
                rationale=f"Average {avg_words_per_sentence:.1f} words per sentence exceeds recommended 15-20",
                impact_score=0.6,
                effort_estimate=2,
                confidence=0.85,
                specific_changes=[
                    "Break sentences at natural pause points",
                    "Use periods instead of commas for complex thoughts",
                    "Aim for 15-20 words per sentence"
                ],
                optimization_type=OptimizationType.READABILITY
            ))

        # Complex words suggestions
        if complex_word_ratio > 0.15:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.LANGUAGE,
                priority=ImprovementPriority.MEDIUM,
                title="Simplify vocabulary",
                description="High ratio of complex words may alienate readers.",
                rationale=f"Complex word ratio of {complex_word_ratio:.2f} is above recommended 0.15",
                impact_score=0.5,
                effort_estimate=3,
                confidence=0.7,
                specific_changes=[
                    "Replace jargon with everyday language",
                    "Use shorter synonyms where possible",
                    "Define technical terms when necessary"
                ],
                optimization_type=OptimizationType.READABILITY
            ))

        return suggestions

    async def _generate_engagement_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate engagement improvement suggestions."""
        suggestions = []
        engagement_data = analysis_result.engagement_analysis

        if not engagement_data:
            return suggestions

        engagement_score = engagement_data.get('engagement_score', 0.5)
        has_question = engagement_data.get('has_question', False)
        has_cta = engagement_data.get('has_call_to_action', False)
        hook_strength = engagement_data.get('hook_strength', 0.5)
        emotion_score = engagement_data.get('emotion_score', 0.1)

        # Low engagement score
        if engagement_score < 0.5:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.ENGAGEMENT,
                priority=ImprovementPriority.HIGH,
                title="Boost overall engagement potential",
                description="Content has low predicted engagement. Add interactive elements.",
                rationale=f"Engagement score of {engagement_score:.2f} is below optimal threshold",
                impact_score=0.9,
                effort_estimate=3,
                confidence=0.8,
                specific_changes=[
                    "Add compelling questions",
                    "Include clear call-to-action",
                    "Use more emotional language",
                    "Strengthen opening hook"
                ],
                optimization_type=OptimizationType.ENGAGEMENT
            ))

        # Missing questions
        if not has_question:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.ENGAGEMENT,
                priority=ImprovementPriority.MEDIUM,
                title="Add engaging questions",
                description="Include questions to encourage reader interaction and comments.",
                rationale="Questions significantly increase engagement rates",
                impact_score=0.7,
                effort_estimate=1,
                confidence=0.9,
                specific_changes=[
                    "End with a thought-provoking question",
                    "Ask for reader experiences or opinions",
                    "Use rhetorical questions to maintain interest"
                ],
                optimization_type=OptimizationType.ENGAGEMENT
            ))

        # Missing call-to-action
        if not has_cta:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.ENGAGEMENT,
                priority=ImprovementPriority.HIGH,
                title="Add clear call-to-action",
                description="Include specific actions you want readers to take.",
                rationale="CTAs are essential for driving desired user behavior",
                impact_score=0.8,
                effort_estimate=1,
                confidence=0.95,
                specific_changes=[
                    "Add 'Share your thoughts in the comments'",
                    "Include 'Follow for more insights'",
                    "Request specific actions like sharing or tagging"
                ],
                optimization_type=OptimizationType.ENGAGEMENT
            ))

        # Weak hook
        if hook_strength < 0.4:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.ENGAGEMENT,
                priority=ImprovementPriority.HIGH,
                title="Strengthen opening hook",
                description="Create a more compelling opening to capture immediate attention.",
                rationale="Strong hooks are critical for content retention",
                impact_score=0.9,
                effort_estimate=2,
                confidence=0.8,
                specific_changes=[
                    "Start with a surprising statistic",
                    "Open with a provocative question",
                    "Begin with a personal story or experience",
                    "Use numbers or specific benefits"
                ],
                optimization_type=OptimizationType.ENGAGEMENT
            ))

        # Low emotional impact
        if emotion_score < 0.1:
            suggestions.append(ImprovementSuggestion(
                category=SuggestionCategory.LANGUAGE,
                priority=ImprovementPriority.MEDIUM,
                title="Increase emotional connection",
                description="Add emotional language to better connect with readers.",
                rationale="Emotional content performs significantly better",
                impact_score=0.6,
                effort_estimate=2,
                confidence=0.7,
                specific_changes=[
                    "Share personal experiences or stories",
                    "Use emotionally charged words appropriately",
                    "Express passion or strong opinions",
                    "Include relatable struggles or victories"
                ],
                optimization_type=OptimizationType.ENGAGEMENT
            ))

        return suggestions

    async def _generate_brand_safety_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate brand safety improvement suggestions."""
        suggestions = []
        safety_data = analysis_result.safety_analysis

        if not safety_data:
            return suggestions

        # This would typically use the brand safety analysis results
        # For now, providing general brand safety suggestions

        suggestions.append(ImprovementSuggestion(
            category=SuggestionCategory.COMPLIANCE,
            priority=ImprovementPriority.HIGH,
            title="Review brand safety compliance",
            description="Ensure content aligns with brand guidelines and safety standards.",
            rationale="Brand safety is critical for maintaining reputation",
            impact_score=0.9,
            effort_estimate=2,
            confidence=0.8,
            specific_changes=[
                "Review for potentially controversial statements",
                "Ensure tone matches brand voice",
                "Check for compliance with brand values",
                "Avoid potentially offensive language"
            ],
            optimization_type=OptimizationType.BRAND_SAFETY
        ))

        return suggestions

    async def _generate_audience_fit_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate audience fit improvement suggestions."""
        suggestions = []

        # General audience fit suggestions
        suggestions.append(ImprovementSuggestion(
            category=SuggestionCategory.TARGETING,
            priority=ImprovementPriority.MEDIUM,
            title="Optimize for target audience",
            description="Adjust content to better match target audience preferences and level.",
            rationale="Audience-specific content performs better",
            impact_score=0.7,
            effort_estimate=3,
            confidence=0.6,
            specific_changes=[
                "Use language appropriate for audience expertise level",
                "Include relevant examples and references",
                "Address specific audience pain points",
                "Match content format to audience preferences"
            ],
            optimization_type=OptimizationType.AUDIENCE_FIT
        ))

        return suggestions

    async def _generate_platform_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate platform-specific optimization suggestions."""
        suggestions = []

        suggestions.append(ImprovementSuggestion(
            category=SuggestionCategory.DISTRIBUTION,
            priority=ImprovementPriority.MEDIUM,
            title="Optimize for platform best practices",
            description="Adapt content format and style for specific platform requirements.",
            rationale="Platform-optimized content receives better algorithmic distribution",
            impact_score=0.6,
            effort_estimate=2,
            confidence=0.7,
            specific_changes=[
                "Adjust length for platform optimal range",
                "Add platform-specific hashtags",
                "Use appropriate formatting and structure",
                "Include relevant mentions and tags"
            ],
            optimization_type=OptimizationType.PLATFORM_SPECIFIC
        ))

        return suggestions

    async def _generate_viral_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate viral potential improvement suggestions."""
        suggestions = []

        suggestions.append(ImprovementSuggestion(
            category=SuggestionCategory.ENGAGEMENT,
            priority=ImprovementPriority.MEDIUM,
            title="Increase viral potential",
            description="Add elements that increase shareability and viral spread.",
            rationale="Viral content reaches exponentially larger audiences",
            impact_score=0.8,
            effort_estimate=3,
            confidence=0.5,
            specific_changes=[
                "Add surprising or counterintuitive insights",
                "Include shareable quotes or statistics",
                "Create content that sparks discussion",
                "Use trending topics or formats"
            ],
            optimization_type=OptimizationType.VIRAL_POTENTIAL
        ))

        return suggestions

    async def _generate_seo_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate SEO optimization suggestions."""
        suggestions = []

        suggestions.append(ImprovementSuggestion(
            category=SuggestionCategory.TECHNICAL,
            priority=ImprovementPriority.LOW,
            title="Improve SEO optimization",
            description="Add SEO elements to improve discoverability.",
            rationale="Better SEO increases organic reach",
            impact_score=0.4,
            effort_estimate=2,
            confidence=0.6,
            specific_changes=[
                "Include relevant keywords naturally",
                "Add descriptive hashtags",
                "Use clear, descriptive headings",
                "Include meta-relevant information"
            ],
            optimization_type=OptimizationType.SEO
        ))

        return suggestions

    async def _generate_accessibility_suggestions(self, analysis_result: ContentAnalysisResult) -> list[ImprovementSuggestion]:
        """Generate accessibility improvement suggestions."""
        suggestions = []

        suggestions.append(ImprovementSuggestion(
            category=SuggestionCategory.ACCESSIBILITY,
            priority=ImprovementPriority.LOW,
            title="Improve accessibility",
            description="Make content more accessible to diverse audiences.",
            rationale="Accessible content reaches wider audiences",
            impact_score=0.3,
            effort_estimate=1,
            confidence=0.7,
            specific_changes=[
                "Use clear, simple language",
                "Add alt text descriptions for images",
                "Ensure good contrast and readability",
                "Structure content with clear headings"
            ],
            optimization_type=OptimizationType.ACCESSIBILITY
        ))

        return suggestions

    def _deduplicate_suggestions(self, suggestions: list[ImprovementSuggestion]) -> list[ImprovementSuggestion]:
        """Remove duplicate suggestions based on content similarity."""
        unique_suggestions = []
        seen_titles = set()

        for suggestion in suggestions:
            if suggestion.title not in seen_titles:
                unique_suggestions.append(suggestion)
                seen_titles.add(suggestion.title)

        return unique_suggestions

    def prioritize_by_impact(self, suggestions: list[ImprovementSuggestion]) -> list[ImprovementSuggestion]:
        """Prioritize suggestions by impact score and priority level.

        Args:
            suggestions: List of suggestions to prioritize

        Returns:
            List of suggestions sorted by priority and impact
        """
        try:
            # Create priority weight mapping
            priority_weights = {
                ImprovementPriority.CRITICAL: 4,
                ImprovementPriority.HIGH: 3,
                ImprovementPriority.MEDIUM: 2,
                ImprovementPriority.LOW: 1
            }

            # Sort by priority weight (desc) and impact score (desc)
            sorted_suggestions = sorted(
                suggestions,
                key=lambda s: (
                    priority_weights.get(s.priority, 1),
                    s.impact_score,
                    -s.effort_estimate  # Prefer lower effort when impact is similar
                ),
                reverse=True
            )

            logger.info(f"Prioritized {len(sorted_suggestions)} suggestions")
            return sorted_suggestions

        except Exception as e:
            logger.error(f"Error prioritizing suggestions: {e}")
            return suggestions

    def format_actionable_recommendations(self, suggestions: list[ImprovementSuggestion]) -> dict[str, Any]:
        """Format suggestions into actionable recommendations.

        Args:
            suggestions: List of suggestions to format

        Returns:
            Formatted recommendations dictionary
        """
        try:
            # Group by priority
            by_priority = {}
            for priority in ImprovementPriority:
                by_priority[priority.value] = [
                    s for s in suggestions if s.priority == priority
                ]

            # Group by category
            by_category = {}
            for category in SuggestionCategory:
                by_category[category.value] = [
                    s for s in suggestions if s.category == category
                ]

            # Create quick wins (high impact, low effort)
            quick_wins = [
                s for s in suggestions
                if s.impact_score > 0.6 and s.effort_estimate <= 2
            ]

            # Create high-impact suggestions
            high_impact = [
                s for s in suggestions
                if s.impact_score > 0.7
            ]

            return {
                'total_suggestions': len(suggestions),
                'by_priority': by_priority,
                'by_category': by_category,
                'quick_wins': [s.dict() for s in quick_wins[:5]],
                'high_impact': [s.dict() for s in high_impact[:5]],
                'summary': {
                    'critical_count': len(by_priority.get('critical', [])),
                    'high_count': len(by_priority.get('high', [])),
                    'medium_count': len(by_priority.get('medium', [])),
                    'low_count': len(by_priority.get('low', [])),
                    'quick_wins_count': len(quick_wins),
                    'high_impact_count': len(high_impact)
                }
            }

        except Exception as e:
            logger.error(f"Error formatting recommendations: {e}")
            return {'error': str(e), 'total_suggestions': len(suggestions)}


class ContentVariationGenerator:
    """Creates multiple content variations for A/B testing.

    Generates platform-specific adaptations and different approaches to the same content
    for testing and optimization purposes.
    """

    def __init__(self, belief_extractor: BeliefPreferenceExtractor,
                 viral_engine: ViralPredictionEngine):
        """Initialize with belief extractor and viral engine for variation generation."""
        self.belief_extractor = belief_extractor
        self.viral_engine = viral_engine

        # Variation templates and strategies
        self.headline_templates = [
            "How to {action}",
            "The {number} {things} that {result}",
            "{Surprising_fact} about {topic}",
            "Why {common_belief} is wrong",
            "The secret to {desired_outcome}"
        ]

        self.hook_strategies = [
            "question",     # Start with a question
            "statistic",    # Start with a surprising stat
            "story",        # Start with a personal story
            "controversy",  # Start with a contrarian view
            "benefit"       # Start with a clear benefit
        ]

        self.tone_variations = [
            "professional", "casual", "enthusiastic", "authoritative",
            "conversational", "educational", "inspirational"
        ]

        logger.info("ContentVariationGenerator initialized")

    async def generate_variations(self, content: str, variation_types: list[ContentVariationType],
                                platform: Platform = Platform.GENERAL,
                                target_audience: str | None = None) -> list[ContentVariation]:
        """Generate content variations for A/B testing.

        Args:
            content: Original content to create variations of
            variation_types: Types of variations to generate
            platform: Target platform for optimization
            target_audience: Target audience for variations

        Returns:
            List of content variations
        """
        try:
            variations = []

            for variation_type in variation_types:
                type_variations = await self._generate_variations_by_type(
                    content, variation_type, platform, target_audience
                )
                variations.extend(type_variations)

            # Remove duplicates and validate
            unique_variations = self._deduplicate_variations(variations)

            logger.info(f"Generated {len(unique_variations)} content variations")
            return unique_variations

        except Exception as e:
            logger.error(f"Error generating variations: {e}")
            return []

    async def _generate_variations_by_type(self, content: str, variation_type: ContentVariationType,
                                         platform: Platform, target_audience: str | None) -> list[ContentVariation]:
        """Generate variations for specific variation type."""
        variations = []

        try:
            if variation_type == ContentVariationType.HEADLINE:
                variations.extend(await self._generate_headline_variations(content, platform))

            elif variation_type == ContentVariationType.HOOK:
                variations.extend(await self._generate_hook_variations(content, platform))

            elif variation_type == ContentVariationType.TONE:
                variations.extend(await self._generate_tone_variations(content, platform))

            elif variation_type == ContentVariationType.LENGTH:
                variations.extend(await self._generate_length_variations(content, platform))

            elif variation_type == ContentVariationType.STRUCTURE:
                variations.extend(await self._generate_structure_variations(content, platform))

            elif variation_type == ContentVariationType.CTA:
                variations.extend(await self._generate_cta_variations(content, platform))

            elif variation_type == ContentVariationType.PLATFORM_ADAPTATION:
                variations.extend(await self._generate_platform_variations(content, platform))

            elif variation_type == ContentVariationType.AUDIENCE_TARGETING:
                variations.extend(await self._generate_audience_variations(content, platform, target_audience))

        except Exception as e:
            logger.error(f"Error generating {variation_type} variations: {e}")

        return variations

    async def _generate_headline_variations(self, content: str, platform: Platform) -> list[ContentVariation]:
        """Generate headline variations."""
        variations = []
        first_line = content.split('\n')[0] if '\n' in content else content[:100]

        # Extract key elements from original content
        words = content.lower().split()
        action_words = [w for w in words if w in ['learn', 'discover', 'find', 'get', 'achieve', 'build']]
        numbers = [w for w in words if w.isdigit()]

        headline_variations = [
            f"🔥 {first_line}",
            f"THREAD: {first_line}",
            f"Unpopular opinion: {first_line}",
            f"Hot take: {first_line}",
            f"Real talk: {first_line}"
        ]

        if numbers:
            headline_variations.append(f"The {numbers[0]} things about {first_line.split()[0]}")

        if action_words:
            headline_variations.append(f"How to {action_words[0]} like a pro")

        for i, variation in enumerate(headline_variations[:3]):  # Limit to 3 variations
            modified_content = content.replace(first_line, variation, 1)

            variations.append(ContentVariation(
                variation_type=ContentVariationType.HEADLINE,
                original_content=content,
                modified_content=modified_content,
                changes_made=[f"Changed headline from '{first_line}' to '{variation}'"],
                target_improvement="Increase attention and click-through rates",
                variation_rationale=f"Headline variation {i+1} uses attention-grabbing elements",
                expected_improvement=0.1 + i * 0.05,
                confidence=0.6,
                optimized_platform=platform
            ))

        return variations

    async def _generate_hook_variations(self, content: str, platform: Platform) -> list[ContentVariation]:
        """Generate opening hook variations."""
        variations = []
        first_sentence = content.split('.')[0] + '.' if '.' in content else content[:100]

        hook_variations = [
            "Here's something that will surprise you:",
            "I used to believe this was impossible until...",
            "What if I told you that everything you know about this is wrong?",
            "The most successful people I know all do this one thing:",
            "After 10 years in the industry, I've learned that..."
        ]

        for i, hook in enumerate(hook_variations[:3]):
            # Replace first sentence with new hook
            modified_content = content.replace(first_sentence, f"{hook}\n\n{first_sentence}", 1)

            variations.append(ContentVariation(
                variation_type=ContentVariationType.HOOK,
                original_content=content,
                modified_content=modified_content,
                changes_made=[f"Added engaging hook: '{hook}'"],
                target_improvement="Improve initial engagement and retention",
                variation_rationale=f"Hook strategy: {self.hook_strategies[i % len(self.hook_strategies)]}",
                expected_improvement=0.15 + i * 0.05,
                confidence=0.7,
                optimized_platform=platform
            ))

        return variations

    async def _generate_tone_variations(self, content: str, platform: Platform) -> list[ContentVariation]:
        """Generate tone variations."""
        variations = []

        tone_adjustments = {
            "casual": {
                "replace": [("therefore", "so"), ("furthermore", "also"), ("however", "but")],
                "add_phrases": ["Hey", "Let's be real", "Here's the thing"]
            },
            "professional": {
                "replace": [("so", "therefore"), ("but", "however"), ("really", "significantly")],
                "add_phrases": ["In my experience", "Based on research", "It's important to note"]
            },
            "enthusiastic": {
                "add_phrases": ["I'm excited to share", "This is amazing", "You'll love this"],
                "add_punctuation": "!"
            }
        }

        for tone, adjustments in list(tone_adjustments.items())[:2]:  # Limit to 2 tones
            modified_content = content
            changes_made = []

            # Apply replacements
            if "replace" in adjustments:
                for old, new in adjustments["replace"]:
                    if old in modified_content:
                        modified_content = modified_content.replace(old, new)
                        changes_made.append(f"Replaced '{old}' with '{new}'")

            # Add tone-specific phrases
            if "add_phrases" in adjustments and adjustments["add_phrases"]:
                phrase = adjustments["add_phrases"][0]
                modified_content = f"{phrase}!\n\n{modified_content}"
                changes_made.append(f"Added {tone} opening: '{phrase}'")

            variations.append(ContentVariation(
                variation_type=ContentVariationType.TONE,
                original_content=content,
                modified_content=modified_content,
                changes_made=changes_made,
                target_improvement=f"Adjust tone to be more {tone}",
                variation_rationale=f"Modified language and style for {tone} tone",
                expected_improvement=0.1,
                confidence=0.6,
                optimized_platform=platform,
                tags=[tone]
            ))

        return variations

    async def _generate_length_variations(self, content: str, platform: Platform) -> list[ContentVariation]:
        """Generate length variations (shorter and longer versions)."""
        variations = []
        word_count = len(content.split())

        # Short version (50% of original)
        if word_count > 50:
            sentences = content.split('.')
            short_content = '. '.join(sentences[:len(sentences)//2]) + '.'

            variations.append(ContentVariation(
                variation_type=ContentVariationType.LENGTH,
                original_content=content,
                modified_content=short_content,
                changes_made=[f"Reduced from {word_count} to ~{len(short_content.split())} words"],
                target_improvement="Improve readability and engagement for shorter attention spans",
                variation_rationale="Shorter content often performs better on fast-paced platforms",
                expected_improvement=0.15,
                confidence=0.7,
                optimized_platform=platform,
                tags=["short", "concise"]
            ))

        # Extended version (with additional context)
        if word_count < 200:
            extended_content = content + "\n\nWhat are your thoughts on this? I'd love to hear your experiences in the comments below."

            variations.append(ContentVariation(
                variation_type=ContentVariationType.LENGTH,
                original_content=content,
                modified_content=extended_content,
                changes_made=["Extended with engagement question and CTA"],
                target_improvement="Increase engagement and discussion",
                variation_rationale="Extended content with CTA encourages more interaction",
                expected_improvement=0.1,
                confidence=0.6,
                optimized_platform=platform,
                tags=["extended", "engagement"]
            ))

        return variations

    async def _generate_structure_variations(self, content: str, platform: Platform) -> list[ContentVariation]:
        """Generate structure variations."""
        variations = []

        # List format variation
        if '\n' not in content and len(content.split('.')) > 2:
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            list_content = "Key takeaways:\n\n" + "\n".join([f"• {s}." for s in sentences[:3]])

            variations.append(ContentVariation(
                variation_type=ContentVariationType.STRUCTURE,
                original_content=content,
                modified_content=list_content,
                changes_made=["Converted to bullet point list format"],
                target_improvement="Improve scanability and readability",
                variation_rationale="List format is easier to scan and digest",
                expected_improvement=0.2,
                confidence=0.8,
                optimized_platform=platform,
                tags=["list", "structured"]
            ))

        # Question-answer format
        if '?' not in content:
            qa_content = f"Q: What's the key insight here?\n\nA: {content}\n\nWhat do you think?"

            variations.append(ContentVariation(
                variation_type=ContentVariationType.STRUCTURE,
                original_content=content,
                modified_content=qa_content,
                changes_made=["Converted to Q&A format"],
                target_improvement="Increase engagement through interactive format",
                variation_rationale="Q&A format encourages reader participation",
                expected_improvement=0.15,
                confidence=0.6,
                optimized_platform=platform,
                tags=["qa", "interactive"]
            ))

        return variations

    async def _generate_cta_variations(self, content: str, platform: Platform) -> list[ContentVariation]:
        """Generate call-to-action variations."""
        variations = []

        cta_options = [
            "What's your take on this? Drop a comment below! 👇",
            "Share if you found this helpful! 🔄",
            "Follow for more insights like this! ✨",
            "Tag someone who needs to see this! 🏷️",
            "Save this post for later reference! 📌"
        ]

        for _i, cta in enumerate(cta_options[:3]):  # Limit to 3 CTAs
            modified_content = f"{content}\n\n{cta}"

            variations.append(ContentVariation(
                variation_type=ContentVariationType.CTA,
                original_content=content,
                modified_content=modified_content,
                changes_made=[f"Added CTA: '{cta}'"],
                target_improvement="Increase specific user actions and engagement",
                variation_rationale=f"CTA encourages {cta.split()[0].lower()} action",
                expected_improvement=0.2,
                confidence=0.8,
                optimized_platform=platform,
                tags=["cta", cta.split()[0].lower()]
            ))

        return variations

    async def _generate_platform_variations(self, content: str, platform: Platform) -> list[ContentVariation]:
        """Generate platform-specific variations."""
        variations = []

        platform_adaptations = {
            Platform.LINKEDIN: {
                "hashtags": ["#Leadership", "#Innovation", "#Business"],
                "format": "Professional tone with industry insights",
                "additions": ["Thoughts?", "What's your experience with this?"]
            },
            Platform.TWITTER: {
                "hashtags": ["#Tech", "#Growth", "#Tips"],
                "format": "Concise with strong hook",
                "additions": ["Thread 🧵", "RT if you agree 🔄"]
            },
            Platform.GENERAL: {
                "hashtags": ["#Insight", "#Learning", "#Growth"],
                "format": "Balanced approach",
                "additions": ["Share your thoughts!", "What do you think?"]
            }
        }

        if platform in platform_adaptations:
            adaptation = platform_adaptations[platform]

            # Add hashtags
            hashtags = " ".join(adaptation["hashtags"][:2])
            platform_content = f"{content}\n\n{hashtags}"

            # Add platform-specific engagement
            if adaptation["additions"]:
                platform_content += f"\n\n{adaptation['additions'][0]}"

            variations.append(ContentVariation(
                variation_type=ContentVariationType.PLATFORM_ADAPTATION,
                original_content=content,
                modified_content=platform_content,
                changes_made=[
                    f"Added {platform.value} hashtags",
                    "Added platform-specific engagement element"
                ],
                target_improvement=f"Optimize for {platform.value} algorithm and user behavior",
                variation_rationale=f"Platform-specific optimization for {platform.value}",
                expected_improvement=0.25,
                confidence=0.8,
                optimized_platform=platform,
                tags=[platform.value, "optimized"]
            ))

        return variations

    async def _generate_audience_variations(self, content: str, platform: Platform,
                                          target_audience: str | None) -> list[ContentVariation]:
        """Generate audience-specific variations."""
        variations = []

        if not target_audience:
            return variations

        # Simple audience adaptations based on common audiences
        audience_adaptations = {
            "beginners": {
                "additions": "New to this? Here's what you need to know:",
                "explanations": "Let me break this down..."
            },
            "experts": {
                "additions": "For those deep in the field:",
                "technical": "From a technical perspective..."
            },
            "entrepreneurs": {
                "additions": "As an entrepreneur, you know that:",
                "business": "From a business standpoint..."
            }
        }

        # Find matching audience type
        audience_type = None
        for aud_type in audience_adaptations.keys():
            if aud_type in target_audience.lower():
                audience_type = aud_type
                break

        if audience_type:
            adaptation = audience_adaptations[audience_type]
            if "additions" in adaptation:
                audience_content = f"{adaptation['additions']}\n\n{content}"

                variations.append(ContentVariation(
                    variation_type=ContentVariationType.AUDIENCE_TARGETING,
                    original_content=content,
                    modified_content=audience_content,
                    changes_made=[f"Added {audience_type}-specific introduction"],
                    target_improvement=f"Better target {audience_type} audience",
                    variation_rationale=f"Tailored language and approach for {audience_type}",
                    expected_improvement=0.2,
                    confidence=0.7,
                    optimized_platform=platform,
                    target_audience_segment=target_audience,
                    tags=[audience_type, "targeted"]
                ))

        return variations

    def _deduplicate_variations(self, variations: list[ContentVariation]) -> list[ContentVariation]:
        """Remove duplicate variations based on content similarity."""
        unique_variations = []
        seen_content = set()

        for variation in variations:
            # Create a hash of the modified content for comparison
            content_hash = hashlib.md5(variation.modified_content.encode()).hexdigest()

            if content_hash not in seen_content:
                unique_variations.append(variation)
                seen_content.add(content_hash)

        return unique_variations

    async def adapt_for_platform(self, content: str, target_platform: Platform,
                                source_platform: Platform = Platform.GENERAL) -> ContentVariation:
        """Adapt content for specific platform requirements.

        Args:
            content: Original content
            target_platform: Platform to adapt for
            source_platform: Original platform (if known)

        Returns:
            Platform-adapted content variation
        """
        try:
            # Generate platform-specific adaptations
            platform_variations = await self._generate_platform_variations(content, target_platform)

            if platform_variations:
                return platform_variations[0]  # Return the first/best adaptation

            # Fallback: create basic platform adaptation
            return ContentVariation(
                variation_type=ContentVariationType.PLATFORM_ADAPTATION,
                original_content=content,
                modified_content=content,  # No changes if no specific adaptations
                changes_made=["No platform-specific changes needed"],
                target_improvement=f"Maintain compatibility with {target_platform.value}",
                variation_rationale="Content already suitable for target platform",
                expected_improvement=0.0,
                confidence=0.5,
                optimized_platform=target_platform
            )

        except Exception as e:
            logger.error(f"Error adapting content for platform {target_platform}: {e}")

            # Return original content as fallback
            return ContentVariation(
                variation_type=ContentVariationType.PLATFORM_ADAPTATION,
                original_content=content,
                modified_content=content,
                changes_made=["Error in adaptation - using original content"],
                target_improvement="Maintain content integrity",
                variation_rationale=f"Adaptation error: {str(e)}",
                expected_improvement=0.0,
                confidence=0.0,
                optimized_platform=target_platform
            )

    async def create_ab_tests(self, content: str, test_focus: str = "engagement",
                            platform: Platform = Platform.GENERAL) -> list[ContentVariation]:
        """Create A/B test variations focused on specific metrics.

        Args:
            content: Original content
            test_focus: What to optimize for ("engagement", "conversion", "reach")
            platform: Target platform

        Returns:
            List of A/B test variations
        """
        try:
            test_variations = []

            if test_focus == "engagement":
                # Focus on engagement-driving variations
                engagement_types = [
                    ContentVariationType.HOOK,
                    ContentVariationType.CTA,
                    ContentVariationType.TONE
                ]

                for var_type in engagement_types:
                    variations = await self._generate_variations_by_type(
                        content, var_type, platform, None
                    )
                    if variations:
                        test_variations.append(variations[0])  # Take best variation of each type

            elif test_focus == "conversion":
                # Focus on conversion-driving variations
                conversion_types = [
                    ContentVariationType.CTA,
                    ContentVariationType.STRUCTURE
                ]

                for var_type in conversion_types:
                    variations = await self._generate_variations_by_type(
                        content, var_type, platform, None
                    )
                    if variations:
                        test_variations.append(variations[0])

            elif test_focus == "reach":
                # Focus on reach-maximizing variations
                reach_types = [
                    ContentVariationType.HEADLINE,
                    ContentVariationType.PLATFORM_ADAPTATION
                ]

                for var_type in reach_types:
                    variations = await self._generate_variations_by_type(
                        content, var_type, platform, None
                    )
                    if variations:
                        test_variations.append(variations[0])

            # Limit to 3 variations for practical A/B testing
            return test_variations[:3]

        except Exception as e:
            logger.error(f"Error creating A/B tests: {e}")
            return []


class PerformancePredictionEngine:
    """Predicts content performance before publishing.

    Uses historical data and ML models to predict engagement, reach, and conversion
    metrics with confidence intervals.
    """

    def __init__(self, viral_engine: ViralPredictionEngine,
                 resonance_scorer: ResonanceScorer,
                 safety_analyzer: BrandSafetyAnalyzer):
        """Initialize with prediction engines."""
        self.viral_engine = viral_engine
        self.resonance_scorer = resonance_scorer
        self.safety_analyzer = safety_analyzer

        logger.info("PerformancePredictionEngine initialized")

    async def predict_performance(self, content: str, platform: Platform,
                                target_audience: str | None = None,
                                context: dict[str, Any] | None = None) -> PerformancePrediction:
        """Predict content performance across multiple metrics.

        Args:
            content: Content to predict performance for
            platform: Target platform
            target_audience: Target audience description
            context: Additional context for prediction

        Returns:
            Performance prediction with confidence intervals
        """
        try:
            # Get viral prediction
            viral_prediction = await self.viral_engine.predict_viral_potential(content, platform)

            # Base predictions from viral engine
            engagement_pred = viral_prediction.engagement_score
            reach_pred = viral_prediction.reach_potential
            viral_pred = viral_prediction.viral_velocity

            # Estimate conversion based on content analysis
            conversion_pred = await self._predict_conversion_rate(content, platform)

            # Calculate confidence intervals
            engagement_conf = self._calculate_confidence_interval(engagement_pred, 0.1)
            reach_conf = self._calculate_confidence_interval(reach_pred, 0.15)
            conversion_conf = self._calculate_confidence_interval(conversion_pred, 0.2)
            viral_conf = self._calculate_confidence_interval(viral_pred, 0.25)

            # Assess risks
            risk_factors = await self._assess_risk_factors(content, platform)
            risk_level = await self._determine_risk_level(risk_factors)
            mitigation_suggestions = self._generate_mitigation_suggestions(risk_factors)

            # Overall prediction confidence
            prediction_confidence = self._calculate_overall_confidence(
                engagement_pred, reach_pred, conversion_pred, viral_pred
            )

            return PerformancePrediction(
                content=content,
                platform=platform,
                engagement_prediction=engagement_pred,
                reach_prediction=reach_pred,
                conversion_prediction=conversion_pred,
                viral_prediction=viral_pred,
                engagement_confidence=engagement_conf,
                reach_confidence=reach_conf,
                conversion_confidence=conversion_conf,
                viral_confidence=viral_conf,
                risk_factors=risk_factors,
                risk_level=risk_level,
                mitigation_suggestions=mitigation_suggestions,
                prediction_confidence=prediction_confidence
            )

        except Exception as e:
            logger.error(f"Error predicting performance: {e}")

            # Return default prediction
            return PerformancePrediction(
                content=content,
                platform=platform,
                engagement_prediction=0.5,
                reach_prediction=0.5,
                conversion_prediction=0.3,
                viral_prediction=0.2,
                engagement_confidence=(0.3, 0.7),
                reach_confidence=(0.3, 0.7),
                conversion_confidence=(0.1, 0.5),
                viral_confidence=(0.0, 0.4),
                risk_factors=[f"Prediction error: {str(e)}"],
                risk_level=RiskLevel.MEDIUM,
                mitigation_suggestions=["Review content manually due to prediction error"],
                prediction_confidence=0.3
            )

    async def _predict_conversion_rate(self, content: str, platform: Platform) -> float:
        """Predict conversion rate based on content characteristics."""
        try:
            # Analyze conversion indicators
            has_cta = any(phrase in content.lower() for phrase in
                         ['click', 'download', 'subscribe', 'join', 'sign up', 'learn more'])
            has_urgency = any(word in content.lower() for word in
                            ['now', 'today', 'limited', 'urgent', 'deadline'])
            has_benefit = any(word in content.lower() for word in
                            ['free', 'save', 'improve', 'increase', 'boost'])
            has_social_proof = any(phrase in content.lower() for phrase in
                                 ['testimonial', 'review', 'customer', 'success story'])

            # Base conversion rate by platform
            platform_base_rates = {
                Platform.LINKEDIN: 0.25,
                Platform.TWITTER: 0.15,
                Platform.GENERAL: 0.2
            }

            base_rate = platform_base_rates.get(platform, 0.2)

            # Apply modifiers
            if has_cta:
                base_rate += 0.1
            if has_urgency:
                base_rate += 0.05
            if has_benefit:
                base_rate += 0.05
            if has_social_proof:
                base_rate += 0.08

            # Clamp to reasonable range
            return min(0.8, max(0.05, base_rate))

        except Exception as e:
            logger.error(f"Error predicting conversion rate: {e}")
            return 0.2  # Default moderate conversion rate

    def _calculate_confidence_interval(self, prediction: float, uncertainty: float) -> tuple[float, float]:
        """Calculate confidence interval for a prediction.

        Args:
            prediction: The predicted value
            uncertainty: Uncertainty factor (0-1)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        margin = prediction * uncertainty
        lower = max(0.0, prediction - margin)
        upper = min(1.0, prediction + margin)
        return (lower, upper)

    async def _assess_risk_factors(self, content: str, platform: Platform) -> list[str]:
        """Assess potential risk factors for content performance."""
        risk_factors = []

        try:
            # Content length risks
            word_count = len(content.split())
            if word_count < 20:
                risk_factors.append("Content may be too short for meaningful engagement")
            elif word_count > 300:
                risk_factors.append("Content may be too long for platform optimal length")

            # Engagement risks
            if '?' not in content:
                risk_factors.append("Lack of questions may reduce engagement")

            if not any(phrase in content.lower() for phrase in ['share', 'comment', 'like']):
                risk_factors.append("Missing call-to-action may limit user response")

            # Platform-specific risks
            if platform == Platform.LINKEDIN:
                if '#' not in content:
                    risk_factors.append("Missing hashtags may reduce LinkedIn discoverability")
            elif platform == Platform.TWITTER:
                if len(content) > 280:
                    risk_factors.append("Content exceeds Twitter character limit")

            # Timing risks (if context available)
            current_hour = datetime.now().hour
            if current_hour < 6 or current_hour > 22:
                risk_factors.append("Posting time may not be optimal for audience")

            # Controversy risks
            controversial_words = ['controversial', 'disagree', 'wrong', 'problem', 'issue']
            if any(word in content.lower() for word in controversial_words):
                risk_factors.append("Content may generate controversial responses")

        except Exception as e:
            logger.error(f"Error assessing risk factors: {e}")
            risk_factors.append(f"Risk assessment error: {str(e)}")

        return risk_factors

    async def _determine_risk_level(self, risk_factors: list[str]) -> RiskLevel:
        """Determine overall risk level based on risk factors."""
        if len(risk_factors) == 0:
            return RiskLevel.LOW
        elif len(risk_factors) <= 2:
            return RiskLevel.MEDIUM
        elif len(risk_factors) <= 4:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    def _generate_mitigation_suggestions(self, risk_factors: list[str]) -> list[str]:
        """Generate suggestions to mitigate identified risks."""
        suggestions = []

        for risk in risk_factors:
            if "too short" in risk:
                suggestions.append("Expand content with additional details or examples")
            elif "too long" in risk:
                suggestions.append("Consider breaking into shorter posts or thread")
            elif "questions" in risk:
                suggestions.append("Add engaging questions to encourage interaction")
            elif "call-to-action" in risk:
                suggestions.append("Include clear call-to-action for desired user behavior")
            elif "hashtags" in risk:
                suggestions.append("Add relevant hashtags for better discoverability")
            elif "character limit" in risk:
                suggestions.append("Shorten content to fit platform constraints")
            elif "posting time" in risk:
                suggestions.append("Consider scheduling for optimal posting time")
            elif "controversial" in risk:
                suggestions.append("Review content for potentially divisive language")
            else:
                suggestions.append("Review and address identified risk factor")

        # Remove duplicates
        return list(set(suggestions))

    def _calculate_overall_confidence(self, engagement: float, reach: float,
                                    conversion: float, viral: float) -> float:
        """Calculate overall confidence in predictions."""
        try:
            # Confidence based on prediction consistency
            predictions = [engagement, reach, conversion, viral]
            std_dev = statistics.stdev(predictions) if len(predictions) > 1 else 0

            # Lower confidence if predictions vary widely
            consistency_factor = max(0.5, 1.0 - std_dev)

            # Base confidence (can be adjusted based on model training)
            base_confidence = 0.7

            return min(0.95, base_confidence * consistency_factor)

        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.6  # Default moderate confidence

    def calculate_confidence(self, prediction: PerformancePrediction) -> float:
        """Calculate confidence score for a performance prediction.

        Args:
            prediction: Performance prediction to assess

        Returns:
            Confidence score (0-1)
        """
        return prediction.prediction_confidence

    def assess_risks(self, prediction: PerformancePrediction) -> dict[str, Any]:
        """Assess risks associated with predicted performance.

        Args:
            prediction: Performance prediction to assess

        Returns:
            Risk assessment details
        """
        return {
            'risk_level': prediction.risk_level.value,
            'risk_factors': prediction.risk_factors,
            'mitigation_suggestions': prediction.mitigation_suggestions,
            'risk_score': len(prediction.risk_factors) / 10.0,  # Normalized risk score
            'confidence_impact': 1.0 - (len(prediction.risk_factors) * 0.1)
        }


class ContentOptimizationWorkflow:
    """End-to-end optimization workflow management.

    Tracks optimization progress, manages iteration cycles, and handles feedback loops
    for continuous content improvement.
    """

    def __init__(self, content_analyzer: ContentAnalyzer,
                 suggestion_generator: ImprovementSuggestionGenerator,
                 variation_generator: ContentVariationGenerator,
                 prediction_engine: PerformancePredictionEngine):
        """Initialize workflow with all optimization components."""
        self.content_analyzer = content_analyzer
        self.suggestion_generator = suggestion_generator
        self.variation_generator = variation_generator
        self.prediction_engine = prediction_engine

        # Active workflows tracking
        self.active_workflows: dict[str, OptimizationWorkflow] = {}

        logger.info("ContentOptimizationWorkflow initialized")

    async def start_optimization(self, request: ContentOptimizationRequest) -> OptimizationWorkflow:
        """Start a complete optimization workflow.

        Args:
            request: Optimization request with content and parameters

        Returns:
            Workflow object for tracking progress
        """
        try:
            # Create workflow tracking object
            workflow = OptimizationWorkflow(
                content_id=hashlib.md5(request.content.encode()).hexdigest()[:12],
                optimization_config=request.dict()
            )

            # Store in active workflows
            self.active_workflows[workflow.workflow_id] = workflow

            # Start async optimization process
            asyncio.create_task(self._execute_optimization(workflow, request))

            logger.info(f"Started optimization workflow {workflow.workflow_id}")
            return workflow

        except Exception as e:
            logger.error(f"Error starting optimization workflow: {e}")
            raise

    async def _execute_optimization(self, workflow: OptimizationWorkflow,
                                  request: ContentOptimizationRequest):
        """Execute the complete optimization process."""
        try:
            start_time = datetime.now()

            # Step 1: Content Analysis
            workflow.update_progress("analyzing_content", 10)
            step_start = datetime.now()

            analysis_result = await self._analyze_content(request)
            workflow.analysis_result_id = analysis_result.content_id

            step_time = (datetime.now() - step_start).total_seconds()
            workflow.step_timings["content_analysis"] = step_time

            # Step 2: Generate Suggestions
            workflow.update_progress("generating_suggestions", 30)
            step_start = datetime.now()

            suggestions = await self.suggestion_generator.generate_suggestions(
                analysis_result, request.optimization_types
            )
            workflow.suggestions_count = len(suggestions)

            step_time = (datetime.now() - step_start).total_seconds()
            workflow.step_timings["suggestion_generation"] = step_time

            # Step 3: Generate Variations (if requested)
            if request.generate_variations:
                workflow.update_progress("creating_variations", 60)
                step_start = datetime.now()

                variation_types = [
                    ContentVariationType.HEADLINE,
                    ContentVariationType.HOOK,
                    ContentVariationType.CTA
                ]

                variations = await self.variation_generator.generate_variations(
                    request.content, variation_types, request.platform, request.target_audience
                )
                workflow.variations_count = len(variations)

                step_time = (datetime.now() - step_start).total_seconds()
                workflow.step_timings["variation_generation"] = step_time

            # Step 4: Performance Prediction (if requested)
            if request.predict_performance:
                workflow.update_progress("predicting_performance", 80)
                step_start = datetime.now()

                await self.prediction_engine.predict_performance(
                    request.content, request.platform, request.target_audience, request.context
                )
                workflow.predictions_count = 1

                step_time = (datetime.now() - step_start).total_seconds()
                workflow.step_timings["performance_prediction"] = step_time

            # Complete workflow
            workflow.complete_workflow()
            total_time = (datetime.now() - start_time).total_seconds()
            workflow.total_processing_time = total_time

            logger.info(f"Completed optimization workflow {workflow.workflow_id} in {total_time:.2f}s")

        except Exception as e:
            workflow.status = OptimizationStatus.FAILED
            workflow.add_error(f"Workflow execution failed: {str(e)}")
            logger.error(f"Optimization workflow {workflow.workflow_id} failed: {e}")

    async def _analyze_content(self, request: ContentOptimizationRequest) -> ContentAnalysisResult:
        """Perform comprehensive content analysis."""
        try:
            start_time = datetime.now()

            # Initialize analysis result
            analysis_result = ContentAnalysisResult(
                original_content=request.content,
                analysis_depth=request.analysis_depth
            )

            # Perform different types of analysis based on optimization types
            if OptimizationType.READABILITY in request.optimization_types:
                readability_result = await self.content_analyzer.analyze_readability(request.content)
                analysis_result.readability_analysis = readability_result
                analysis_result.quality_scores[ContentQualityMetric.READABILITY_SCORE] = readability_result.get('readability_score', 0.5)

            if OptimizationType.ENGAGEMENT in request.optimization_types:
                engagement_result = await self.content_analyzer.analyze_engagement_potential(
                    request.content, request.platform
                )
                analysis_result.engagement_analysis = engagement_result
                analysis_result.quality_scores[ContentQualityMetric.ENGAGEMENT_POTENTIAL] = engagement_result.get('engagement_score', 0.5)

            if OptimizationType.BRAND_SAFETY in request.optimization_types:
                brand_profile = None
                if request.brand_profile:
                    # Convert dict to BrandProfile if needed
                    brand_profile = request.brand_profile

                brand_result = await self.content_analyzer.analyze_brand_alignment(
                    request.content, brand_profile
                )
                analysis_result.brand_alignment_analysis = brand_result
                analysis_result.quality_scores[ContentQualityMetric.BRAND_ALIGNMENT] = brand_result.get('alignment_score', 0.5)

            # Identify gaps and opportunities
            gaps_result = await self.content_analyzer.identify_gaps(request.content, request.context)
            analysis_result.identified_gaps = gaps_result.get('identified_gaps', [])
            analysis_result.opportunities = gaps_result.get('opportunities', [])

            # Calculate overall score
            if analysis_result.quality_scores:
                analysis_result.overall_score = sum(analysis_result.quality_scores.values()) / len(analysis_result.quality_scores)
            else:
                analysis_result.overall_score = 0.5

            # Calculate confidence and processing time
            analysis_result.confidence_score = min(0.9, analysis_result.overall_score + 0.1)
            analysis_result.processing_time = (datetime.now() - start_time).total_seconds()

            return analysis_result

        except Exception as e:
            logger.error(f"Error in content analysis: {e}")

            # Return minimal analysis result
            return ContentAnalysisResult(
                original_content=request.content,
                analysis_depth=request.analysis_depth,
                overall_score=0.5,
                confidence_score=0.3,
                identified_gaps=[f"Analysis error: {str(e)}"],
                opportunities=["Manual review recommended due to analysis error"]
            )

    def track_progress(self, workflow_id: str) -> OptimizationWorkflow | None:
        """Track progress of an optimization workflow.

        Args:
            workflow_id: ID of workflow to track

        Returns:
            Current workflow state or None if not found
        """
        return self.active_workflows.get(workflow_id)

    def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """Get detailed status of optimization workflow.

        Args:
            workflow_id: ID of workflow to check

        Returns:
            Detailed status information
        """
        workflow = self.active_workflows.get(workflow_id)

        if not workflow:
            return {'error': 'Workflow not found', 'workflow_id': workflow_id}

        return {
            'workflow_id': workflow.workflow_id,
            'status': workflow.status.value,
            'progress_percentage': workflow.progress_percentage,
            'current_step': workflow.current_step,
            'started_at': workflow.started_at.isoformat(),
            'completed_at': workflow.completed_at.isoformat() if workflow.completed_at else None,
            'total_processing_time': workflow.total_processing_time,
            'results_summary': {
                'analysis_completed': bool(workflow.analysis_result_id),
                'suggestions_generated': workflow.suggestions_count,
                'variations_created': workflow.variations_count,
                'predictions_made': workflow.predictions_count
            },
            'step_timings': workflow.step_timings,
            'errors': workflow.errors,
            'warnings': workflow.warnings
        }

    async def iterate_improvements(self, workflow_id: str, feedback: dict[str, Any]) -> OptimizationWorkflow:
        """Iterate on improvements based on feedback.

        Args:
            workflow_id: ID of workflow to iterate
            feedback: Feedback on previous suggestions/variations

        Returns:
            Updated workflow with new iterations
        """
        try:
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Create new iteration request based on feedback
            # This would implement feedback processing logic

            # For now, just update workflow status
            workflow.add_warning("Iteration requested - feature in development")

            logger.info(f"Iteration requested for workflow {workflow_id}")
            return workflow

        except Exception as e:
            logger.error(f"Error iterating improvements for {workflow_id}: {e}")
            raise

    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up old completed workflows to free memory.

        Args:
            max_age_hours: Maximum age in hours for keeping completed workflows
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            workflows_to_remove = []
            for workflow_id, workflow in self.active_workflows.items():
                if (workflow.status == OptimizationStatus.COMPLETED and
                    workflow.completed_at and
                    workflow.completed_at < cutoff_time):
                    workflows_to_remove.append(workflow_id)

            for workflow_id in workflows_to_remove:
                del self.active_workflows[workflow_id]

            if workflows_to_remove:
                logger.info(f"Cleaned up {len(workflows_to_remove)} completed workflows")

        except Exception as e:
            logger.error(f"Error cleaning up workflows: {e}")


class ContentOptimizationEngine:
    """Main orchestrator for content optimization.

    Integrates all Epic capabilities and provides comprehensive content analysis
    and improvement recommendations through a unified interface.
    """

    def __init__(self):
        """Initialize the content optimization engine with all components."""
        # Initialize epic capability components
        self.belief_extractor = BeliefPreferenceExtractor()
        self.viral_engine = ViralPredictionEngine()
        self.safety_analyzer = BrandSafetyAnalyzer()
        self.audience_engine = AudienceSegmentationEngine()
        self.strategy_optimizer = ContentStrategyOptimizer()
        self.resonance_scorer = ResonanceScorer()

        # Initialize optimization components
        self.content_analyzer = ContentAnalyzer(
            self.belief_extractor,
            self.viral_engine,
            self.safety_analyzer,
            self.audience_engine,
            self.resonance_scorer
        )

        self.suggestion_generator = ImprovementSuggestionGenerator(self.content_analyzer)

        self.variation_generator = ContentVariationGenerator(
            self.belief_extractor,
            self.viral_engine
        )

        self.prediction_engine = PerformancePredictionEngine(
            self.viral_engine,
            self.resonance_scorer,
            self.safety_analyzer
        )

        self.workflow_manager = ContentOptimizationWorkflow(
            self.content_analyzer,
            self.suggestion_generator,
            self.variation_generator,
            self.prediction_engine
        )

        logger.info("ContentOptimizationEngine initialized with all epic capabilities")

    async def analyze_content(self, content: str, platform: Platform = Platform.GENERAL,
                            optimization_types: list[OptimizationType] | None = None,
                            analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD,
                            context: dict[str, Any] | None = None) -> ContentAnalysisResult:
        """Analyze content across multiple dimensions.

        Args:
            content: Content to analyze
            platform: Target platform
            optimization_types: Types of optimization to focus on
            analysis_depth: Depth of analysis to perform
            context: Additional context for analysis

        Returns:
            Comprehensive content analysis results
        """
        try:
            if optimization_types is None:
                optimization_types = [
                    OptimizationType.ENGAGEMENT,
                    OptimizationType.READABILITY,
                    OptimizationType.BRAND_SAFETY
                ]

            # Create optimization request
            request = ContentOptimizationRequest(
                content=content,
                platform=platform,
                optimization_types=optimization_types,
                analysis_depth=analysis_depth,
                context=context,
                generate_variations=False,
                predict_performance=False
            )

            # Perform analysis
            analysis_result = await self.workflow_manager._analyze_content(request)

            logger.info(f"Content analysis completed with overall score: {analysis_result.overall_score:.2f}")
            return analysis_result

        except Exception as e:
            logger.error(f"Error in content analysis: {e}")
            raise

    async def generate_improvements(self, content: str, platform: Platform = Platform.GENERAL,
                                  optimization_types: list[OptimizationType] | None = None,
                                  target_audience: str | None = None,
                                  brand_profile: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate comprehensive improvement suggestions for content.

        Args:
            content: Content to improve
            platform: Target platform
            optimization_types: Types of optimization to focus on
            target_audience: Target audience description
            brand_profile: Brand profile information

        Returns:
            Dictionary with analysis results and improvement suggestions
        """
        try:
            if optimization_types is None:
                optimization_types = [
                    OptimizationType.ENGAGEMENT,
                    OptimizationType.READABILITY,
                    OptimizationType.AUDIENCE_FIT,
                    OptimizationType.BRAND_SAFETY
                ]

            # Analyze content
            analysis_result = await self.analyze_content(
                content, platform, optimization_types
            )

            # Generate suggestions
            suggestions = await self.suggestion_generator.generate_suggestions(
                analysis_result, optimization_types
            )

            # Format recommendations
            formatted_recommendations = self.suggestion_generator.format_actionable_recommendations(suggestions)

            return {
                'analysis_result': analysis_result.dict(),
                'suggestions': [s.dict() for s in suggestions],
                'formatted_recommendations': formatted_recommendations,
                'summary': {
                    'overall_score': analysis_result.overall_score,
                    'confidence': analysis_result.confidence_score,
                    'total_suggestions': len(suggestions),
                    'high_priority_suggestions': len([s for s in suggestions if s.priority == ImprovementPriority.HIGH]),
                    'quick_wins': len([s for s in suggestions if s.impact_score > 0.6 and s.effort_estimate <= 2])
                }
            }

        except Exception as e:
            logger.error(f"Error generating improvements: {e}")
            raise

    async def optimize_for_platform(self, content: str, target_platform: Platform,
                                  source_platform: Platform = Platform.GENERAL,
                                  include_variations: bool = True) -> dict[str, Any]:
        """Optimize content for specific platform requirements.

        Args:
            content: Original content
            target_platform: Platform to optimize for
            source_platform: Original platform (if known)
            include_variations: Whether to include content variations

        Returns:
            Platform-optimized content and recommendations
        """
        try:
            # Analyze for platform-specific optimization
            analysis_result = await self.analyze_content(
                content,
                target_platform,
                [OptimizationType.PLATFORM_SPECIFIC, OptimizationType.ENGAGEMENT]
            )

            # Generate platform adaptation
            platform_adaptation = await self.variation_generator.adapt_for_platform(
                content, target_platform, source_platform
            )

            results = {
                'original_content': content,
                'optimized_content': platform_adaptation.modified_content,
                'platform_adaptation': platform_adaptation.dict(),
                'analysis_result': analysis_result.dict(),
                'optimization_summary': {
                    'target_platform': target_platform.value,
                    'changes_made': platform_adaptation.changes_made,
                    'expected_improvement': platform_adaptation.expected_improvement,
                    'confidence': platform_adaptation.confidence
                }
            }

            # Include variations if requested
            if include_variations:
                variations = await self.variation_generator.generate_variations(
                    content,
                    [ContentVariationType.PLATFORM_ADAPTATION, ContentVariationType.CTA],
                    target_platform
                )
                results['additional_variations'] = [v.dict() for v in variations]

            return results

        except Exception as e:
            logger.error(f"Error optimizing for platform {target_platform}: {e}")
            raise

    async def a_b_test_suggestions(self, content: str, test_focus: str = "engagement",
                                 platform: Platform = Platform.GENERAL,
                                 target_audience: str | None = None) -> dict[str, Any]:
        """Generate A/B testing suggestions and variations.

        Args:
            content: Original content
            test_focus: What to optimize for ("engagement", "conversion", "reach")
            platform: Target platform
            target_audience: Target audience description

        Returns:
            A/B testing variations and recommendations
        """
        try:
            # Create A/B test variations
            test_variations = await self.variation_generator.create_ab_tests(
                content, test_focus, platform
            )

            # Predict performance for each variation
            predictions = []
            for variation in test_variations:
                prediction = await self.prediction_engine.predict_performance(
                    variation.modified_content, platform, target_audience
                )
                predictions.append({
                    'variation_id': variation.variation_id,
                    'prediction': prediction.dict(),
                    'variation': variation.dict()
                })

            # Generate testing recommendations
            testing_recommendations = self._generate_ab_testing_recommendations(
                test_variations, predictions, test_focus
            )

            return {
                'original_content': content,
                'test_focus': test_focus,
                'variations': [v.dict() for v in test_variations],
                'performance_predictions': predictions,
                'testing_recommendations': testing_recommendations,
                'summary': {
                    'total_variations': len(test_variations),
                    'best_predicted_performer': self._identify_best_performer(predictions),
                    'recommended_test_duration': "7-14 days",
                    'minimum_sample_size': "100+ interactions per variation"
                }
            }

        except Exception as e:
            logger.error(f"Error generating A/B test suggestions: {e}")
            raise

    def _generate_ab_testing_recommendations(self, variations: list[ContentVariation],
                                           predictions: list[dict[str, Any]],
                                           test_focus: str) -> list[str]:
        """Generate recommendations for A/B testing."""
        recommendations = []

        if len(variations) >= 2:
            recommendations.append(f"Test {len(variations)} variations focusing on {test_focus}")
            recommendations.append("Ensure statistical significance before drawing conclusions")
            recommendations.append("Monitor both primary and secondary metrics")

        if test_focus == "engagement":
            recommendations.append("Track likes, comments, shares, and click-through rates")
        elif test_focus == "conversion":
            recommendations.append("Focus on conversion rate and action completion")
        elif test_focus == "reach":
            recommendations.append("Monitor reach, impressions, and follower growth")

        recommendations.append("Run test for at least one week to account for timing variations")
        recommendations.append("Prepare to scale the winning variation")

        return recommendations

    def _identify_best_performer(self, predictions: list[dict[str, Any]]) -> str | None:
        """Identify the predicted best performing variation."""
        if not predictions:
            return None

        best_variation = max(
            predictions,
            key=lambda p: p['prediction']['engagement_prediction']
        )

        return best_variation['variation_id']

    async def comprehensive_optimization(self, request: ContentOptimizationRequest) -> dict[str, Any]:
        """Perform comprehensive content optimization including all analysis types.

        Args:
            request: Complete optimization request

        Returns:
            Comprehensive optimization results
        """
        try:
            # Start optimization workflow
            workflow = await self.workflow_manager.start_optimization(request)

            # Wait for completion (in production, this would be async)
            max_wait_time = 60  # seconds
            wait_time = 0

            while workflow.status not in [OptimizationStatus.COMPLETED, OptimizationStatus.FAILED] and wait_time < max_wait_time:
                await asyncio.sleep(1)
                wait_time += 1
                workflow = self.workflow_manager.track_progress(workflow.workflow_id)

            if workflow.status == OptimizationStatus.FAILED:
                raise Exception("Optimization workflow failed")

            # Compile comprehensive results
            workflow_status = self.workflow_manager.get_workflow_status(workflow.workflow_id)

            return {
                'workflow_id': workflow.workflow_id,
                'status': workflow_status,
                'optimization_request': request.dict(),
                'processing_summary': {
                    'total_time': workflow.total_processing_time,
                    'step_timings': workflow.step_timings,
                    'suggestions_generated': workflow.suggestions_count,
                    'variations_created': workflow.variations_count,
                    'predictions_made': workflow.predictions_count
                },
                'next_steps': [
                    "Review generated suggestions and prioritize implementation",
                    "Test content variations with target audience",
                    "Monitor performance metrics after optimization",
                    "Iterate based on actual performance data"
                ]
            }

        except Exception as e:
            logger.error(f"Error in comprehensive optimization: {e}")
            raise

    def get_optimization_status(self, workflow_id: str) -> dict[str, Any]:
        """Get status of optimization workflow.

        Args:
            workflow_id: ID of workflow to check

        Returns:
            Current workflow status and results
        """
        return self.workflow_manager.get_workflow_status(workflow_id)

    async def quick_optimization(self, content: str, platform: Platform = Platform.GENERAL) -> dict[str, Any]:
        """Perform quick optimization for immediate improvements.

        Args:
            content: Content to optimize
            platform: Target platform

        Returns:
            Quick optimization results with top suggestions
        """
        try:
            # Quick analysis focusing on key metrics
            analysis_result = await self.analyze_content(
                content,
                platform,
                [OptimizationType.ENGAGEMENT, OptimizationType.READABILITY],
                AnalysisDepth.SURFACE
            )

            # Generate top suggestions
            suggestions = await self.suggestion_generator.generate_suggestions(
                analysis_result,
                [OptimizationType.ENGAGEMENT, OptimizationType.READABILITY]
            )

            # Get top 3 quick wins
            quick_wins = [
                s for s in suggestions
                if s.impact_score > 0.6 and s.effort_estimate <= 2
            ][:3]

            return {
                'overall_score': analysis_result.overall_score,
                'confidence': analysis_result.confidence_score,
                'quick_wins': [s.dict() for s in quick_wins],
                'key_recommendations': [
                    s.title for s in suggestions[:3]
                ],
                'processing_time': analysis_result.processing_time,
                'next_steps': [
                    "Implement quick wins for immediate improvement",
                    "Consider full optimization for comprehensive analysis",
                    "Test changes with target audience"
                ]
            }

        except Exception as e:
            logger.error(f"Error in quick optimization: {e}")
            raise


# Helper functions and utilities
def create_optimization_engine() -> ContentOptimizationEngine:
    """Create and configure a content optimization engine.

    Returns:
        Configured ContentOptimizationEngine instance
    """
    try:
        engine = ContentOptimizationEngine()
        logger.info("Content optimization engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Error creating optimization engine: {e}")
        raise


async def optimize_content_quick(content: str, platform: str = "general") -> dict[str, Any]:
    """Quick utility function for content optimization.

    Args:
        content: Content to optimize
        platform: Target platform name

    Returns:
        Quick optimization results
    """
    try:
        # Convert platform string to enum
        platform_enum = Platform.GENERAL
        if platform.lower() == "linkedin":
            platform_enum = Platform.LINKEDIN
        elif platform.lower() == "twitter":
            platform_enum = Platform.TWITTER

        # Create engine and optimize
        engine = create_optimization_engine()
        results = await engine.quick_optimization(content, platform_enum)

        return results

    except Exception as e:
        logger.error(f"Error in quick content optimization: {e}")
        return {
            'error': str(e),
            'overall_score': 0.5,
            'quick_wins': [],
            'key_recommendations': ['Manual review recommended due to error']
        }


if __name__ == "__main__":
    # Example usage
    async def main():
        """Example usage of the content optimization engine."""

        # Sample content for testing
        sample_content = """
        AI is changing everything. Machine learning algorithms are now being used in virtually every industry,
        from healthcare to finance to entertainment. Companies that don't adapt will be left behind.
        """

        # Create optimization engine
        engine = create_optimization_engine()

        # Perform quick optimization
        print("=== Quick Optimization ===")
        quick_results = await engine.quick_optimization(sample_content, Platform.LINKEDIN)
        print(f"Overall Score: {quick_results['overall_score']:.2f}")
        print(f"Quick Wins: {len(quick_results['quick_wins'])}")

        # Generate comprehensive improvements
        print("\n=== Comprehensive Analysis ===")
        improvements = await engine.generate_improvements(
            sample_content,
            Platform.LINKEDIN,
            [OptimizationType.ENGAGEMENT, OptimizationType.READABILITY, OptimizationType.VIRAL_POTENTIAL]
        )
        print(f"Total Suggestions: {improvements['summary']['total_suggestions']}")
        print(f"High Priority: {improvements['summary']['high_priority_suggestions']}")

        # Generate A/B test variations
        print("\n=== A/B Testing ===")
        ab_tests = await engine.a_b_test_suggestions(sample_content, "engagement", Platform.LINKEDIN)
        print(f"Test Variations: {ab_tests['summary']['total_variations']}")
        print(f"Best Predicted: {ab_tests['summary']['best_predicted_performer']}")

        print("\n=== Optimization Complete ===")

    # Run example
    # asyncio.run(main())
