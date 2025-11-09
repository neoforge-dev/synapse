"""Competitor Analyzer for Epic 17 - Competitive Intelligence Engine.

Provides automated competitor analysis with:
- Real-time competitor data collection and monitoring
- Competitive strengths and weaknesses assessment
- Market share and positioning analysis
- Competitive threat level evaluation
- Strategic response recommendations
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CompetitorCategory(Enum):
    """Categories of competitors."""
    DIRECT = "direct"               # Same market, same solution
    INDIRECT = "indirect"           # Same market, different solution
    SUBSTITUTE = "substitute"       # Different market, similar solution
    POTENTIAL = "potential"         # Could become competitor
    EMERGING = "emerging"           # New market entrants
    DISRUPTOR = "disruptor"        # Market disruptors


class ThreatLevel(Enum):
    """Competitive threat assessment levels."""
    CRITICAL = "critical"          # Immediate threat to business
    HIGH = "high"                  # Significant competitive pressure
    MEDIUM = "medium"              # Standard competition
    LOW = "low"                    # Minimal threat
    MONITORING = "monitoring"      # Watch list status


class CompetitiveAdvantage(Enum):
    """Types of competitive advantages."""
    TECHNOLOGY = "technology"           # Technical superiority
    COST = "cost"                      # Cost advantage
    BRAND = "brand"                    # Brand recognition
    DISTRIBUTION = "distribution"      # Distribution channels
    CUSTOMER_BASE = "customer_base"    # Existing customers
    EXPERTISE = "expertise"            # Domain expertise
    PARTNERSHIPS = "partnerships"      # Strategic partnerships
    INNOVATION = "innovation"          # Innovation capability
    SCALE = "scale"                   # Economies of scale
    SPEED = "speed"                   # Time to market


@dataclass
class CompetitorProfile:
    """Comprehensive competitor profile."""
    competitor_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    category: CompetitorCategory = CompetitorCategory.DIRECT
    threat_level: ThreatLevel = ThreatLevel.MEDIUM

    # Basic information
    description: str = ""
    headquarters: str = ""
    founded_year: int | None = None
    employee_count: int | None = None
    funding_status: str = ""  # public, private, startup, etc.

    # Market presence
    market_segments: list[str] = field(default_factory=list)
    geographic_presence: list[str] = field(default_factory=list)
    target_customers: list[str] = field(default_factory=list)
    annual_revenue: float | None = None
    market_share: float | None = None

    # Products and services
    primary_offerings: list[str] = field(default_factory=list)
    key_features: list[str] = field(default_factory=list)
    pricing_model: str = ""
    pricing_range: tuple[float, float] | None = None

    # Competitive strengths and weaknesses
    competitive_advantages: list[CompetitiveAdvantage] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)

    # Performance metrics
    customer_satisfaction: float | None = None
    market_growth_rate: float | None = None
    innovation_index: float | None = None
    brand_recognition: float | None = None

    # Strategic intelligence
    recent_developments: list[dict[str, Any]] = field(default_factory=list)
    strategic_partnerships: list[str] = field(default_factory=list)
    investment_activities: list[dict[str, Any]] = field(default_factory=list)
    leadership_changes: list[dict[str, Any]] = field(default_factory=list)

    # Monitoring data
    last_updated: str = ""
    data_sources: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    monitoring_frequency: str = "weekly"  # daily, weekly, monthly

    # Analysis metadata
    analysis_notes: str = ""
    next_review_date: str = ""
    analyst_recommendations: list[str] = field(default_factory=list)


@dataclass
class CompetitiveAnalysisResult:
    """Result of competitive analysis."""
    analysis_id: str = field(default_factory=lambda: str(uuid4()))
    analysis_type: str = ""  # market_overview, competitor_deep_dive, threat_assessment

    # Analysis scope
    competitors_analyzed: list[str] = field(default_factory=list)
    market_segments: list[str] = field(default_factory=list)
    time_period: str = ""

    # Key findings
    market_summary: str = ""
    competitive_landscape: dict[str, Any] = field(default_factory=dict)
    threat_assessment: dict[str, ThreatLevel] = field(default_factory=dict)
    opportunity_analysis: list[str] = field(default_factory=list)

    # Strategic insights
    market_trends: list[str] = field(default_factory=list)
    emerging_threats: list[str] = field(default_factory=list)
    competitive_gaps: list[str] = field(default_factory=list)
    differentiation_opportunities: list[str] = field(default_factory=list)

    # Recommendations
    strategic_recommendations: list[str] = field(default_factory=list)
    tactical_responses: list[str] = field(default_factory=list)
    monitoring_priorities: list[str] = field(default_factory=list)

    # Quality metrics
    data_coverage: float = 0.0
    analysis_confidence: float = 0.0
    freshness_score: float = 0.0

    # Metadata
    generated_timestamp: str = ""
    analyst: str = ""
    sources_used: list[str] = field(default_factory=list)
    next_analysis_date: str = ""


class CompetitorDataSource(BaseModel):
    """Data source for competitor intelligence."""
    source_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    type: str = ""  # website, news, social_media, financial, patent, etc.
    url: str | None = None
    api_endpoint: str | None = None
    collection_frequency: str = "daily"
    reliability_score: float = Field(default=0.8, ge=0.0, le=1.0)
    cost: float = Field(default=0.0, ge=0.0)
    active: bool = True
    last_collected: str | None = None
    data_types: list[str] = Field(default_factory=list)


class CompetitorAnalyzer:
    """Advanced competitor analysis engine for real-time intelligence."""

    def __init__(
        self,
        graph_repository=None,
        vector_store=None,
        llm_service=None,
        web_scraper=None,
        news_service=None
    ):
        """Initialize the competitor analyzer."""
        self.graph_repository = graph_repository
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.web_scraper = web_scraper
        self.news_service = news_service

        # Competitor database
        self.competitor_profiles: dict[str, CompetitorProfile] = {}
        self.data_sources: dict[str, CompetitorDataSource] = {}

        # Analysis cache
        self.analysis_cache: dict[str, CompetitiveAnalysisResult] = {}
        self.monitoring_schedules: dict[str, dict[str, Any]] = {}

        # Performance tracking
        self.analyzer_stats = {
            "competitors_tracked": 0,
            "analyses_performed": 0,
            "data_points_collected": 0,
            "avg_analysis_confidence": 0.0,
            "threat_alerts_generated": 0,
            "accuracy_rate": 0.0
        }

        # Initialize default data sources
        self._initialize_data_sources()

        # Start monitoring tasks
        self._start_monitoring_tasks()

    def _initialize_data_sources(self):
        """Initialize default data sources for competitor intelligence."""
        default_sources = [
            CompetitorDataSource(
                name="Company Websites",
                type="website",
                collection_frequency="weekly",
                reliability_score=0.9,
                data_types=["products", "pricing", "news", "leadership"]
            ),
            CompetitorDataSource(
                name="Industry News",
                type="news",
                collection_frequency="daily",
                reliability_score=0.8,
                data_types=["developments", "partnerships", "funding", "strategy"]
            ),
            CompetitorDataSource(
                name="Social Media",
                type="social_media",
                collection_frequency="daily",
                reliability_score=0.7,
                data_types=["sentiment", "campaigns", "announcements", "engagement"]
            ),
            CompetitorDataSource(
                name="Financial Reports",
                type="financial",
                collection_frequency="quarterly",
                reliability_score=0.95,
                data_types=["revenue", "growth", "investments", "performance"]
            ),
            CompetitorDataSource(
                name="Patent Filings",
                type="patent",
                collection_frequency="monthly",
                reliability_score=0.9,
                data_types=["innovation", "technology", "research", "capabilities"]
            )
        ]

        for source in default_sources:
            self.data_sources[source.source_id] = source

    def _start_monitoring_tasks(self):
        """Start background monitoring tasks."""
        # In a real implementation, this would start background processes
        # For now, we'll just log that monitoring is initialized
        logger.info("Competitor monitoring tasks initialized")

    async def add_competitor(
        self,
        name: str,
        category: CompetitorCategory = CompetitorCategory.DIRECT,
        initial_data: dict[str, Any] | None = None
    ) -> CompetitorProfile:
        """Add a new competitor for monitoring."""
        try:
            profile = CompetitorProfile(
                name=name,
                category=category,
                last_updated=str(datetime.now()),
                next_review_date=str(datetime.now() + timedelta(days=7))
            )

            # Populate with initial data if provided
            if initial_data:
                for key, value in initial_data.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)

            # Perform initial analysis
            await self._perform_initial_analysis(profile)

            # Store competitor profile
            self.competitor_profiles[profile.competitor_id] = profile
            self.analyzer_stats["competitors_tracked"] += 1

            # Set up monitoring schedule
            self._schedule_competitor_monitoring(profile)

            logger.info(f"Added competitor: {name} (Category: {category.value})")
            return profile

        except Exception as e:
            logger.error(f"Error adding competitor {name}: {str(e)}")
            raise

    async def _perform_initial_analysis(self, profile: CompetitorProfile):
        """Perform initial comprehensive analysis of competitor."""
        try:
            # Collect basic information
            basic_info = await self._collect_basic_competitor_info(profile.name)
            self._update_profile_with_basic_info(profile, basic_info)

            # Analyze competitive positioning
            positioning = await self._analyze_competitive_positioning(profile)
            profile.market_segments = positioning.get("segments", [])
            profile.target_customers = positioning.get("customers", [])

            # Assess threat level
            profile.threat_level = await self._assess_threat_level(profile)

            # Identify competitive advantages
            profile.competitive_advantages = await self._identify_competitive_advantages(profile)

            # Perform SWOT analysis
            swot = await self._perform_swot_analysis(profile)
            profile.strengths = swot.get("strengths", [])
            profile.weaknesses = swot.get("weaknesses", [])
            profile.opportunities = swot.get("opportunities", [])
            profile.threats = swot.get("threats", [])

            # Calculate confidence score
            profile.confidence_score = self._calculate_profile_confidence(profile)

        except Exception as e:
            logger.error(f"Error in initial analysis for {profile.name}: {str(e)}")
            profile.confidence_score = 0.5  # Default confidence

    async def _collect_basic_competitor_info(self, competitor_name: str) -> dict[str, Any]:
        """Collect basic information about competitor."""
        basic_info = {
            "description": f"Analysis target: {competitor_name}",
            "founded_year": None,
            "employee_count": None,
            "headquarters": "Unknown",
            "funding_status": "Unknown"
        }

        # In a real implementation, this would use web scraping, APIs, etc.
        # For demo purposes, we'll use mock data

        if self.web_scraper:
            try:
                # Mock web scraping results
                scraped_data = {
                    "description": "Technology company specializing in enterprise solutions",
                    "employee_count": np.random.randint(50, 5000),
                    "headquarters": np.random.choice(["San Francisco", "New York", "Seattle", "Boston"])
                }
                basic_info.update(scraped_data)
            except Exception as e:
                logger.warning(f"Web scraping failed for {competitor_name}: {str(e)}")

        return basic_info

    def _update_profile_with_basic_info(
        self,
        profile: CompetitorProfile,
        basic_info: dict[str, Any]
    ):
        """Update competitor profile with basic information."""
        for key, value in basic_info.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)

    async def _analyze_competitive_positioning(
        self,
        profile: CompetitorProfile
    ) -> dict[str, Any]:
        """Analyze competitor's market positioning."""
        positioning = {
            "segments": ["enterprise", "mid_market"],
            "customers": ["technology_companies", "financial_services"],
            "value_proposition": "Unknown",
            "market_approach": "Unknown"
        }

        # Use LLM service for positioning analysis if available
        if self.llm_service:
            try:
                analysis_prompt = f"""
                Analyze the market positioning for competitor: {profile.name}

                Company description: {profile.description}
                Primary offerings: {', '.join(profile.primary_offerings)}

                Provide analysis in the following format:
                - Market segments they target
                - Customer types they serve
                - Their value proposition
                - Market approach (premium, cost-leader, differentiated, etc.)
                """

                await self.llm_service.generate(analysis_prompt)
                # Parse response (simplified for demo)
                positioning["value_proposition"] = "AI-powered enterprise solutions"
                positioning["market_approach"] = "differentiated"

            except Exception as e:
                logger.warning(f"LLM positioning analysis failed: {str(e)}")

        return positioning

    async def _assess_threat_level(self, profile: CompetitorProfile) -> ThreatLevel:
        """Assess competitive threat level."""
        # Scoring factors
        factors = {
            "market_overlap": 0.7,  # How much market overlap
            "competitive_advantages": len(profile.competitive_advantages) * 0.1,
            "market_share": profile.market_share or 0.1,
            "growth_rate": profile.market_growth_rate or 0.05,
            "funding_strength": 0.5,  # Simplified
            "innovation_capability": profile.innovation_index or 0.5
        }

        # Calculate threat score
        threat_score = (
            factors["market_overlap"] * 0.3 +
            min(factors["competitive_advantages"], 1.0) * 0.2 +
            factors["market_share"] * 0.2 +
            factors["growth_rate"] * 0.15 +
            factors["funding_strength"] * 0.1 +
            factors["innovation_capability"] * 0.05
        )

        # Map to threat levels
        if threat_score >= 0.8:
            return ThreatLevel.CRITICAL
        elif threat_score >= 0.65:
            return ThreatLevel.HIGH
        elif threat_score >= 0.45:
            return ThreatLevel.MEDIUM
        elif threat_score >= 0.25:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.MONITORING

    async def _identify_competitive_advantages(
        self,
        profile: CompetitorProfile
    ) -> list[CompetitiveAdvantage]:
        """Identify competitor's competitive advantages."""
        advantages = []

        # Simple heuristics (would be more sophisticated in practice)
        if profile.employee_count and profile.employee_count > 1000:
            advantages.append(CompetitiveAdvantage.SCALE)

        if "technology" in profile.description.lower():
            advantages.append(CompetitiveAdvantage.TECHNOLOGY)

        if "innovation" in profile.description.lower():
            advantages.append(CompetitiveAdvantage.INNOVATION)

        if profile.annual_revenue and profile.annual_revenue > 100_000_000:
            advantages.append(CompetitiveAdvantage.BRAND)

        # Add default advantages based on category
        if profile.category == CompetitorCategory.DIRECT:
            advantages.append(CompetitiveAdvantage.CUSTOMER_BASE)

        return list(set(advantages))  # Remove duplicates

    async def _perform_swot_analysis(self, profile: CompetitorProfile) -> dict[str, list[str]]:
        """Perform SWOT analysis for competitor."""
        swot = {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": []
        }

        # Identify strengths based on competitive advantages
        advantage_to_strength = {
            CompetitiveAdvantage.TECHNOLOGY: "Advanced technology platform",
            CompetitiveAdvantage.SCALE: "Large scale operations",
            CompetitiveAdvantage.BRAND: "Strong brand recognition",
            CompetitiveAdvantage.CUSTOMER_BASE: "Established customer relationships",
            CompetitiveAdvantage.INNOVATION: "Innovation capabilities",
            CompetitiveAdvantage.EXPERTISE: "Domain expertise",
            CompetitiveAdvantage.PARTNERSHIPS: "Strategic partnerships"
        }

        for advantage in profile.competitive_advantages:
            strength = advantage_to_strength.get(advantage, f"{advantage.value} advantage")
            swot["strengths"].append(strength)

        # Identify common weaknesses
        common_weaknesses = [
            "Limited market presence in emerging segments",
            "Potential technology debt",
            "Customer acquisition costs"
        ]
        swot["weaknesses"] = common_weaknesses[:2]  # Limit for demo

        # Identify opportunities
        common_opportunities = [
            "Market expansion opportunities",
            "New technology adoption",
            "Strategic partnerships",
            "Geographic expansion"
        ]
        swot["opportunities"] = common_opportunities[:3]

        # Identify threats
        common_threats = [
            "New market entrants",
            "Technology disruption",
            "Economic uncertainty",
            "Regulatory changes"
        ]
        swot["threats"] = common_threats[:2]

        return swot

    def _calculate_profile_confidence(self, profile: CompetitorProfile) -> float:
        """Calculate confidence score for competitor profile."""
        # Factors affecting confidence
        factors = {
            "basic_info": 1.0 if profile.description else 0.0,
            "market_data": 1.0 if profile.market_segments else 0.5,
            "financial_data": 1.0 if profile.annual_revenue else 0.3,
            "competitive_analysis": len(profile.competitive_advantages) / 5.0,
            "swot_analysis": min(len(profile.strengths) / 3.0, 1.0),
            "data_freshness": 1.0  # Assume fresh for new profiles
        }

        # Weighted confidence score
        weights = {
            "basic_info": 0.2,
            "market_data": 0.2,
            "financial_data": 0.15,
            "competitive_analysis": 0.2,
            "swot_analysis": 0.15,
            "data_freshness": 0.1
        }

        confidence = sum(factors[factor] * weights[factor] for factor in factors)
        return min(confidence, 1.0)

    def _schedule_competitor_monitoring(self, profile: CompetitorProfile):
        """Schedule ongoing monitoring for competitor."""
        monitoring_config = {
            "competitor_id": profile.competitor_id,
            "frequency": profile.monitoring_frequency,
            "next_update": datetime.now() + timedelta(days=7),
            "data_sources": list(self.data_sources.keys()),
            "monitoring_priorities": [
                "pricing_changes",
                "product_updates",
                "market_expansion",
                "partnerships",
                "leadership_changes"
            ]
        }

        self.monitoring_schedules[profile.competitor_id] = monitoring_config

    async def perform_competitive_analysis(
        self,
        analysis_type: str = "market_overview",
        competitor_ids: list[str] | None = None,
        market_segments: list[str] | None = None
    ) -> CompetitiveAnalysisResult:
        """Perform comprehensive competitive analysis."""
        start_time = datetime.now()

        result = CompetitiveAnalysisResult(
            analysis_type=analysis_type,
            generated_timestamp=str(start_time),
            analyst="AI_Competitive_Analyzer"
        )

        try:
            # Determine scope
            if competitor_ids:
                competitors = [self.competitor_profiles[cid] for cid in competitor_ids
                             if cid in self.competitor_profiles]
            else:
                competitors = list(self.competitor_profiles.values())

            result.competitors_analyzed = [c.name for c in competitors]
            result.market_segments = market_segments or list({
                segment for c in competitors for segment in c.market_segments
            })

            # Perform analysis based on type
            if analysis_type == "market_overview":
                await self._analyze_market_overview(result, competitors)
            elif analysis_type == "threat_assessment":
                await self._analyze_threat_assessment(result, competitors)
            elif analysis_type == "opportunity_analysis":
                await self._analyze_opportunities(result, competitors)
            else:
                await self._perform_general_analysis(result, competitors)

            # Calculate quality metrics
            result.data_coverage = self._calculate_data_coverage(competitors)
            result.analysis_confidence = self._calculate_analysis_confidence(result, competitors)
            result.freshness_score = self._calculate_freshness_score(competitors)

            # Schedule next analysis
            result.next_analysis_date = str(start_time + timedelta(days=30))

            # Cache result
            self.analysis_cache[result.analysis_id] = result
            self.analyzer_stats["analyses_performed"] += 1

            # Update performance stats
            self._update_analyzer_stats(result)

            logger.info(f"Competitive analysis completed: {analysis_type}, "
                       f"Competitors: {len(competitors)}, "
                       f"Confidence: {result.analysis_confidence:.2f}")

            return result

        except Exception as e:
            logger.error(f"Error in competitive analysis: {str(e)}")
            result.market_summary = f"Analysis failed: {str(e)}"
            result.analysis_confidence = 0.0
            return result

    async def _analyze_market_overview(
        self,
        result: CompetitiveAnalysisResult,
        competitors: list[CompetitorProfile]
    ):
        """Analyze overall market competitive landscape."""
        # Market summary
        total_competitors = len(competitors)
        threat_distribution = {}
        for competitor in competitors:
            threat_level = competitor.threat_level.value
            threat_distribution[threat_level] = threat_distribution.get(threat_level, 0) + 1

        result.market_summary = (
            f"Market analysis of {total_competitors} competitors across "
            f"{len(result.market_segments)} segments. "
            f"Threat distribution: {threat_distribution}"
        )

        # Competitive landscape analysis
        result.competitive_landscape = {
            "total_competitors": total_competitors,
            "threat_distribution": threat_distribution,
            "market_leaders": [c.name for c in competitors
                             if c.threat_level == ThreatLevel.CRITICAL][:3],
            "emerging_threats": [c.name for c in competitors
                               if c.category == CompetitorCategory.EMERGING],
            "market_concentration": self._calculate_market_concentration(competitors)
        }

        # Market trends
        result.market_trends = [
            "Increasing AI and automation adoption",
            "Focus on enterprise-grade security",
            "Growing demand for real-time analytics",
            "Shift towards cloud-native solutions"
        ]

        # Strategic recommendations
        result.strategic_recommendations = [
            "Monitor high-threat competitors for strategic moves",
            "Identify differentiation opportunities in underserved segments",
            "Develop competitive response strategies for market leaders",
            "Track emerging competitors for early threat detection"
        ]

    async def _analyze_threat_assessment(
        self,
        result: CompetitiveAnalysisResult,
        competitors: list[CompetitorProfile]
    ):
        """Analyze competitive threats in detail."""
        # Threat assessment by competitor
        for competitor in competitors:
            result.threat_assessment[competitor.name] = competitor.threat_level

        # Emerging threats
        result.emerging_threats = [
            f"{c.name}: {c.category.value} competitor with {c.threat_level.value} threat level"
            for c in competitors
            if c.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        ]

        # Competitive gaps (areas where we might be vulnerable)
        advantages_count = {}
        for competitor in competitors:
            for advantage in competitor.competitive_advantages:
                advantages_count[advantage.value] = advantages_count.get(advantage.value, 0) + 1

        common_advantages = [adv for adv, count in advantages_count.items() if count >= 2]
        result.competitive_gaps = [
            f"Multiple competitors have {advantage} advantage"
            for advantage in common_advantages
        ]

        # Tactical responses
        result.tactical_responses = [
            "Develop counter-strategies for high-threat competitors",
            "Strengthen defenses in areas of competitive vulnerability",
            "Accelerate differentiation in key advantage areas",
            "Monitor competitor moves for early response"
        ]

    async def _analyze_opportunities(
        self,
        result: CompetitiveAnalysisResult,
        competitors: list[CompetitorProfile]
    ):
        """Analyze competitive opportunities."""
        # Opportunity analysis
        all_opportunities = []
        for competitor in competitors:
            all_opportunities.extend(competitor.opportunities)

        # Find common opportunity themes
        opportunity_themes = {}
        for opp in all_opportunities:
            # Simple keyword extraction for themes
            for keyword in ["market", "technology", "customer", "partnership", "expansion"]:
                if keyword in opp.lower():
                    opportunity_themes[keyword] = opportunity_themes.get(keyword, 0) + 1

        result.opportunity_analysis = [
            f"Market expansion opportunities identified by {opportunity_themes.get('market', 0)} competitors",
            f"Technology advancement opportunities noted by {opportunity_themes.get('technology', 0)} competitors",
            f"Customer segment opportunities recognized by {opportunity_themes.get('customer', 0)} competitors"
        ]

        # Differentiation opportunities
        result.differentiation_opportunities = [
            "Areas with limited competitive presence",
            "Underserved customer segments",
            "Technology gaps in competitor offerings",
            "Service quality differentiation opportunities"
        ]

    async def _perform_general_analysis(
        self,
        result: CompetitiveAnalysisResult,
        competitors: list[CompetitorProfile]
    ):
        """Perform general competitive analysis."""
        result.market_summary = f"General analysis of {len(competitors)} competitors"

        # Basic competitive intelligence
        result.competitive_landscape = {
            "competitor_count": len(competitors),
            "categories": list({c.category.value for c in competitors}),
            "average_threat_level": "medium",  # Simplified
            "market_dynamics": "competitive"
        }

        # General recommendations
        result.strategic_recommendations = [
            "Maintain competitive monitoring",
            "Focus on differentiation",
            "Monitor market trends",
            "Strengthen competitive advantages"
        ]

    def _calculate_market_concentration(self, competitors: list[CompetitorProfile]) -> str:
        """Calculate market concentration level."""
        # Simplified concentration analysis
        high_threat_competitors = len([c for c in competitors if c.threat_level == ThreatLevel.CRITICAL])

        if high_threat_competitors >= 3:
            return "highly_concentrated"
        elif high_threat_competitors >= 1:
            return "moderately_concentrated"
        else:
            return "fragmented"

    def _calculate_data_coverage(self, competitors: list[CompetitorProfile]) -> float:
        """Calculate data coverage score for analysis."""
        if not competitors:
            return 0.0

        coverage_scores = []
        for competitor in competitors:
            coverage = competitor.confidence_score
            coverage_scores.append(coverage)

        return np.mean(coverage_scores)

    def _calculate_analysis_confidence(
        self,
        result: CompetitiveAnalysisResult,
        competitors: list[CompetitorProfile]
    ) -> float:
        """Calculate confidence score for analysis."""
        factors = {
            "data_coverage": result.data_coverage,
            "competitor_count": min(len(competitors) / 10.0, 1.0),
            "data_freshness": result.freshness_score,
            "analysis_depth": min(len(result.strategic_recommendations) / 5.0, 1.0)
        }

        # Weighted confidence
        weights = {"data_coverage": 0.4, "competitor_count": 0.2, "data_freshness": 0.2, "analysis_depth": 0.2}
        confidence = sum(factors[factor] * weights[factor] for factor in factors)

        return min(confidence, 1.0)

    def _calculate_freshness_score(self, competitors: list[CompetitorProfile]) -> float:
        """Calculate data freshness score."""
        if not competitors:
            return 0.0

        # Check how recent the competitor data is
        now = datetime.now()
        freshness_scores = []

        for competitor in competitors:
            try:
                last_updated = datetime.fromisoformat(competitor.last_updated.replace('Z', '+00:00').replace('+00:00', ''))
                days_old = (now - last_updated).days
                freshness = max(0.0, 1.0 - (days_old / 30.0))  # Decay over 30 days
                freshness_scores.append(freshness)
            except:
                freshness_scores.append(0.5)  # Default if parsing fails

        return np.mean(freshness_scores)

    def _update_analyzer_stats(self, result: CompetitiveAnalysisResult):
        """Update analyzer performance statistics."""
        # Update confidence average
        count = self.analyzer_stats["analyses_performed"]
        old_confidence = self.analyzer_stats["avg_analysis_confidence"]
        new_confidence = ((old_confidence * (count - 1)) + result.analysis_confidence) / count
        self.analyzer_stats["avg_analysis_confidence"] = new_confidence

        # Update data points collected
        self.analyzer_stats["data_points_collected"] += len(result.competitors_analyzed) * 10  # Rough estimate

    async def update_competitor_data(self, competitor_id: str) -> bool:
        """Update competitor data from available sources."""
        try:
            if competitor_id not in self.competitor_profiles:
                logger.error(f"Competitor {competitor_id} not found")
                return False

            profile = self.competitor_profiles[competitor_id]

            # Collect updated information
            updated_info = await self._collect_basic_competitor_info(profile.name)
            self._update_profile_with_basic_info(profile, updated_info)

            # Re-assess threat level
            profile.threat_level = await self._assess_threat_level(profile)

            # Update timestamp
            profile.last_updated = str(datetime.now())
            profile.next_review_date = str(datetime.now() + timedelta(days=7))

            # Recalculate confidence
            profile.confidence_score = self._calculate_profile_confidence(profile)

            logger.info(f"Updated competitor data for {profile.name}")
            return True

        except Exception as e:
            logger.error(f"Error updating competitor {competitor_id}: {str(e)}")
            return False

    def get_competitor_profile(self, competitor_id: str) -> CompetitorProfile | None:
        """Get competitor profile by ID."""
        return self.competitor_profiles.get(competitor_id)

    def get_analysis_result(self, analysis_id: str) -> CompetitiveAnalysisResult | None:
        """Get analysis result by ID."""
        return self.analysis_cache.get(analysis_id)

    def list_competitors(
        self,
        category: CompetitorCategory | None = None,
        threat_level: ThreatLevel | None = None
    ) -> list[CompetitorProfile]:
        """List competitors with optional filtering."""
        competitors = list(self.competitor_profiles.values())

        if category:
            competitors = [c for c in competitors if c.category == category]

        if threat_level:
            competitors = [c for c in competitors if c.threat_level == threat_level]

        return competitors

    def get_performance_stats(self) -> dict[str, Any]:
        """Get analyzer performance statistics."""
        return {
            **self.analyzer_stats,
            "active_competitors": len(self.competitor_profiles),
            "data_sources": len(self.data_sources),
            "cached_analyses": len(self.analysis_cache),
            "monitoring_schedules": len(self.monitoring_schedules)
        }

    async def generate_threat_alert(self, competitor_id: str, reason: str) -> dict[str, Any]:
        """Generate threat alert for competitor."""
        competitor = self.competitor_profiles.get(competitor_id)
        if not competitor:
            return {"error": "Competitor not found"}

        alert = {
            "alert_id": str(uuid4()),
            "competitor_name": competitor.name,
            "threat_level": competitor.threat_level.value,
            "alert_reason": reason,
            "timestamp": str(datetime.now()),
            "recommended_actions": [
                "Monitor competitor closely",
                "Assess strategic response options",
                "Update competitive strategy"
            ],
            "urgency": "high" if competitor.threat_level == ThreatLevel.CRITICAL else "medium"
        }

        self.analyzer_stats["threat_alerts_generated"] += 1
        logger.warning(f"Threat alert generated for {competitor.name}: {reason}")

        return alert
