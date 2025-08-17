"""AI-powered Content Strategy Recommendation Engine for Epic 9.1.

This module provides a sophisticated system that combines all previous epic capabilities
to generate intelligent content strategy recommendations. It integrates:
- Belief preference extraction (Epic 6)
- Viral prediction (Epic 7)
- Brand safety analysis (Epic 7)
- Audience intelligence (Epic 8)

Key Features:
- Multi-factor strategy optimization
- Content gap analysis and opportunity identification
- Strategic timeline planning with milestone recommendations
- Resource requirement estimation and budget planning
- Performance prediction with confidence intervals
- Competitive positioning and differentiation strategies
- Cross-platform content strategy coordination
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from graph_rag.core.audience_intelligence import (
    AudienceSegment,
    AudienceSegmentationEngine,
    ContentPreference,
)
from graph_rag.core.brand_safety_analyzer import BrandProfile, BrandSafetyAnalyzer
from graph_rag.core.concept_entity_extractor import BeliefPreferenceExtractor
from graph_rag.core.content_audience_resonance import ResonanceScorer
from graph_rag.core.viral_prediction_engine import ContentType, Platform, ViralPredictionEngine

logger = logging.getLogger(__name__)


# Enums for Strategy Optimization
class StrategyObjective(Enum):
    """Primary strategy objectives."""
    BRAND_AWARENESS = "brand_awareness"
    LEAD_GENERATION = "lead_generation"
    THOUGHT_LEADERSHIP = "thought_leadership"
    ENGAGEMENT = "engagement"
    CONVERSION = "conversion"
    COMMUNITY_BUILDING = "community_building"
    CUSTOMER_RETENTION = "customer_retention"


class ContentFormat(Enum):
    """Content format types."""
    TEXT_POST = "text_post"
    LONG_FORM_ARTICLE = "long_form_article"
    VIDEO = "video"
    INFOGRAPHIC = "infographic"
    PODCAST = "podcast"
    CAROUSEL = "carousel"
    POLL = "poll"
    LIVE_STREAM = "live_stream"
    CASE_STUDY = "case_study"


class CompetitivePosition(Enum):
    """Competitive positioning strategies."""
    CHALLENGER = "challenger"           # Challenge status quo
    FOLLOWER = "follower"              # Follow market leaders
    NICHER = "nicher"                  # Focus on specific niche
    LEADER = "leader"                  # Market leadership position


class ResourceType(Enum):
    """Resource requirement types."""
    CONTENT_CREATION = "content_creation"
    DESIGN_VISUAL = "design_visual"
    VIDEO_PRODUCTION = "video_production"
    RESEARCH_ANALYSIS = "research_analysis"
    COMMUNITY_MANAGEMENT = "community_management"
    PAID_PROMOTION = "paid_promotion"


class MilestoneType(Enum):
    """Strategic milestone types."""
    CONTENT_LAUNCH = "content_launch"
    CAMPAIGN_START = "campaign_start"
    PERFORMANCE_REVIEW = "performance_review"
    OPTIMIZATION_CHECKPOINT = "optimization_checkpoint"
    GOAL_ACHIEVEMENT = "goal_achievement"


# Data Models
@dataclass
class ContentGap:
    """Identified content opportunity gap."""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""

    # Gap characteristics
    audience_segment: str | None = None
    content_type: ContentType | None = None
    platform: Platform | None = None
    topic_area: str = ""

    # Opportunity scoring
    opportunity_score: float = 0.0  # 0.0 - 1.0
    competition_intensity: float = 0.0  # 0.0 - 1.0 (higher = more competitive)
    market_demand: float = 0.0  # 0.0 - 1.0
    brand_fit: float = 0.0  # 0.0 - 1.0

    # Performance potential
    estimated_reach: int = 0
    estimated_engagement_rate: float = 0.0
    viral_potential: float = 0.0
    conversion_potential: float = 0.0

    # Risk factors
    brand_safety_risk: float = 0.0  # 0.0 - 1.0
    execution_difficulty: float = 0.0  # 0.0 - 1.0
    resource_requirements: dict[ResourceType, float] = field(default_factory=dict)

    # Strategic importance
    strategic_priority: str = "medium"  # low, medium, high, critical
    business_impact: float = 0.0  # 0.0 - 1.0
    confidence: float = 0.0  # 0.0 - 1.0

    # Recommendations
    recommended_content_formats: list[ContentFormat] = field(default_factory=list)
    suggested_angles: list[str] = field(default_factory=list)
    target_keywords: list[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResourcePlan:
    """Resource requirement plan for strategy execution."""
    id: str = field(default_factory=lambda: str(uuid4()))
    strategy_id: str = ""

    # Personnel requirements
    content_creators: int = 1
    designers: int = 0
    video_producers: int = 0
    community_managers: int = 1
    analysts: int = 0

    # Time requirements (hours per week)
    content_creation_hours: float = 10.0
    design_hours: float = 5.0
    video_production_hours: float = 0.0
    community_management_hours: float = 5.0
    analysis_hours: float = 2.0

    # Budget requirements
    content_budget: float = 1000.0
    design_budget: float = 500.0
    video_budget: float = 0.0
    promotion_budget: float = 2000.0
    tools_budget: float = 300.0

    # Total estimates
    total_personnel: int = field(init=False)
    total_hours_per_week: float = field(init=False)
    total_monthly_budget: float = field(init=False)

    # Timeline
    implementation_weeks: int = 12
    ramp_up_weeks: int = 4

    def __post_init__(self):
        self.total_personnel = (
            self.content_creators + self.designers + self.video_producers +
            self.community_managers + self.analysts
        )
        self.total_hours_per_week = (
            self.content_creation_hours + self.design_hours +
            self.video_production_hours + self.community_management_hours +
            self.analysis_hours
        )
        self.total_monthly_budget = (
            self.content_budget + self.design_budget + self.video_budget +
            self.promotion_budget + self.tools_budget
        )


@dataclass
class PerformancePrediction:
    """Performance prediction with confidence intervals."""
    id: str = field(default_factory=lambda: str(uuid4()))
    strategy_id: str = ""

    # Engagement predictions
    predicted_reach: tuple[int, int, int] = (0, 0, 0)  # min, expected, max
    predicted_engagement_rate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    predicted_click_rate: tuple[float, float, float] = (0.01, 0.02, 0.05)
    predicted_conversion_rate: tuple[float, float, float] = (0.001, 0.005, 0.02)

    # Growth predictions
    follower_growth: tuple[int, int, int] = (0, 0, 0)
    brand_mention_increase: tuple[float, float, float] = (0.0, 0.0, 0.0)
    website_traffic_increase: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # ROI predictions
    estimated_leads: tuple[int, int, int] = (0, 0, 0)
    estimated_revenue: tuple[float, float, float] = (0.0, 0.0, 0.0)
    cost_per_lead: tuple[float, float, float] = (50.0, 100.0, 200.0)
    roi_percentage: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # Risk factors
    market_volatility_risk: float = 0.2
    competitive_response_risk: float = 0.3
    algorithm_change_risk: float = 0.1
    brand_safety_risk: float = 0.1

    # Confidence metrics
    prediction_confidence: float = 0.7  # 0.0 - 1.0
    data_quality_score: float = 0.8  # 0.0 - 1.0
    model_accuracy: float = 0.75  # 0.0 - 1.0

    # Timeline
    prediction_horizon_weeks: int = 12
    review_frequency_weeks: int = 4

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StrategicMilestone:
    """Strategic milestone with timeline and success criteria."""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    milestone_type: MilestoneType = MilestoneType.CONTENT_LAUNCH

    # Timeline
    target_date: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(weeks=4))
    duration_days: int = 7

    # Success criteria
    success_metrics: dict[str, float] = field(default_factory=dict)
    success_threshold: float = 0.8  # 0.0 - 1.0

    # Dependencies
    dependencies: list[str] = field(default_factory=list)  # milestone IDs
    blocking_issues: list[str] = field(default_factory=list)

    # Status
    status: str = "planned"  # planned, in_progress, completed, delayed, cancelled
    completion_percentage: float = 0.0
    actual_completion_date: datetime | None = None

    # Impact assessment
    business_impact: float = 0.5
    strategic_importance: str = "medium"
    risk_level: str = "low"


@dataclass
class ContentCalendar:
    """Strategic timeline-based content planning with milestones."""
    id: str = field(default_factory=lambda: str(uuid4()))
    strategy_id: str = ""
    name: str = ""

    # Timeline
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(weeks=12))

    # Strategic milestones
    milestones: list[StrategicMilestone] = field(default_factory=list)

    # Content planning
    weekly_content_targets: dict[str, int] = field(default_factory=dict)  # week -> content count
    platform_distribution: dict[Platform, float] = field(default_factory=dict)
    content_theme_rotation: list[str] = field(default_factory=list)

    # Optimization points
    performance_review_dates: list[datetime] = field(default_factory=list)
    optimization_checkpoints: list[datetime] = field(default_factory=list)
    pivot_decision_dates: list[datetime] = field(default_factory=list)

    # Success tracking
    kpi_targets: dict[str, float] = field(default_factory=dict)
    current_progress: dict[str, float] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)


class StrategicRecommendation(BaseModel):
    """Complete strategic recommendation with implementation plan."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str

    # Strategic focus
    primary_objective: StrategyObjective
    secondary_objectives: list[StrategyObjective] = Field(default_factory=list)
    competitive_position: CompetitivePosition

    # Target analysis
    target_audiences: list[str] = Field(default_factory=list)  # audience segment IDs
    target_platforms: list[Platform] = Field(default_factory=list)
    target_content_types: list[ContentType] = Field(default_factory=list)

    # Content strategy
    content_themes: list[str] = Field(default_factory=list)
    messaging_framework: dict[str, str] = Field(default_factory=dict)
    content_calendar: ContentCalendar

    # Gap analysis
    identified_gaps: list[ContentGap] = Field(default_factory=list)
    opportunity_prioritization: list[str] = Field(default_factory=list)  # gap IDs by priority

    # Resource planning
    resource_plan: ResourcePlan

    # Performance expectations
    performance_prediction: PerformancePrediction

    # Implementation strategy
    implementation_phases: list[str] = Field(default_factory=list)
    risk_mitigation_strategies: list[str] = Field(default_factory=list)
    success_metrics: dict[str, float] = Field(default_factory=dict)

    # Optimization strategy
    optimization_frequency: str = "monthly"  # weekly, bi-weekly, monthly, quarterly
    pivot_triggers: list[str] = Field(default_factory=list)
    scaling_criteria: dict[str, float] = Field(default_factory=dict)

    # Integration points
    belief_alignment_score: float = Field(ge=0.0, le=1.0, description="Alignment with brand beliefs")
    brand_safety_score: float = Field(ge=0.0, le=1.0, description="Brand safety assessment")
    audience_resonance_score: float = Field(ge=0.0, le=1.0, description="Audience resonance potential")
    viral_potential_score: float = Field(ge=0.0, le=1.0, description="Viral content potential")

    # Confidence and quality
    recommendation_confidence: float = Field(ge=0.0, le=1.0, description="Overall recommendation confidence")
    data_quality_score: float = Field(ge=0.0, le=1.0, description="Underlying data quality")
    strategic_coherence_score: float = Field(ge=0.0, le=1.0, description="Strategic coherence assessment")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# Content Strategy Optimizer Core Classes
