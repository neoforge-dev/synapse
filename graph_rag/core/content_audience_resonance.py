"""Content-Audience Resonance Scoring Algorithms for Epic 8.2.

This module provides sophisticated algorithms that measure how well content resonates 
with specific audience segments and predict engagement potential. It analyzes 
multi-dimensional resonance including demographic, behavioral, and psychographic fit.

Features:
- Comprehensive content-audience matching algorithms
- Multi-dimensional resonance analysis
- Real-time optimization recommendations
- Platform-specific resonance scoring
- Temporal and competitive landscape considerations
- ML-inspired scoring with confidence intervals
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from graph_rag.core.audience_intelligence import (
    AgeGroup,
    AudienceSegment,
    BehaviorProfile,
    ContentPreference,
    DemographicProfile,
    EngagementType,
    ExperienceLevel,
    Industry,
    PersonalityTrait,
    Platform,
    PsychographicProfile,
)
from graph_rag.core.concept_extractor import ConceptualEntity
from graph_rag.core.viral_prediction_engine import ViralPrediction

logger = logging.getLogger(__name__)


# Enums for resonance scoring
class ResonanceComponent(Enum):
    """Components of resonance analysis."""
    DEMOGRAPHIC = "demographic"
    BEHAVIORAL = "behavioral"
    PSYCHOGRAPHIC = "psychographic"
    CONTENT_COMPLEXITY = "content_complexity"
    PLATFORM_OPTIMIZATION = "platform_optimization"
    TEMPORAL_RELEVANCE = "temporal_relevance"
    COMPETITIVE_LANDSCAPE = "competitive_landscape"


class ResonanceLevel(Enum):
    """Resonance levels for content-audience fit."""
    POOR = "poor"          # 0.0 - 0.2
    WEAK = "weak"          # 0.2 - 0.4
    MODERATE = "moderate"  # 0.4 - 0.6
    STRONG = "strong"      # 0.6 - 0.8
    EXCELLENT = "excellent" # 0.8 - 1.0


class OptimizationType(Enum):
    """Types of optimization recommendations."""
    CONTENT_ADJUSTMENT = "content_adjustment"
    PLATFORM_OPTIMIZATION = "platform_optimization"
    TIMING_OPTIMIZATION = "timing_optimization"
    AUDIENCE_TARGETING = "audience_targeting"
    MESSAGING_REFINEMENT = "messaging_refinement"


# Data Models
@dataclass
class ResonanceScore:
    """Individual resonance score with detailed breakdown."""
    component: ResonanceComponent
    score: float = 0.0
    confidence: float = 0.0
    weight: float = 1.0
    contributing_factors: list[str] = field(default_factory=list)
    optimization_opportunities: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DemographicResonance:
    """Demographic alignment analysis."""
    age_alignment: float = 0.0
    industry_alignment: float = 0.0
    experience_alignment: float = 0.0
    location_alignment: float = 0.0
    role_alignment: float = 0.0
    overall_score: float = 0.0
    confidence: float = 0.0
    misalignment_factors: list[str] = field(default_factory=list)
    optimization_recommendations: list[str] = field(default_factory=list)


@dataclass
class BehavioralResonance:
    """Behavioral pattern alignment analysis."""
    engagement_pattern_fit: float = 0.0
    content_preference_fit: float = 0.0
    platform_usage_fit: float = 0.0
    interaction_style_fit: float = 0.0
    content_length_fit: float = 0.0
    timing_fit: float = 0.0
    overall_score: float = 0.0
    confidence: float = 0.0
    engagement_predictions: dict[EngagementType, float] = field(default_factory=dict)
    optimization_recommendations: list[str] = field(default_factory=list)


@dataclass
class PsychographicResonance:
    """Psychographic matching analysis."""
    personality_alignment: float = 0.0
    values_alignment: float = 0.0
    interests_alignment: float = 0.0
    motivation_alignment: float = 0.0
    communication_style_fit: float = 0.0
    overall_score: float = 0.0
    confidence: float = 0.0
    psychological_triggers: list[str] = field(default_factory=list)
    resonance_drivers: list[str] = field(default_factory=list)
    optimization_recommendations: list[str] = field(default_factory=list)


@dataclass
class ContentComplexityFit:
    """Content complexity and audience sophistication matching."""
    reading_level_fit: float = 0.0
    technical_depth_fit: float = 0.0
    concept_density_fit: float = 0.0
    expertise_level_fit: float = 0.0
    cognitive_load_fit: float = 0.0
    overall_score: float = 0.0
    confidence: float = 0.0
    complexity_metrics: dict[str, float] = field(default_factory=dict)
    adjustment_recommendations: list[str] = field(default_factory=list)


@dataclass
class PlatformOptimization:
    """Platform-specific optimization analysis."""
    format_fit: float = 0.0
    length_optimization: float = 0.0
    visual_element_fit: float = 0.0
    hashtag_optimization: float = 0.0
    posting_style_fit: float = 0.0
    algorithm_compatibility: float = 0.0
    overall_score: float = 0.0
    confidence: float = 0.0
    platform_specific_recommendations: list[str] = field(default_factory=list)


@dataclass
class TemporalRelevance:
    """Temporal factors and timing optimization."""
    trending_topic_alignment: float = 0.0
    seasonal_relevance: float = 0.0
    audience_activity_timing: float = 0.0
    content_freshness: float = 0.0
    time_sensitivity: float = 0.0
    overall_score: float = 0.0
    confidence: float = 0.0
    optimal_posting_windows: list[tuple[datetime, float]] = field(default_factory=list)
    timing_recommendations: list[str] = field(default_factory=list)


class OptimizationRecommendation(BaseModel):
    """Specific optimization recommendation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: OptimizationType
    priority: str = Field(description="high, medium, low")
    title: str
    description: str
    specific_actions: list[str] = Field(default_factory=list)
    expected_impact: float = Field(ge=0.0, le=1.0, description="Expected improvement")
    implementation_difficulty: str = Field(description="easy, medium, hard")
    estimated_time_to_implement: str = Field(description="Time estimate")
    success_metrics: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ResonanceAnalysis(BaseModel):
    """Comprehensive resonance analysis result."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    content_id: str | None = None
    audience_segment_id: str | None = None

    # Core resonance scores
    demographic_resonance: DemographicResonance
    behavioral_resonance: BehavioralResonance
    psychographic_resonance: PsychographicResonance
    content_complexity_fit: ContentComplexityFit
    platform_optimization: PlatformOptimization
    temporal_relevance: TemporalRelevance

    # Overall metrics
    overall_resonance_score: float = Field(ge=0.0, le=1.0)
    resonance_level: ResonanceLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    engagement_prediction: float = Field(ge=0.0, le=1.0)
    viral_potential_prediction: float = Field(ge=0.0, le=1.0)

    # Optimization insights
    optimization_recommendations: list[OptimizationRecommendation] = Field(default_factory=list)
    key_strengths: list[str] = Field(default_factory=list)
    major_gaps: list[str] = Field(default_factory=list)
    quick_wins: list[str] = Field(default_factory=list)

    # Metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    analysis_version: str = "1.0"
    processing_time_ms: float | None = None


class ContentAudienceMatch(BaseModel):
    """Content-audience pairing with resonance metrics."""
    content_id: str
    audience_segment_id: str
    resonance_score: float = Field(ge=0.0, le=1.0)
    engagement_prediction: float = Field(ge=0.0, le=1.0)
    conversion_prediction: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    match_quality: str = Field(description="excellent, good, moderate, poor")
    primary_resonance_drivers: list[str] = Field(default_factory=list)
    optimization_priority: str = Field(description="high, medium, low")


# Core Analyzers
class DemographicResonanceAnalyzer:
    """Analyzes demographic alignment between content and audience."""

    def __init__(self):
        self.age_group_weights = {
            AgeGroup.GEN_Z: {"informal": 0.9, "trending": 0.8, "visual": 0.9},
            AgeGroup.MILLENNIALS: {"professional": 0.8, "balanced": 0.9, "practical": 0.8},
            AgeGroup.GEN_X: {"authoritative": 0.8, "experienced": 0.9, "traditional": 0.7},
            AgeGroup.BOOMERS: {"formal": 0.9, "respectful": 0.9, "conservative": 0.8}
        }

        self.industry_expertise_indicators = {
            Industry.TECHNOLOGY: ["technical", "innovation", "digital", "software", "ai", "data"],
            Industry.FINANCE: ["financial", "investment", "market", "economic", "banking", "roi"],
            Industry.HEALTHCARE: ["medical", "patient", "clinical", "health", "treatment", "care"],
            Industry.EDUCATION: ["learning", "teaching", "academic", "student", "curriculum", "knowledge"],
            Industry.MARKETING: ["brand", "campaign", "audience", "engagement", "content", "analytics"]
        }

        self.experience_level_complexity = {
            ExperienceLevel.ENTRY: {"simple": 0.9, "basic": 0.8, "introductory": 0.9},
            ExperienceLevel.JUNIOR: {"intermediate": 0.8, "practical": 0.9, "guided": 0.7},
            ExperienceLevel.MID: {"advanced": 0.8, "strategic": 0.7, "comprehensive": 0.8},
            ExperienceLevel.SENIOR: {"expert": 0.9, "nuanced": 0.8, "sophisticated": 0.9},
            ExperienceLevel.EXECUTIVE: {"strategic": 0.9, "high-level": 0.9, "leadership": 0.9}
        }

    async def analyze_demographic_resonance(
        self,
        content: str,
        audience_demo: DemographicProfile,
        content_concepts: list[ConceptualEntity] = None
    ) -> DemographicResonance:
        """Analyze demographic resonance between content and audience."""
        try:
            resonance = DemographicResonance()
            content_lower = content.lower()

            # Age alignment analysis
            resonance.age_alignment = await self._analyze_age_alignment(
                content_lower, audience_demo.age_group, content_concepts
            )

            # Industry alignment analysis
            resonance.industry_alignment = await self._analyze_industry_alignment(
                content_lower, audience_demo.industry, content_concepts
            )

            # Experience level alignment
            resonance.experience_alignment = await self._analyze_experience_alignment(
                content_lower, audience_demo.job_level, content_concepts
            )

            # Location/cultural alignment
            resonance.location_alignment = await self._analyze_location_alignment(
                content_lower, audience_demo.location
            )

            # Role-specific alignment
            resonance.role_alignment = await self._analyze_role_alignment(
                content_lower, audience_demo.job_title, audience_demo.job_level
            )

            # Calculate overall demographic resonance
            resonance.overall_score = self._calculate_demographic_overall_score(resonance)
            resonance.confidence = self._calculate_demographic_confidence(resonance, audience_demo)

            # Generate optimization recommendations
            resonance.optimization_recommendations = await self._generate_demographic_optimizations(
                resonance, audience_demo, content_concepts
            )

            # Identify misalignment factors
            resonance.misalignment_factors = self._identify_demographic_misalignments(
                resonance, audience_demo
            )

            logger.debug(f"Demographic resonance analysis: {resonance.overall_score:.3f}")
            return resonance

        except Exception as e:
            logger.error(f"Error in demographic resonance analysis: {str(e)}")
            return DemographicResonance(confidence=0.0)

    async def _analyze_age_alignment(
        self,
        content: str,
        age_group: AgeGroup | None,
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze age group alignment."""
        if not age_group:
            return 0.5  # Neutral when unknown

        alignment_score = 0.0
        age_weights = self.age_group_weights.get(age_group, {})

        # Analyze content style alignment
        for style, weight in age_weights.items():
            if style in content:
                alignment_score += weight * 0.3

        # Analyze concept sophistication
        if concepts:
            concept_sophistication = sum(
                1 for c in concepts
                if c.concept_type in ["STRATEGY", "INSIGHT"] and age_group in [AgeGroup.GEN_X, AgeGroup.BOOMERS]
            ) / max(len(concepts), 1)
            alignment_score += concept_sophistication * 0.4

        # Language formality analysis
        formal_indicators = ["therefore", "furthermore", "consequently", "moreover"]
        informal_indicators = ["hey", "cool", "awesome", "totally", "literally"]

        formal_score = sum(1 for indicator in formal_indicators if indicator in content) / 4
        informal_score = sum(1 for indicator in informal_indicators if indicator in content) / 5

        if age_group in [AgeGroup.GEN_Z, AgeGroup.MILLENNIALS]:
            alignment_score += informal_score * 0.3
        else:
            alignment_score += formal_score * 0.3

        return min(1.0, alignment_score)

    async def _analyze_industry_alignment(
        self,
        content: str,
        industry: Industry | None,
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze industry-specific alignment."""
        if not industry:
            return 0.5  # Neutral when unknown

        alignment_score = 0.0
        industry_keywords = self.industry_expertise_indicators.get(industry, [])

        # Industry keyword presence
        keyword_matches = sum(1 for keyword in industry_keywords if keyword in content)
        alignment_score += min(1.0, keyword_matches / len(industry_keywords)) * 0.5

        # Concept relevance to industry
        if concepts:
            industry_relevant_concepts = 0
            for concept in concepts:
                if any(keyword in concept.text.lower() for keyword in industry_keywords):
                    industry_relevant_concepts += 1

            if concepts:
                alignment_score += (industry_relevant_concepts / len(concepts)) * 0.3

        # Industry-specific communication patterns
        if industry == Industry.TECHNOLOGY:
            tech_patterns = ["innovation", "scale", "optimize", "efficient", "disrupt"]
            pattern_score = sum(1 for pattern in tech_patterns if pattern in content) / len(tech_patterns)
            alignment_score += pattern_score * 0.2
        elif industry == Industry.FINANCE:
            finance_patterns = ["roi", "value", "investment", "returns", "growth", "margin"]
            pattern_score = sum(1 for pattern in finance_patterns if pattern in content) / len(finance_patterns)
            alignment_score += pattern_score * 0.2

        return min(1.0, alignment_score)

    async def _analyze_experience_alignment(
        self,
        content: str,
        experience_level: ExperienceLevel | None,
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze experience level alignment."""
        if not experience_level:
            return 0.5  # Neutral when unknown

        alignment_score = 0.0
        level_indicators = self.experience_level_complexity.get(experience_level, {})

        # Complexity indicators
        for indicator, weight in level_indicators.items():
            if indicator in content:
                alignment_score += weight * 0.3

        # Content sophistication analysis
        sophisticated_words = ["strategic", "nuanced", "comprehensive", "synthesize", "paradigm"]
        basic_words = ["simple", "easy", "basic", "introduction", "beginner"]

        sophisticated_score = sum(1 for word in sophisticated_words if word in content) / len(sophisticated_words)
        basic_score = sum(1 for word in basic_words if word in content) / len(basic_words)

        if experience_level in [ExperienceLevel.SENIOR, ExperienceLevel.EXECUTIVE]:
            alignment_score += sophisticated_score * 0.4
        elif experience_level in [ExperienceLevel.ENTRY, ExperienceLevel.JUNIOR]:
            alignment_score += basic_score * 0.4
        else:  # Mid-level
            alignment_score += (sophisticated_score + basic_score) / 2 * 0.4

        # Concept complexity analysis
        if concepts:
            complex_concepts = sum(
                1 for c in concepts
                if c.concept_type in ["STRATEGY", "FRAMEWORK", "METHODOLOGY"]
            )
            complexity_ratio = complex_concepts / len(concepts)

            if experience_level in [ExperienceLevel.SENIOR, ExperienceLevel.EXECUTIVE]:
                alignment_score += complexity_ratio * 0.3
            else:
                alignment_score += (1.0 - complexity_ratio) * 0.3

        return min(1.0, alignment_score)

    async def _analyze_location_alignment(self, content: str, location: str | None) -> float:
        """Analyze location/cultural alignment."""
        if not location:
            return 1.0  # Neutral when unknown

        # For now, implement basic timezone/region awareness
        # In production, this would include cultural nuances, local references, etc.

        # Check for time zone appropriate language
        time_sensitive_words = ["morning", "afternoon", "evening", "tonight", "today"]
        has_time_reference = any(word in content.lower() for word in time_sensitive_words)

        if has_time_reference:
            return 0.8  # Slight penalty for time-specific content

        return 1.0  # Default good alignment for location-neutral content

    async def _analyze_role_alignment(
        self,
        content: str,
        job_title: str | None,
        job_level: ExperienceLevel | None
    ) -> float:
        """Analyze role-specific alignment."""
        alignment_score = 0.5  # Default neutral

        if not job_title:
            return alignment_score

        job_title_lower = job_title.lower()
        content_lower = content.lower()

        # Role-specific keyword alignment
        role_keywords = {
            "manager": ["team", "leadership", "strategy", "management", "responsibility"],
            "developer": ["code", "technical", "programming", "development", "solution"],
            "analyst": ["data", "analysis", "insights", "metrics", "research"],
            "director": ["strategic", "vision", "leadership", "organizational", "executive"],
            "consultant": ["advisory", "recommendations", "expertise", "solutions", "client"]
        }

        for role, keywords in role_keywords.items():
            if role in job_title_lower:
                keyword_matches = sum(1 for keyword in keywords if keyword in content_lower)
                alignment_score += (keyword_matches / len(keywords)) * 0.5
                break

        return min(1.0, alignment_score)

    def _calculate_demographic_overall_score(self, resonance: DemographicResonance) -> float:
        """Calculate overall demographic resonance score."""
        scores = [
            resonance.age_alignment * 0.25,
            resonance.industry_alignment * 0.30,
            resonance.experience_alignment * 0.25,
            resonance.location_alignment * 0.10,
            resonance.role_alignment * 0.10
        ]
        return sum(scores)

    def _calculate_demographic_confidence(
        self,
        resonance: DemographicResonance,
        demo_profile: DemographicProfile
    ) -> float:
        """Calculate confidence in demographic analysis."""
        confidence_factors = [
            1.0 if demo_profile.age_group else 0.0,
            1.0 if demo_profile.industry else 0.0,
            1.0 if demo_profile.job_level else 0.0,
            1.0 if demo_profile.location else 0.0,
            1.0 if demo_profile.job_title else 0.0
        ]

        data_completeness = sum(confidence_factors) / len(confidence_factors)

        # Adjust for score consistency
        score_consistency = 1.0 - statistics.stdev([
            resonance.age_alignment,
            resonance.industry_alignment,
            resonance.experience_alignment,
            resonance.location_alignment,
            resonance.role_alignment
        ]) if len(set([
            resonance.age_alignment,
            resonance.industry_alignment,
            resonance.experience_alignment,
            resonance.location_alignment,
            resonance.role_alignment
        ])) > 1 else 1.0

        return (data_completeness * 0.7 + score_consistency * 0.3)

    async def _generate_demographic_optimizations(
        self,
        resonance: DemographicResonance,
        demo_profile: DemographicProfile,
        concepts: list[ConceptualEntity] = None
    ) -> list[str]:
        """Generate demographic optimization recommendations."""
        recommendations = []

        if resonance.age_alignment < 0.6 and demo_profile.age_group:
            if demo_profile.age_group in [AgeGroup.GEN_Z, AgeGroup.MILLENNIALS]:
                recommendations.append("Use more informal, conversational tone")
                recommendations.append("Include trending references and current terminology")
            else:
                recommendations.append("Adopt more formal, professional tone")
                recommendations.append("Focus on proven experience and established methods")

        if resonance.industry_alignment < 0.6 and demo_profile.industry:
            industry_keywords = self.industry_expertise_indicators.get(demo_profile.industry, [])
            recommendations.append(f"Incorporate more {demo_profile.industry.value}-specific terminology")
            recommendations.append("Reference industry-relevant examples and case studies")

        if resonance.experience_alignment < 0.6 and demo_profile.job_level:
            if demo_profile.job_level in [ExperienceLevel.ENTRY, ExperienceLevel.JUNIOR]:
                recommendations.append("Simplify technical concepts and provide more context")
                recommendations.append("Include step-by-step guidance and examples")
            else:
                recommendations.append("Increase content sophistication and strategic depth")
                recommendations.append("Assume higher baseline knowledge and focus on insights")

        return recommendations

    def _identify_demographic_misalignments(
        self,
        resonance: DemographicResonance,
        demo_profile: DemographicProfile
    ) -> list[str]:
        """Identify specific demographic misalignment factors."""
        misalignments = []

        if resonance.age_alignment < 0.4:
            misalignments.append(f"Content style doesn't match {demo_profile.age_group.value if demo_profile.age_group else 'unknown'} preferences")

        if resonance.industry_alignment < 0.4:
            misalignments.append(f"Limited {demo_profile.industry.value if demo_profile.industry else 'industry'}-specific relevance")

        if resonance.experience_alignment < 0.4:
            misalignments.append(f"Content complexity mismatch for {demo_profile.job_level.value if demo_profile.job_level else 'unknown'} level")

        return misalignments


class BehavioralResonanceAnalyzer:
    """Analyzes behavioral pattern alignment between content and audience."""

    def __init__(self):
        self.engagement_prediction_weights = {
            EngagementType.LIKE: 0.15,
            EngagementType.COMMENT: 0.25,
            EngagementType.SHARE: 0.30,
            EngagementType.SAVE: 0.15,
            EngagementType.CLICK: 0.10,
            EngagementType.VIEW: 0.05
        }

        self.content_length_preferences = {
            "short": (0, 100),
            "medium": (100, 500),
            "long": (500, float('inf'))
        }

        self.optimal_posting_patterns = {
            "professional": [8, 9, 12, 13, 17, 18],  # Business hours
            "social": [18, 19, 20, 21],  # Evening hours
            "educational": [9, 10, 14, 15],  # Learning hours
            "casual": [12, 13, 19, 20, 21]  # Lunch and evening
        }

    async def analyze_behavioral_resonance(
        self,
        content: str,
        audience_behavior: BehaviorProfile,
        content_concepts: list[ConceptualEntity] = None,
        posting_time: datetime | None = None
    ) -> BehavioralResonance:
        """Analyze behavioral resonance between content and audience."""
        try:
            resonance = BehavioralResonance()

            # Engagement pattern fit analysis
            resonance.engagement_pattern_fit = await self._analyze_engagement_pattern_fit(
                content, audience_behavior.engagement_patterns, content_concepts
            )

            # Content preference fit
            resonance.content_preference_fit = await self._analyze_content_preference_fit(
                content, audience_behavior.content_preferences, content_concepts
            )

            # Platform usage fit
            resonance.platform_usage_fit = await self._analyze_platform_usage_fit(
                content, audience_behavior.platform_usage
            )

            # Interaction style fit
            resonance.interaction_style_fit = await self._analyze_interaction_style_fit(
                content, audience_behavior.interaction_style, content_concepts
            )

            # Content length fit
            resonance.content_length_fit = await self._analyze_content_length_fit(
                content, audience_behavior.content_length_preference
            )

            # Timing fit analysis
            resonance.timing_fit = await self._analyze_timing_fit(
                posting_time, audience_behavior.optimal_posting_times
            )

            # Calculate overall behavioral resonance
            resonance.overall_score = self._calculate_behavioral_overall_score(resonance)
            resonance.confidence = self._calculate_behavioral_confidence(resonance, audience_behavior)

            # Generate engagement predictions
            resonance.engagement_predictions = await self._predict_engagement_types(
                resonance, audience_behavior, content_concepts
            )

            # Generate optimization recommendations
            resonance.optimization_recommendations = await self._generate_behavioral_optimizations(
                resonance, audience_behavior, content_concepts
            )

            logger.debug(f"Behavioral resonance analysis: {resonance.overall_score:.3f}")
            return resonance

        except Exception as e:
            logger.error(f"Error in behavioral resonance analysis: {str(e)}")
            return BehavioralResonance(confidence=0.0)

    async def _analyze_engagement_pattern_fit(
        self,
        content: str,
        engagement_patterns: dict[EngagementType, float],
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze how well content matches audience engagement patterns."""
        if not engagement_patterns:
            return 0.5  # Neutral when unknown

        fit_score = 0.0
        content_lower = content.lower()

        # Analyze content features that drive different engagement types
        engagement_drivers = {
            EngagementType.LIKE: ["agree", "love", "appreciate", "exactly", "yes"],
            EngagementType.COMMENT: ["thoughts", "opinion", "what do you think", "discuss", "?"],
            EngagementType.SHARE: ["everyone should", "important", "valuable", "worth sharing"],
            EngagementType.SAVE: ["tips", "reference", "guide", "remember", "bookmark"],
            EngagementType.CLICK: ["link", "read more", "learn more", "check out"],
            EngagementType.VIEW: ["watch", "see", "look at", "visual", "image"]
        }

        for engagement_type, audience_propensity in engagement_patterns.items():
            drivers = engagement_drivers.get(engagement_type, [])
            content_driver_score = sum(1 for driver in drivers if driver in content_lower) / len(drivers)

            # Weight by audience propensity for this engagement type
            fit_score += content_driver_score * audience_propensity * self.engagement_prediction_weights[engagement_type]

        # Analyze concept-based engagement potential
        if concepts:
            high_engagement_concepts = [c for c in concepts if c.concept_type in ["HOT_TAKE", "CONTROVERSY", "QUESTION"]]
            if high_engagement_concepts:
                fit_score += len(high_engagement_concepts) / len(concepts) * 0.3

        return min(1.0, fit_score)

    async def _analyze_content_preference_fit(
        self,
        content: str,
        content_preferences: dict[ContentPreference, float],
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze content preference alignment."""
        if not content_preferences:
            return 0.5  # Neutral when unknown

        fit_score = 0.0
        content_lower = content.lower()

        # Content preference indicators
        preference_indicators = {
            ContentPreference.EDUCATIONAL: ["learn", "how to", "guide", "tutorial", "tip", "knowledge"],
            ContentPreference.ENTERTAINMENT: ["fun", "funny", "amusing", "entertaining", "humor"],
            ContentPreference.NEWS: ["news", "update", "breaking", "announcement", "latest"],
            ContentPreference.INSPIRATIONAL: ["inspire", "motivation", "success", "achieve", "dream"],
            ContentPreference.PROFESSIONAL: ["career", "business", "professional", "industry", "leadership"],
            ContentPreference.PERSONAL: ["personal", "story", "experience", "journey", "life"],
            ContentPreference.CONTROVERSIAL: ["controversial", "unpopular", "against", "disagree"],
            ContentPreference.TRENDING: ["trending", "hot", "viral", "popular", "everyone"]
        }

        for preference, audience_score in content_preferences.items():
            indicators = preference_indicators.get(preference, [])
            content_indicator_score = sum(1 for indicator in indicators if indicator in content_lower) / len(indicators)
            fit_score += content_indicator_score * audience_score

        # Normalize by total preference weights
        total_preference_weight = sum(content_preferences.values())
        if total_preference_weight > 0:
            fit_score = fit_score / total_preference_weight

        return min(1.0, fit_score)

    async def _analyze_platform_usage_fit(
        self,
        content: str,
        platform_usage: dict[Platform, float]
    ) -> float:
        """Analyze platform-specific content fit."""
        if not platform_usage:
            return 0.5  # Neutral when unknown

        # For now, analyze general platform compatibility
        # In production, this would be more sophisticated based on specific platform

        primary_platform = max(platform_usage.items(), key=lambda x: x[1])[0] if platform_usage else Platform.GENERAL

        platform_fit_scores = {
            Platform.LINKEDIN: self._analyze_linkedin_fit(content),
            Platform.TWITTER: self._analyze_twitter_fit(content),
            Platform.GENERAL: 0.7  # Default moderate fit
        }

        return platform_fit_scores.get(primary_platform, 0.5)

    def _analyze_linkedin_fit(self, content: str) -> float:
        """Analyze LinkedIn-specific content fit."""
        linkedin_indicators = [
            "professional", "career", "business", "industry", "leadership",
            "experience", "skills", "networking", "growth", "opportunity"
        ]

        content_lower = content.lower()
        indicator_score = sum(1 for indicator in linkedin_indicators if indicator in content_lower) / len(linkedin_indicators)

        # Length considerations for LinkedIn
        length_score = 1.0
        if len(content) > 1300:  # LinkedIn posts are typically shorter
            length_score = 0.7
        elif len(content) < 50:  # Too short for meaningful professional content
            length_score = 0.6

        return (indicator_score * 0.7 + length_score * 0.3)

    def _analyze_twitter_fit(self, content: str) -> float:
        """Analyze Twitter-specific content fit."""
        twitter_indicators = [
            "quick", "brief", "update", "breaking", "hot take", "thread",
            "viral", "trending", "#", "@"
        ]

        content_lower = content.lower()
        indicator_score = sum(1 for indicator in twitter_indicators if indicator in content_lower) / len(twitter_indicators)

        # Length considerations for Twitter
        length_score = 1.0
        if len(content) > 280:  # Twitter character limit consideration
            length_score = 0.5
        elif len(content) < 20:  # Too short even for Twitter
            length_score = 0.7

        return (indicator_score * 0.6 + length_score * 0.4)

    async def _analyze_interaction_style_fit(
        self,
        content: str,
        interaction_style: str | None,
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze interaction style fit."""
        if not interaction_style:
            return 0.5  # Neutral when unknown

        style_indicators = {
            "lurker": ["observe", "watch", "read", "follow", "see"],
            "commenter": ["thoughts", "opinion", "discuss", "feedback", "what do you think"],
            "sharer": ["share", "spread", "everyone", "important", "worth sharing"],
            "creator": ["create", "build", "make", "develop", "produce"]
        }

        indicators = style_indicators.get(interaction_style, [])
        content_lower = content.lower()

        style_fit = sum(1 for indicator in indicators if indicator in content_lower) / len(indicators) if indicators else 0.5

        # Adjust based on content concepts
        if concepts and interaction_style == "creator":
            creative_concepts = [c for c in concepts if c.concept_type in ["INNOVATION", "STRATEGY", "FRAMEWORK"]]
            if creative_concepts:
                style_fit += (len(creative_concepts) / len(concepts)) * 0.3

        return min(1.0, style_fit)

    async def _analyze_content_length_fit(
        self,
        content: str,
        preferred_length: str | None
    ) -> float:
        """Analyze content length preferences."""
        if not preferred_length:
            return 0.8  # Assume moderate fit when unknown

        content_length = len(content)
        length_ranges = self.content_length_preferences.get(preferred_length, (0, float('inf')))

        if length_ranges[0] <= content_length <= length_ranges[1]:
            return 1.0  # Perfect fit
        elif preferred_length == "short" and content_length > length_ranges[1]:
            # Penalty for too long when short preferred
            excess_ratio = (content_length - length_ranges[1]) / length_ranges[1]
            return max(0.2, 1.0 - excess_ratio * 0.5)
        elif preferred_length == "long" and content_length < length_ranges[0]:
            # Penalty for too short when long preferred
            deficit_ratio = (length_ranges[0] - content_length) / length_ranges[0]
            return max(0.2, 1.0 - deficit_ratio * 0.5)
        else:
            return 0.6  # Moderate mismatch

    async def _analyze_timing_fit(
        self,
        posting_time: datetime | None,
        optimal_hours: list[int] | None
    ) -> float:
        """Analyze posting time fit with audience activity patterns."""
        if not posting_time or not optimal_hours:
            return 0.7  # Neutral when unknown

        posting_hour = posting_time.hour

        if posting_hour in optimal_hours:
            return 1.0  # Perfect timing

        # Calculate distance to nearest optimal hour
        hour_distances = [min(abs(posting_hour - hour), abs(posting_hour - hour + 24), abs(posting_hour - hour - 24)) for hour in optimal_hours]
        min_distance = min(hour_distances)

        # Score based on proximity (closer = better)
        if min_distance <= 1:
            return 0.8
        elif min_distance <= 2:
            return 0.6
        elif min_distance <= 3:
            return 0.4
        else:
            return 0.2

    def _calculate_behavioral_overall_score(self, resonance: BehavioralResonance) -> float:
        """Calculate overall behavioral resonance score."""
        scores = [
            resonance.engagement_pattern_fit * 0.25,
            resonance.content_preference_fit * 0.25,
            resonance.platform_usage_fit * 0.20,
            resonance.interaction_style_fit * 0.15,
            resonance.content_length_fit * 0.10,
            resonance.timing_fit * 0.05
        ]
        return sum(scores)

    def _calculate_behavioral_confidence(
        self,
        resonance: BehavioralResonance,
        behavior_profile: BehaviorProfile
    ) -> float:
        """Calculate confidence in behavioral analysis."""
        confidence_factors = [
            1.0 if behavior_profile.engagement_patterns else 0.0,
            1.0 if behavior_profile.content_preferences else 0.0,
            1.0 if behavior_profile.platform_usage else 0.0,
            1.0 if behavior_profile.interaction_style else 0.0,
            1.0 if behavior_profile.content_length_preference else 0.0,
            1.0 if behavior_profile.optimal_posting_times else 0.0
        ]

        return sum(confidence_factors) / len(confidence_factors)

    async def _predict_engagement_types(
        self,
        resonance: BehavioralResonance,
        behavior_profile: BehaviorProfile,
        concepts: list[ConceptualEntity] = None
    ) -> dict[EngagementType, float]:
        """Predict likelihood of different engagement types."""
        predictions = {}

        if not behavior_profile.engagement_patterns:
            return predictions

        base_engagement_score = resonance.overall_score

        for engagement_type, audience_propensity in behavior_profile.engagement_patterns.items():
            # Base prediction from audience propensity and content fit
            prediction = audience_propensity * base_engagement_score

            # Adjust based on content characteristics
            if engagement_type == EngagementType.COMMENT and concepts:
                question_concepts = [c for c in concepts if c.concept_type == "QUESTION"]
                if question_concepts:
                    prediction *= 1.3  # Questions drive more comments

            if engagement_type == EngagementType.SHARE and concepts:
                viral_concepts = [c for c in concepts if c.concept_type in ["HOT_TAKE", "INSIGHT", "CONTROVERSY"]]
                if viral_concepts:
                    prediction *= 1.2  # Shareable content types

            predictions[engagement_type] = min(1.0, prediction)

        return predictions

    async def _generate_behavioral_optimizations(
        self,
        resonance: BehavioralResonance,
        behavior_profile: BehaviorProfile,
        concepts: list[ConceptualEntity] = None
    ) -> list[str]:
        """Generate behavioral optimization recommendations."""
        recommendations = []

        if resonance.engagement_pattern_fit < 0.6:
            top_engagement = max(behavior_profile.engagement_patterns.items(), key=lambda x: x[1]) if behavior_profile.engagement_patterns else None
            if top_engagement:
                recommendations.append(f"Optimize content to encourage {top_engagement[0].value} behavior")

        if resonance.content_preference_fit < 0.6:
            top_preference = max(behavior_profile.content_preferences.items(), key=lambda x: x[1]) if behavior_profile.content_preferences else None
            if top_preference:
                recommendations.append(f"Align more closely with {top_preference[0].value} content preferences")

        if resonance.content_length_fit < 0.6 and behavior_profile.content_length_preference:
            recommendations.append(f"Adjust content length to match {behavior_profile.content_length_preference} preference")

        if resonance.timing_fit < 0.6 and behavior_profile.optimal_posting_times:
            optimal_times = behavior_profile.optimal_posting_times
            recommendations.append(f"Post during optimal hours: {optimal_times}")

        return recommendations


class PsychographicResonanceAnalyzer:
    """Analyzes psychographic alignment between content and audience."""

    def __init__(self):
        self.personality_content_mapping = {
            PersonalityTrait.ANALYTICAL: {
                "keywords": ["data", "analysis", "evidence", "research", "logical", "objective"],
                "concepts": ["INSIGHT", "RESEARCH", "ANALYSIS"],
                "style": "data-driven and objective"
            },
            PersonalityTrait.CREATIVE: {
                "keywords": ["creative", "innovative", "original", "artistic", "inspiration"],
                "concepts": ["INNOVATION", "CREATIVITY", "VISION"],
                "style": "imaginative and original"
            },
            PersonalityTrait.SOCIAL: {
                "keywords": ["community", "together", "collaborate", "people", "relationship"],
                "concepts": ["COLLABORATION", "COMMUNITY", "NETWORKING"],
                "style": "collaborative and people-focused"
            },
            PersonalityTrait.COMPETITIVE: {
                "keywords": ["win", "best", "achieve", "compete", "excel", "performance"],
                "concepts": ["ACHIEVEMENT", "SUCCESS", "PERFORMANCE"],
                "style": "achievement-oriented and competitive"
            },
            PersonalityTrait.INNOVATIVE: {
                "keywords": ["innovation", "future", "disrupt", "transform", "breakthrough"],
                "concepts": ["INNOVATION", "DISRUPTION", "TRANSFORMATION"],
                "style": "forward-thinking and disruptive"
            }
        }

        self.value_content_mapping = {
            "authenticity": ["authentic", "genuine", "real", "honest", "transparent"],
            "growth": ["growth", "learn", "develop", "improve", "progress", "evolve"],
            "impact": ["impact", "difference", "change", "influence", "meaningful"],
            "freedom": ["freedom", "independence", "autonomy", "flexible", "choice"],
            "security": ["security", "stable", "reliable", "consistent", "safe"],
            "recognition": ["recognition", "appreciate", "acknowledge", "valued", "respect"],
            "excellence": ["excellence", "quality", "superior", "best", "perfection"]
        }

        self.motivation_triggers = {
            "achievement": ["goal", "accomplish", "succeed", "target", "milestone"],
            "affiliation": ["belong", "connect", "community", "relationship", "team"],
            "power": ["influence", "control", "leadership", "authority", "impact"],
            "learning": ["learn", "knowledge", "understand", "discover", "insight"],
            "helping": ["help", "support", "serve", "contribute", "assist"]
        }

    async def analyze_psychographic_resonance(
        self,
        content: str,
        audience_psycho: PsychographicProfile,
        content_concepts: list[ConceptualEntity] = None
    ) -> PsychographicResonance:
        """Analyze psychographic resonance between content and audience."""
        try:
            resonance = PsychographicResonance()
            content_lower = content.lower()

            # Personality alignment analysis
            resonance.personality_alignment = await self._analyze_personality_alignment(
                content_lower, audience_psycho.personality_traits, content_concepts
            )

            # Values alignment analysis
            resonance.values_alignment = await self._analyze_values_alignment(
                content_lower, audience_psycho.values
            )

            # Interests alignment analysis
            resonance.interests_alignment = await self._analyze_interests_alignment(
                content_lower, audience_psycho.interests, content_concepts
            )

            # Motivation alignment analysis
            resonance.motivation_alignment = await self._analyze_motivation_alignment(
                content_lower, audience_psycho.motivations
            )

            # Communication style fit
            resonance.communication_style_fit = await self._analyze_communication_style_fit(
                content, audience_psycho.communication_style
            )

            # Calculate overall psychographic resonance
            resonance.overall_score = self._calculate_psychographic_overall_score(resonance)
            resonance.confidence = self._calculate_psychographic_confidence(resonance, audience_psycho)

            # Identify psychological triggers and resonance drivers
            resonance.psychological_triggers = await self._identify_psychological_triggers(
                content_lower, audience_psycho, content_concepts
            )
            resonance.resonance_drivers = await self._identify_resonance_drivers(
                resonance, audience_psycho
            )

            # Generate optimization recommendations
            resonance.optimization_recommendations = await self._generate_psychographic_optimizations(
                resonance, audience_psycho, content_concepts
            )

            logger.debug(f"Psychographic resonance analysis: {resonance.overall_score:.3f}")
            return resonance

        except Exception as e:
            logger.error(f"Error in psychographic resonance analysis: {str(e)}")
            return PsychographicResonance(confidence=0.0)

    async def _analyze_personality_alignment(
        self,
        content: str,
        personality_traits: dict[PersonalityTrait, float],
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze personality trait alignment."""
        if not personality_traits:
            return 0.5  # Neutral when unknown

        alignment_score = 0.0
        total_weight = sum(personality_traits.values())

        for trait, audience_strength in personality_traits.items():
            trait_mapping = self.personality_content_mapping.get(trait, {})

            # Keyword alignment
            keywords = trait_mapping.get("keywords", [])
            keyword_score = sum(1 for keyword in keywords if keyword in content) / len(keywords) if keywords else 0

            # Concept alignment
            if concepts:
                relevant_concepts = trait_mapping.get("concepts", [])
                concept_matches = sum(1 for c in concepts if c.concept_type in relevant_concepts)
                concept_score = concept_matches / len(concepts) if concepts else 0
            else:
                concept_score = 0

            # Combined trait alignment weighted by audience strength
            trait_alignment = (keyword_score * 0.6 + concept_score * 0.4) * audience_strength
            alignment_score += trait_alignment

        return min(1.0, alignment_score / total_weight) if total_weight > 0 else 0.5

    async def _analyze_values_alignment(
        self,
        content: str,
        values: dict[str, float]
    ) -> float:
        """Analyze values alignment."""
        if not values:
            return 0.5  # Neutral when unknown

        alignment_score = 0.0
        total_weight = sum(values.values())

        for value, audience_importance in values.items():
            value_keywords = self.value_content_mapping.get(value, [])
            keyword_matches = sum(1 for keyword in value_keywords if keyword in content)
            value_score = keyword_matches / len(value_keywords) if value_keywords else 0

            # Weight by audience importance of this value
            weighted_score = value_score * audience_importance
            alignment_score += weighted_score

        return min(1.0, alignment_score / total_weight) if total_weight > 0 else 0.5

    async def _analyze_interests_alignment(
        self,
        content: str,
        interests: dict[str, float],
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze interests alignment."""
        if not interests:
            return 0.5  # Neutral when unknown

        alignment_score = 0.0
        total_weight = sum(interests.values())

        # Define interest keywords
        interest_keywords = {
            "technology": ["tech", "ai", "software", "digital", "innovation", "coding"],
            "business": ["business", "entrepreneurship", "startup", "finance", "strategy"],
            "leadership": ["leadership", "management", "team", "vision", "influence"],
            "personal_development": ["growth", "learning", "skills", "development", "improvement"],
            "health": ["health", "fitness", "wellness", "exercise", "nutrition", "wellbeing"],
            "travel": ["travel", "explore", "adventure", "culture", "world", "journey"],
            "creativity": ["art", "design", "creative", "music", "writing", "artistic"]
        }

        for interest, audience_strength in interests.items():
            keywords = interest_keywords.get(interest, [])
            keyword_matches = sum(1 for keyword in keywords if keyword in content)
            interest_score = keyword_matches / len(keywords) if keywords else 0

            # Also check concepts for interest relevance
            if concepts and interest == "technology":
                tech_concepts = [c for c in concepts if "tech" in c.text.lower() or "innovation" in c.text.lower()]
                if tech_concepts:
                    interest_score += len(tech_concepts) / len(concepts) * 0.5

            weighted_score = interest_score * audience_strength
            alignment_score += weighted_score

        return min(1.0, alignment_score / total_weight) if total_weight > 0 else 0.5

    async def _analyze_motivation_alignment(
        self,
        content: str,
        motivations: dict[str, float]
    ) -> float:
        """Analyze motivation alignment."""
        if not motivations:
            return 0.5  # Neutral when unknown

        alignment_score = 0.0
        total_weight = sum(motivations.values())

        for motivation, audience_strength in motivations.items():
            triggers = self.motivation_triggers.get(motivation, [])
            trigger_matches = sum(1 for trigger in triggers if trigger in content)
            motivation_score = trigger_matches / len(triggers) if triggers else 0

            weighted_score = motivation_score * audience_strength
            alignment_score += weighted_score

        return min(1.0, alignment_score / total_weight) if total_weight > 0 else 0.5

    async def _analyze_communication_style_fit(
        self,
        content: str,
        preferred_style: str | None
    ) -> float:
        """Analyze communication style fit."""
        if not preferred_style:
            return 0.7  # Neutral when unknown

        content_lower = content.lower()

        style_indicators = {
            "formal": {
                "keywords": ["therefore", "furthermore", "consequently", "however", "moreover"],
                "patterns": ["complex sentences", "technical terminology", "structured"]
            },
            "casual": {
                "keywords": ["hey", "cool", "awesome", "totally", "yeah", "definitely"],
                "patterns": ["contractions", "informal language", "conversational"]
            },
            "professional": {
                "keywords": ["expertise", "experience", "professional", "industry", "strategic"],
                "patterns": ["business terminology", "formal but accessible"]
            }
        }

        if preferred_style in style_indicators:
            indicators = style_indicators[preferred_style]
            keywords = indicators.get("keywords", [])
            keyword_score = sum(1 for keyword in keywords if keyword in content_lower) / len(keywords)

            # Additional style analysis
            if preferred_style == "formal":
                # Check for formal sentence structure
                sentence_count = len([s for s in content.split('.') if s.strip()])
                avg_sentence_length = len(content.split()) / sentence_count if sentence_count > 0 else 0
                formal_bonus = min(0.3, avg_sentence_length / 20) if avg_sentence_length > 15 else 0
                return min(1.0, keyword_score + formal_bonus)

            elif preferred_style == "casual":
                # Check for contractions and informal patterns
                contractions = ["'re", "'ve", "'ll", "'d", "can't", "won't", "don't"]
                contraction_score = sum(1 for contraction in contractions if contraction in content) / 10
                return min(1.0, keyword_score + contraction_score)

            return keyword_score

        return 0.5  # Default neutral fit

    def _calculate_psychographic_overall_score(self, resonance: PsychographicResonance) -> float:
        """Calculate overall psychographic resonance score."""
        scores = [
            resonance.personality_alignment * 0.25,
            resonance.values_alignment * 0.25,
            resonance.interests_alignment * 0.20,
            resonance.motivation_alignment * 0.20,
            resonance.communication_style_fit * 0.10
        ]
        return sum(scores)

    def _calculate_psychographic_confidence(
        self,
        resonance: PsychographicResonance,
        psycho_profile: PsychographicProfile
    ) -> float:
        """Calculate confidence in psychographic analysis."""
        confidence_factors = [
            1.0 if psycho_profile.personality_traits else 0.0,
            1.0 if psycho_profile.values else 0.0,
            1.0 if psycho_profile.interests else 0.0,
            1.0 if psycho_profile.motivations else 0.0,
            1.0 if psycho_profile.communication_style else 0.0
        ]

        return sum(confidence_factors) / len(confidence_factors)

    async def _identify_psychological_triggers(
        self,
        content: str,
        audience_psycho: PsychographicProfile,
        concepts: list[ConceptualEntity] = None
    ) -> list[str]:
        """Identify psychological triggers in content that resonate with audience."""
        triggers = []

        # Personality-based triggers
        for trait, strength in audience_psycho.personality_traits.items():
            if strength > 0.6:  # Strong trait
                trait_mapping = self.personality_content_mapping.get(trait, {})
                keywords = trait_mapping.get("keywords", [])
                if any(keyword in content for keyword in keywords):
                    triggers.append(f"{trait.value} personality trigger activated")

        # Value-based triggers
        for value, importance in audience_psycho.values.items():
            if importance > 0.6:  # Important value
                value_keywords = self.value_content_mapping.get(value, [])
                if any(keyword in content for keyword in value_keywords):
                    triggers.append(f"{value} value resonance")

        # Motivation-based triggers
        for motivation, strength in audience_psycho.motivations.items():
            if strength > 0.6:  # Strong motivation
                motivation_keywords = self.motivation_triggers.get(motivation, [])
                if any(keyword in content for keyword in motivation_keywords):
                    triggers.append(f"{motivation} motivation trigger")

        return triggers

    async def _identify_resonance_drivers(
        self,
        resonance: PsychographicResonance,
        audience_psycho: PsychographicProfile
    ) -> list[str]:
        """Identify key drivers of psychographic resonance."""
        drivers = []

        if resonance.personality_alignment > 0.7:
            drivers.append("Strong personality trait alignment")

        if resonance.values_alignment > 0.7:
            drivers.append("Core values alignment")

        if resonance.interests_alignment > 0.7:
            drivers.append("Interest area relevance")

        if resonance.motivation_alignment > 0.7:
            drivers.append("Motivational trigger activation")

        if resonance.communication_style_fit > 0.8:
            drivers.append("Communication style match")

        return drivers

    async def _generate_psychographic_optimizations(
        self,
        resonance: PsychographicResonance,
        audience_psycho: PsychographicProfile,
        concepts: list[ConceptualEntity] = None
    ) -> list[str]:
        """Generate psychographic optimization recommendations."""
        recommendations = []

        if resonance.personality_alignment < 0.6:
            top_trait = max(audience_psycho.personality_traits.items(), key=lambda x: x[1]) if audience_psycho.personality_traits else None
            if top_trait:
                trait_mapping = self.personality_content_mapping.get(top_trait[0], {})
                style = trait_mapping.get("style", "")
                if style:
                    recommendations.append(f"Adopt more {style} approach")

        if resonance.values_alignment < 0.6:
            top_value = max(audience_psycho.values.items(), key=lambda x: x[1]) if audience_psycho.values else None
            if top_value:
                recommendations.append(f"Emphasize {top_value[0]} more prominently")

        if resonance.interests_alignment < 0.6:
            top_interest = max(audience_psycho.interests.items(), key=lambda x: x[1]) if audience_psycho.interests else None
            if top_interest:
                recommendations.append(f"Include more {top_interest[0]}-related content")

        if resonance.motivation_alignment < 0.6:
            top_motivation = max(audience_psycho.motivations.items(), key=lambda x: x[1]) if audience_psycho.motivations else None
            if top_motivation:
                recommendations.append(f"Appeal to {top_motivation[0]} motivation")

        if resonance.communication_style_fit < 0.6 and audience_psycho.communication_style:
            recommendations.append(f"Adjust to {audience_psycho.communication_style} communication style")

        return recommendations


class ComplexityAnalyzer:
    """Analyzes content complexity and audience sophistication matching."""

    def __init__(self):
        self.readability_metrics = {
            "syllable_complexity": 0.2,
            "sentence_length": 0.2,
            "word_difficulty": 0.2,
            "concept_density": 0.2,
            "technical_depth": 0.2
        }

        self.difficulty_indicators = {
            "basic": ["simple", "easy", "basic", "introduction", "beginner", "start"],
            "intermediate": ["understand", "learn", "develop", "improve", "practice"],
            "advanced": ["complex", "sophisticated", "advanced", "expert", "master"],
            "expert": ["nuanced", "intricate", "paradigm", "framework", "methodology"]
        }

    async def analyze_content_complexity_fit(
        self,
        content: str,
        audience_demo: DemographicProfile,
        content_concepts: list[ConceptualEntity] = None
    ) -> ContentComplexityFit:
        """Analyze content complexity fit with audience sophistication."""
        try:
            complexity_fit = ContentComplexityFit()

            # Calculate content complexity metrics
            complexity_fit.complexity_metrics = await self._calculate_complexity_metrics(content, content_concepts)

            # Determine audience sophistication level
            audience_sophistication = self._determine_audience_sophistication(audience_demo)

            # Analyze individual fit components
            complexity_fit.reading_level_fit = await self._analyze_reading_level_fit(
                complexity_fit.complexity_metrics, audience_sophistication
            )

            complexity_fit.technical_depth_fit = await self._analyze_technical_depth_fit(
                content, audience_demo.industry, audience_demo.job_level, content_concepts
            )

            complexity_fit.concept_density_fit = await self._analyze_concept_density_fit(
                content_concepts, audience_sophistication
            )

            complexity_fit.expertise_level_fit = await self._analyze_expertise_level_fit(
                content, audience_demo.job_level, content_concepts
            )

            complexity_fit.cognitive_load_fit = await self._analyze_cognitive_load_fit(
                complexity_fit.complexity_metrics, audience_sophistication
            )

            # Calculate overall complexity fit
            complexity_fit.overall_score = self._calculate_complexity_overall_score(complexity_fit)
            complexity_fit.confidence = self._calculate_complexity_confidence(complexity_fit, audience_demo)

            # Generate adjustment recommendations
            complexity_fit.adjustment_recommendations = await self._generate_complexity_adjustments(
                complexity_fit, audience_sophistication, content_concepts
            )

            logger.debug(f"Content complexity analysis: {complexity_fit.overall_score:.3f}")
            return complexity_fit

        except Exception as e:
            logger.error(f"Error in complexity analysis: {str(e)}")
            return ContentComplexityFit(confidence=0.0)

    async def _calculate_complexity_metrics(
        self,
        content: str,
        concepts: list[ConceptualEntity] = None
    ) -> dict[str, float]:
        """Calculate various complexity metrics for content."""
        metrics = {}

        words = content.split()
        sentences = [s.strip() for s in content.split('.') if s.strip()]

        # Basic readability metrics
        metrics["word_count"] = len(words)
        metrics["sentence_count"] = len(sentences)
        metrics["avg_words_per_sentence"] = len(words) / len(sentences) if sentences else 0

        # Syllable complexity (approximation)
        syllable_count = sum(self._estimate_syllables(word) for word in words)
        metrics["avg_syllables_per_word"] = syllable_count / len(words) if words else 0

        # Word difficulty (based on length as proxy)
        long_words = [word for word in words if len(word) > 6]
        metrics["long_word_ratio"] = len(long_words) / len(words) if words else 0

        # Technical terminology density
        technical_words = self._count_technical_words(content)
        metrics["technical_density"] = technical_words / len(words) if words else 0

        # Concept density
        if concepts:
            metrics["concepts_per_100_words"] = (len(concepts) / len(words)) * 100 if words else 0
            metrics["complex_concept_ratio"] = len([c for c in concepts if c.concept_type in ["STRATEGY", "FRAMEWORK", "METHODOLOGY"]]) / len(concepts)
        else:
            metrics["concepts_per_100_words"] = 0
            metrics["complex_concept_ratio"] = 0

        return metrics

    def _estimate_syllables(self, word: str) -> int:
        """Estimate syllable count for a word (simple approximation)."""
        word = word.lower().strip(".,!?;:")
        if len(word) <= 3:
            return 1

        vowels = "aeiouy"
        syllable_count = 0
        prev_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel

        # Handle silent e
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1

        return max(1, syllable_count)

    def _count_technical_words(self, content: str) -> int:
        """Count technical/specialized words in content."""
        technical_indicators = [
            "implementation", "methodology", "framework", "algorithm", "optimization",
            "paradigm", "infrastructure", "architecture", "ecosystem", "leverage",
            "scalability", "synchronization", "integration", "configuration", "deployment"
        ]

        content_lower = content.lower()
        return sum(1 for term in technical_indicators if term in content_lower)

    def _determine_audience_sophistication(self, demo_profile: DemographicProfile) -> str:
        """Determine audience sophistication level."""
        if not demo_profile.job_level:
            return "intermediate"  # Default

        sophistication_mapping = {
            ExperienceLevel.ENTRY: "basic",
            ExperienceLevel.JUNIOR: "intermediate",
            ExperienceLevel.MID: "intermediate",
            ExperienceLevel.SENIOR: "advanced",
            ExperienceLevel.EXECUTIVE: "expert"
        }

        return sophistication_mapping.get(demo_profile.job_level, "intermediate")

    async def _analyze_reading_level_fit(
        self,
        complexity_metrics: dict[str, float],
        audience_sophistication: str
    ) -> float:
        """Analyze reading level appropriateness."""
        # Calculate approximate reading level score
        avg_sentence_length = complexity_metrics.get("avg_words_per_sentence", 15)
        avg_syllables = complexity_metrics.get("avg_syllables_per_word", 1.5)
        long_word_ratio = complexity_metrics.get("long_word_ratio", 0.3)

        # Simple readability score (Flesch-Kincaid inspired)
        reading_difficulty = (avg_sentence_length * 0.39) + (avg_syllables * 11.8) + (long_word_ratio * 15.59)

        # Normalize to 0-1 scale (lower is easier)
        normalized_difficulty = min(1.0, reading_difficulty / 100)

        # Map audience sophistication to preferred difficulty
        sophistication_preferences = {
            "basic": 0.2,
            "intermediate": 0.4,
            "advanced": 0.7,
            "expert": 0.9
        }

        preferred_difficulty = sophistication_preferences.get(audience_sophistication, 0.5)

        # Calculate fit (1.0 - difference from preferred)
        difficulty_gap = abs(normalized_difficulty - preferred_difficulty)
        return max(0.0, 1.0 - difficulty_gap * 2)

    async def _analyze_technical_depth_fit(
        self,
        content: str,
        industry: Industry | None,
        job_level: ExperienceLevel | None,
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze technical depth appropriateness."""
        content_lower = content.lower()
        technical_density = 0.0

        # Industry-specific technical terms
        if industry:
            industry_technical_terms = {
                Industry.TECHNOLOGY: ["algorithm", "api", "cloud", "devops", "microservices", "machine learning"],
                Industry.FINANCE: ["derivatives", "portfolio", "arbitrage", "quantitative", "risk management"],
                Industry.HEALTHCARE: ["clinical", "pharmacological", "diagnostic", "therapeutic", "epidemiological"],
                Industry.MARKETING: ["attribution", "conversion", "segmentation", "optimization", "analytics"]
            }

            terms = industry_technical_terms.get(industry, [])
            if terms:
                technical_matches = sum(1 for term in terms if term in content_lower)
                technical_density = technical_matches / len(terms)

        # Job level expectations for technical depth
        if job_level:
            level_expectations = {
                ExperienceLevel.ENTRY: 0.2,
                ExperienceLevel.JUNIOR: 0.4,
                ExperienceLevel.MID: 0.6,
                ExperienceLevel.SENIOR: 0.8,
                ExperienceLevel.EXECUTIVE: 0.7  # High level but not necessarily deep technical
            }

            expected_depth = level_expectations.get(job_level, 0.5)
            depth_gap = abs(technical_density - expected_depth)
            return max(0.0, 1.0 - depth_gap * 1.5)

        return 0.7  # Default moderate fit when job level unknown

    async def _analyze_concept_density_fit(
        self,
        concepts: list[ConceptualEntity],
        audience_sophistication: str
    ) -> float:
        """Analyze concept density appropriateness."""
        if not concepts:
            return 0.6  # Neutral when no concepts

        # Calculate concept complexity
        complex_concepts = [c for c in concepts if c.concept_type in ["STRATEGY", "FRAMEWORK", "METHODOLOGY", "PARADIGM"]]
        complexity_ratio = len(complex_concepts) / len(concepts)

        # Expected complexity by sophistication
        sophistication_complexity = {
            "basic": 0.1,
            "intermediate": 0.3,
            "advanced": 0.6,
            "expert": 0.8
        }

        expected_complexity = sophistication_complexity.get(audience_sophistication, 0.4)
        complexity_gap = abs(complexity_ratio - expected_complexity)

        return max(0.0, 1.0 - complexity_gap * 1.5)

    async def _analyze_expertise_level_fit(
        self,
        content: str,
        job_level: ExperienceLevel | None,
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Analyze expertise level alignment."""
        if not job_level:
            return 0.5  # Neutral when unknown

        content_lower = content.lower()
        expertise_indicators = {
            ExperienceLevel.ENTRY: ["learn", "getting started", "basics", "introduction", "beginner"],
            ExperienceLevel.JUNIOR: ["understand", "practice", "develop", "improve", "guide"],
            ExperienceLevel.MID: ["implement", "optimize", "manage", "coordinate", "lead"],
            ExperienceLevel.SENIOR: ["strategy", "architecture", "design", "mentor", "expert"],
            ExperienceLevel.EXECUTIVE: ["vision", "transformation", "leadership", "strategic", "organizational"]
        }

        level_indicators = expertise_indicators.get(job_level, [])
        indicator_matches = sum(1 for indicator in level_indicators if indicator in content_lower)
        indicator_score = indicator_matches / len(level_indicators) if level_indicators else 0

        # Bonus for concept alignment with expertise level
        if concepts and job_level in [ExperienceLevel.SENIOR, ExperienceLevel.EXECUTIVE]:
            strategic_concepts = [c for c in concepts if c.concept_type in ["STRATEGY", "VISION", "LEADERSHIP"]]
            if strategic_concepts:
                indicator_score += (len(strategic_concepts) / len(concepts)) * 0.3

        return min(1.0, indicator_score)

    async def _analyze_cognitive_load_fit(
        self,
        complexity_metrics: dict[str, float],
        audience_sophistication: str
    ) -> float:
        """Analyze cognitive load appropriateness."""
        # Calculate cognitive load factors
        sentence_length_load = min(1.0, complexity_metrics.get("avg_words_per_sentence", 15) / 30)
        concept_density_load = min(1.0, complexity_metrics.get("concepts_per_100_words", 5) / 15)
        technical_load = complexity_metrics.get("technical_density", 0.1)

        overall_load = (sentence_length_load + concept_density_load + technical_load) / 3

        # Preferred cognitive load by sophistication
        sophistication_load_preference = {
            "basic": 0.3,
            "intermediate": 0.5,
            "advanced": 0.7,
            "expert": 0.8
        }

        preferred_load = sophistication_load_preference.get(audience_sophistication, 0.5)
        load_gap = abs(overall_load - preferred_load)

        return max(0.0, 1.0 - load_gap * 1.5)

    def _calculate_complexity_overall_score(self, complexity_fit: ContentComplexityFit) -> float:
        """Calculate overall complexity fit score."""
        scores = [
            complexity_fit.reading_level_fit * 0.25,
            complexity_fit.technical_depth_fit * 0.25,
            complexity_fit.concept_density_fit * 0.20,
            complexity_fit.expertise_level_fit * 0.20,
            complexity_fit.cognitive_load_fit * 0.10
        ]
        return sum(scores)

    def _calculate_complexity_confidence(
        self,
        complexity_fit: ContentComplexityFit,
        demo_profile: DemographicProfile
    ) -> float:
        """Calculate confidence in complexity analysis."""
        confidence_factors = [
            1.0 if demo_profile.job_level else 0.0,
            1.0 if demo_profile.industry else 0.0,
            1.0 if complexity_fit.complexity_metrics else 0.0
        ]

        return sum(confidence_factors) / len(confidence_factors)

    async def _generate_complexity_adjustments(
        self,
        complexity_fit: ContentComplexityFit,
        audience_sophistication: str,
        concepts: list[ConceptualEntity] = None
    ) -> list[str]:
        """Generate complexity adjustment recommendations."""
        recommendations = []

        if complexity_fit.reading_level_fit < 0.6:
            if audience_sophistication in ["basic", "intermediate"]:
                recommendations.append("Simplify language and reduce sentence length")
                recommendations.append("Use more common vocabulary and shorter paragraphs")
            else:
                recommendations.append("Increase sophistication with more nuanced language")
                recommendations.append("Use industry-specific terminology appropriately")

        if complexity_fit.technical_depth_fit < 0.6:
            if audience_sophistication in ["basic", "intermediate"]:
                recommendations.append("Reduce technical jargon and explain concepts more clearly")
            else:
                recommendations.append("Include more technical depth and industry expertise")

        if complexity_fit.concept_density_fit < 0.6:
            recommendations.append("Adjust concept density to match audience sophistication")

        if complexity_fit.cognitive_load_fit < 0.6:
            recommendations.append("Balance information density with readability")
            recommendations.append("Use structured formatting to reduce cognitive load")

        return recommendations


class ResonanceScorer:
    """Main class for comprehensive content-audience resonance scoring."""

    def __init__(self):
        self.demographic_analyzer = DemographicResonanceAnalyzer()
        self.behavioral_analyzer = BehavioralResonanceAnalyzer()
        self.psychographic_analyzer = PsychographicResonanceAnalyzer()
        self.complexity_analyzer = ComplexityAnalyzer()

        # Component weights for overall scoring
        self.component_weights = {
            ResonanceComponent.DEMOGRAPHIC: 0.20,
            ResonanceComponent.BEHAVIORAL: 0.25,
            ResonanceComponent.PSYCHOGRAPHIC: 0.25,
            ResonanceComponent.CONTENT_COMPLEXITY: 0.15,
            ResonanceComponent.PLATFORM_OPTIMIZATION: 0.10,
            ResonanceComponent.TEMPORAL_RELEVANCE: 0.05
        }

        # Resonance level thresholds
        self.resonance_thresholds = {
            ResonanceLevel.POOR: (0.0, 0.2),
            ResonanceLevel.WEAK: (0.2, 0.4),
            ResonanceLevel.MODERATE: (0.4, 0.6),
            ResonanceLevel.STRONG: (0.6, 0.8),
            ResonanceLevel.EXCELLENT: (0.8, 1.0)
        }

        logger.info("ResonanceScorer initialized")

    async def analyze_content_audience_resonance(
        self,
        content: str,
        audience_segment: AudienceSegment,
        content_concepts: list[ConceptualEntity] = None,
        viral_prediction: ViralPrediction = None,
        posting_time: datetime | None = None,
        platform: Platform | None = None
    ) -> ResonanceAnalysis:
        """Perform comprehensive content-audience resonance analysis."""
        try:
            start_time = datetime.utcnow()
            logger.info("Starting comprehensive content-audience resonance analysis")

            # Perform individual component analyses
            demographic_resonance = await self.demographic_analyzer.analyze_demographic_resonance(
                content, audience_segment.demographic_profile, content_concepts
            )

            behavioral_resonance = await self.behavioral_analyzer.analyze_behavioral_resonance(
                content, audience_segment.behavior_profile, content_concepts, posting_time
            )

            psychographic_resonance = await self.psychographic_analyzer.analyze_psychographic_resonance(
                content, audience_segment.psychographic_profile, content_concepts
            )

            content_complexity_fit = await self.complexity_analyzer.analyze_content_complexity_fit(
                content, audience_segment.demographic_profile, content_concepts
            )

            platform_optimization = await self._analyze_platform_optimization(
                content, platform or (audience_segment.preferred_platforms[0] if audience_segment.preferred_platforms else Platform.GENERAL),
                viral_prediction
            )

            temporal_relevance = await self._analyze_temporal_relevance(
                content, posting_time, audience_segment, content_concepts
            )

            # Calculate overall resonance score
            overall_score = self._calculate_overall_resonance_score(
                demographic_resonance, behavioral_resonance, psychographic_resonance,
                content_complexity_fit, platform_optimization, temporal_relevance
            )

            # Determine resonance level
            resonance_level = self._determine_resonance_level(overall_score)

            # Calculate confidence score
            confidence_score = self._calculate_overall_confidence(
                demographic_resonance, behavioral_resonance, psychographic_resonance,
                content_complexity_fit, platform_optimization, temporal_relevance
            )

            # Predict engagement and viral potential
            engagement_prediction = await self._predict_engagement_potential(
                behavioral_resonance, psychographic_resonance, viral_prediction
            )

            viral_potential_prediction = await self._predict_viral_potential(
                overall_score, viral_prediction, content_concepts
            )

            # Generate optimization recommendations
            optimization_recommendations = await self._generate_optimization_recommendations(
                demographic_resonance, behavioral_resonance, psychographic_resonance,
                content_complexity_fit, platform_optimization, temporal_relevance,
                overall_score
            )

            # Identify key insights
            key_strengths = self._identify_key_strengths(
                demographic_resonance, behavioral_resonance, psychographic_resonance,
                content_complexity_fit, platform_optimization, temporal_relevance
            )

            major_gaps = self._identify_major_gaps(
                demographic_resonance, behavioral_resonance, psychographic_resonance,
                content_complexity_fit, platform_optimization, temporal_relevance
            )

            quick_wins = self._identify_quick_wins(optimization_recommendations)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            analysis = ResonanceAnalysis(
                content_id=f"content_{hash(content) % 1000000}",
                audience_segment_id=audience_segment.id,
                demographic_resonance=demographic_resonance,
                behavioral_resonance=behavioral_resonance,
                psychographic_resonance=psychographic_resonance,
                content_complexity_fit=content_complexity_fit,
                platform_optimization=platform_optimization,
                temporal_relevance=temporal_relevance,
                overall_resonance_score=overall_score,
                resonance_level=resonance_level,
                confidence_score=confidence_score,
                engagement_prediction=engagement_prediction,
                viral_potential_prediction=viral_potential_prediction,
                optimization_recommendations=optimization_recommendations,
                key_strengths=key_strengths,
                major_gaps=major_gaps,
                quick_wins=quick_wins,
                processing_time_ms=processing_time
            )

            logger.info(f"Resonance analysis completed: {overall_score:.3f} ({resonance_level.value})")
            return analysis

        except Exception as e:
            logger.error(f"Error in resonance analysis: {str(e)}")
            # Return minimal analysis with error indication
            return ResonanceAnalysis(
                demographic_resonance=DemographicResonance(),
                behavioral_resonance=BehavioralResonance(),
                psychographic_resonance=PsychographicResonance(),
                content_complexity_fit=ContentComplexityFit(),
                platform_optimization=PlatformOptimization(),
                temporal_relevance=TemporalRelevance(),
                overall_resonance_score=0.0,
                resonance_level=ResonanceLevel.POOR,
                confidence_score=0.0,
                engagement_prediction=0.0,
                viral_potential_prediction=0.0
            )

    async def batch_analyze_content_audience_matches(
        self,
        content_audience_pairs: list[tuple[str, AudienceSegment]],
        content_concepts_map: dict[str, list[ConceptualEntity]] = None,
        viral_predictions_map: dict[str, ViralPrediction] = None
    ) -> list[ContentAudienceMatch]:
        """Analyze multiple content-audience pairs for optimal matching."""
        try:
            logger.info(f"Batch analyzing {len(content_audience_pairs)} content-audience pairs")

            matches = []

            for i, (content, audience_segment) in enumerate(content_audience_pairs):
                content_id = f"content_{i}"
                content_concepts = content_concepts_map.get(content_id, []) if content_concepts_map else []
                viral_prediction = viral_predictions_map.get(content_id) if viral_predictions_map else None

                # Perform resonance analysis
                analysis = await self.analyze_content_audience_resonance(
                    content, audience_segment, content_concepts, viral_prediction
                )

                # Create match object
                match = ContentAudienceMatch(
                    content_id=content_id,
                    audience_segment_id=audience_segment.id,
                    resonance_score=analysis.overall_resonance_score,
                    engagement_prediction=analysis.engagement_prediction,
                    conversion_prediction=audience_segment.conversion_likelihood * analysis.overall_resonance_score,
                    risk_score=self._calculate_risk_score(analysis),
                    confidence=analysis.confidence_score,
                    match_quality=self._determine_match_quality(analysis.overall_resonance_score),
                    primary_resonance_drivers=analysis.key_strengths[:3],
                    optimization_priority=self._determine_optimization_priority(analysis)
                )

                matches.append(match)

            # Sort by resonance score (best matches first)
            matches.sort(key=lambda x: x.resonance_score, reverse=True)

            logger.info(f"Batch analysis completed. Best match: {matches[0].resonance_score:.3f}")
            return matches

        except Exception as e:
            logger.error(f"Error in batch content-audience analysis: {str(e)}")
            return []

    async def get_real_time_optimization_recommendations(
        self,
        content: str,
        audience_segment: AudienceSegment,
        current_performance: dict[str, float] = None
    ) -> list[OptimizationRecommendation]:
        """Get real-time optimization recommendations for content-audience fit."""
        try:
            # Perform quick resonance analysis
            analysis = await self.analyze_content_audience_resonance(content, audience_segment)

            # Generate prioritized recommendations
            recommendations = analysis.optimization_recommendations

            # Adjust recommendations based on current performance
            if current_performance:
                recommendations = self._adjust_recommendations_for_performance(
                    recommendations, current_performance
                )

            # Sort by priority and expected impact
            recommendations.sort(key=lambda x: (
                {"high": 3, "medium": 2, "low": 1}[x.priority],
                x.expected_impact
            ), reverse=True)

            return recommendations[:5]  # Return top 5 recommendations

        except Exception as e:
            logger.error(f"Error generating real-time recommendations: {str(e)}")
            return []

    async def _analyze_platform_optimization(
        self,
        content: str,
        platform: Platform,
        viral_prediction: ViralPrediction = None
    ) -> PlatformOptimization:
        """Analyze platform-specific optimization."""
        optimization = PlatformOptimization()

        try:
            if platform == Platform.LINKEDIN:
                optimization = await self._analyze_linkedin_optimization(content, viral_prediction)
            elif platform == Platform.TWITTER:
                optimization = await self._analyze_twitter_optimization(content, viral_prediction)
            else:
                optimization = await self._analyze_general_platform_optimization(content, viral_prediction)

            optimization.overall_score = self._calculate_platform_optimization_overall_score(optimization)
            optimization.confidence = 0.8  # Platform rules are well-defined

            return optimization

        except Exception as e:
            logger.error(f"Error in platform optimization analysis: {str(e)}")
            return PlatformOptimization(confidence=0.0)

    async def _analyze_linkedin_optimization(
        self,
        content: str,
        viral_prediction: ViralPrediction = None
    ) -> PlatformOptimization:
        """Analyze LinkedIn-specific optimization."""
        optimization = PlatformOptimization()

        # Format fit analysis
        professional_indicators = ["professional", "business", "career", "industry", "leadership"]
        professional_score = sum(1 for indicator in professional_indicators if indicator in content.lower()) / len(professional_indicators)
        optimization.format_fit = professional_score

        # Length optimization (LinkedIn sweet spot: 150-300 words)
        content_length = len(content.split())
        if 150 <= content_length <= 300:
            optimization.length_optimization = 1.0
        elif content_length < 150:
            optimization.length_optimization = 0.7  # Too short
        else:
            optimization.length_optimization = max(0.3, 1.0 - (content_length - 300) / 1000)

        # Visual element considerations
        has_structure = "\n" in content or any(marker in content for marker in ["•", "-", "1.", "2."])
        optimization.visual_element_fit = 0.8 if has_structure else 0.5

        # Hashtag optimization (LinkedIn: 3-5 hashtags)
        hashtag_count = content.count("#")
        if 3 <= hashtag_count <= 5:
            optimization.hashtag_optimization = 1.0
        elif hashtag_count == 0:
            optimization.hashtag_optimization = 0.3
        else:
            optimization.hashtag_optimization = 0.6

        # Professional posting style
        call_to_action = any(phrase in content.lower() for phrase in ["what do you think", "share your thoughts", "comment below"])
        optimization.posting_style_fit = 0.9 if call_to_action else 0.6

        # Algorithm compatibility
        engagement_words = ["insights", "experience", "lessons", "tips", "strategy"]
        algorithm_score = sum(1 for word in engagement_words if word in content.lower()) / len(engagement_words)
        optimization.algorithm_compatibility = algorithm_score

        # Platform-specific recommendations
        optimization.platform_specific_recommendations = [
            "Use professional tone and industry-relevant terminology",
            "Include 3-5 relevant hashtags",
            "Ask thought-provoking questions to encourage engagement",
            "Share personal insights and experiences",
            "Use bullet points or numbered lists for readability"
        ]

        return optimization

    async def _analyze_twitter_optimization(
        self,
        content: str,
        viral_prediction: ViralPrediction = None
    ) -> PlatformOptimization:
        """Analyze Twitter-specific optimization."""
        optimization = PlatformOptimization()

        # Format fit for Twitter
        twitter_indicators = ["breaking", "hot take", "thread", "quick", "update"]
        twitter_score = sum(1 for indicator in twitter_indicators if indicator in content.lower()) / len(twitter_indicators)
        optimization.format_fit = twitter_score

        # Length optimization (Twitter: ideally under 280 characters)
        content_length = len(content)
        if content_length <= 280:
            optimization.length_optimization = 1.0
        else:
            optimization.length_optimization = max(0.2, 1.0 - (content_length - 280) / 280)

        # Visual elements (minimal for Twitter)
        optimization.visual_element_fit = 0.8  # Default good for text-based

        # Hashtag optimization (Twitter: 1-2 hashtags)
        hashtag_count = content.count("#")
        if 1 <= hashtag_count <= 2:
            optimization.hashtag_optimization = 1.0
        elif hashtag_count == 0:
            optimization.hashtag_optimization = 0.4
        else:
            optimization.hashtag_optimization = 0.5

        # Twitter posting style
        is_conversational = any(word in content.lower() for word in ["think", "feel", "anyone else", "just me"])
        optimization.posting_style_fit = 0.9 if is_conversational else 0.6

        # Algorithm compatibility (engagement-driven)
        viral_words = ["viral", "trending", "everyone", "must see", "incredible"]
        algorithm_score = sum(1 for word in viral_words if word in content.lower()) / len(viral_words)
        optimization.algorithm_compatibility = algorithm_score

        optimization.platform_specific_recommendations = [
            "Keep under 280 characters",
            "Use 1-2 relevant hashtags",
            "Make it conversational and engaging",
            "Include trending topics when relevant",
            "Use emojis sparingly but effectively"
        ]

        return optimization

    async def _analyze_general_platform_optimization(
        self,
        content: str,
        viral_prediction: ViralPrediction = None
    ) -> PlatformOptimization:
        """Analyze general platform optimization."""
        optimization = PlatformOptimization()

        # Default moderate scores for general platform
        optimization.format_fit = 0.7
        optimization.length_optimization = 0.7
        optimization.visual_element_fit = 0.7
        optimization.hashtag_optimization = 0.6
        optimization.posting_style_fit = 0.7
        optimization.algorithm_compatibility = 0.6

        optimization.platform_specific_recommendations = [
            "Ensure content is platform-appropriate",
            "Use clear, engaging language",
            "Include relevant hashtags",
            "Encourage audience interaction",
            "Maintain consistent posting style"
        ]

        return optimization

    async def _analyze_temporal_relevance(
        self,
        content: str,
        posting_time: datetime | None,
        audience_segment: AudienceSegment,
        concepts: list[ConceptualEntity] = None
    ) -> TemporalRelevance:
        """Analyze temporal relevance and timing factors."""
        relevance = TemporalRelevance()

        try:
            content_lower = content.lower()

            # Trending topic alignment
            trending_indicators = ["trending", "hot", "viral", "everyone's talking", "latest", "breaking"]
            trending_score = sum(1 for indicator in trending_indicators if indicator in content_lower) / len(trending_indicators)
            relevance.trending_topic_alignment = trending_score

            # Seasonal relevance (basic implementation)
            if posting_time:
                month = posting_time.month
                seasonal_words = {
                    "winter": [12, 1, 2],
                    "spring": [3, 4, 5],
                    "summer": [6, 7, 8],
                    "fall": [9, 10, 11]
                }

                seasonal_score = 0.0
                for season, months in seasonal_words.items():
                    if month in months and season in content_lower:
                        seasonal_score = 1.0
                        break

                relevance.seasonal_relevance = seasonal_score if seasonal_score > 0 else 0.7  # Neutral
            else:
                relevance.seasonal_relevance = 0.7

            # Audience activity timing
            if posting_time and audience_segment.peak_activity_hours:
                posting_hour = posting_time.hour
                if posting_hour in audience_segment.peak_activity_hours:
                    relevance.audience_activity_timing = 1.0
                else:
                    # Calculate proximity to peak hours
                    distances = [abs(posting_hour - peak_hour) for peak_hour in audience_segment.peak_activity_hours]
                    min_distance = min(distances) if distances else 12
                    relevance.audience_activity_timing = max(0.2, 1.0 - min_distance / 12)
            else:
                relevance.audience_activity_timing = 0.6

            # Content freshness
            time_sensitive_words = ["today", "now", "current", "latest", "recent", "just", "new"]
            freshness_score = sum(1 for word in time_sensitive_words if word in content_lower) / len(time_sensitive_words)
            relevance.content_freshness = freshness_score

            # Time sensitivity
            urgent_indicators = ["urgent", "breaking", "immediate", "now", "asap", "critical"]
            urgency_score = sum(1 for indicator in urgent_indicators if indicator in content_lower) / len(urgent_indicators)
            relevance.time_sensitivity = urgency_score

            # Calculate overall temporal score
            relevance.overall_score = (
                relevance.trending_topic_alignment * 0.25 +
                relevance.seasonal_relevance * 0.15 +
                relevance.audience_activity_timing * 0.30 +
                relevance.content_freshness * 0.20 +
                relevance.time_sensitivity * 0.10
            )

            relevance.confidence = 0.7  # Moderate confidence for temporal analysis

            # Generate timing recommendations
            if posting_time:
                relevance.timing_recommendations = [
                    f"Content posted at {posting_time.strftime('%H:%M')} on {posting_time.strftime('%A')}",
                    f"Audience peak hours: {audience_segment.peak_activity_hours}",
                    "Consider timing for maximum audience overlap"
                ]
            else:
                relevance.timing_recommendations = [
                    f"Recommend posting during peak hours: {audience_segment.peak_activity_hours}",
                    "Consider time zone of target audience",
                    "Monitor trending topics for optimal timing"
                ]

            return relevance

        except Exception as e:
            logger.error(f"Error in temporal relevance analysis: {str(e)}")
            return TemporalRelevance(confidence=0.0)

    def _calculate_overall_resonance_score(
        self,
        demographic: DemographicResonance,
        behavioral: BehavioralResonance,
        psychographic: PsychographicResonance,
        complexity: ContentComplexityFit,
        platform: PlatformOptimization,
        temporal: TemporalRelevance
    ) -> float:
        """Calculate overall resonance score."""
        component_scores = [
            demographic.overall_score * self.component_weights[ResonanceComponent.DEMOGRAPHIC],
            behavioral.overall_score * self.component_weights[ResonanceComponent.BEHAVIORAL],
            psychographic.overall_score * self.component_weights[ResonanceComponent.PSYCHOGRAPHIC],
            complexity.overall_score * self.component_weights[ResonanceComponent.CONTENT_COMPLEXITY],
            platform.overall_score * self.component_weights[ResonanceComponent.PLATFORM_OPTIMIZATION],
            temporal.overall_score * self.component_weights[ResonanceComponent.TEMPORAL_RELEVANCE]
        ]

        return sum(component_scores)

    def _determine_resonance_level(self, overall_score: float) -> ResonanceLevel:
        """Determine resonance level from overall score."""
        for level, (min_score, max_score) in self.resonance_thresholds.items():
            if min_score <= overall_score <= max_score:
                return level
        return ResonanceLevel.MODERATE  # Default fallback

    def _calculate_overall_confidence(
        self,
        demographic: DemographicResonance,
        behavioral: BehavioralResonance,
        psychographic: PsychographicResonance,
        complexity: ContentComplexityFit,
        platform: PlatformOptimization,
        temporal: TemporalRelevance
    ) -> float:
        """Calculate overall confidence score."""
        confidences = [
            demographic.confidence * self.component_weights[ResonanceComponent.DEMOGRAPHIC],
            behavioral.confidence * self.component_weights[ResonanceComponent.BEHAVIORAL],
            psychographic.confidence * self.component_weights[ResonanceComponent.PSYCHOGRAPHIC],
            complexity.confidence * self.component_weights[ResonanceComponent.CONTENT_COMPLEXITY],
            platform.confidence * self.component_weights[ResonanceComponent.PLATFORM_OPTIMIZATION],
            temporal.confidence * self.component_weights[ResonanceComponent.TEMPORAL_RELEVANCE]
        ]

        return sum(confidences)

    async def _predict_engagement_potential(
        self,
        behavioral: BehavioralResonance,
        psychographic: PsychographicResonance,
        viral_prediction: ViralPrediction = None
    ) -> float:
        """Predict engagement potential based on resonance analysis."""
        # Base engagement from behavioral resonance
        base_engagement = behavioral.overall_score * 0.6

        # Boost from psychographic alignment
        psycho_boost = psychographic.overall_score * 0.3

        # Additional boost from viral prediction if available
        viral_boost = 0.0
        if viral_prediction:
            viral_boost = viral_prediction.engagement_score * 0.1

        return min(1.0, base_engagement + psycho_boost + viral_boost)

    async def _predict_viral_potential(
        self,
        overall_resonance: float,
        viral_prediction: ViralPrediction = None,
        concepts: list[ConceptualEntity] = None
    ) -> float:
        """Predict viral potential based on resonance and other factors."""
        # Base viral potential from overall resonance
        base_viral = overall_resonance * 0.5

        # Boost from viral prediction if available
        if viral_prediction:
            base_viral += viral_prediction.viral_score * 0.4

        # Concept-based viral potential
        if concepts:
            viral_concepts = [c for c in concepts if c.concept_type in ["HOT_TAKE", "CONTROVERSY", "TRENDING"]]
            concept_boost = (len(viral_concepts) / len(concepts)) * 0.1
            base_viral += concept_boost

        return min(1.0, base_viral)

    async def _generate_optimization_recommendations(
        self,
        demographic: DemographicResonance,
        behavioral: BehavioralResonance,
        psychographic: PsychographicResonance,
        complexity: ContentComplexityFit,
        platform: PlatformOptimization,
        temporal: TemporalRelevance,
        overall_score: float
    ) -> list[OptimizationRecommendation]:
        """Generate comprehensive optimization recommendations."""
        recommendations = []

        # Demographic optimizations
        if demographic.overall_score < 0.6:
            for rec_text in demographic.optimization_recommendations:
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.AUDIENCE_TARGETING,
                    priority="high" if demographic.overall_score < 0.4 else "medium",
                    title="Demographic Alignment",
                    description=rec_text,
                    specific_actions=[rec_text],
                    expected_impact=0.8 - demographic.overall_score,
                    implementation_difficulty="medium",
                    estimated_time_to_implement="2-4 hours",
                    success_metrics=["Improved demographic resonance score", "Better audience engagement"]
                ))

        # Behavioral optimizations
        if behavioral.overall_score < 0.6:
            for rec_text in behavioral.optimization_recommendations:
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.CONTENT_ADJUSTMENT,
                    priority="high" if behavioral.overall_score < 0.4 else "medium",
                    title="Behavioral Pattern Alignment",
                    description=rec_text,
                    specific_actions=[rec_text],
                    expected_impact=0.7 - behavioral.overall_score,
                    implementation_difficulty="easy",
                    estimated_time_to_implement="1-2 hours",
                    success_metrics=["Higher engagement rates", "Better behavioral fit"]
                ))

        # Psychographic optimizations
        if psychographic.overall_score < 0.6:
            for rec_text in psychographic.optimization_recommendations:
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.MESSAGING_REFINEMENT,
                    priority="medium",
                    title="Psychographic Resonance",
                    description=rec_text,
                    specific_actions=[rec_text],
                    expected_impact=0.6 - psychographic.overall_score,
                    implementation_difficulty="medium",
                    estimated_time_to_implement="2-3 hours",
                    success_metrics=["Improved emotional connection", "Better value alignment"]
                ))

        # Complexity optimizations
        if complexity.overall_score < 0.6:
            for rec_text in complexity.adjustment_recommendations:
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.CONTENT_ADJUSTMENT,
                    priority="medium",
                    title="Content Complexity Adjustment",
                    description=rec_text,
                    specific_actions=[rec_text],
                    expected_impact=0.6 - complexity.overall_score,
                    implementation_difficulty="easy",
                    estimated_time_to_implement="1 hour",
                    success_metrics=["Better readability", "Appropriate complexity level"]
                ))

        # Platform optimizations
        if platform.overall_score < 0.7:
            for rec_text in platform.platform_specific_recommendations:
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.PLATFORM_OPTIMIZATION,
                    priority="low" if platform.overall_score > 0.5 else "medium",
                    title="Platform Optimization",
                    description=rec_text,
                    specific_actions=[rec_text],
                    expected_impact=0.8 - platform.overall_score,
                    implementation_difficulty="easy",
                    estimated_time_to_implement="30 minutes",
                    success_metrics=["Better platform fit", "Improved algorithmic visibility"]
                ))

        # Temporal optimizations
        if temporal.overall_score < 0.6:
            for rec_text in temporal.timing_recommendations:
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.TIMING_OPTIMIZATION,
                    priority="low",
                    title="Timing Optimization",
                    description=rec_text,
                    specific_actions=[rec_text],
                    expected_impact=0.7 - temporal.overall_score,
                    implementation_difficulty="easy",
                    estimated_time_to_implement="15 minutes",
                    success_metrics=["Better timing alignment", "Increased reach"]
                ))

        # Sort by priority and expected impact
        priority_weights = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(key=lambda x: (priority_weights[x.priority], x.expected_impact), reverse=True)

        return recommendations[:10]  # Return top 10 recommendations

    def _identify_key_strengths(
        self,
        demographic: DemographicResonance,
        behavioral: BehavioralResonance,
        psychographic: PsychographicResonance,
        complexity: ContentComplexityFit,
        platform: PlatformOptimization,
        temporal: TemporalRelevance
    ) -> list[str]:
        """Identify key strengths in content-audience resonance."""
        strengths = []

        if demographic.overall_score > 0.7:
            strengths.append("Strong demographic alignment")

        if behavioral.overall_score > 0.7:
            strengths.append("Excellent behavioral pattern match")

        if psychographic.overall_score > 0.7:
            strengths.append("Deep psychographic resonance")

        if complexity.overall_score > 0.7:
            strengths.append("Appropriate content complexity")

        if platform.overall_score > 0.8:
            strengths.append("Well-optimized for platform")

        if temporal.overall_score > 0.7:
            strengths.append("Good timing and relevance")

        return strengths

    def _identify_major_gaps(
        self,
        demographic: DemographicResonance,
        behavioral: BehavioralResonance,
        psychographic: PsychographicResonance,
        complexity: ContentComplexityFit,
        platform: PlatformOptimization,
        temporal: TemporalRelevance
    ) -> list[str]:
        """Identify major gaps in content-audience resonance."""
        gaps = []

        if demographic.overall_score < 0.4:
            gaps.append("Poor demographic alignment - audience mismatch")

        if behavioral.overall_score < 0.4:
            gaps.append("Behavioral pattern mismatch - low engagement potential")

        if psychographic.overall_score < 0.4:
            gaps.append("Weak psychographic connection - values misalignment")

        if complexity.overall_score < 0.4:
            gaps.append("Content complexity mismatch - readability issues")

        if platform.overall_score < 0.5:
            gaps.append("Poor platform optimization")

        if temporal.overall_score < 0.4:
            gaps.append("Timing and relevance issues")

        return gaps

    def _identify_quick_wins(self, recommendations: list[OptimizationRecommendation]) -> list[str]:
        """Identify quick wins from optimization recommendations."""
        quick_wins = []

        for rec in recommendations:
            if rec.implementation_difficulty == "easy" and rec.expected_impact > 0.3:
                quick_wins.append(rec.title + ": " + rec.description)

        return quick_wins[:3]  # Return top 3 quick wins

    def _calculate_platform_optimization_overall_score(self, optimization: PlatformOptimization) -> float:
        """Calculate overall platform optimization score."""
        scores = [
            optimization.format_fit * 0.25,
            optimization.length_optimization * 0.20,
            optimization.visual_element_fit * 0.15,
            optimization.hashtag_optimization * 0.15,
            optimization.posting_style_fit * 0.15,
            optimization.algorithm_compatibility * 0.10
        ]
        return sum(scores)

    def _calculate_risk_score(self, analysis: ResonanceAnalysis) -> float:
        """Calculate risk score for content-audience match."""
        # Risk is inverse of resonance (higher resonance = lower risk)
        base_risk = 1.0 - analysis.overall_resonance_score

        # Adjust for confidence (lower confidence = higher risk)
        confidence_adjustment = (1.0 - analysis.confidence_score) * 0.2

        return min(1.0, base_risk + confidence_adjustment)

    def _determine_match_quality(self, resonance_score: float) -> str:
        """Determine match quality from resonance score."""
        if resonance_score >= 0.8:
            return "excellent"
        elif resonance_score >= 0.6:
            return "good"
        elif resonance_score >= 0.4:
            return "moderate"
        else:
            return "poor"

    def _determine_optimization_priority(self, analysis: ResonanceAnalysis) -> str:
        """Determine optimization priority based on analysis."""
        if analysis.overall_resonance_score < 0.4:
            return "high"
        elif analysis.overall_resonance_score < 0.6:
            return "medium"
        else:
            return "low"

    def _adjust_recommendations_for_performance(
        self,
        recommendations: list[OptimizationRecommendation],
        performance: dict[str, float]
    ) -> list[OptimizationRecommendation]:
        """Adjust recommendations based on current performance metrics."""
        # Simple adjustment based on performance
        # In production, this would be more sophisticated

        for rec in recommendations:
            # If engagement is low, prioritize engagement-related recommendations
            if performance.get("engagement_rate", 0) < 0.3:
                if "engagement" in rec.description.lower():
                    rec.priority = "high"
                    rec.expected_impact *= 1.2

            # If reach is low, prioritize platform optimization
            if performance.get("reach", 0) < 0.4:
                if rec.type == OptimizationType.PLATFORM_OPTIMIZATION:
                    rec.priority = "high"
                    rec.expected_impact *= 1.1

        return recommendations


# Integration and utility functions
async def analyze_content_audience_resonance(
    content: str,
    audience_segment: AudienceSegment,
    content_concepts: list[ConceptualEntity] = None,
    viral_prediction: ViralPrediction = None,
    platform: Platform = Platform.LINKEDIN
) -> ResonanceAnalysis:
    """Quick function to analyze content-audience resonance."""
    scorer = ResonanceScorer()
    return await scorer.analyze_content_audience_resonance(
        content, audience_segment, content_concepts, viral_prediction, platform=platform
    )


async def find_best_audience_for_content(
    content: str,
    audience_segments: list[AudienceSegment],
    content_concepts: list[ConceptualEntity] = None
) -> list[ContentAudienceMatch]:
    """Find the best audience segments for given content."""
    scorer = ResonanceScorer()
    pairs = [(content, segment) for segment in audience_segments]

    concepts_map = {"content_0": content_concepts} if content_concepts else None

    return await scorer.batch_analyze_content_audience_matches(pairs, concepts_map)


async def optimize_content_for_audience(
    content: str,
    target_audience: AudienceSegment,
    current_performance: dict[str, float] = None
) -> list[OptimizationRecommendation]:
    """Get optimization recommendations for content-audience fit."""
    scorer = ResonanceScorer()
    return await scorer.get_real_time_optimization_recommendations(
        content, target_audience, current_performance
    )


# Configuration and constants
RESONANCE_CONFIG = {
    "component_weights": {
        "demographic": 0.20,
        "behavioral": 0.25,
        "psychographic": 0.25,
        "content_complexity": 0.15,
        "platform_optimization": 0.10,
        "temporal_relevance": 0.05
    },
    "confidence_thresholds": {
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4
    },
    "optimization_priorities": {
        "critical": 0.3,
        "high": 0.5,
        "medium": 0.7,
        "low": 0.8
    }
}

logger.info("Content-Audience Resonance Scoring module initialized")
