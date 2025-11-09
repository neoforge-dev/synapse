"""Competitive Analysis Framework for Epic 8.3 & 8.4.

This module provides comprehensive competitive intelligence capabilities including:
- Competitor content analysis and positioning insights
- Market gap identification and opportunity analysis
- Audience overlap and differentiation strategies
- Competitive benchmarking and market positioning
- Content strategy recommendations based on competitive landscape
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from graph_rag.core.audience_intelligence import AudienceSegmentationEngine
from graph_rag.core.concept_extractor import LinkedInConceptExtractor
from graph_rag.core.viral_prediction_engine import Platform

logger = logging.getLogger(__name__)


# Enums for competitive analysis
class CompetitorType(Enum):
    """Types of competitors in the market."""
    DIRECT = "direct"           # Same audience, same value proposition
    INDIRECT = "indirect"       # Same audience, different value proposition
    SUBSTITUTE = "substitute"   # Different audience, similar value proposition
    POTENTIAL = "potential"     # Could become competitor with strategic shift
    ASPIRATIONAL = "aspirational"  # Target to emulate or surpass


class MarketPosition(Enum):
    """Market positioning categories."""
    LEADER = "leader"           # Dominant market position
    CHALLENGER = "challenger"   # Strong position, challenging leader
    FOLLOWER = "follower"       # Following market trends
    NICHER = "nicher"          # Specialized focus area
    DISRUPTOR = "disruptor"    # Changing market dynamics


class ContentStrategy(Enum):
    """Content strategy approaches."""
    THOUGHT_LEADERSHIP = "thought_leadership"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    NEWS_COMMENTARY = "news_commentary"
    PERSONAL_BRAND = "personal_brand"
    COMPANY_PROMOTION = "company_promotion"
    INDUSTRY_INSIGHTS = "industry_insights"
    CONTRARIAN = "contrarian"


class EngagementPattern(Enum):
    """Engagement pattern classifications."""
    HIGH_FREQUENCY_LOW_DEPTH = "high_frequency_low_depth"
    LOW_FREQUENCY_HIGH_DEPTH = "low_frequency_high_depth"
    CONSISTENT_MODERATE = "consistent_moderate"
    VIRAL_SPIKES = "viral_spikes"
    COMMUNITY_FOCUSED = "community_focused"


# Data Models
@dataclass
class CompetitorProfile:
    """Comprehensive competitor profile for analysis."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    competitor_type: CompetitorType | None = None
    market_position: MarketPosition | None = None

    # Content analysis
    content_strategy: ContentStrategy | None = None
    posting_frequency: float = 0.0  # posts per week
    average_engagement_rate: float = 0.0
    viral_content_percentage: float = 0.0
    engagement_pattern: EngagementPattern | None = None

    # Audience analysis
    primary_audience_segments: list[str] = field(default_factory=list)
    audience_size_estimate: int = 0
    audience_overlap_score: float = 0.0  # overlap with our audience
    unique_audience_percentage: float = 0.0

    # Content themes and topics
    primary_topics: list[str] = field(default_factory=list)
    content_tone: str = ""  # professional, casual, authoritative, etc.
    platform_focus: list[Platform] = field(default_factory=list)
    content_formats: list[str] = field(default_factory=list)

    # Performance metrics
    average_viral_score: float = 0.0
    brand_safety_score: float = 0.0
    consistency_score: float = 0.0
    innovation_score: float = 0.0

    # Competitive advantages
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    unique_value_props: list[str] = field(default_factory=list)

    # Analysis metadata
    last_analyzed: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 0.0
    data_freshness_days: int = 0


@dataclass
class MarketGap:
    """Identified market gap or opportunity."""
    id: str = field(default_factory=lambda: str(uuid4()))
    gap_type: str = ""  # content, audience, platform, timing, topic
    description: str = ""
    opportunity_size: float = 0.0  # 0.0-1.0 scale
    difficulty_score: float = 0.0  # 0.0-1.0 scale (higher = more difficult)

    # Gap details
    target_audience: str | None = None
    content_themes: list[str] = field(default_factory=list)
    platforms_affected: list[Platform] = field(default_factory=list)
    timing_window: str | None = None

    # Strategic implications
    competitive_advantage_potential: float = 0.0
    resource_requirements: list[str] = field(default_factory=list)
    success_probability: float = 0.0
    estimated_timeline: str = ""

    # Supporting evidence
    evidence: list[str] = field(default_factory=list)
    competitor_coverage: dict[str, float] = field(default_factory=dict)
    market_demand_indicators: list[str] = field(default_factory=list)

    discovered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompetitiveInsight:
    """Strategic insight from competitive analysis."""
    id: str = field(default_factory=lambda: str(uuid4()))
    insight_type: str = ""  # positioning, content, audience, opportunity, threat
    title: str = ""
    description: str = ""
    confidence: float = 0.0

    # Strategic implications
    strategic_priority: str = ""  # high, medium, low
    actionable_recommendations: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    implementation_timeline: str = ""

    # Supporting data
    competitors_involved: list[str] = field(default_factory=list)
    market_segments_affected: list[str] = field(default_factory=list)
    potential_impact: dict[str, float] = field(default_factory=dict)
    risk_factors: list[str] = field(default_factory=list)

    generated_at: datetime = field(default_factory=datetime.utcnow)


class CompetitiveAnalysisResult(BaseModel):
    """Comprehensive competitive analysis result."""
    analysis_id: str = Field(default_factory=lambda: str(uuid4()))

    # Market overview
    market_landscape: dict[str, Any] = Field(default_factory=dict)
    competitive_intensity: float = Field(ge=0.0, le=1.0, description="Market competition intensity")
    market_maturity: str = Field(default="", description="Market development stage")

    # Competitor analysis
    competitor_profiles: list[CompetitorProfile] = Field(default_factory=list)
    competitive_positioning: dict[str, Any] = Field(default_factory=dict)
    market_share_distribution: dict[str, float] = Field(default_factory=dict)

    # Gap analysis
    market_gaps: list[MarketGap] = Field(default_factory=list)
    opportunity_assessment: dict[str, Any] = Field(default_factory=dict)
    white_space_analysis: dict[str, Any] = Field(default_factory=dict)

    # Strategic insights
    competitive_insights: list[CompetitiveInsight] = Field(default_factory=list)
    strategic_recommendations: list[str] = Field(default_factory=list)
    differentiation_opportunities: list[str] = Field(default_factory=list)

    # Audience overlap analysis
    audience_overlap_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    unique_audience_opportunities: list[str] = Field(default_factory=list)
    audience_migration_patterns: dict[str, Any] = Field(default_factory=dict)

    # Content strategy insights
    content_gap_analysis: dict[str, Any] = Field(default_factory=dict)
    optimal_content_mix: dict[str, float] = Field(default_factory=dict)
    content_differentiation_strategies: list[str] = Field(default_factory=list)

    # Performance benchmarks
    competitive_benchmarks: dict[str, float] = Field(default_factory=dict)
    performance_gaps: dict[str, float] = Field(default_factory=dict)
    improvement_potential: dict[str, float] = Field(default_factory=dict)

    # Analysis metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    analysis_scope: dict[str, Any] = Field(default_factory=dict)
    confidence_level: float = Field(ge=0.0, le=1.0, description="Overall analysis confidence")
    data_sources: list[str] = Field(default_factory=list)