class ContentGapAnalyzer:
    """Advanced content gap analysis and opportunity identification."""

    def __init__(self):
        self.viral_engine = ViralPredictionEngine()
        self.audience_engine = AudienceSegmentationEngine()
        self.resonance_scorer = ResonanceScorer()

    async def identify_content_gaps(self,
                                  target_audiences: list[AudienceSegment],
                                  existing_content: list[str],
                                  competitive_analysis: dict[str, Any] = None) -> list[ContentGap]:
        """Identify content gaps and opportunities."""
        gaps = []

        # Analyze each audience segment for gaps
        for audience in target_audiences:
            segment_gaps = await self._analyze_audience_gaps(audience, existing_content, competitive_analysis)
            gaps.extend(segment_gaps)

        # Cross-audience gap analysis
        cross_audience_gaps = await self._identify_cross_audience_opportunities(target_audiences)
        gaps.extend(cross_audience_gaps)

        # Score and prioritize gaps
        scored_gaps = await self._score_and_prioritize_gaps(gaps, target_audiences)

        logger.info(f"Identified {len(scored_gaps)} content gaps across {len(target_audiences)} audience segments")
        return scored_gaps

    async def _analyze_audience_gaps(self, audience: AudienceSegment,
                                   existing_content: list[str],
                                   competitive_analysis: dict[str, Any] = None) -> list[ContentGap]:
        """Analyze content gaps for a specific audience segment."""
        gaps = []

        # Analyze content preferences vs existing content
        preference_gaps = await self._identify_preference_gaps(audience, existing_content)
        gaps.extend(preference_gaps)

        # Analyze platform-specific gaps
        platform_gaps = await self._identify_platform_gaps(audience, existing_content)
        gaps.extend(platform_gaps)

        # Analyze format gaps
        format_gaps = await self._identify_format_gaps(audience, existing_content)
        gaps.extend(format_gaps)

        # Analyze competitive gaps
        if competitive_analysis:
            competitive_gaps = await self._identify_competitive_gaps(audience, competitive_analysis)
            gaps.extend(competitive_gaps)

        return gaps

    async def _identify_preference_gaps(self, audience: AudienceSegment,
                                      existing_content: list[str]) -> list[ContentGap]:
        """Identify gaps in content preferences satisfaction."""
        gaps = []

        # Analyze audience content preferences
        top_preferences = sorted(
            audience.behavior_profile.content_preferences.items(),
            key=lambda x: x[1], reverse=True
        )[:3]

        for preference, preference_score in top_preferences:
            # Calculate how well existing content serves this preference
            satisfaction_score = await self._calculate_preference_satisfaction(
                preference, existing_content, audience
            )

            if satisfaction_score < 0.6:  # Significant gap
                gap = ContentGap(
                    title=f"{preference.value.title()} Content Gap",
                    description=f"Audience shows high preference for {preference.value} content but current content portfolio shows low satisfaction",
                    audience_segment=audience.id,
                    topic_area=preference.value,
                    market_demand=preference_score,
                    brand_fit=0.8,  # Assume good brand fit for audience preferences
                    opportunity_score=preference_score * (1.0 - satisfaction_score),
                    strategic_priority="high" if preference_score > 0.7 else "medium",
                    suggested_angles=[
                        f"Create more {preference.value} content",
                        f"Optimize existing content for {preference.value} preferences",
                        f"Develop {preference.value} content series"
                    ]
                )
                gaps.append(gap)

        return gaps

    async def _identify_platform_gaps(self, audience: AudienceSegment,
                                    existing_content: list[str]) -> list[ContentGap]:
        """Identify platform-specific content gaps."""
        gaps = []

        # Analyze platform preferences vs content distribution
        for platform in audience.preferred_platforms:
            platform_content_score = await self._calculate_platform_content_coverage(
                platform, existing_content
            )

            if platform_content_score < 0.5:  # Platform gap
                gap = ContentGap(
                    title=f"{platform.value.title()} Platform Gap",
                    description=f"Audience is active on {platform.value} but content presence is limited",
                    audience_segment=audience.id,
                    platform=platform,
                    topic_area="platform_optimization",
                    market_demand=0.8,
                    brand_fit=0.7,
                    opportunity_score=0.8 * (1.0 - platform_content_score),
                    strategic_priority="high",
                    recommended_content_formats=self._get_platform_optimal_formats(platform),
                    suggested_angles=[
                        f"Develop {platform.value}-native content",
                        f"Adapt existing content for {platform.value}",
                        f"Create {platform.value} engagement campaigns"
                    ]
                )
                gaps.append(gap)

        return gaps

    async def _identify_format_gaps(self, audience: AudienceSegment,
                                  existing_content: list[str]) -> list[ContentGap]:
        """Identify content format gaps."""
        gaps = []

        # Analyze media preferences
        media_prefs = audience.behavior_profile.media_preferences
        if not media_prefs:
            return gaps

        for media_type, preference_score in media_prefs.items():
            if preference_score > 0.6:  # High preference
                format_coverage = await self._calculate_format_coverage(media_type, existing_content)

                if format_coverage < 0.4:  # Format gap
                    content_format = self._map_media_type_to_format(media_type)
                    gap = ContentGap(
                        title=f"{media_type.title()} Format Gap",
                        description=f"Audience prefers {media_type} content but portfolio lacks adequate coverage",
                        audience_segment=audience.id,
                        topic_area="format_diversification",
                        market_demand=preference_score,
                        brand_fit=0.7,
                        opportunity_score=preference_score * (1.0 - format_coverage),
                        strategic_priority="medium",
                        recommended_content_formats=[content_format] if content_format else [],
                        suggested_angles=[
                            f"Develop {media_type} content series",
                            f"Convert existing content to {media_type} format",
                            f"Create interactive {media_type} experiences"
                        ]
                    )
                    gaps.append(gap)

        return gaps

    async def _identify_competitive_gaps(self, audience: AudienceSegment,
                                       competitive_analysis: dict[str, Any]) -> list[ContentGap]:
        """Identify gaps based on competitive analysis."""
        gaps = []

        # Analyze competitor content strategies
        competitor_strengths = competitive_analysis.get("competitor_strengths", [])
        our_weaknesses = competitive_analysis.get("our_weaknesses", [])

        for weakness in our_weaknesses:
            if weakness.get("audience_segment") == audience.id:
                gap = ContentGap(
                    title=f"Competitive Gap: {weakness.get('area', 'Unknown')}",
                    description=weakness.get("description", "Competitive disadvantage identified"),
                    audience_segment=audience.id,
                    topic_area=weakness.get("area", "competitive_positioning"),
                    competition_intensity=weakness.get("competitor_strength", 0.8),
                    market_demand=weakness.get("market_demand", 0.7),
                    brand_fit=weakness.get("brand_fit", 0.6),
                    opportunity_score=weakness.get("opportunity_score", 0.5),
                    strategic_priority=weakness.get("priority", "medium"),
                    suggested_angles=weakness.get("recommendations", [])
                )
                gaps.append(gap)

        return gaps

    async def _identify_cross_audience_opportunities(self, audiences: list[AudienceSegment]) -> list[ContentGap]:
        """Identify opportunities that span multiple audience segments."""
        gaps = []

        if len(audiences) < 2:
            return gaps

        # Find common interests across audiences
        common_interests = await self._find_common_interests(audiences)

        for interest, audience_count in common_interests.items():
            if audience_count >= 2:  # Shared by multiple audiences
                gap = ContentGap(
                    title=f"Cross-Audience Opportunity: {interest}",
                    description=f"Content theme '{interest}' resonates with {audience_count} audience segments",
                    topic_area=interest,
                    market_demand=0.8,
                    brand_fit=0.7,
                    opportunity_score=min(1.0, audience_count / len(audiences)),
                    strategic_priority="high" if audience_count > 2 else "medium",
                    suggested_angles=[
                        f"Create comprehensive {interest} content series",
                        f"Develop {interest} thought leadership campaign",
                        f"Build {interest} community engagement initiatives"
                    ]
                )
                gaps.append(gap)

        return gaps

    async def _score_and_prioritize_gaps(self, gaps: list[ContentGap],
                                       audiences: list[AudienceSegment]) -> list[ContentGap]:
        """Score and prioritize identified content gaps."""
        scored_gaps = []

        for gap in gaps:
            # Calculate comprehensive opportunity score
            opportunity_score = await self._calculate_comprehensive_opportunity_score(gap, audiences)
            gap.opportunity_score = opportunity_score

            # Estimate performance potential
            await self._estimate_gap_performance_potential(gap, audiences)

            # Assess execution requirements
            await self._assess_gap_execution_requirements(gap)

            # Calculate final priority
            gap.strategic_priority = self._calculate_gap_priority(gap)

            scored_gaps.append(gap)

        # Sort by opportunity score
        scored_gaps.sort(key=lambda g: g.opportunity_score, reverse=True)

        return scored_gaps

    async def _calculate_preference_satisfaction(self, preference: ContentPreference,
                                               existing_content: list[str],
                                               audience: AudienceSegment) -> float:
        """Calculate how well existing content satisfies a preference."""
        # Simplified implementation - in production would analyze content against preference
        satisfaction_scores = []

        for content in existing_content[:10]:  # Sample analysis
            # Use resonance scorer to evaluate content-preference alignment
            try:
                resonance = await self.resonance_scorer.calculate_resonance_score(
                    content, audience, {"preference_focus": preference.value}
                )
                satisfaction_scores.append(resonance.overall_score)
            except Exception as e:
                logger.warning(f"Error calculating preference satisfaction: {e}")
                satisfaction_scores.append(0.3)  # Default low satisfaction

        return statistics.mean(satisfaction_scores) if satisfaction_scores else 0.3

    async def _calculate_platform_content_coverage(self, platform: Platform,
                                                 existing_content: list[str]) -> float:
        """Calculate content coverage for a specific platform."""
        # Simplified implementation - analyze platform optimization
        platform_optimized_count = 0

        for content in existing_content:
            # Use viral engine to assess platform optimization
            try:
                viral_prediction = await self.viral_engine.predict_viral_potential(content, platform)
                if viral_prediction.platform_optimization_score > 0.6:
                    platform_optimized_count += 1
            except Exception as e:
                logger.warning(f"Error calculating platform coverage: {e}")

        return platform_optimized_count / max(len(existing_content), 1)

    async def _calculate_format_coverage(self, media_type: str, existing_content: list[str]) -> float:
        """Calculate coverage for a specific content format."""
        # Simplified format analysis
        format_indicators = {
            "video": ["video", "watch", "play", "stream"],
            "image": ["image", "photo", "visual", "graphic"],
            "text": ["article", "post", "blog", "story"],
            "audio": ["podcast", "audio", "listen", "sound"]
        }

        indicators = format_indicators.get(media_type.lower(), [])
        format_content_count = 0

        for content in existing_content:
            content_lower = content.lower()
            if any(indicator in content_lower for indicator in indicators):
                format_content_count += 1

        return format_content_count / max(len(existing_content), 1)

    def _map_media_type_to_format(self, media_type: str) -> ContentFormat | None:
        """Map media type to ContentFormat enum."""
        mapping = {
            "video": ContentFormat.VIDEO,
            "image": ContentFormat.INFOGRAPHIC,
            "text": ContentFormat.LONG_FORM_ARTICLE,
            "audio": ContentFormat.PODCAST
        }
        return mapping.get(media_type.lower())

    def _get_platform_optimal_formats(self, platform: Platform) -> list[ContentFormat]:
        """Get optimal content formats for a platform."""
        platform_formats = {
            Platform.LINKEDIN: [ContentFormat.TEXT_POST, ContentFormat.LONG_FORM_ARTICLE, ContentFormat.CAROUSEL],
            Platform.TWITTER: [ContentFormat.TEXT_POST, ContentFormat.POLL, ContentFormat.VIDEO],
            Platform.GENERAL: [ContentFormat.TEXT_POST, ContentFormat.INFOGRAPHIC, ContentFormat.VIDEO]
        }
        return platform_formats.get(platform, [ContentFormat.TEXT_POST])

    async def _find_common_interests(self, audiences: list[AudienceSegment]) -> dict[str, int]:
        """Find interests common across multiple audience segments."""
        interest_counts = {}

        for audience in audiences:
            interests = audience.psychographic_profile.interests
            for interest in interests.keys():
                interest_counts[interest] = interest_counts.get(interest, 0) + 1

        return interest_counts

    async def _calculate_comprehensive_opportunity_score(self, gap: ContentGap,
                                                       audiences: list[AudienceSegment]) -> float:
        """Calculate comprehensive opportunity score for a gap."""
        # Multi-factor scoring
        factors = [
            gap.market_demand * 0.25,
            gap.brand_fit * 0.20,
            (1.0 - gap.competition_intensity) * 0.15,  # Lower competition = higher opportunity
            (1.0 - gap.execution_difficulty) * 0.15,  # Lower difficulty = higher opportunity
            gap.business_impact * 0.25
        ]

        base_score = sum(factors)

        # Adjust for audience size and quality
        audience_multiplier = 1.0
        if gap.audience_segment:
            matching_audience = next((a for a in audiences if a.id == gap.audience_segment), None)
            if matching_audience:
                audience_multiplier = min(1.5, 1.0 + (matching_audience.quality_score * 0.5))

        return min(1.0, base_score * audience_multiplier)

    async def _estimate_gap_performance_potential(self, gap: ContentGap, audiences: list[AudienceSegment]):
        """Estimate performance potential for a content gap."""
        # Use viral engine to estimate potential
        sample_content = f"Content about {gap.topic_area} targeting {gap.description[:100]}"

        try:
            if gap.platform:
                viral_prediction = await self.viral_engine.predict_viral_potential(sample_content, gap.platform)
                gap.viral_potential = viral_prediction.overall_viral_score
                gap.estimated_engagement_rate = viral_prediction.expected_engagement_rate

                # Estimate reach based on viral potential and audience size
                base_reach = 1000  # Base reach estimate
                if gap.audience_segment:
                    matching_audience = next((a for a in audiences if a.id == gap.audience_segment), None)
                    if matching_audience:
                        base_reach = matching_audience.size_estimate

                gap.estimated_reach = int(base_reach * viral_prediction.reach_potential)
                gap.conversion_potential = viral_prediction.expected_engagement_rate * 0.1  # Rough conversion estimate
        except Exception as e:
            logger.warning(f"Error estimating gap performance: {e}")
            gap.viral_potential = 0.5
            gap.estimated_engagement_rate = 0.03
            gap.estimated_reach = 1000
            gap.conversion_potential = 0.003

    async def _assess_gap_execution_requirements(self, gap: ContentGap):
        """Assess resource requirements for executing a content gap strategy."""
        # Estimate resource requirements based on gap characteristics
        resource_requirements = {}

        # Content creation requirements
        if gap.recommended_content_formats:
            for content_format in gap.recommended_content_formats:
                if content_format in [ContentFormat.VIDEO, ContentFormat.LIVE_STREAM]:
                    resource_requirements[ResourceType.VIDEO_PRODUCTION] = 0.8
                    gap.execution_difficulty = max(gap.execution_difficulty, 0.7)
                elif content_format in [ContentFormat.INFOGRAPHIC, ContentFormat.CAROUSEL]:
                    resource_requirements[ResourceType.DESIGN_VISUAL] = 0.6
                    gap.execution_difficulty = max(gap.execution_difficulty, 0.4)
                else:
                    resource_requirements[ResourceType.CONTENT_CREATION] = 0.5
                    gap.execution_difficulty = max(gap.execution_difficulty, 0.3)

        # Analysis and research requirements
        if gap.competition_intensity > 0.7:
            resource_requirements[ResourceType.RESEARCH_ANALYSIS] = 0.7
            gap.execution_difficulty = max(gap.execution_difficulty, 0.5)

        # Community management for engagement
        resource_requirements[ResourceType.COMMUNITY_MANAGEMENT] = 0.4

        gap.resource_requirements = resource_requirements

    def _calculate_gap_priority(self, gap: ContentGap) -> str:
        """Calculate strategic priority for a content gap."""
        priority_score = (
            gap.opportunity_score * 0.4 +
            gap.business_impact * 0.3 +
            gap.viral_potential * 0.2 +
            (1.0 - gap.execution_difficulty) * 0.1
        )

        if priority_score >= 0.8:
            return "critical"
        elif priority_score >= 0.6:
            return "high"
        elif priority_score >= 0.4:
            return "medium"
        else:
            return "low"


class StrategicPlanner:
    """Strategic timeline planning with milestone recommendations."""

    def __init__(self):
        self.default_milestone_templates = {
            MilestoneType.CONTENT_LAUNCH: {
                "duration_days": 7,
                "success_metrics": {"engagement_rate": 0.03, "reach": 1000},
                "business_impact": 0.6
            },
            MilestoneType.CAMPAIGN_START: {
                "duration_days": 14,
                "success_metrics": {"campaign_reach": 5000, "lead_generation": 10},
                "business_impact": 0.8
            },
            MilestoneType.PERFORMANCE_REVIEW: {
                "duration_days": 3,
                "success_metrics": {"kpi_achievement": 0.8, "roi_positive": 1.0},
                "business_impact": 0.5
            }
        }

    async def create_strategic_timeline(self,
                                      recommendation: StrategicRecommendation,
                                      content_gaps: list[ContentGap],
                                      resource_constraints: dict[str, Any] = None) -> ContentCalendar:
        """Create comprehensive strategic timeline with milestones."""

        # Initialize calendar
        calendar = ContentCalendar(
            strategy_id=recommendation.id,
            name=f"Strategy: {recommendation.title}",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(weeks=12)
        )

        # Create milestone timeline
        milestones = await self._create_milestone_timeline(recommendation, content_gaps, resource_constraints)
        calendar.milestones = milestones

        # Plan content distribution
        await self._plan_content_distribution(calendar, recommendation, content_gaps)

        # Set optimization checkpoints
        await self._set_optimization_checkpoints(calendar, recommendation)

        # Calculate KPI targets
        await self._set_kpi_targets(calendar, recommendation)

        logger.info(f"Created strategic timeline with {len(milestones)} milestones over {(calendar.end_date - calendar.start_date).days} days")
        return calendar

    async def _create_milestone_timeline(self,
                                       recommendation: StrategicRecommendation,
                                       content_gaps: list[ContentGap],
                                       resource_constraints: dict[str, Any] = None) -> list[StrategicMilestone]:
        """Create milestone timeline based on strategy and gaps."""
        milestones = []
        current_date = datetime.utcnow()

        # Phase 1: Strategy Setup (Weeks 1-2)
        setup_milestone = StrategicMilestone(
            title="Strategy Implementation Setup",
            description="Complete initial setup and resource allocation for content strategy",
            milestone_type=MilestoneType.CAMPAIGN_START,
            target_date=current_date + timedelta(weeks=2),
            duration_days=14,
            success_metrics={
                "team_onboarding": 1.0,
                "tool_setup": 1.0,
                "content_calendar_approval": 1.0
            },
            business_impact=0.7,
            strategic_importance="high"
        )
        milestones.append(setup_milestone)

        # Phase 2: Content Gap Execution (Weeks 3-8)
        gap_execution_start = current_date + timedelta(weeks=3)
        high_priority_gaps = [g for g in content_gaps if g.strategic_priority in ["critical", "high"]]

        for i, gap in enumerate(high_priority_gaps[:5]):  # Top 5 high-priority gaps
            gap_milestone = StrategicMilestone(
                title=f"Execute: {gap.title}",
                description=f"Implementation of content strategy for {gap.title}",
                milestone_type=MilestoneType.CONTENT_LAUNCH,
                target_date=gap_execution_start + timedelta(weeks=i),
                duration_days=7,
                success_metrics={
                    "content_published": 1.0,
                    "engagement_rate": gap.estimated_engagement_rate,
                    "reach_target": gap.estimated_reach * 0.8  # 80% of estimated reach
                },
                business_impact=gap.business_impact,
                strategic_importance=gap.strategic_priority
            )
            milestones.append(gap_milestone)

        # Phase 3: Performance Reviews (Every 4 weeks)
        for week in [4, 8, 12]:
            review_date = current_date + timedelta(weeks=week)
            review_milestone = StrategicMilestone(
                title=f"Performance Review - Week {week}",
                description="Comprehensive performance review and strategy optimization",
                milestone_type=MilestoneType.PERFORMANCE_REVIEW,
                target_date=review_date,
                duration_days=3,
                success_metrics={
                    "kpi_achievement": 0.8,
                    "roi_assessment": 1.0,
                    "optimization_recommendations": 1.0
                },
                business_impact=0.6,
                strategic_importance="medium"
            )
            milestones.append(review_milestone)

        # Phase 4: Optimization Checkpoints (Weeks 6, 10)
        for week in [6, 10]:
            optimization_date = current_date + timedelta(weeks=week)
            optimization_milestone = StrategicMilestone(
                title=f"Strategy Optimization - Week {week}",
                description="Strategic optimization based on performance data",
                milestone_type=MilestoneType.OPTIMIZATION_CHECKPOINT,
                target_date=optimization_date,
                duration_days=5,
                success_metrics={
                    "optimization_implemented": 1.0,
                    "performance_improvement": 0.1  # 10% improvement target
                },
                business_impact=0.7,
                strategic_importance="high"
            )
            milestones.append(optimization_milestone)

        # Sort milestones by target date
        milestones.sort(key=lambda m: m.target_date)

        # Set dependencies
        for i in range(1, len(milestones)):
            # Each milestone depends on the previous one
            milestones[i].dependencies = [milestones[i-1].id]

        return milestones

    async def _plan_content_distribution(self, calendar: ContentCalendar,
                                       recommendation: StrategicRecommendation,
                                       content_gaps: list[ContentGap]):
        """Plan weekly content distribution targets."""
        total_weeks = (calendar.end_date - calendar.start_date).days // 7

        # Calculate base content targets
        base_weekly_content = 3  # Base target

        # Adjust based on resource plan
        if recommendation.resource_plan.content_creation_hours > 15:
            base_weekly_content = 5
        elif recommendation.resource_plan.content_creation_hours < 10:
            base_weekly_content = 2

        # Set weekly targets with ramp-up
        for week in range(total_weeks):
            week_key = f"week_{week + 1}"
            if week < 2:  # Ramp-up period
                calendar.weekly_content_targets[week_key] = max(1, base_weekly_content // 2)
            elif week < 4:  # Build-up period
                calendar.weekly_content_targets[week_key] = base_weekly_content
            else:  # Full capacity
                calendar.weekly_content_targets[week_key] = base_weekly_content

        # Set platform distribution
        total_platform_weight = sum(
            1.0 for platform in recommendation.target_platforms
        )

        for platform in recommendation.target_platforms:
            calendar.platform_distribution[platform] = 1.0 / total_platform_weight

        # Set content theme rotation
        calendar.content_theme_rotation = recommendation.content_themes[:4]  # Rotate top 4 themes

    async def _set_optimization_checkpoints(self, calendar: ContentCalendar,
                                          recommendation: StrategicRecommendation):
        """Set performance review and optimization checkpoint dates."""
        start_date = calendar.start_date

        # Performance reviews every 4 weeks
        for week in [4, 8, 12]:
            review_date = start_date + timedelta(weeks=week)
            calendar.performance_review_dates.append(review_date)

        # Optimization checkpoints every 6 weeks
        for week in [6, 12]:
            optimization_date = start_date + timedelta(weeks=week)
            calendar.optimization_checkpoints.append(optimization_date)

        # Pivot decision points at 8 and 16 weeks
        for week in [8, 16]:
            if week <= 12:  # Within calendar period
                pivot_date = start_date + timedelta(weeks=week)
                calendar.pivot_decision_dates.append(pivot_date)

    async def _set_kpi_targets(self, calendar: ContentCalendar,
                             recommendation: StrategicRecommendation):
        """Set KPI targets based on performance predictions."""
        prediction = recommendation.performance_prediction

        # Set targets based on expected values from predictions
        calendar.kpi_targets = {
            "reach": prediction.predicted_reach[1],  # Expected reach
            "engagement_rate": prediction.predicted_engagement_rate[1],
            "click_rate": prediction.predicted_click_rate[1],
            "conversion_rate": prediction.predicted_conversion_rate[1],
            "follower_growth": prediction.follower_growth[1],
            "lead_generation": prediction.estimated_leads[1],
            "roi_percentage": prediction.roi_percentage[1]
        }

        # Initialize current progress tracking
        calendar.current_progress = dict.fromkeys(calendar.kpi_targets.keys(), 0.0)


class PerformancePredictor:
    """Performance prediction with confidence intervals and ROI estimation."""

    def __init__(self):
        self.viral_engine = ViralPredictionEngine()
        self.audience_engine = AudienceSegmentationEngine()

        # Historical performance baselines (would be learned from data)
        self.baseline_metrics = {
            "engagement_rate": (0.01, 0.03, 0.08),  # min, expected, max
            "click_rate": (0.005, 0.02, 0.05),
            "conversion_rate": (0.001, 0.005, 0.02),
            "follower_growth_weekly": (10, 50, 200),
        }

    async def predict_strategy_performance(self,
                                         recommendation: StrategicRecommendation,
                                         content_gaps: list[ContentGap],
                                         historical_data: dict[str, Any] = None) -> PerformancePrediction:
        """Predict comprehensive performance for content strategy."""

        prediction = PerformancePrediction(
            strategy_id=recommendation.id,
            prediction_horizon_weeks=12
        )

        # Predict engagement metrics
        await self._predict_engagement_metrics(prediction, recommendation, content_gaps)

        # Predict growth metrics
        await self._predict_growth_metrics(prediction, recommendation, content_gaps)

        # Predict ROI metrics
        await self._predict_roi_metrics(prediction, recommendation, content_gaps)

        # Assess prediction confidence
        await self._assess_prediction_confidence(prediction, recommendation, historical_data)

        # Calculate risk factors
        await self._calculate_risk_factors(prediction, recommendation)

        logger.info(f"Generated performance prediction with {prediction.prediction_confidence:.2f} confidence")
        return prediction

    async def _predict_engagement_metrics(self, prediction: PerformancePrediction,
                                        recommendation: StrategicRecommendation,
                                        content_gaps: list[ContentGap]):
        """Predict engagement-related metrics."""

        # Aggregate viral predictions from content gaps
        viral_scores = []
        engagement_rates = []
        reach_estimates = []

        for gap in content_gaps[:10]:  # Top 10 gaps
            if gap.viral_potential > 0:
                viral_scores.append(gap.viral_potential)
                engagement_rates.append(gap.estimated_engagement_rate)
                reach_estimates.append(gap.estimated_reach)

        # Calculate baseline predictions
        if viral_scores:
            avg_viral_score = statistics.mean(viral_scores)
            avg_engagement_rate = statistics.mean(engagement_rates)
            total_reach = sum(reach_estimates)
        else:
            avg_viral_score = 0.5
            avg_engagement_rate = 0.03
            total_reach = 5000

        # Apply multipliers based on strategy quality
        strategy_multiplier = (
            recommendation.recommendation_confidence * 0.5 +
            recommendation.audience_resonance_score * 0.3 +
            recommendation.brand_safety_score * 0.2
        )

        # Reach predictions with confidence intervals
        base_reach = int(total_reach * strategy_multiplier)
        prediction.predicted_reach = (
            int(base_reach * 0.7),  # Conservative estimate
            base_reach,  # Expected
            int(base_reach * 1.5)   # Optimistic estimate
        )

        # Engagement rate predictions
        base_engagement = avg_engagement_rate * strategy_multiplier
        prediction.predicted_engagement_rate = (
            base_engagement * 0.6,
            base_engagement,
            base_engagement * 1.8
        )

        # Click rate predictions (typically 20-50% of engagement rate)
        base_click_rate = base_engagement * 0.3
        prediction.predicted_click_rate = (
            base_click_rate * 0.5,
            base_click_rate,
            base_click_rate * 2.0
        )

        # Conversion rate predictions (typically 1-10% of click rate)
        base_conversion_rate = base_click_rate * 0.05
        prediction.predicted_conversion_rate = (
            base_conversion_rate * 0.2,
            base_conversion_rate,
            base_conversion_rate * 5.0
        )

    async def _predict_growth_metrics(self, prediction: PerformancePrediction,
                                    recommendation: StrategicRecommendation,
                                    content_gaps: list[ContentGap]):
        """Predict growth-related metrics."""

        # Base follower growth calculation
        strategy_quality = recommendation.recommendation_confidence
        content_quality = statistics.mean([gap.opportunity_score for gap in content_gaps[:5]]) if content_gaps else 0.5

        weekly_base_growth = 50 * strategy_quality * content_quality
        total_weeks = prediction.prediction_horizon_weeks

        # Follower growth over prediction horizon
        total_growth = int(weekly_base_growth * total_weeks)
        prediction.follower_growth = (
            int(total_growth * 0.5),
            total_growth,
            int(total_growth * 2.0)
        )

        # Brand mention increase (based on viral potential)
        avg_viral_potential = statistics.mean([gap.viral_potential for gap in content_gaps[:5]]) if content_gaps else 0.5
        mention_increase = avg_viral_potential * 0.5  # 50% increase at max viral potential

        prediction.brand_mention_increase = (
            mention_increase * 0.3,
            mention_increase,
            mention_increase * 2.0
        )

        # Website traffic increase
        traffic_increase = (
            prediction.predicted_click_rate[1] * prediction.predicted_reach[1] / 1000
        )  # Rough estimate

        prediction.website_traffic_increase = (
            traffic_increase * 0.5,
            traffic_increase,
            traffic_increase * 1.8
        )

    async def _predict_roi_metrics(self, prediction: PerformancePrediction,
                                 recommendation: StrategicRecommendation,
                                 content_gaps: list[ContentGap]):
        """Predict ROI and business impact metrics."""

        # Lead generation predictions
        base_leads = int(
            prediction.predicted_reach[1] *
            prediction.predicted_conversion_rate[1]
        )

        prediction.estimated_leads = (
            int(base_leads * 0.4),
            base_leads,
            int(base_leads * 2.5)
        )

        # Revenue predictions (assuming average deal value)
        avg_deal_value = 500  # Configurable based on business
        base_revenue = base_leads * avg_deal_value * 0.2  # 20% lead-to-customer rate

        prediction.estimated_revenue = (
            base_revenue * 0.3,
            base_revenue,
            base_revenue * 3.0
        )

        # Cost per lead calculation
        total_monthly_cost = recommendation.resource_plan.total_monthly_budget
        total_cost = total_monthly_cost * (prediction.prediction_horizon_weeks / 4.33)  # Convert to campaign cost

        if base_leads > 0:
            base_cost_per_lead = total_cost / base_leads
            prediction.cost_per_lead = (
                base_cost_per_lead * 0.4,  # Best case (more leads, same cost)
                base_cost_per_lead,        # Expected
                base_cost_per_lead * 2.5   # Worst case (fewer leads, same cost)
            )
        else:
            prediction.cost_per_lead = (100.0, 200.0, 500.0)  # Default estimates

        # ROI calculation
        if total_cost > 0:
            base_roi = ((base_revenue - total_cost) / total_cost) * 100
            prediction.roi_percentage = (
                max(-50.0, base_roi - 50),  # Cap losses at -50%
                base_roi,
                base_roi + 100  # Optimistic scenario
            )
        else:
            prediction.roi_percentage = (-10.0, 50.0, 200.0)  # Default estimates

    async def _assess_prediction_confidence(self, prediction: PerformancePrediction,
                                          recommendation: StrategicRecommendation,
                                          historical_data: dict[str, Any] = None):
        """Assess confidence in predictions based on data quality and strategy coherence."""

        confidence_factors = []

        # Strategy quality factor
        strategy_confidence = recommendation.recommendation_confidence
        confidence_factors.append(strategy_confidence)

        # Data quality factor
        data_quality = recommendation.data_quality_score
        confidence_factors.append(data_quality)

        # Historical data availability
        if historical_data and len(historical_data.get("past_campaigns", [])) > 3:
            historical_factor = 0.9
        elif historical_data:
            historical_factor = 0.6
        else:
            historical_factor = 0.4
        confidence_factors.append(historical_factor)

        # Audience intelligence quality
        audience_factor = recommendation.audience_resonance_score
        confidence_factors.append(audience_factor)

        # Brand safety factor (lower risk = higher confidence)
        safety_factor = recommendation.brand_safety_score
        confidence_factors.append(safety_factor)

        # Calculate overall confidence
        prediction.prediction_confidence = statistics.mean(confidence_factors)
        prediction.data_quality_score = data_quality
        prediction.model_accuracy = min(0.9, prediction.prediction_confidence + 0.1)

    async def _calculate_risk_factors(self, prediction: PerformancePrediction,
                                    recommendation: StrategicRecommendation):
        """Calculate various risk factors that could impact performance."""

        # Market volatility risk
        if recommendation.primary_objective in [StrategyObjective.LEAD_GENERATION, StrategyObjective.CONVERSION]:
            prediction.market_volatility_risk = 0.3  # Higher for conversion-focused strategies
        else:
            prediction.market_volatility_risk = 0.2

        # Competitive response risk
        if recommendation.competitive_position == CompetitivePosition.CHALLENGER:
            prediction.competitive_response_risk = 0.4  # Higher for challengers
        else:
            prediction.competitive_response_risk = 0.2

        # Algorithm change risk (platform-dependent)
        platform_count = len(recommendation.target_platforms)
        prediction.algorithm_change_risk = min(0.3, 0.1 * platform_count)

        # Brand safety risk
        prediction.brand_safety_risk = 1.0 - recommendation.brand_safety_score


class ContentStrategyOptimizer:
    """Main AI-powered content strategy recommendation engine."""

    def __init__(self, brand_profile: BrandProfile = BrandProfile.MODERATE):
        """Initialize the content strategy optimizer.
        
        Args:
            brand_profile: Brand safety profile to use for analysis
        """
        self.brand_profile = brand_profile

        # Initialize component engines
        self.belief_extractor = BeliefPreferenceExtractor()
        self.viral_engine = ViralPredictionEngine()
        self.brand_safety_analyzer = BrandSafetyAnalyzer(brand_profile)
        self.audience_engine = AudienceSegmentationEngine()
        self.resonance_scorer = ResonanceScorer()

        # Initialize strategy components
        self.gap_analyzer = ContentGapAnalyzer()
        self.strategic_planner = StrategicPlanner()
        self.performance_predictor = PerformancePredictor()

        logger.info(f"ContentStrategyOptimizer initialized with {brand_profile.value} brand profile")

    async def generate_comprehensive_strategy(self,
                                            business_context: dict[str, Any],
                                            content_samples: list[str] = None,
                                            competitive_analysis: dict[str, Any] = None,
                                            historical_performance: dict[str, Any] = None) -> StrategicRecommendation:
        """Generate comprehensive AI-powered content strategy recommendation.
        
        Args:
            business_context: Business objectives, target audience info, brand guidelines
            content_samples: Sample content for analysis and belief extraction
            competitive_analysis: Competitive landscape analysis
            historical_performance: Historical content performance data
            
        Returns:
            Complete strategic recommendation with implementation plan
        """
        try:
            logger.info("Starting comprehensive content strategy generation")

            # Phase 1: Multi-dimensional Analysis
            analysis_results = await self._perform_multi_dimensional_analysis(
                business_context, content_samples, competitive_analysis
            )

            # Phase 2: Strategic Objective Optimization
            optimized_objectives = await self._optimize_strategic_objectives(
                business_context, analysis_results
            )

            # Phase 3: Content Gap Analysis
            content_gaps = await self._perform_content_gap_analysis(
                analysis_results, competitive_analysis
            )

            # Phase 4: Resource Planning
            resource_plan = await self._create_resource_plan(
                business_context, content_gaps, optimized_objectives
            )

            # Phase 5: Performance Prediction
            performance_prediction = await self._predict_strategy_performance(
                optimized_objectives, content_gaps, resource_plan, historical_performance
            )

            # Phase 6: Strategic Timeline Creation
            content_calendar = await self._create_strategic_timeline(
                optimized_objectives, content_gaps, resource_plan
            )

            # Phase 7: Integration Scoring
            integration_scores = await self._calculate_integration_scores(
                analysis_results, content_gaps, optimized_objectives
            )

            # Phase 8: Build Final Recommendation
            recommendation = await self._build_final_recommendation(
                business_context, optimized_objectives, content_gaps, resource_plan,
                performance_prediction, content_calendar, integration_scores, analysis_results
            )

            logger.info(f"Generated comprehensive strategy with {recommendation.recommendation_confidence:.2f} confidence")
            return recommendation

        except Exception as e:
            logger.error(f"Error generating content strategy: {str(e)}")
            return await self._create_fallback_strategy(business_context)

    async def optimize_existing_strategy(self,
                                       existing_strategy: StrategicRecommendation,
                                       performance_data: dict[str, Any],
                                       market_changes: dict[str, Any] = None) -> StrategicRecommendation:
        """Optimize an existing content strategy based on performance data."""

        logger.info(f"Optimizing existing strategy: {existing_strategy.title}")

        # Analyze current performance vs predictions
        performance_analysis = await self._analyze_strategy_performance(
            existing_strategy, performance_data
        )

        # Identify optimization opportunities
        optimization_opportunities = await self._identify_optimization_opportunities(
            existing_strategy, performance_analysis, market_changes
        )

        # Update strategy components
        optimized_strategy = await self._apply_optimizations(
            existing_strategy, optimization_opportunities, performance_data
        )

        # Update predictions based on new data
        optimized_strategy.performance_prediction = await self.performance_predictor.predict_strategy_performance(
            optimized_strategy, optimized_strategy.identified_gaps, performance_data
        )

        # Update timeline if needed
        if optimization_opportunities.get("timeline_adjustment_needed", False):
            optimized_strategy.content_calendar = await self.strategic_planner.create_strategic_timeline(
                optimized_strategy, optimized_strategy.identified_gaps
            )

        optimized_strategy.last_updated = datetime.utcnow()

        logger.info(f"Strategy optimization completed with {len(optimization_opportunities)} opportunities addressed")
        return optimized_strategy

    async def _perform_multi_dimensional_analysis(self,
                                                business_context: dict[str, Any],
                                                content_samples: list[str] = None,
                                                competitive_analysis: dict[str, Any] = None) -> dict[str, Any]:
        """Perform comprehensive multi-dimensional analysis."""

        analysis_results = {}

        # Belief and preference analysis
        if content_samples:
            belief_analysis = await self._analyze_beliefs_and_preferences(content_samples)
            analysis_results["beliefs"] = belief_analysis

        # Audience intelligence analysis
        target_description = business_context.get("target_audience", "")
        if target_description:
            audience_analysis = await self.audience_engine.analyze_audience(target_description)
            analysis_results["audience"] = audience_analysis

        # Brand safety baseline
        brand_safety_baseline = await self._establish_brand_safety_baseline(
            business_context, content_samples
        )
        analysis_results["brand_safety"] = brand_safety_baseline

        # Viral potential baseline
        if content_samples:
            viral_baseline = await self._analyze_viral_potential_baseline(content_samples)
            analysis_results["viral_baseline"] = viral_baseline

        # Competitive positioning
        if competitive_analysis:
            competitive_position = await self._analyze_competitive_position(competitive_analysis)
            analysis_results["competitive_position"] = competitive_position

        return analysis_results

    async def _optimize_strategic_objectives(self,
                                           business_context: dict[str, Any],
                                           analysis_results: dict[str, Any]) -> dict[str, Any]:
        """Optimize strategic objectives based on analysis results."""

        # Extract business objectives
        stated_objectives = business_context.get("objectives", [])
        budget_range = business_context.get("budget", {})
        timeline = business_context.get("timeline", {})

        # Determine primary objective based on business context and capabilities
        primary_objective = await self._determine_optimal_primary_objective(
            stated_objectives, analysis_results, budget_range
        )

        # Determine secondary objectives
        secondary_objectives = await self._determine_secondary_objectives(
            primary_objective, analysis_results, timeline
        )

        # Determine competitive positioning
        competitive_position = await self._determine_competitive_positioning(
            analysis_results, business_context
        )

        # Select target platforms
        target_platforms = await self._optimize_platform_selection(
            analysis_results, primary_objective
        )

        # Define content themes
        content_themes = await self._define_content_themes(
            analysis_results, primary_objective, competitive_position
        )

        return {
            "primary_objective": primary_objective,
            "secondary_objectives": secondary_objectives,
            "competitive_position": competitive_position,
            "target_platforms": target_platforms,
            "content_themes": content_themes,
            "messaging_framework": await self._create_messaging_framework(analysis_results)
        }

    async def _perform_content_gap_analysis(self,
                                          analysis_results: dict[str, Any],
                                          competitive_analysis: dict[str, Any] = None) -> list[ContentGap]:
        """Perform comprehensive content gap analysis."""

        # Extract target audiences from analysis
        target_audiences = []
        if "audience" in analysis_results and analysis_results["audience"].get("audience_segment"):
            # Convert audience analysis to AudienceSegment objects
            audience_data = analysis_results["audience"]["audience_segment"]
            target_audiences = [AudienceSegment(**audience_data)]

        # Use existing content from analysis as baseline
        existing_content = []
        if "viral_baseline" in analysis_results:
            existing_content = analysis_results["viral_baseline"].get("analyzed_content", [])

        # Perform gap analysis
        content_gaps = await self.gap_analyzer.identify_content_gaps(
            target_audiences, existing_content, competitive_analysis
        )

        return content_gaps

    async def _create_resource_plan(self,
                                  business_context: dict[str, Any],
                                  content_gaps: list[ContentGap],
                                  optimized_objectives: dict[str, Any]) -> ResourcePlan:
        """Create comprehensive resource plan."""

        budget_info = business_context.get("budget", {})
        team_size = business_context.get("team_size", {})
        timeline_weeks = business_context.get("timeline", {}).get("weeks", 12)

        # Calculate resource requirements based on content gaps
        total_content_creation_hours = 0
        total_design_hours = 0
        total_video_hours = 0

        for gap in content_gaps[:10]:  # Top 10 gaps
            if ResourceType.CONTENT_CREATION in gap.resource_requirements:
                total_content_creation_hours += gap.resource_requirements[ResourceType.CONTENT_CREATION] * 10
            if ResourceType.DESIGN_VISUAL in gap.resource_requirements:
                total_design_hours += gap.resource_requirements[ResourceType.DESIGN_VISUAL] * 8
            if ResourceType.VIDEO_PRODUCTION in gap.resource_requirements:
                total_video_hours += gap.resource_requirements[ResourceType.VIDEO_PRODUCTION] * 15

        # Create resource plan
        resource_plan = ResourcePlan(
            content_creation_hours=max(10, total_content_creation_hours / timeline_weeks),
            design_hours=max(5, total_design_hours / timeline_weeks),
            video_production_hours=total_video_hours / timeline_weeks,
            community_management_hours=8,  # Base requirement
            analysis_hours=4,  # Base requirement
            implementation_weeks=timeline_weeks
        )

        # Adjust budgets based on business context
        if budget_info.get("monthly_budget"):
            monthly_budget = budget_info["monthly_budget"]
            resource_plan.content_budget = monthly_budget * 0.3
            resource_plan.design_budget = monthly_budget * 0.2
            resource_plan.video_budget = monthly_budget * 0.2
            resource_plan.promotion_budget = monthly_budget * 0.25
            resource_plan.tools_budget = monthly_budget * 0.05

        return resource_plan

    async def _predict_strategy_performance(self,
                                          optimized_objectives: dict[str, Any],
                                          content_gaps: list[ContentGap],
                                          resource_plan: ResourcePlan,
                                          historical_performance: dict[str, Any] = None) -> PerformancePrediction:
        """Predict strategy performance."""

        # Create temporary recommendation for prediction
        temp_recommendation = StrategicRecommendation(
            title="Temporary for Prediction",
            description="",
            primary_objective=optimized_objectives["primary_objective"],
            target_platforms=optimized_objectives["target_platforms"],
            resource_plan=resource_plan,
            recommendation_confidence=0.7,
            audience_resonance_score=0.7,
            brand_safety_score=0.8,
            performance_prediction=PerformancePrediction()  # Will be replaced
        )

        return await self.performance_predictor.predict_strategy_performance(
            temp_recommendation, content_gaps, historical_performance
        )

    async def _create_strategic_timeline(self,
                                       optimized_objectives: dict[str, Any],
                                       content_gaps: list[ContentGap],
                                       resource_plan: ResourcePlan) -> ContentCalendar:
        """Create strategic timeline."""

        # Create temporary recommendation for timeline planning
        temp_recommendation = StrategicRecommendation(
            title="Timeline Planning",
            description="",
            primary_objective=optimized_objectives["primary_objective"],
            target_platforms=optimized_objectives["target_platforms"],
            content_themes=optimized_objectives["content_themes"],
            resource_plan=resource_plan,
            performance_prediction=PerformancePrediction()
        )

        return await self.strategic_planner.create_strategic_timeline(
            temp_recommendation, content_gaps
        )

    async def _calculate_integration_scores(self,
                                          analysis_results: dict[str, Any],
                                          content_gaps: list[ContentGap],
                                          optimized_objectives: dict[str, Any]) -> dict[str, float]:
        """Calculate integration scores across all epic components."""

        # Belief alignment score
        belief_alignment = 0.7  # Default
        if "beliefs" in analysis_results:
            belief_data = analysis_results["beliefs"]
            belief_alignment = belief_data.get("overall_confidence", 0.7)

        # Brand safety score
        brand_safety = 0.8  # Default
        if "brand_safety" in analysis_results:
            safety_data = analysis_results["brand_safety"]
            brand_safety = safety_data.get("average_safety_score", 0.8)

        # Audience resonance score
        audience_resonance = 0.7  # Default
        if "audience" in analysis_results:
            audience_data = analysis_results["audience"]
            audience_resonance = audience_data.get("overall_confidence", 0.7)

        # Viral potential score
        viral_potential = 0.6  # Default
        if content_gaps:
            viral_scores = [gap.viral_potential for gap in content_gaps if gap.viral_potential > 0]
            viral_potential = statistics.mean(viral_scores) if viral_scores else 0.6

        return {
            "belief_alignment_score": belief_alignment,
            "brand_safety_score": brand_safety,
            "audience_resonance_score": audience_resonance,
            "viral_potential_score": viral_potential
        }

    async def _build_final_recommendation(self,
                                        business_context: dict[str, Any],
                                        optimized_objectives: dict[str, Any],
                                        content_gaps: list[ContentGap],
                                        resource_plan: ResourcePlan,
                                        performance_prediction: PerformancePrediction,
                                        content_calendar: ContentCalendar,
                                        integration_scores: dict[str, float],
                                        analysis_results: dict[str, Any]) -> StrategicRecommendation:
        """Build final strategic recommendation."""

        # Generate recommendation title and description
        title = f"{optimized_objectives['primary_objective'].value.title().replace('_', ' ')} Strategy"
        description = f"AI-powered content strategy optimized for {optimized_objectives['primary_objective'].value} targeting {len(content_gaps)} identified opportunities"

        # Calculate overall confidence
        confidence_factors = [
            integration_scores["belief_alignment_score"],
            integration_scores["brand_safety_score"],
            integration_scores["audience_resonance_score"],
            performance_prediction.prediction_confidence,
            min(1.0, len(content_gaps) / 5.0)  # Gap analysis completeness
        ]
        recommendation_confidence = statistics.mean(confidence_factors)

        # Calculate data quality score
        data_quality_factors = [
            integration_scores["audience_resonance_score"],
            performance_prediction.data_quality_score,
            1.0 if business_context.get("historical_data") else 0.5
        ]
        data_quality_score = statistics.mean(data_quality_factors)

        # Calculate strategic coherence
        strategic_coherence = min(1.0, (
            integration_scores["belief_alignment_score"] * 0.3 +
            integration_scores["brand_safety_score"] * 0.3 +
            (len(content_gaps) / 10.0) * 0.2 +  # Gap analysis depth
            (len(optimized_objectives["content_themes"]) / 5.0) * 0.2  # Theme coherence
        ))

        # Create implementation phases
        implementation_phases = [
            "Phase 1: Strategy Setup & Team Onboarding (Weeks 1-2)",
            "Phase 2: Content Gap Execution (Weeks 3-8)",
            "Phase 3: Performance Optimization (Weeks 9-12)",
            "Phase 4: Scaling & Evolution (Ongoing)"
        ]

        # Create risk mitigation strategies
        risk_mitigation_strategies = [
            "Regular performance monitoring and KPI tracking",
            "Agile content creation with rapid iteration cycles",
            "Brand safety checkpoints for all content",
            "Competitive intelligence and market trend monitoring",
            "Audience feedback loops and sentiment tracking"
        ]

        # Create success metrics
        success_metrics = {
            "reach_target": performance_prediction.predicted_reach[1],
            "engagement_rate_target": performance_prediction.predicted_engagement_rate[1],
            "conversion_rate_target": performance_prediction.predicted_conversion_rate[1],
            "roi_target": performance_prediction.roi_percentage[1],
            "brand_safety_score": integration_scores["brand_safety_score"]
        }

        # Build final recommendation
        recommendation = StrategicRecommendation(
            title=title,
            description=description,
            primary_objective=optimized_objectives["primary_objective"],
            secondary_objectives=optimized_objectives["secondary_objectives"],
            competitive_position=optimized_objectives["competitive_position"],
            target_platforms=optimized_objectives["target_platforms"],
            content_themes=optimized_objectives["content_themes"],
            messaging_framework=optimized_objectives["messaging_framework"],
            content_calendar=content_calendar,
            identified_gaps=content_gaps,
            opportunity_prioritization=[gap.id for gap in sorted(content_gaps, key=lambda g: g.opportunity_score, reverse=True)],
            resource_plan=resource_plan,
            performance_prediction=performance_prediction,
            implementation_phases=implementation_phases,
            risk_mitigation_strategies=risk_mitigation_strategies,
            success_metrics=success_metrics,
            belief_alignment_score=integration_scores["belief_alignment_score"],
            brand_safety_score=integration_scores["brand_safety_score"],
            audience_resonance_score=integration_scores["audience_resonance_score"],
            viral_potential_score=integration_scores["viral_potential_score"],
            recommendation_confidence=recommendation_confidence,
            data_quality_score=data_quality_score,
            strategic_coherence_score=strategic_coherence
        )

        return recommendation

    # Helper methods for analysis
    async def _analyze_beliefs_and_preferences(self, content_samples: list[str]) -> dict[str, Any]:
        """Analyze beliefs and preferences from content samples."""
        all_beliefs = []
        all_preferences = []

        for content in content_samples[:5]:  # Analyze top 5 samples
            try:
                belief_analysis = await self.belief_extractor.extract_beliefs_and_preferences(content)
                all_beliefs.extend(belief_analysis.get("beliefs", []))
                all_preferences.extend(belief_analysis.get("preferences", []))
            except Exception as e:
                logger.warning(f"Error analyzing beliefs in content: {e}")

        return {
            "beliefs": all_beliefs,
            "preferences": all_preferences,
            "belief_count": len(all_beliefs),
            "preference_count": len(all_preferences),
            "overall_confidence": min(1.0, (len(all_beliefs) + len(all_preferences)) / 10.0)
        }

    async def _establish_brand_safety_baseline(self,
                                             business_context: dict[str, Any],
                                             content_samples: list[str] = None) -> dict[str, Any]:
        """Establish brand safety baseline."""
        safety_scores = []

        if content_samples:
            for content in content_samples[:3]:
                try:
                    safety_assessment = await self.brand_safety_analyzer.assess_brand_safety(content)
                    safety_scores.append(safety_assessment.risk_score.overall)
                except Exception as e:
                    logger.warning(f"Error in brand safety assessment: {e}")
                    safety_scores.append(0.2)  # Assume low risk

        average_safety_score = 1.0 - statistics.mean(safety_scores) if safety_scores else 0.8

        return {
            "average_safety_score": average_safety_score,
            "brand_profile": self.brand_profile.value,
            "assessment_count": len(safety_scores)
        }

    async def _analyze_viral_potential_baseline(self, content_samples: list[str]) -> dict[str, Any]:
        """Analyze baseline viral potential."""
        viral_scores = []

        for content in content_samples[:3]:
            try:
                viral_prediction = await self.viral_engine.predict_viral_potential(content)
                viral_scores.append(viral_prediction.overall_viral_score)
            except Exception as e:
                logger.warning(f"Error in viral prediction: {e}")
                viral_scores.append(0.4)  # Default moderate potential

        return {
            "average_viral_score": statistics.mean(viral_scores) if viral_scores else 0.4,
            "analyzed_content": content_samples,
            "prediction_count": len(viral_scores)
        }

    async def _analyze_competitive_position(self, competitive_analysis: dict[str, Any]) -> dict[str, Any]:
        """Analyze competitive positioning."""
        # Extract competitive insights
        competitor_count = len(competitive_analysis.get("competitors", []))
        market_saturation = competitive_analysis.get("market_saturation", 0.5)
        our_position = competitive_analysis.get("current_position", "follower")

        return {
            "competitor_count": competitor_count,
            "market_saturation": market_saturation,
            "current_position": our_position,
            "recommended_position": "challenger" if market_saturation < 0.7 else "nicher"
        }

    async def _determine_optimal_primary_objective(self,
                                                 stated_objectives: list[str],
                                                 analysis_results: dict[str, Any],
                                                 budget_range: dict[str, Any]) -> StrategyObjective:
        """Determine optimal primary objective."""

        # Map stated objectives to StrategyObjective enum
        objective_mapping = {
            "awareness": StrategyObjective.BRAND_AWARENESS,
            "leads": StrategyObjective.LEAD_GENERATION,
            "thought_leadership": StrategyObjective.THOUGHT_LEADERSHIP,
            "engagement": StrategyObjective.ENGAGEMENT,
            "conversion": StrategyObjective.CONVERSION,
            "community": StrategyObjective.COMMUNITY_BUILDING,
            "retention": StrategyObjective.CUSTOMER_RETENTION
        }

        # Check for explicitly stated objective
        for stated in stated_objectives:
            for key, obj in objective_mapping.items():
                if key in stated.lower():
                    return obj

        # Determine based on analysis results and budget
        monthly_budget = budget_range.get("monthly_budget", 5000)

        # High budget + good viral potential = thought leadership
        if monthly_budget > 10000 and analysis_results.get("viral_baseline", {}).get("average_viral_score", 0) > 0.6:
            return StrategyObjective.THOUGHT_LEADERSHIP

        # Medium budget + good audience data = lead generation
        if monthly_budget > 5000 and analysis_results.get("audience", {}).get("overall_confidence", 0) > 0.6:
            return StrategyObjective.LEAD_GENERATION

        # Default to brand awareness for broader reach
        return StrategyObjective.BRAND_AWARENESS

    async def _determine_secondary_objectives(self,
                                            primary_objective: StrategyObjective,
                                            analysis_results: dict[str, Any],
                                            timeline: dict[str, Any]) -> list[StrategyObjective]:
        """Determine secondary objectives."""
        secondary = []

        # Add complementary objectives based on primary
        if primary_objective == StrategyObjective.BRAND_AWARENESS:
            secondary.extend([StrategyObjective.ENGAGEMENT, StrategyObjective.COMMUNITY_BUILDING])
        elif primary_objective == StrategyObjective.LEAD_GENERATION:
            secondary.extend([StrategyObjective.THOUGHT_LEADERSHIP, StrategyObjective.CONVERSION])
        elif primary_objective == StrategyObjective.THOUGHT_LEADERSHIP:
            secondary.extend([StrategyObjective.BRAND_AWARENESS, StrategyObjective.ENGAGEMENT])
        else:
            secondary.append(StrategyObjective.ENGAGEMENT)

        return secondary[:2]  # Max 2 secondary objectives

    async def _determine_competitive_positioning(self,
                                               analysis_results: dict[str, Any],
                                               business_context: dict[str, Any]) -> CompetitivePosition:
        """Determine competitive positioning strategy."""

        competitive_data = analysis_results.get("competitive_position", {})
        market_saturation = competitive_data.get("market_saturation", 0.5)
        competitor_count = competitive_data.get("competitor_count", 5)

        # Business stage indicators
        company_stage = business_context.get("company_stage", "growth")

        if company_stage == "startup" and market_saturation < 0.6:
            return CompetitivePosition.CHALLENGER
        elif market_saturation > 0.8 or competitor_count > 10:
            return CompetitivePosition.NICHER
        elif company_stage == "enterprise":
            return CompetitivePosition.LEADER
        else:
            return CompetitivePosition.FOLLOWER

    async def _optimize_platform_selection(self,
                                         analysis_results: dict[str, Any],
                                         primary_objective: StrategyObjective) -> list[Platform]:
        """Optimize platform selection."""

        # Default platform recommendations by objective
        objective_platforms = {
            StrategyObjective.BRAND_AWARENESS: [Platform.LINKEDIN, Platform.TWITTER],
            StrategyObjective.LEAD_GENERATION: [Platform.LINKEDIN],
            StrategyObjective.THOUGHT_LEADERSHIP: [Platform.LINKEDIN, Platform.TWITTER],
            StrategyObjective.ENGAGEMENT: [Platform.LINKEDIN, Platform.TWITTER],
            StrategyObjective.CONVERSION: [Platform.LINKEDIN],
            StrategyObjective.COMMUNITY_BUILDING: [Platform.LINKEDIN, Platform.TWITTER],
            StrategyObjective.CUSTOMER_RETENTION: [Platform.LINKEDIN]
        }

        recommended_platforms = objective_platforms.get(primary_objective, [Platform.LINKEDIN])

        # Adjust based on audience analysis
        if "audience" in analysis_results:
            audience_data = analysis_results["audience"]
            if audience_data.get("audience_segment", {}).get("preferred_platforms"):
                audience_platforms = audience_data["audience_segment"]["preferred_platforms"]
                # Intersect with recommended platforms
                platform_overlap = set(recommended_platforms) & set(audience_platforms)
                if platform_overlap:
                    recommended_platforms = list(platform_overlap)

        return recommended_platforms[:2]  # Max 2 platforms to start

    async def _define_content_themes(self,
                                   analysis_results: dict[str, Any],
                                   primary_objective: StrategyObjective,
                                   competitive_position: CompetitivePosition) -> list[str]:
        """Define content themes based on analysis."""

        themes = []

        # Base themes by objective
        objective_themes = {
            StrategyObjective.BRAND_AWARENESS: ["Industry Insights", "Company Culture", "Educational Content"],
            StrategyObjective.LEAD_GENERATION: ["Solution Benefits", "Case Studies", "Expert Advice"],
            StrategyObjective.THOUGHT_LEADERSHIP: ["Industry Trends", "Opinion Pieces", "Innovation Insights"],
            StrategyObjective.ENGAGEMENT: ["Behind the Scenes", "Interactive Content", "Community Stories"],
            StrategyObjective.CONVERSION: ["Product Demos", "Customer Success", "Comparison Content"],
            StrategyObjective.COMMUNITY_BUILDING: ["User Generated Content", "Community Highlights", "Collaborative Content"],
            StrategyObjective.CUSTOMER_RETENTION: ["Product Updates", "Best Practices", "Customer Spotlights"]
        }

        base_themes = objective_themes.get(primary_objective, ["Industry Insights", "Educational Content"])
        themes.extend(base_themes)

        # Add competitive positioning themes
        if competitive_position == CompetitivePosition.CHALLENGER:
            themes.append("Disruptive Perspectives")
        elif competitive_position == CompetitivePosition.NICHER:
            themes.append("Specialized Expertise")
        elif competitive_position == CompetitivePosition.LEADER:
            themes.append("Market Leadership")

        # Add themes based on belief analysis
        if "beliefs" in analysis_results and analysis_results["beliefs"]["beliefs"]:
            themes.append("Brand Values & Beliefs")

        return themes[:5]  # Max 5 themes

    async def _create_messaging_framework(self, analysis_results: dict[str, Any]) -> dict[str, str]:
        """Create messaging framework."""

        framework = {
            "brand_voice": "Professional and Authentic",
            "tone": "Informative and Engaging",
            "key_messages": "Value-driven content that educates and inspires",
            "call_to_action_style": "Clear and compelling invitations to engage"
        }

        # Customize based on audience analysis
        if "audience" in analysis_results:
            audience_data = analysis_results["audience"]
            communication_style = audience_data.get("psychographic_analysis", {}).get("profile", {}).get("communication_style")

            if communication_style == "formal":
                framework["tone"] = "Professional and Authoritative"
            elif communication_style == "casual":
                framework["tone"] = "Conversational and Approachable"

        return framework

    async def _create_fallback_strategy(self, business_context: dict[str, Any]) -> StrategicRecommendation:
        """Create a fallback strategy when main generation fails."""

        logger.warning("Creating fallback strategy due to analysis error")

        # Basic fallback strategy
        fallback_recommendation = StrategicRecommendation(
            title="Fallback Content Strategy",
            description="Basic content strategy generated as fallback",
            primary_objective=StrategyObjective.BRAND_AWARENESS,
            secondary_objectives=[StrategyObjective.ENGAGEMENT],
            competitive_position=CompetitivePosition.FOLLOWER,
            target_platforms=[Platform.LINKEDIN],
            content_themes=["Industry Insights", "Educational Content", "Company Updates"],
            messaging_framework={
                "brand_voice": "Professional",
                "tone": "Informative",
                "key_messages": "Educational and value-driven content",
                "call_to_action_style": "Clear and direct"
            },
            content_calendar=ContentCalendar(
                name="Basic Content Calendar",
                weekly_content_targets={"week_1": 2, "week_2": 2, "week_3": 3, "week_4": 3}
            ),
            identified_gaps=[],
            resource_plan=ResourcePlan(),
            performance_prediction=PerformancePrediction(
                predicted_reach=(500, 1000, 2000),
                predicted_engagement_rate=(0.02, 0.03, 0.05)
            ),
            implementation_phases=["Setup", "Content Creation", "Optimization"],
            risk_mitigation_strategies=["Regular monitoring", "Performance tracking"],
            success_metrics={"reach": 1000, "engagement_rate": 0.03},
            belief_alignment_score=0.5,
            brand_safety_score=0.8,
            audience_resonance_score=0.5,
            viral_potential_score=0.4,
            recommendation_confidence=0.3,
            data_quality_score=0.2,
            strategic_coherence_score=0.4
        )

        return fallback_recommendation

    # Additional helper methods for optimization
    async def _analyze_strategy_performance(self,
                                          strategy: StrategicRecommendation,
                                          performance_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze current strategy performance vs predictions."""

        actual_metrics = performance_data.get("actual_metrics", {})
        predicted_metrics = {
            "reach": strategy.performance_prediction.predicted_reach[1],
            "engagement_rate": strategy.performance_prediction.predicted_engagement_rate[1],
            "conversion_rate": strategy.performance_prediction.predicted_conversion_rate[1]
        }

        performance_analysis = {}

        for metric, predicted_value in predicted_metrics.items():
            actual_value = actual_metrics.get(metric, 0)
            if predicted_value > 0:
                performance_ratio = actual_value / predicted_value
                performance_analysis[metric] = {
                    "predicted": predicted_value,
                    "actual": actual_value,
                    "performance_ratio": performance_ratio,
                    "status": "over_performing" if performance_ratio > 1.1 else
                             "under_performing" if performance_ratio < 0.9 else "on_track"
                }

        return performance_analysis

    async def _identify_optimization_opportunities(self,
                                                 strategy: StrategicRecommendation,
                                                 performance_analysis: dict[str, Any],
                                                 market_changes: dict[str, Any] = None) -> dict[str, Any]:
        """Identify optimization opportunities."""

        opportunities = {}

        # Performance-based optimizations
        under_performing_metrics = [
            metric for metric, data in performance_analysis.items()
            if data.get("status") == "under_performing"
        ]

        if under_performing_metrics:
            opportunities["performance_optimization"] = {
                "metrics_to_improve": under_performing_metrics,
                "recommended_actions": [
                    "Analyze content performance patterns",
                    "Adjust content themes and messaging",
                    "Optimize posting times and frequency",
                    "Review audience targeting"
                ]
            }

        # Content gap evolution
        if len(strategy.identified_gaps) < 5:
            opportunities["gap_analysis_refresh"] = {
                "reason": "Limited content gaps identified",
                "action": "Perform fresh content gap analysis"
            }

        # Market changes adaptation
        if market_changes:
            opportunities["market_adaptation"] = {
                "changes": market_changes,
                "action": "Adapt strategy to market changes"
            }

        return opportunities

    async def _apply_optimizations(self,
                                 strategy: StrategicRecommendation,
                                 opportunities: dict[str, Any],
                                 performance_data: dict[str, Any]) -> StrategicRecommendation:
        """Apply optimizations to strategy."""

        optimized_strategy = strategy.copy(deep=True)
        optimized_strategy.last_updated = datetime.utcnow()

        # Apply performance optimizations
        if "performance_optimization" in opportunities:
            perf_opt = opportunities["performance_optimization"]

            # Adjust content themes if reach/engagement is low
            if "reach" in perf_opt["metrics_to_improve"] or "engagement_rate" in perf_opt["metrics_to_improve"]:
                optimized_strategy.content_themes.append("Trending Topics")
                optimized_strategy.viral_potential_score = min(1.0, optimized_strategy.viral_potential_score + 0.1)

        # Refresh gap analysis if needed
        if "gap_analysis_refresh" in opportunities:
            # In a real implementation, would re-run gap analysis
            optimized_strategy.recommendation_confidence = min(1.0, optimized_strategy.recommendation_confidence + 0.05)

        # Market adaptation
        if "market_adaptation" in opportunities:
            market_changes = opportunities["market_adaptation"]["changes"]
            if market_changes.get("new_platform_trends"):
                # Adapt platform strategy
                new_platforms = market_changes["new_platform_trends"]
                for platform_name in new_platforms:
                    if platform_name.lower() == "twitter" and Platform.TWITTER not in optimized_strategy.target_platforms:
                        optimized_strategy.target_platforms.append(Platform.TWITTER)

        return optimized_strategy


# Integration and utility functions
async def generate_ai_content_strategy(business_context: dict[str, Any],
                                     content_samples: list[str] = None,
                                     brand_profile: BrandProfile = BrandProfile.MODERATE) -> StrategicRecommendation:
    """Generate comprehensive AI-powered content strategy."""
    optimizer = ContentStrategyOptimizer(brand_profile)
    return await optimizer.generate_comprehensive_strategy(
        business_context, content_samples
    )


async def optimize_content_strategy(existing_strategy: StrategicRecommendation,
                                  performance_data: dict[str, Any]) -> StrategicRecommendation:
    """Optimize existing content strategy based on performance."""
    optimizer = ContentStrategyOptimizer()
    return await optimizer.optimize_existing_strategy(existing_strategy, performance_data)


async def analyze_content_gaps_for_audience(target_audience_description: str,
                                          existing_content: list[str] = None) -> list[ContentGap]:
    """Analyze content gaps for a specific target audience."""
    audience_engine = AudienceSegmentationEngine()
    gap_analyzer = ContentGapAnalyzer()

    # Analyze target audience
    audience_analysis = await audience_engine.analyze_audience(target_audience_description)
    target_audiences = [AudienceSegment(**audience_analysis["audience_segment"])]

    # Identify gaps
    return await gap_analyzer.identify_content_gaps(
        target_audiences, existing_content or []
    )


async def predict_content_strategy_performance(strategy: StrategicRecommendation,
                                             historical_data: dict[str, Any] = None) -> PerformancePrediction:
    """Predict performance for a content strategy."""
    predictor = PerformancePredictor()
    return await predictor.predict_strategy_performance(
        strategy, strategy.identified_gaps, historical_data
    )