# Analysis Engines
class ContentAnalyzer:
    """Analyzes competitor content strategies and performance."""

    def __init__(self):
        self.concept_extractor = LinkedInConceptExtractor()

        # Content strategy indicators
        self.strategy_indicators = {
            ContentStrategy.THOUGHT_LEADERSHIP: [
                "industry trends", "future predictions", "strategic insights",
                "market analysis", "innovation", "disruption", "transformation"
            ],
            ContentStrategy.EDUCATIONAL: [
                "how to", "tutorial", "guide", "tips", "learn", "education",
                "training", "development", "skills", "knowledge"
            ],
            ContentStrategy.ENTERTAINMENT: [
                "funny", "humor", "story", "anecdote", "personal", "behind the scenes",
                "fun fact", "interesting", "amazing", "incredible"
            ],
            ContentStrategy.NEWS_COMMENTARY: [
                "breaking", "news", "update", "announcement", "reaction",
                "opinion", "analysis", "commentary", "perspective", "take"
            ],
            ContentStrategy.PERSONAL_BRAND: [
                "my journey", "personal experience", "lessons learned", "my story",
                "authenticity", "vulnerability", "growth", "challenges"
            ]
        }

        # Engagement pattern indicators
        self.engagement_patterns = {
            EngagementPattern.HIGH_FREQUENCY_LOW_DEPTH: {
                "posting_frequency_min": 7.0,  # posts per week
                "avg_engagement_max": 0.03,
                "comment_ratio_max": 0.1
            },
            EngagementPattern.LOW_FREQUENCY_HIGH_DEPTH: {
                "posting_frequency_max": 2.0,
                "avg_engagement_min": 0.08,
                "comment_ratio_min": 0.3
            },
            EngagementPattern.VIRAL_SPIKES: {
                "viral_content_percentage_min": 0.15,
                "engagement_variance_min": 0.6
            }
        }

    async def analyze_competitor_content(self, content_samples: list[dict[str, Any]],
                                       competitor_name: str) -> CompetitorProfile:
        """Analyze competitor's content strategy and performance."""
        try:
            logger.info(f"Analyzing content strategy for competitor: {competitor_name}")

            if not content_samples:
                logger.warning(f"No content samples provided for {competitor_name}")
                return CompetitorProfile(name=competitor_name)

            profile = CompetitorProfile(name=competitor_name)

            # Analyze content strategy
            profile.content_strategy = await self._identify_content_strategy(content_samples)

            # Calculate posting metrics
            profile.posting_frequency = self._calculate_posting_frequency(content_samples)
            profile.average_engagement_rate = self._calculate_average_engagement(content_samples)
            profile.viral_content_percentage = self._calculate_viral_percentage(content_samples)

            # Identify engagement pattern
            profile.engagement_pattern = self._identify_engagement_pattern(
                profile.posting_frequency, profile.average_engagement_rate,
                profile.viral_content_percentage, content_samples
            )

            # Extract content themes and topics
            profile.primary_topics = await self._extract_primary_topics(content_samples)
            profile.content_tone = self._analyze_content_tone(content_samples)
            profile.platform_focus = self._identify_platform_focus(content_samples)
            profile.content_formats = self._identify_content_formats(content_samples)

            # Performance analysis
            profile.average_viral_score = self._calculate_average_viral_score(content_samples)
            profile.brand_safety_score = self._assess_brand_safety(content_samples)
            profile.consistency_score = self._assess_content_consistency(content_samples)
            profile.innovation_score = self._assess_innovation_level(content_samples)

            # Calculate confidence
            profile.confidence_score = self._calculate_analysis_confidence(content_samples, profile)
            profile.data_freshness_days = self._calculate_data_freshness(content_samples)

            logger.info(f"Content analysis complete for {competitor_name} - "
                       f"Strategy: {profile.content_strategy.value if profile.content_strategy else 'Unknown'}, "
                       f"Confidence: {profile.confidence_score:.2f}")

            return profile

        except Exception as e:
            logger.error(f"Error analyzing competitor content for {competitor_name}: {str(e)}")
            return CompetitorProfile(name=competitor_name, confidence_score=0.0)

    async def _identify_content_strategy(self, content_samples: list[dict[str, Any]]) -> ContentStrategy | None:
        """Identify the primary content strategy."""
        strategy_scores = {}

        for strategy, indicators in self.strategy_indicators.items():
            score = 0
            for content in content_samples:
                text = content.get('text', '').lower()
                matches = sum(1 for indicator in indicators if indicator in text)
                score += matches

            if score > 0:
                strategy_scores[strategy] = score / len(content_samples)

        if strategy_scores:
            return max(strategy_scores, key=strategy_scores.get)

        return None

    def _calculate_posting_frequency(self, content_samples: list[dict[str, Any]]) -> float:
        """Calculate average posting frequency per week."""
        if not content_samples:
            return 0.0

        # Extract timestamps and calculate frequency
        timestamps = []
        for content in content_samples:
            if 'timestamp' in content:
                try:
                    if isinstance(content['timestamp'], str):
                        timestamp = datetime.fromisoformat(content['timestamp'].replace('Z', '+00:00'))
                    else:
                        timestamp = content['timestamp']
                    timestamps.append(timestamp)
                except:
                    continue

        if len(timestamps) < 2:
            return 1.0  # Default assumption

        # Calculate time span and frequency
        timestamps.sort()
        time_span = (timestamps[-1] - timestamps[0]).days
        if time_span == 0:
            return 1.0

        posts_per_day = len(timestamps) / time_span
        return posts_per_day * 7  # Convert to posts per week

    def _calculate_average_engagement(self, content_samples: list[dict[str, Any]]) -> float:
        """Calculate average engagement rate."""
        engagement_rates = []

        for content in content_samples:
            metrics = content.get('engagement_metrics', {})
            if metrics:
                likes = metrics.get('likes', 0)
                comments = metrics.get('comments', 0)
                shares = metrics.get('shares', 0)
                views = metrics.get('views', 0)

                if views > 0:
                    engagement_rate = (likes + comments + shares) / views
                    engagement_rates.append(min(1.0, engagement_rate))  # Cap at 100%

        return statistics.mean(engagement_rates) if engagement_rates else 0.0

    def _calculate_viral_percentage(self, content_samples: list[dict[str, Any]]) -> float:
        """Calculate percentage of content that achieved viral status."""
        if not content_samples:
            return 0.0

        viral_threshold = 0.7  # Viral score threshold
        viral_count = 0

        for content in content_samples:
            viral_score = content.get('viral_score', 0.0)
            if viral_score >= viral_threshold:
                viral_count += 1

        return viral_count / len(content_samples)

    def _identify_engagement_pattern(self, posting_freq: float, avg_engagement: float,
                                   viral_percentage: float, content_samples: list[dict[str, Any]]) -> EngagementPattern | None:
        """Identify the engagement pattern based on metrics."""

        # Calculate engagement variance for viral spike detection
        engagement_rates = []
        for content in content_samples:
            metrics = content.get('engagement_metrics', {})
            if metrics and metrics.get('views', 0) > 0:
                engagement_rate = (metrics.get('likes', 0) + metrics.get('comments', 0) +
                                 metrics.get('shares', 0)) / metrics['views']
                engagement_rates.append(engagement_rate)

        engagement_variance = statistics.variance(engagement_rates) if len(engagement_rates) > 1 else 0.0

        # Check patterns
        if (posting_freq >= self.engagement_patterns[EngagementPattern.HIGH_FREQUENCY_LOW_DEPTH]["posting_frequency_min"] and
            avg_engagement <= self.engagement_patterns[EngagementPattern.HIGH_FREQUENCY_LOW_DEPTH]["avg_engagement_max"]):
            return EngagementPattern.HIGH_FREQUENCY_LOW_DEPTH

        if (posting_freq <= self.engagement_patterns[EngagementPattern.LOW_FREQUENCY_HIGH_DEPTH]["posting_frequency_max"] and
            avg_engagement >= self.engagement_patterns[EngagementPattern.LOW_FREQUENCY_HIGH_DEPTH]["avg_engagement_min"]):
            return EngagementPattern.LOW_FREQUENCY_HIGH_DEPTH

        if (viral_percentage >= self.engagement_patterns[EngagementPattern.VIRAL_SPIKES]["viral_content_percentage_min"] and
            engagement_variance >= self.engagement_patterns[EngagementPattern.VIRAL_SPIKES]["engagement_variance_min"]):
            return EngagementPattern.VIRAL_SPIKES

        return EngagementPattern.CONSISTENT_MODERATE  # Default

    async def _extract_primary_topics(self, content_samples: list[dict[str, Any]]) -> list[str]:
        """Extract primary topics from content."""
        all_topics = []

        for content in content_samples[:10]:  # Analyze sample of content
            text = content.get('text', '')
            if text:
                try:
                    concepts = await self.concept_extractor.extract_concepts(text)
                    topics = [c.name for c in concepts if c.concept_type in ['STRATEGY', 'INNOVATION', 'TREND']]
                    all_topics.extend(topics)
                except:
                    continue

        # Count topic frequency and return top topics
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        # Return top 5 topics
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics[:5]]

    def _analyze_content_tone(self, content_samples: list[dict[str, Any]]) -> str:
        """Analyze overall content tone."""
        tone_indicators = {
            "professional": ["expertise", "industry", "business", "strategic", "professional"],
            "casual": ["hey", "cool", "awesome", "personally", "honestly"],
            "authoritative": ["proven", "research", "data", "evidence", "fact"],
            "inspirational": ["inspire", "motivate", "achieve", "dream", "success"],
            "controversial": ["wrong", "disagree", "unpopular", "contrary", "hot take"]
        }

        tone_scores = {}
        for tone, indicators in tone_indicators.items():
            score = 0
            for content in content_samples:
                text = content.get('text', '').lower()
                matches = sum(1 for indicator in indicators if indicator in text)
                score += matches
            tone_scores[tone] = score

        return max(tone_scores, key=tone_scores.get) if tone_scores else "neutral"

    def _identify_platform_focus(self, content_samples: list[dict[str, Any]]) -> list[Platform]:
        """Identify primary platforms."""
        platform_counts = {}

        for content in content_samples:
            platform = content.get('platform', 'general')
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        # Convert to Platform enums and return sorted by usage
        platforms = []
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}

        for platform, _count in sorted(platform_counts.items(), key=lambda x: x[1], reverse=True):
            if platform in platform_map:
                platforms.append(platform_map[platform])

        return platforms[:3]  # Return top 3 platforms

    def _identify_content_formats(self, content_samples: list[dict[str, Any]]) -> list[str]:
        """Identify content formats used."""
        formats = set()

        for content in content_samples:
            # Check for format indicators in content
            text = content.get('text', '').lower()

            if any(indicator in text for indicator in ['thread', '1/', '2/', 'part 1']):
                formats.add("threads")
            if any(indicator in text for indicator in ['poll', 'vote', 'which option']):
                formats.add("polls")
            if any(indicator in text for indicator in ['story', 'story time', 'let me tell you']):
                formats.add("stories")
            if any(indicator in text for indicator in ['tips', 'how to', 'guide', 'steps']):
                formats.add("tutorials")
            if any(indicator in text for indicator in ['question', 'thoughts?', 'what do you think']):
                formats.add("questions")

            # Check metadata for format info
            if content.get('has_image'):
                formats.add("image_posts")
            if content.get('has_video'):
                formats.add("video_posts")
            if content.get('has_link'):
                formats.add("link_shares")

        return list(formats)

    def _calculate_average_viral_score(self, content_samples: list[dict[str, Any]]) -> float:
        """Calculate average viral score."""
        viral_scores = [content.get('viral_score', 0.0) for content in content_samples]
        return statistics.mean(viral_scores) if viral_scores else 0.0

    def _assess_brand_safety(self, content_samples: list[dict[str, Any]]) -> float:
        """Assess brand safety score."""
        # Simple assessment based on content characteristics
        safety_deductions = 0
        total_content = len(content_samples)

        if total_content == 0:
            return 0.8  # Default neutral score

        for content in content_samples:
            text = content.get('text', '').lower()

            # Check for risky indicators
            risky_indicators = [
                'controversy', 'outrage', 'angry', 'hate', 'stupid', 'idiot',
                'scam', 'fraud', 'terrible', 'awful', 'disgusting'
            ]

            risk_count = sum(1 for indicator in risky_indicators if indicator in text)
            if risk_count > 0:
                safety_deductions += risk_count / len(risky_indicators)

        safety_score = max(0.0, 1.0 - (safety_deductions / total_content))
        return safety_score

    def _assess_content_consistency(self, content_samples: list[dict[str, Any]]) -> float:
        """Assess content consistency score."""
        if len(content_samples) < 2:
            return 0.5  # Default for insufficient data

        # Check posting schedule consistency
        timestamps = []
        for content in content_samples:
            if 'timestamp' in content:
                try:
                    if isinstance(content['timestamp'], str):
                        timestamp = datetime.fromisoformat(content['timestamp'].replace('Z', '+00:00'))
                    else:
                        timestamp = content['timestamp']
                    timestamps.append(timestamp)
                except:
                    continue

        if len(timestamps) < 2:
            return 0.5

        # Calculate time intervals between posts
        timestamps.sort()
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # hours
            intervals.append(interval)

        # Consistency based on variance in intervals
        if len(intervals) > 1:
            interval_variance = statistics.variance(intervals)
            mean_interval = statistics.mean(intervals)

            # Normalized consistency score (lower variance = higher consistency)
            if mean_interval > 0:
                consistency = max(0.0, 1.0 - (interval_variance / (mean_interval ** 2)))
            else:
                consistency = 0.5
        else:
            consistency = 0.5

        return min(1.0, consistency)

    def _assess_innovation_level(self, content_samples: list[dict[str, Any]]) -> float:
        """Assess content innovation and originality."""
        innovation_indicators = [
            'innovation', 'revolutionary', 'breakthrough', 'cutting-edge', 'pioneering',
            'disruptive', 'game-changing', 'unprecedented', 'novel', 'groundbreaking',
            'first-of-its-kind', 'paradigm shift', 'transformative'
        ]

        innovation_score = 0
        total_content = len(content_samples)

        if total_content == 0:
            return 0.0

        for content in content_samples:
            text = content.get('text', '').lower()
            matches = sum(1 for indicator in innovation_indicators if indicator in text)
            innovation_score += min(1.0, matches / 3.0)  # Normalize per content piece

        return innovation_score / total_content

    def _calculate_analysis_confidence(self, content_samples: list[dict[str, Any]],
                                     profile: CompetitorProfile) -> float:
        """Calculate confidence score for the analysis."""
        confidence_factors = []

        # Data quantity factor
        data_quantity_score = min(1.0, len(content_samples) / 20.0)  # Max confidence at 20+ samples
        confidence_factors.append(data_quantity_score)

        # Data completeness factor
        complete_samples = sum(1 for content in content_samples
                             if content.get('text') and content.get('engagement_metrics'))
        completeness_score = complete_samples / len(content_samples) if content_samples else 0.0
        confidence_factors.append(completeness_score)

        # Analysis depth factor
        depth_factors = [
            1.0 if profile.content_strategy else 0.0,
            1.0 if profile.primary_topics else 0.0,
            1.0 if profile.engagement_pattern else 0.0,
            1.0 if profile.platform_focus else 0.0
        ]
        depth_score = sum(depth_factors) / len(depth_factors)
        confidence_factors.append(depth_score)

        return statistics.mean(confidence_factors)

    def _calculate_data_freshness(self, content_samples: list[dict[str, Any]]) -> int:
        """Calculate how fresh the data is (days since newest content)."""
        if not content_samples:
            return 999  # Very stale

        newest_timestamp = datetime.min.replace(tzinfo=None)

        for content in content_samples:
            if 'timestamp' in content:
                try:
                    if isinstance(content['timestamp'], str):
                        timestamp = datetime.fromisoformat(content['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None)
                    else:
                        timestamp = content['timestamp'].replace(tzinfo=None)

                    if timestamp > newest_timestamp:
                        newest_timestamp = timestamp
                except:
                    continue

        if newest_timestamp == datetime.min.replace(tzinfo=None):
            return 999

        days_old = (datetime.utcnow() - newest_timestamp).days
        return max(0, days_old)


class MarketGapAnalyzer:
    """Analyzes market gaps and identifies opportunities."""

    def __init__(self):
        self.audience_engine = AudienceSegmentationEngine()

        # Gap type indicators
        self.gap_types = {
            "content": "Lack of specific content types or themes",
            "audience": "Underserved audience segments",
            "platform": "Limited presence on specific platforms",
            "timing": "Missed timing opportunities",
            "topic": "Unexplored topic areas",
            "format": "Missing content formats",
            "engagement": "Low engagement approaches"
        }

    async def identify_market_gaps(self, competitor_profiles: list[CompetitorProfile],
                                 our_content_strategy: dict[str, Any] | None = None) -> list[MarketGap]:
        """Identify gaps in the competitive landscape."""
        try:
            logger.info(f"Analyzing market gaps across {len(competitor_profiles)} competitors")

            gaps = []

            # Content theme gaps
            content_gaps = await self._identify_content_gaps(competitor_profiles, our_content_strategy)
            gaps.extend(content_gaps)

            # Audience segment gaps
            audience_gaps = await self._identify_audience_gaps(competitor_profiles)
            gaps.extend(audience_gaps)

            # Platform gaps
            platform_gaps = self._identify_platform_gaps(competitor_profiles)
            gaps.extend(platform_gaps)

            # Engagement pattern gaps
            engagement_gaps = self._identify_engagement_gaps(competitor_profiles)
            gaps.extend(engagement_gaps)

            # Format gaps
            format_gaps = self._identify_format_gaps(competitor_profiles)
            gaps.extend(format_gaps)

            # Score and rank gaps
            for gap in gaps:
                gap.opportunity_size = self._calculate_opportunity_size(gap, competitor_profiles)
                gap.difficulty_score = self._calculate_difficulty_score(gap, competitor_profiles)
                gap.success_probability = self._calculate_success_probability(gap)

            # Sort by opportunity score (size - difficulty)
            gaps.sort(key=lambda g: g.opportunity_size - g.difficulty_score, reverse=True)

            logger.info(f"Identified {len(gaps)} market gaps")
            return gaps

        except Exception as e:
            logger.error(f"Error identifying market gaps: {str(e)}")
            return []

    async def _identify_content_gaps(self, competitor_profiles: list[CompetitorProfile],
                                   our_strategy: dict[str, Any] | None) -> list[MarketGap]:
        """Identify content theme and topic gaps."""
        gaps = []

        # Analyze coverage of content strategies
        covered_strategies = set()
        for profile in competitor_profiles:
            if profile.content_strategy:
                covered_strategies.add(profile.content_strategy)

        # Check for uncovered strategies
        all_strategies = set(ContentStrategy)
        uncovered_strategies = all_strategies - covered_strategies

        for strategy in uncovered_strategies:
            gap = MarketGap(
                gap_type="content",
                description=f"Limited competition in {strategy.value.replace('_', ' ')} content",
                target_audience="General professional audience",
                content_themes=[strategy.value],
                evidence=[f"Only {len(covered_strategies)}/{len(all_strategies)} content strategies covered by competitors"],
                estimated_timeline="3-6 months to establish position"
            )
            gaps.append(gap)

        # Analyze topic coverage
        all_topics = set()
        for profile in competitor_profiles:
            all_topics.update(profile.primary_topics)

        # Identify underrepresented topics
        topic_coverage = {}
        for profile in competitor_profiles:
            for topic in profile.primary_topics:
                topic_coverage[topic] = topic_coverage.get(topic, 0) + 1

        underrepresented_topics = [topic for topic, count in topic_coverage.items() if count <= 1]

        if underrepresented_topics:
            gap = MarketGap(
                gap_type="topic",
                description="Multiple topics with minimal competitive coverage",
                content_themes=underrepresented_topics[:5],  # Top 5
                evidence=[f"{len(underrepresented_topics)} topics covered by only one competitor"],
                estimated_timeline="2-4 months to build expertise"
            )
            gaps.append(gap)

        return gaps

    async def _identify_audience_gaps(self, competitor_profiles: list[CompetitorProfile]) -> list[MarketGap]:
        """Identify underserved audience segments."""
        gaps = []

        # Analyze audience segment coverage
        covered_segments = set()
        for profile in competitor_profiles:
            covered_segments.update(profile.primary_audience_segments)

        # Define potential audience segments
        potential_segments = [
            "entry_level_professionals", "mid_career_professionals", "senior_executives",
            "entrepreneurs", "consultants", "freelancers", "remote_workers",
            "tech_professionals", "marketing_professionals", "sales_professionals",
            "hr_professionals", "finance_professionals", "healthcare_professionals"
        ]

        underserved_segments = [seg for seg in potential_segments if seg not in covered_segments]

        if underserved_segments:
            gap = MarketGap(
                gap_type="audience",
                description="Multiple audience segments with limited competitive focus",
                target_audience=", ".join(underserved_segments[:3]),
                evidence=[f"{len(underserved_segments)} audience segments underrepresented"],
                resource_requirements=["Audience research", "Persona development", "Content adaptation"],
                estimated_timeline="4-8 months to build audience"
            )
            gaps.append(gap)

        return gaps

    def _identify_platform_gaps(self, competitor_profiles: list[CompetitorProfile]) -> list[MarketGap]:
        """Identify platform presence gaps."""
        gaps = []

        # Analyze platform coverage
        platform_usage = {}
        for profile in competitor_profiles:
            for platform in profile.platform_focus:
                platform_usage[platform] = platform_usage.get(platform, 0) + 1

        # Check for underutilized platforms
        all_platforms = [Platform.LINKEDIN, Platform.TWITTER, Platform.GENERAL]
        for platform in all_platforms:
            usage_count = platform_usage.get(platform, 0)
            if usage_count < len(competitor_profiles) * 0.3:  # Less than 30% coverage
                gap = MarketGap(
                    gap_type="platform",
                    description=f"Limited competitive presence on {platform.value}",
                    platforms_affected=[platform],
                    evidence=[f"Only {usage_count}/{len(competitor_profiles)} competitors active on {platform.value}"],
                    resource_requirements=["Platform-specific content strategy", "Community building"],
                    estimated_timeline="2-3 months to establish presence"
                )
                gaps.append(gap)

        return gaps

    def _identify_engagement_gaps(self, competitor_profiles: list[CompetitorProfile]) -> list[MarketGap]:
        """Identify engagement strategy gaps."""
        gaps = []

        # Analyze engagement patterns
        pattern_usage = {}
        for profile in competitor_profiles:
            if profile.engagement_pattern:
                pattern_usage[profile.engagement_pattern] = pattern_usage.get(profile.engagement_pattern, 0) + 1

        # Check for underutilized patterns
        all_patterns = list(EngagementPattern)
        for pattern in all_patterns:
            usage_count = pattern_usage.get(pattern, 0)
            if usage_count == 0:  # No competitors using this pattern
                gap = MarketGap(
                    gap_type="engagement",
                    description=f"No competitors using {pattern.value.replace('_', ' ')} engagement strategy",
                    evidence=[f"0/{len(competitor_profiles)} competitors use this engagement pattern"],
                    resource_requirements=["Engagement strategy development", "Community management"],
                    estimated_timeline="1-2 months to implement"
                )
                gaps.append(gap)

        return gaps

    def _identify_format_gaps(self, competitor_profiles: list[CompetitorProfile]) -> list[MarketGap]:
        """Identify content format gaps."""
        gaps = []

        # Analyze format coverage
        format_usage = {}
        for profile in competitor_profiles:
            for format in profile.content_formats:
                format_usage[format] = format_usage.get(format, 0) + 1

        # Define potential formats
        potential_formats = [
            "threads", "polls", "stories", "tutorials", "questions",
            "image_posts", "video_posts", "link_shares", "carousels",
            "live_videos", "documents", "events", "newsletters"
        ]

        underutilized_formats = [fmt for fmt in potential_formats
                               if format_usage.get(fmt, 0) < len(competitor_profiles) * 0.2]

        if underutilized_formats:
            gap = MarketGap(
                gap_type="format",
                description="Multiple content formats with limited competitive usage",
                evidence=[f"{len(underutilized_formats)} formats underutilized by competitors"],
                resource_requirements=["Content creation tools", "Format-specific expertise"],
                estimated_timeline="1-3 months to implement"
            )
            gaps.append(gap)

        return gaps

    def _calculate_opportunity_size(self, gap: MarketGap, competitor_profiles: list[CompetitorProfile]) -> float:
        """Calculate the size of the opportunity."""
        # Base opportunity size on gap type and market conditions
        base_scores = {
            "content": 0.7,
            "audience": 0.8,
            "platform": 0.6,
            "timing": 0.9,
            "topic": 0.7,
            "format": 0.5,
            "engagement": 0.6
        }

        base_score = base_scores.get(gap.gap_type, 0.5)

        # Adjust based on competitive intensity
        competitive_intensity = len(competitor_profiles) / 10.0  # Normalize to 0-1
        intensity_adjustment = max(0.1, 1.0 - competitive_intensity * 0.3)

        # Adjust based on evidence strength
        evidence_adjustment = min(1.2, len(gap.evidence) * 0.1 + 0.8)

        opportunity_size = base_score * intensity_adjustment * evidence_adjustment
        return min(1.0, opportunity_size)

    def _calculate_difficulty_score(self, gap: MarketGap, competitor_profiles: list[CompetitorProfile]) -> float:
        """Calculate the difficulty of exploiting the gap."""
        # Base difficulty by gap type
        base_difficulties = {
            "content": 0.3,
            "audience": 0.6,
            "platform": 0.4,
            "timing": 0.2,
            "topic": 0.4,
            "format": 0.2,
            "engagement": 0.3
        }

        base_difficulty = base_difficulties.get(gap.gap_type, 0.5)

        # Adjust based on resource requirements
        resource_adjustment = len(gap.resource_requirements) * 0.1

        # Adjust based on market maturity (more competitors = higher difficulty)
        market_maturity_adjustment = len(competitor_profiles) * 0.05

        difficulty = base_difficulty + resource_adjustment + market_maturity_adjustment
        return min(1.0, difficulty)

    def _calculate_success_probability(self, gap: MarketGap) -> float:
        """Calculate probability of successfully exploiting the gap."""
        # Success probability inversely related to difficulty, positively to opportunity
        base_probability = gap.opportunity_size * (1.0 - gap.difficulty_score)

        # Adjust based on timeline (shorter timeline = higher probability)
        timeline_adjustment = 1.0
        if "month" in gap.estimated_timeline.lower():
            months = 6  # Default
            try:
                # Extract number of months
                parts = gap.estimated_timeline.lower().split()
                for i, part in enumerate(parts):
                    if "month" in part and i > 0:
                        months = int(parts[i-1].split('-')[0])
                        break
            except:
                pass

            timeline_adjustment = max(0.3, 1.0 - (months - 1) * 0.1)

        success_probability = base_probability * timeline_adjustment
        return min(1.0, max(0.0, success_probability))


class CompetitiveAnalyzer:
    """Main competitive analysis engine combining all analysis capabilities."""

    def __init__(self):
        self.content_analyzer = ContentAnalyzer()
        self.gap_analyzer = MarketGapAnalyzer()
        self.audience_engine = AudienceSegmentationEngine()

        logger.info("CompetitiveAnalyzer initialized")

    async def analyze_competitive_landscape(self,
                                          competitor_data: dict[str, list[dict[str, Any]]],
                                          our_content_strategy: dict[str, Any] | None = None,
                                          analysis_scope: dict[str, Any] | None = None) -> CompetitiveAnalysisResult:
        """Perform comprehensive competitive landscape analysis."""
        try:
            logger.info(f"Starting competitive analysis for {len(competitor_data)} competitors")

            result = CompetitiveAnalysisResult()
            result.analysis_scope = analysis_scope or {}
            result.data_sources = list(competitor_data.keys())

            # Analyze each competitor
            competitor_profiles = []
            for competitor_name, content_samples in competitor_data.items():
                profile = await self.content_analyzer.analyze_competitor_content(
                    content_samples, competitor_name
                )

                # Enhance profile with competitive positioning
                profile.competitor_type = self._classify_competitor_type(profile, our_content_strategy)
                profile.market_position = self._determine_market_position(profile, competitor_profiles)

                competitor_profiles.append(profile)

            result.competitor_profiles = competitor_profiles

            # Market landscape analysis
            result.market_landscape = await self._analyze_market_landscape(competitor_profiles)
            result.competitive_intensity = self._calculate_competitive_intensity(competitor_profiles)
            result.market_maturity = self._assess_market_maturity(competitor_profiles)

            # Competitive positioning analysis
            result.competitive_positioning = await self._analyze_competitive_positioning(competitor_profiles)
            result.market_share_distribution = self._estimate_market_share_distribution(competitor_profiles)

            # Gap analysis
            result.market_gaps = await self.gap_analyzer.identify_market_gaps(
                competitor_profiles, our_content_strategy
            )
            result.opportunity_assessment = self._assess_opportunities(result.market_gaps)
            result.white_space_analysis = await self._analyze_white_space(competitor_profiles)

            # Strategic insights
            result.competitive_insights = await self._generate_competitive_insights(
                competitor_profiles, result.market_gaps
            )
            result.strategic_recommendations = self._generate_strategic_recommendations(
                result.competitive_insights, result.market_gaps
            )
            result.differentiation_opportunities = self._identify_differentiation_opportunities(
                competitor_profiles
            )

            # Audience analysis
            result.audience_overlap_matrix = await self._analyze_audience_overlap(competitor_profiles)
            result.unique_audience_opportunities = self._identify_unique_audience_opportunities(
                result.audience_overlap_matrix
            )
            result.audience_migration_patterns = await self._analyze_audience_migration(competitor_profiles)

            # Content strategy insights
            result.content_gap_analysis = self._analyze_content_gaps(competitor_profiles)
            result.optimal_content_mix = self._determine_optimal_content_mix(competitor_profiles)
            result.content_differentiation_strategies = self._generate_content_differentiation_strategies(
                competitor_profiles
            )

            # Performance benchmarks
            result.competitive_benchmarks = self._calculate_competitive_benchmarks(competitor_profiles)
            result.performance_gaps = self._identify_performance_gaps(
                competitor_profiles, our_content_strategy
            )
            result.improvement_potential = self._assess_improvement_potential(
                result.performance_gaps, result.market_gaps
            )

            # Calculate overall confidence
            result.confidence_level = self._calculate_overall_confidence(
                competitor_profiles, result.market_gaps
            )

            logger.info(f"Competitive analysis complete - {len(result.competitive_insights)} insights generated, "
                       f"confidence: {result.confidence_level:.2f}")

            return result

        except Exception as e:
            logger.error(f"Error in competitive landscape analysis: {str(e)}")
            return CompetitiveAnalysisResult(confidence_level=0.0)

    def _classify_competitor_type(self, profile: CompetitorProfile,
                                our_strategy: dict[str, Any] | None) -> CompetitorType:
        """Classify the type of competitor."""
        if not our_strategy:
            return CompetitorType.POTENTIAL

        # Simple classification based on content strategy and audience overlap
        our_content_strategy = our_strategy.get('content_strategy')
        our_audience_segments = our_strategy.get('audience_segments', [])

        # Check content strategy similarity
        strategy_match = (profile.content_strategy and
                         str(profile.content_strategy) == our_content_strategy)

        # Check audience overlap
        audience_overlap = 0.0
        if profile.primary_audience_segments and our_audience_segments:
            overlap_count = len(set(profile.primary_audience_segments) & set(our_audience_segments))
            audience_overlap = overlap_count / len(set(profile.primary_audience_segments) | set(our_audience_segments))

        # Classify based on overlaps
        if strategy_match and audience_overlap > 0.6:
            return CompetitorType.DIRECT
        elif audience_overlap > 0.6:
            return CompetitorType.INDIRECT
        elif strategy_match:
            return CompetitorType.SUBSTITUTE
        else:
            return CompetitorType.POTENTIAL

    def _determine_market_position(self, profile: CompetitorProfile,
                                 existing_profiles: list[CompetitorProfile]) -> MarketPosition:
        """Determine market position based on performance metrics."""
        # Calculate overall performance score
        performance_score = (
            profile.average_engagement_rate * 0.3 +
            profile.average_viral_score * 0.3 +
            profile.consistency_score * 0.2 +
            profile.innovation_score * 0.2
        )

        # Compare to existing competitors
        if not existing_profiles:
            if performance_score > 0.7:
                return MarketPosition.LEADER
            elif performance_score > 0.5:
                return MarketPosition.CHALLENGER
            else:
                return MarketPosition.FOLLOWER

        existing_scores = []
        for existing in existing_profiles:
            existing_score = (
                existing.average_engagement_rate * 0.3 +
                existing.average_viral_score * 0.3 +
                existing.consistency_score * 0.2 +
                existing.innovation_score * 0.2
            )
            existing_scores.append(existing_score)

        avg_score = statistics.mean(existing_scores) if existing_scores else 0.5

        if performance_score > avg_score * 1.3:
            return MarketPosition.LEADER
        elif performance_score > avg_score * 1.1:
            return MarketPosition.CHALLENGER
        elif performance_score > avg_score * 0.7:
            return MarketPosition.FOLLOWER
        elif profile.innovation_score > avg_score * 1.2:
            return MarketPosition.DISRUPTOR
        else:
            return MarketPosition.NICHER

    async def _analyze_market_landscape(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, Any]:
        """Analyze overall market landscape."""
        landscape = {
            "total_competitors": len(competitor_profiles),
            "strategy_distribution": {},
            "platform_distribution": {},
            "performance_statistics": {},
            "market_dynamics": {}
        }

        # Strategy distribution
        strategy_counts = {}
        for profile in competitor_profiles:
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        landscape["strategy_distribution"] = strategy_counts

        # Platform distribution
        platform_counts = {}
        for profile in competitor_profiles:
            for platform in profile.platform_focus:
                platform_name = platform.value
                platform_counts[platform_name] = platform_counts.get(platform_name, 0) + 1
        landscape["platform_distribution"] = platform_counts

        # Performance statistics
        if competitor_profiles:
            engagement_rates = [p.average_engagement_rate for p in competitor_profiles]
            viral_scores = [p.average_viral_score for p in competitor_profiles]

            landscape["performance_statistics"] = {
                "avg_engagement_rate": statistics.mean(engagement_rates),
                "median_engagement_rate": statistics.median(engagement_rates),
                "avg_viral_score": statistics.mean(viral_scores),
                "median_viral_score": statistics.median(viral_scores),
                "top_performer_engagement": max(engagement_rates),
                "top_performer_viral": max(viral_scores)
            }

        # Market dynamics
        landscape["market_dynamics"] = {
            "strategy_diversity": len(strategy_counts),
            "platform_coverage": len(platform_counts),
            "innovation_level": statistics.mean([p.innovation_score for p in competitor_profiles]) if competitor_profiles else 0.0,
            "content_safety_level": statistics.mean([p.brand_safety_score for p in competitor_profiles]) if competitor_profiles else 0.0
        }

        return landscape

    def _calculate_competitive_intensity(self, competitor_profiles: list[CompetitorProfile]) -> float:
        """Calculate overall competitive intensity in the market."""
        if not competitor_profiles:
            return 0.0

        # Factors contributing to competitive intensity
        factors = []

        # Number of competitors
        competitor_factor = min(1.0, len(competitor_profiles) / 20.0)
        factors.append(competitor_factor)

        # Average performance level
        avg_performance = statistics.mean([
            (p.average_engagement_rate + p.average_viral_score + p.consistency_score) / 3
            for p in competitor_profiles
        ])
        factors.append(avg_performance)

        # Strategy diversity (more diverse = more intense)
        strategies = {p.content_strategy for p in competitor_profiles if p.content_strategy}
        strategy_diversity = len(strategies) / len(ContentStrategy)
        factors.append(strategy_diversity)

        # Innovation level
        avg_innovation = statistics.mean([p.innovation_score for p in competitor_profiles])
        factors.append(avg_innovation)

        return statistics.mean(factors)

    def _assess_market_maturity(self, competitor_profiles: list[CompetitorProfile]) -> str:
        """Assess market maturity stage."""
        if not competitor_profiles:
            return "emerging"

        # Factors indicating market maturity
        avg_consistency = statistics.mean([p.consistency_score for p in competitor_profiles])
        avg_brand_safety = statistics.mean([p.brand_safety_score for p in competitor_profiles])
        strategy_standardization = len({p.content_strategy for p in competitor_profiles if p.content_strategy}) / max(1, len(competitor_profiles))

        maturity_score = (avg_consistency + avg_brand_safety + (1 - strategy_standardization)) / 3

        if maturity_score > 0.8:
            return "mature"
        elif maturity_score > 0.6:
            return "growth"
        elif maturity_score > 0.4:
            return "developing"
        else:
            return "emerging"

    async def _analyze_competitive_positioning(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, Any]:
        """Analyze competitive positioning in the market."""
        positioning = {
            "position_map": {},
            "strategy_clusters": {},
            "performance_tiers": {},
            "differentiation_factors": []
        }

        # Position map (engagement vs viral performance)
        for profile in competitor_profiles:
            positioning["position_map"][profile.name] = {
                "engagement_rate": profile.average_engagement_rate,
                "viral_score": profile.average_viral_score,
                "market_position": profile.market_position.value if profile.market_position else "unknown"
            }

        # Strategy clusters
        strategy_clusters = {}
        for profile in competitor_profiles:
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                if strategy not in strategy_clusters:
                    strategy_clusters[strategy] = []
                strategy_clusters[strategy].append({
                    "name": profile.name,
                    "performance": profile.average_engagement_rate + profile.average_viral_score
                })

        positioning["strategy_clusters"] = strategy_clusters

        # Performance tiers
        if competitor_profiles:
            performances = [(p.name, p.average_engagement_rate + p.average_viral_score)
                          for p in competitor_profiles]
            performances.sort(key=lambda x: x[1], reverse=True)

            tier_size = max(1, len(performances) // 3)
            positioning["performance_tiers"] = {
                "tier_1": [p[0] for p in performances[:tier_size]],
                "tier_2": [p[0] for p in performances[tier_size:tier_size*2]],
                "tier_3": [p[0] for p in performances[tier_size*2:]]
            }

        # Differentiation factors
        differentiation_factors = []

        # Content strategy differentiation
        strategy_counts = {}
        for profile in competitor_profiles:
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        unique_strategies = [strategy for strategy, count in strategy_counts.items() if count == 1]
        if unique_strategies:
            differentiation_factors.append(f"Unique content strategies: {', '.join(unique_strategies)}")

        # Platform focus differentiation
        platform_usage = {}
        for profile in competitor_profiles:
            for platform in profile.platform_focus:
                platform_name = platform.value
                platform_usage[platform_name] = platform_usage.get(platform_name, 0) + 1

        underutilized_platforms = [platform for platform, count in platform_usage.items()
                                 if count < len(competitor_profiles) * 0.3]
        if underutilized_platforms:
            differentiation_factors.append(f"Underutilized platforms: {', '.join(underutilized_platforms)}")

        positioning["differentiation_factors"] = differentiation_factors

        return positioning

    def _estimate_market_share_distribution(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, float]:
        """Estimate relative market share distribution."""
        if not competitor_profiles:
            return {}

        # Calculate relative performance scores
        total_performance = 0
        performance_scores = {}

        for profile in competitor_profiles:
            # Combined performance metric
            performance = (
                profile.average_engagement_rate * 0.4 +
                profile.average_viral_score * 0.3 +
                profile.audience_size_estimate / 100000.0 * 0.3  # Normalize audience size
            )
            performance_scores[profile.name] = performance
            total_performance += performance

        # Convert to market share percentages
        market_shares = {}
        if total_performance > 0:
            for name, performance in performance_scores.items():
                market_shares[name] = (performance / total_performance) * 100

        return market_shares

    def _assess_opportunities(self, market_gaps: list[MarketGap]) -> dict[str, Any]:
        """Assess market opportunities from identified gaps."""
        if not market_gaps:
            return {"total_opportunities": 0}

        assessment = {
            "total_opportunities": len(market_gaps),
            "high_opportunity_gaps": [],
            "quick_wins": [],
            "strategic_opportunities": [],
            "opportunity_distribution": {}
        }

        # Categorize opportunities
        for gap in market_gaps:
            opportunity_score = gap.opportunity_size - gap.difficulty_score

            if opportunity_score > 0.5:
                assessment["high_opportunity_gaps"].append({
                    "id": gap.id,
                    "description": gap.description,
                    "opportunity_score": opportunity_score
                })

            if gap.difficulty_score < 0.3 and gap.opportunity_size > 0.4:
                assessment["quick_wins"].append({
                    "id": gap.id,
                    "description": gap.description,
                    "timeline": gap.estimated_timeline
                })

            if gap.opportunity_size > 0.7:
                assessment["strategic_opportunities"].append({
                    "id": gap.id,
                    "description": gap.description,
                    "competitive_advantage_potential": gap.competitive_advantage_potential
                })

        # Opportunity distribution by type
        gap_type_counts = {}
        for gap in market_gaps:
            gap_type_counts[gap.gap_type] = gap_type_counts.get(gap.gap_type, 0) + 1
        assessment["opportunity_distribution"] = gap_type_counts

        return assessment

    async def _analyze_white_space(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, Any]:
        """Analyze white space in the market."""
        white_space = {
            "content_white_space": [],
            "audience_white_space": [],
            "platform_white_space": [],
            "timing_white_space": []
        }

        # Content white space - topics not covered
        all_topics = set()
        for profile in competitor_profiles:
            all_topics.update(profile.primary_topics)

        # Define comprehensive topic universe
        potential_topics = [
            "artificial intelligence", "remote work", "leadership", "innovation",
            "sustainability", "digital transformation", "workplace culture",
            "productivity", "entrepreneurship", "personal branding", "networking",
            "career development", "industry trends", "market analysis", "strategy"
        ]

        uncovered_topics = [topic for topic in potential_topics if topic not in all_topics]
        white_space["content_white_space"] = uncovered_topics[:10]  # Top 10

        # Platform white space
        platform_coverage = {}
        for profile in competitor_profiles:
            for platform in profile.platform_focus:
                platform_coverage[platform.value] = platform_coverage.get(platform.value, 0) + 1

        all_platforms = ["linkedin", "twitter", "general"]
        underutilized_platforms = [
            platform for platform in all_platforms
            if platform_coverage.get(platform, 0) < len(competitor_profiles) * 0.5
        ]
        white_space["platform_white_space"] = underutilized_platforms

        return white_space

    async def _generate_competitive_insights(self, competitor_profiles: list[CompetitorProfile],
                                           market_gaps: list[MarketGap]) -> list[CompetitiveInsight]:
        """Generate strategic insights from competitive analysis."""
        insights = []

        # Performance gap insights
        if competitor_profiles:
            avg_engagement = statistics.mean([p.average_engagement_rate for p in competitor_profiles])
            top_performer = max(competitor_profiles, key=lambda p: p.average_engagement_rate)

            if top_performer.average_engagement_rate > avg_engagement * 1.5:
                insight = CompetitiveInsight(
                    insight_type="performance",
                    title="Significant Performance Leader Identified",
                    description=f"{top_performer.name} significantly outperforms market average in engagement",
                    confidence=0.9,
                    strategic_priority="high",
                    actionable_recommendations=[
                        f"Analyze {top_performer.name}'s content strategy and format choices",
                        "Identify replicable engagement tactics",
                        "Consider partnership or collaboration opportunities"
                    ],
                    competitors_involved=[top_performer.name],
                    potential_impact={"engagement_improvement": 0.3, "reach_expansion": 0.2}
                )
                insights.append(insight)

        # Strategy gap insights
        strategy_distribution = {}
        for profile in competitor_profiles:
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1

        underrepresented_strategies = [
            strategy for strategy, count in strategy_distribution.items()
            if count == 1
        ]

        if underrepresented_strategies:
            insight = CompetitiveInsight(
                insight_type="positioning",
                title="Content Strategy Differentiation Opportunity",
                description=f"Several content strategies have minimal competition: {', '.join(underrepresented_strategies)}",
                confidence=0.8,
                strategic_priority="medium",
                actionable_recommendations=[
                    "Evaluate feasibility of underrepresented strategies",
                    "Develop expertise in chosen differentiation area",
                    "Create content pillars around unique positioning"
                ],
                potential_impact={"market_share_gain": 0.15, "brand_differentiation": 0.4}
            )
            insights.append(insight)

        # Market gap insights
        high_value_gaps = [gap for gap in market_gaps if gap.opportunity_size > 0.7]
        if high_value_gaps:
            insight = CompetitiveInsight(
                insight_type="opportunity",
                title="High-Value Market Gaps Identified",
                description=f"Found {len(high_value_gaps)} high-value market gaps with significant opportunity",
                confidence=0.85,
                strategic_priority="high",
                actionable_recommendations=[
                    "Prioritize gaps by resource requirements and timeline",
                    "Develop capability roadmap for gap exploitation",
                    "Create measurement framework for opportunity capture"
                ],
                potential_impact={"market_expansion": 0.5, "competitive_advantage": 0.6}
            )
            insights.append(insight)

        # Innovation insights
        innovation_leaders = [p for p in competitor_profiles if p.innovation_score > 0.7]
        if innovation_leaders and len(innovation_leaders) < len(competitor_profiles) * 0.3:
            insight = CompetitiveInsight(
                insight_type="threat",
                title="Innovation Leaders Emerging",
                description=f"Small group of competitors showing high innovation: {', '.join([p.name for p in innovation_leaders])}",
                confidence=0.75,
                strategic_priority="high",
                actionable_recommendations=[
                    "Monitor innovation leaders for new strategies",
                    "Invest in innovation capabilities",
                    "Consider defensive strategies to protect market position"
                ],
                competitors_involved=[p.name for p in innovation_leaders],
                risk_factors=["Market disruption", "Competitive disadvantage", "Audience migration"]
            )
            insights.append(insight)

        return insights

    def _generate_strategic_recommendations(self, insights: list[CompetitiveInsight],
                                          market_gaps: list[MarketGap]) -> list[str]:
        """Generate strategic recommendations based on insights and gaps."""
        recommendations = []

        # Priority-based recommendations
        high_priority_insights = [i for i in insights if i.strategic_priority == "high"]
        for insight in high_priority_insights:
            recommendations.extend(insight.actionable_recommendations[:2])  # Top 2 per insight

        # Gap-based recommendations
        quick_wins = [gap for gap in market_gaps if gap.difficulty_score < 0.3 and gap.opportunity_size > 0.5]
        if quick_wins:
            recommendations.append(f"Execute {len(quick_wins)} quick-win opportunities to gain market traction")

        strategic_gaps = [gap for gap in market_gaps if gap.opportunity_size > 0.7]
        if strategic_gaps:
            recommendations.append(f"Develop long-term strategy to capture {len(strategic_gaps)} high-value market opportunities")

        # General strategic recommendations
        recommendations.extend([
            "Establish competitive intelligence monitoring system",
            "Develop differentiated value proposition based on gap analysis",
            "Create content calendar incorporating competitive insights",
            "Build measurement framework for competitive positioning"
        ])

        return recommendations[:10]  # Return top 10 recommendations

    def _identify_differentiation_opportunities(self, competitor_profiles: list[CompetitorProfile]) -> list[str]:
        """Identify specific differentiation opportunities."""
        opportunities = []

        # Content strategy differentiation
        strategy_counts = {}
        for profile in competitor_profiles:
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        # Underutilized strategies
        total_competitors = len(competitor_profiles)
        for strategy, count in strategy_counts.items():
            if count / total_competitors < 0.2:  # Less than 20% adoption
                opportunities.append(f"Limited competition in {strategy.replace('_', ' ')} content strategy")

        # Format differentiation
        all_formats = set()
        for profile in competitor_profiles:
            all_formats.update(profile.content_formats)

        potential_formats = ["threads", "polls", "live_videos", "carousels", "documents"]
        unused_formats = [fmt for fmt in potential_formats if fmt not in all_formats]
        if unused_formats:
            opportunities.append(f"Unexplored content formats: {', '.join(unused_formats)}")

        # Tone differentiation
        tone_counts = {}
        for profile in competitor_profiles:
            tone_counts[profile.content_tone] = tone_counts.get(profile.content_tone, 0) + 1

        underrepresented_tones = [tone for tone, count in tone_counts.items()
                                if count / total_competitors < 0.15]
        if underrepresented_tones:
            opportunities.append(f"Underrepresented content tones: {', '.join(underrepresented_tones)}")

        # Engagement pattern differentiation
        pattern_counts = {}
        for profile in competitor_profiles:
            if profile.engagement_pattern:
                pattern = profile.engagement_pattern.value
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        all_patterns = [p.value for p in EngagementPattern]
        unused_patterns = [pattern for pattern in all_patterns if pattern not in pattern_counts]
        if unused_patterns:
            opportunities.append(f"Unused engagement patterns: {', '.join(unused_patterns)}")

        return opportunities[:8]  # Return top 8 opportunities

    async def _analyze_audience_overlap(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, dict[str, float]]:
        """Analyze audience overlap between competitors."""
        overlap_matrix = {}

        for i, profile1 in enumerate(competitor_profiles):
            overlap_matrix[profile1.name] = {}

            for j, profile2 in enumerate(competitor_profiles):
                if i == j:
                    overlap_matrix[profile1.name][profile2.name] = 1.0
                else:
                    # Calculate overlap based on audience segments
                    segments1 = set(profile1.primary_audience_segments)
                    segments2 = set(profile2.primary_audience_segments)

                    if segments1 and segments2:
                        intersection = len(segments1 & segments2)
                        union = len(segments1 | segments2)
                        overlap = intersection / union if union > 0 else 0.0
                    else:
                        overlap = 0.0

                    overlap_matrix[profile1.name][profile2.name] = overlap

        return overlap_matrix

    def _identify_unique_audience_opportunities(self, overlap_matrix: dict[str, dict[str, float]]) -> list[str]:
        """Identify opportunities for unique audience capture."""
        opportunities = []

        # Find competitors with low overlap (unique audiences)
        for competitor1, overlaps in overlap_matrix.items():
            avg_overlap = statistics.mean([score for name, score in overlaps.items() if name != competitor1])

            if avg_overlap < 0.3:  # Low overlap threshold
                opportunities.append(f"{competitor1} has relatively unique audience (avg overlap: {avg_overlap:.2f})")

        # Find audience segments that could be captured
        if len(overlap_matrix) > 2:
            opportunities.append("Consider targeting audiences with low competitive overlap")
            opportunities.append("Develop content strategy for underserved audience segments")

        return opportunities

    async def _analyze_audience_migration(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, Any]:
        """Analyze potential audience migration patterns."""
        migration_analysis = {
            "high_retention_competitors": [],
            "vulnerable_competitors": [],
            "migration_opportunities": [],
            "retention_strategies": []
        }

        # Identify high retention competitors (consistent engagement)
        for profile in competitor_profiles:
            if profile.consistency_score > 0.8 and profile.average_engagement_rate > 0.05:
                migration_analysis["high_retention_competitors"].append({
                    "name": profile.name,
                    "retention_score": profile.consistency_score,
                    "engagement_rate": profile.average_engagement_rate
                })

        # Identify vulnerable competitors (inconsistent or declining)
        for profile in competitor_profiles:
            if profile.consistency_score < 0.4 or profile.average_engagement_rate < 0.02:
                migration_analysis["vulnerable_competitors"].append({
                    "name": profile.name,
                    "vulnerability_factors": [
                        "Low consistency" if profile.consistency_score < 0.4 else "",
                        "Low engagement" if profile.average_engagement_rate < 0.02 else ""
                    ]
                })

        # Migration opportunities
        if migration_analysis["vulnerable_competitors"]:
            migration_analysis["migration_opportunities"].extend([
                "Target audiences of inconsistent competitors with superior content quality",
                "Provide consistent value proposition to capture migrating audiences",
                "Develop content addressing gaps left by vulnerable competitors"
            ])

        # Retention strategies
        migration_analysis["retention_strategies"].extend([
            "Maintain high content consistency and quality",
            "Build strong community engagement",
            "Provide unique value not available from competitors",
            "Monitor audience satisfaction and feedback"
        ])

        return migration_analysis

    def _analyze_content_gaps(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, Any]:
        """Analyze content gaps in the competitive landscape."""
        gap_analysis = {
            "strategy_gaps": [],
            "topic_gaps": [],
            "format_gaps": [],
            "tone_gaps": [],
            "frequency_gaps": []
        }

        # Strategy gaps
        covered_strategies = {p.content_strategy for p in competitor_profiles if p.content_strategy}
        all_strategies = set(ContentStrategy)
        strategy_gaps = all_strategies - covered_strategies
        gap_analysis["strategy_gaps"] = [s.value for s in strategy_gaps]

        # Topic gaps (simplified analysis)
        all_competitor_topics = set()
        for profile in competitor_profiles:
            all_competitor_topics.update(profile.primary_topics)

        potential_topics = [
            "artificial intelligence", "blockchain", "sustainability", "mental health",
            "diversity and inclusion", "remote work", "cybersecurity", "data privacy"
        ]
        topic_gaps = [topic for topic in potential_topics if topic not in all_competitor_topics]
        gap_analysis["topic_gaps"] = topic_gaps

        # Format gaps
        all_formats = set()
        for profile in competitor_profiles:
            all_formats.update(profile.content_formats)

        potential_formats = ["threads", "polls", "live_videos", "carousels", "documents", "events"]
        format_gaps = [fmt for fmt in potential_formats if fmt not in all_formats]
        gap_analysis["format_gaps"] = format_gaps

        # Tone gaps
        used_tones = {p.content_tone for p in competitor_profiles}
        potential_tones = ["professional", "casual", "authoritative", "inspirational", "controversial", "educational"]
        tone_gaps = [tone for tone in potential_tones if tone not in used_tones]
        gap_analysis["tone_gaps"] = tone_gaps

        # Frequency gaps
        frequencies = [p.posting_frequency for p in competitor_profiles if p.posting_frequency > 0]
        if frequencies:
            avg_frequency = statistics.mean(frequencies)
            gap_analysis["frequency_gaps"] = {
                "average_posting_frequency": avg_frequency,
                "high_frequency_opportunity": avg_frequency < 3.0,  # Less than 3 posts per week
                "low_frequency_opportunity": avg_frequency > 10.0   # More than 10 posts per week
            }

        return gap_analysis

    def _determine_optimal_content_mix(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, float]:
        """Determine optimal content mix based on competitive analysis."""
        if not competitor_profiles:
            return {}

        # Analyze successful competitor strategies
        strategy_performance = {}

        for profile in competitor_profiles:
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                performance = (profile.average_engagement_rate + profile.average_viral_score) / 2

                if strategy not in strategy_performance:
                    strategy_performance[strategy] = []
                strategy_performance[strategy].append(performance)

        # Calculate average performance by strategy
        strategy_avg_performance = {}
        for strategy, performances in strategy_performance.items():
            strategy_avg_performance[strategy] = statistics.mean(performances)

        # Create optimal mix based on performance and gap opportunities
        total_performance = sum(strategy_avg_performance.values())
        optimal_mix = {}

        if total_performance > 0:
            for strategy, performance in strategy_avg_performance.items():
                optimal_mix[strategy] = (performance / total_performance) * 100

        # Adjust for underrepresented strategies (opportunity boost)
        strategy_counts = {}
        for profile in competitor_profiles:
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        for strategy in optimal_mix:
            competition_level = strategy_counts.get(strategy, 0) / len(competitor_profiles)
            if competition_level < 0.3:  # Underrepresented
                optimal_mix[strategy] *= 1.2  # Boost by 20%

        # Normalize to 100%
        total_mix = sum(optimal_mix.values())
        if total_mix > 0:
            for strategy in optimal_mix:
                optimal_mix[strategy] = (optimal_mix[strategy] / total_mix) * 100

        return optimal_mix

    def _generate_content_differentiation_strategies(self, competitor_profiles: list[CompetitorProfile]) -> list[str]:
        """Generate content differentiation strategies."""
        strategies = []

        # Analyze competitive landscape
        strategy_distribution = {}
        tone_distribution = {}
        format_usage = {}

        for profile in competitor_profiles:
            # Strategy distribution
            if profile.content_strategy:
                strategy = profile.content_strategy.value
                strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1

            # Tone distribution
            tone_distribution[profile.content_tone] = tone_distribution.get(profile.content_tone, 0) + 1

            # Format usage
            for fmt in profile.content_formats:
                format_usage[fmt] = format_usage.get(fmt, 0) + 1

        total_competitors = len(competitor_profiles)

        # Strategy differentiation
        underused_strategies = [
            strategy for strategy, count in strategy_distribution.items()
            if count / total_competitors < 0.2
        ]
        if underused_strategies:
            strategies.append(f"Focus on underutilized content strategies: {', '.join(underused_strategies)}")

        # Tone differentiation
        underused_tones = [
            tone for tone, count in tone_distribution.items()
            if count / total_competitors < 0.15
        ]
        if underused_tones:
            strategies.append(f"Differentiate with underrepresented tones: {', '.join(underused_tones)}")

        # Format innovation
        unused_formats = []
        potential_formats = ["threads", "polls", "live_videos", "carousels", "documents"]
        for fmt in potential_formats:
            if format_usage.get(fmt, 0) == 0:
                unused_formats.append(fmt)

        if unused_formats:
            strategies.append(f"Innovate with unused content formats: {', '.join(unused_formats)}")

        # Quality differentiation
        avg_consistency = statistics.mean([p.consistency_score for p in competitor_profiles])
        if avg_consistency < 0.7:
            strategies.append("Differentiate through superior content consistency and reliability")

        avg_innovation = statistics.mean([p.innovation_score for p in competitor_profiles])
        if avg_innovation < 0.6:
            strategies.append("Lead market through innovative content approaches and topics")

        # Engagement differentiation
        engagement_patterns = {p.engagement_pattern for p in competitor_profiles if p.engagement_pattern}
        all_patterns = set(EngagementPattern)
        unused_patterns = all_patterns - engagement_patterns

        if unused_patterns:
            pattern_names = [p.value.replace('_', ' ') for p in unused_patterns]
            strategies.append(f"Explore unused engagement patterns: {', '.join(pattern_names)}")

        return strategies[:6]  # Return top 6 strategies

    def _calculate_competitive_benchmarks(self, competitor_profiles: list[CompetitorProfile]) -> dict[str, float]:
        """Calculate competitive benchmarks for performance comparison."""
        if not competitor_profiles:
            return {}

        benchmarks = {}

        # Engagement benchmarks
        engagement_rates = [p.average_engagement_rate for p in competitor_profiles]
        benchmarks["engagement_rate_median"] = statistics.median(engagement_rates)
        benchmarks["engagement_rate_top_quartile"] = statistics.quantiles(engagement_rates, n=4)[2] if len(engagement_rates) >= 4 else max(engagement_rates)
        benchmarks["engagement_rate_average"] = statistics.mean(engagement_rates)

        # Viral performance benchmarks
        viral_scores = [p.average_viral_score for p in competitor_profiles]
        benchmarks["viral_score_median"] = statistics.median(viral_scores)
        benchmarks["viral_score_top_quartile"] = statistics.quantiles(viral_scores, n=4)[2] if len(viral_scores) >= 4 else max(viral_scores)
        benchmarks["viral_score_average"] = statistics.mean(viral_scores)

        # Consistency benchmarks
        consistency_scores = [p.consistency_score for p in competitor_profiles]
        benchmarks["consistency_median"] = statistics.median(consistency_scores)
        benchmarks["consistency_top_quartile"] = statistics.quantiles(consistency_scores, n=4)[2] if len(consistency_scores) >= 4 else max(consistency_scores)

        # Innovation benchmarks
        innovation_scores = [p.innovation_score for p in competitor_profiles]
        benchmarks["innovation_median"] = statistics.median(innovation_scores)
        benchmarks["innovation_top_quartile"] = statistics.quantiles(innovation_scores, n=4)[2] if len(innovation_scores) >= 4 else max(innovation_scores)

        # Posting frequency benchmarks
        frequencies = [p.posting_frequency for p in competitor_profiles if p.posting_frequency > 0]
        if frequencies:
            benchmarks["posting_frequency_median"] = statistics.median(frequencies)
            benchmarks["posting_frequency_average"] = statistics.mean(frequencies)

        # Brand safety benchmarks
        safety_scores = [p.brand_safety_score for p in competitor_profiles]
        benchmarks["brand_safety_median"] = statistics.median(safety_scores)
        benchmarks["brand_safety_average"] = statistics.mean(safety_scores)

        return benchmarks

    def _identify_performance_gaps(self, competitor_profiles: list[CompetitorProfile],
                                 our_strategy: dict[str, Any] | None) -> dict[str, float]:
        """Identify performance gaps compared to competitors."""
        gaps = {}

        if not competitor_profiles or not our_strategy:
            return gaps

        # Calculate competitive benchmarks
        benchmarks = self._calculate_competitive_benchmarks(competitor_profiles)

        # Our current performance (from strategy data)
        our_engagement = our_strategy.get('engagement_rate', 0.0)
        our_viral_score = our_strategy.get('viral_score', 0.0)
        our_consistency = our_strategy.get('consistency_score', 0.0)
        our_posting_frequency = our_strategy.get('posting_frequency', 0.0)

        # Calculate gaps (negative = we're behind, positive = we're ahead)
        if 'engagement_rate_median' in benchmarks:
            gaps['engagement_rate_gap'] = our_engagement - benchmarks['engagement_rate_median']
            gaps['engagement_rate_top_quartile_gap'] = our_engagement - benchmarks['engagement_rate_top_quartile']

        if 'viral_score_median' in benchmarks:
            gaps['viral_score_gap'] = our_viral_score - benchmarks['viral_score_median']
            gaps['viral_score_top_quartile_gap'] = our_viral_score - benchmarks['viral_score_top_quartile']

        if 'consistency_median' in benchmarks:
            gaps['consistency_gap'] = our_consistency - benchmarks['consistency_median']

        if 'posting_frequency_median' in benchmarks:
            gaps['posting_frequency_gap'] = our_posting_frequency - benchmarks['posting_frequency_median']

        return gaps

    def _assess_improvement_potential(self, performance_gaps: dict[str, float],
                                    market_gaps: list[MarketGap]) -> dict[str, float]:
        """Assess improvement potential based on gaps and opportunities."""
        improvement_potential = {}

        # Performance-based improvement potential
        for gap_name, gap_value in performance_gaps.items():
            if gap_value < 0:  # We're behind
                # Potential improvement = absolute gap value (how much we can improve)
                improvement_potential[gap_name.replace('_gap', '_improvement')] = abs(gap_value)

        # Market gap-based improvement potential
        high_opportunity_gaps = [gap for gap in market_gaps if gap.opportunity_size > 0.6]
        if high_opportunity_gaps:
            avg_opportunity_size = statistics.mean([gap.opportunity_size for gap in high_opportunity_gaps])
            improvement_potential['market_expansion_potential'] = avg_opportunity_size

        # Content strategy improvement potential
        content_gaps = [gap for gap in market_gaps if gap.gap_type == "content"]
        if content_gaps:
            avg_content_opportunity = statistics.mean([gap.opportunity_size for gap in content_gaps])
            improvement_potential['content_strategy_improvement'] = avg_content_opportunity

        # Audience expansion potential
        audience_gaps = [gap for gap in market_gaps if gap.gap_type == "audience"]
        if audience_gaps:
            avg_audience_opportunity = statistics.mean([gap.opportunity_size for gap in audience_gaps])
            improvement_potential['audience_expansion_potential'] = avg_audience_opportunity

        return improvement_potential

    def _calculate_overall_confidence(self, competitor_profiles: list[CompetitorProfile],
                                    market_gaps: list[MarketGap]) -> float:
        """Calculate overall confidence in the competitive analysis."""
        confidence_factors = []

        # Data quality factor
        if competitor_profiles:
            avg_profile_confidence = statistics.mean([p.confidence_score for p in competitor_profiles])
            confidence_factors.append(avg_profile_confidence)

        # Data quantity factor
        data_quantity_score = min(1.0, len(competitor_profiles) / 10.0)  # Max confidence at 10+ competitors
        confidence_factors.append(data_quantity_score)

        # Analysis completeness factor
        analysis_completeness = 0.0
        if competitor_profiles:
            complete_profiles = sum(1 for p in competitor_profiles
                                  if p.content_strategy and p.primary_topics and p.engagement_pattern)
            analysis_completeness = complete_profiles / len(competitor_profiles)
        confidence_factors.append(analysis_completeness)

        # Gap analysis confidence
        if market_gaps:
            avg_gap_confidence = statistics.mean([
                gap.success_probability for gap in market_gaps
            ])
            confidence_factors.append(avg_gap_confidence)

        # Data freshness factor
        if competitor_profiles:
            avg_freshness = statistics.mean([p.data_freshness_days for p in competitor_profiles])
            freshness_score = max(0.0, 1.0 - (avg_freshness / 30.0))  # Decrease confidence as data gets older
            confidence_factors.append(freshness_score)

        return statistics.mean(confidence_factors) if confidence_factors else 0.0


# Example usage and integration functions
async def analyze_competitor_landscape(competitor_data: dict[str, list[dict[str, Any]]],
                                     our_strategy: dict[str, Any] | None = None) -> CompetitiveAnalysisResult:
    """Quick function to analyze competitive landscape."""
    analyzer = CompetitiveAnalyzer()
    return await analyzer.analyze_competitive_landscape(competitor_data, our_strategy)


async def identify_market_opportunities(competitor_data: dict[str, list[dict[str, Any]]]) -> list[MarketGap]:
    """Quick function to identify market opportunities."""
    analyzer = CompetitiveAnalyzer()

    # Analyze competitors first
    competitor_profiles = []
    for competitor_name, content_samples in competitor_data.items():
        profile = await analyzer.content_analyzer.analyze_competitor_content(
            content_samples, competitor_name
        )
        competitor_profiles.append(profile)

    # Identify gaps
    return await analyzer.gap_analyzer.identify_market_gaps(competitor_profiles)


async def benchmark_against_competitors(our_metrics: dict[str, float],
                                      competitor_data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Quick function to benchmark performance against competitors."""
    analyzer = CompetitiveAnalyzer()

    # Analyze competitors
    competitor_profiles = []
    for competitor_name, content_samples in competitor_data.items():
        profile = await analyzer.content_analyzer.analyze_competitor_content(
            content_samples, competitor_name
        )
        competitor_profiles.append(profile)

    # Calculate benchmarks and gaps
    benchmarks = analyzer._calculate_competitive_benchmarks(competitor_profiles)
    gaps = analyzer._identify_performance_gaps(competitor_profiles, our_metrics)

    return {
        "benchmarks": benchmarks,
        "performance_gaps": gaps,
        "competitor_count": len(competitor_profiles),
        "analysis_confidence": analyzer._calculate_overall_confidence(competitor_profiles, [])
    }
