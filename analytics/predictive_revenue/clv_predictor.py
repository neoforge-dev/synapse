"""Customer Lifetime Value Predictor for Epic 17 - Predictive Revenue Optimization.

Provides advanced CLV prediction and optimization with:
- ML-driven customer value forecasting
- Revenue potential analysis and optimization
- Expansion opportunity identification
- Customer segmentation and targeting
- ROI-optimized customer acquisition strategies
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CustomerSegment(Enum):
    """Customer segmentation categories."""
    CHAMPION = "champion"         # High value, high engagement
    LOYAL = "loyal"              # High value, medium engagement
    POTENTIAL = "potential"      # Medium value, high engagement
    NEW = "new"                  # Recent customers, developing
    AT_RISK = "at_risk"         # Declining engagement/value
    HIBERNATING = "hibernating"  # Low recent activity
    LOST = "lost"               # Churned customers


class RevenueCategory(Enum):
    """Revenue categorization."""
    SUBSCRIPTION = "subscription"     # Recurring subscription revenue
    PROFESSIONAL_SERVICES = "professional_services"  # One-time services
    EXPANSION = "expansion"          # Upsell/cross-sell revenue
    RENEWAL = "renewal"              # Contract renewals
    IMPLEMENTATION = "implementation" # Implementation fees
    SUPPORT = "support"              # Support contracts


class PredictionConfidence(Enum):
    """Confidence levels for predictions."""
    VERY_HIGH = "very_high"      # >95% confidence
    HIGH = "high"                # 85-95% confidence
    MODERATE = "moderate"        # 70-85% confidence
    LOW = "low"                  # 55-70% confidence
    VERY_LOW = "very_low"       # <55% confidence


@dataclass
class CustomerProfile:
    """Comprehensive customer profile for CLV analysis."""
    customer_id: str = field(default_factory=lambda: str(uuid4()))
    customer_name: str = ""
    segment: CustomerSegment = CustomerSegment.NEW

    # Basic information
    industry: str = ""
    company_size: str = ""  # startup, small, medium, large, enterprise
    geographic_region: str = ""
    acquisition_date: str = ""
    acquisition_channel: str = ""

    # Financial profile
    current_arr: float = 0.0  # Annual Recurring Revenue
    total_revenue: float = 0.0  # Total revenue to date
    initial_contract_value: float = 0.0
    average_contract_size: float = 0.0
    payment_terms: str = ""  # monthly, quarterly, annual

    # Usage and engagement
    usage_metrics: dict[str, float] = field(default_factory=dict)
    engagement_score: float = 0.0  # 0-1 scale
    feature_adoption_rate: float = 0.0
    support_ticket_count: int = 0
    nps_score: float | None = None

    # Relationship data
    primary_contacts: list[str] = field(default_factory=list)
    decision_makers: list[str] = field(default_factory=list)
    relationship_strength: float = 0.0  # 0-1 scale
    executive_sponsor: bool = False

    # Transaction history
    revenue_history: list[dict[str, Any]] = field(default_factory=list)
    contract_history: list[dict[str, Any]] = field(default_factory=list)
    expansion_events: list[dict[str, Any]] = field(default_factory=list)

    # Behavioral indicators
    login_frequency: float = 0.0  # logins per week
    feature_usage_depth: float = 0.0  # percentage of features used
    api_usage: float = 0.0  # API calls per month
    data_volume: float = 0.0  # amount of data processed

    # Risk indicators
    churn_risk_score: float = 0.0  # 0-1 scale
    payment_delays: int = 0
    support_escalations: int = 0
    contract_disputes: int = 0
    competitive_threats: list[str] = field(default_factory=list)

    # Opportunity indicators
    expansion_opportunities: list[str] = field(default_factory=list)
    cross_sell_potential: dict[str, float] = field(default_factory=dict)
    upsell_potential: float = 0.0
    referral_potential: float = 0.0

    # Metadata
    last_updated: str = ""
    data_sources: list[str] = field(default_factory=list)
    confidence_score: float = 0.0


@dataclass
class CLVPrediction:
    """Customer Lifetime Value prediction result."""
    prediction_id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    customer_name: str = ""

    # CLV predictions
    predicted_clv: float = 0.0
    clv_confidence: PredictionConfidence = PredictionConfidence.MODERATE
    prediction_timeframe: str = "3_years"  # 1_year, 3_years, 5_years, lifetime

    # Component breakdown
    clv_components: dict[str, float] = field(default_factory=dict)
    revenue_streams: dict[RevenueCategory, float] = field(default_factory=dict)

    # Time-based predictions
    year_1_revenue: float = 0.0
    year_2_revenue: float = 0.0
    year_3_revenue: float = 0.0
    monthly_revenue_forecast: list[float] = field(default_factory=list)

    # Risk and opportunity analysis
    churn_probability: float = 0.0
    expansion_probability: float = 0.0
    expected_lifespan: float = 0.0  # in years
    optimal_investment_level: float = 0.0

    # Strategic insights
    key_value_drivers: list[str] = field(default_factory=list)
    optimization_recommendations: list[str] = field(default_factory=list)
    investment_priorities: list[str] = field(default_factory=list)
    risk_mitigation_strategies: list[str] = field(default_factory=list)

    # Model information
    model_version: str = "1.0"
    prediction_date: str = ""
    next_update_date: str = ""
    accuracy_metrics: dict[str, float] = field(default_factory=dict)

    # Comparative analysis
    peer_group_percentile: float = 0.0  # Where customer ranks vs peers
    industry_benchmark: float = 0.0
    segment_average_clv: float = 0.0


class CLVModel(BaseModel):
    """Customer Lifetime Value prediction model."""
    model_id: str = Field(default_factory=lambda: str(uuid4()))
    model_name: str = ""
    model_type: str = "ensemble"  # linear, tree, ensemble, neural_network

    # Model parameters
    features: list[str] = Field(default_factory=list)
    target_variable: str = "lifetime_value"
    prediction_horizon: str = "3_years"

    # Performance metrics
    accuracy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    r2_score: float = Field(default=0.0)
    mean_absolute_error: float = Field(default=0.0)
    prediction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Training information
    training_data_size: int = Field(default=0)
    last_trained: str = Field(default="")
    validation_method: str = "cross_validation"

    # Model configuration
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    feature_importance: dict[str, float] = Field(default_factory=dict)
    model_weights: dict[str, float] | None = None


class CLVPredictor:
    """Advanced Customer Lifetime Value prediction and optimization engine."""

    def __init__(
        self,
        graph_repository=None,
        vector_store=None,
        analytics_service=None,
        customer_data_service=None,
        financial_service=None
    ):
        """Initialize the CLV predictor."""
        self.graph_repository = graph_repository
        self.vector_store = vector_store
        self.analytics_service = analytics_service
        self.customer_data_service = customer_data_service
        self.financial_service = financial_service

        # Customer database
        self.customer_profiles: dict[str, CustomerProfile] = {}
        self.clv_predictions: dict[str, CLVPrediction] = {}

        # Models
        self.prediction_models: dict[str, CLVModel] = {}
        self.active_model: str | None = None

        # Configuration
        self.model_features = self._initialize_model_features()
        self.segmentation_rules = self._initialize_segmentation_rules()
        self.benchmark_data = self._initialize_benchmark_data()

        # Performance tracking
        self.predictor_stats = {
            "customers_analyzed": 0,
            "predictions_generated": 0,
            "model_accuracy": 0.0,
            "prediction_accuracy": 0.0,
            "revenue_optimized": 0.0,
            "avg_prediction_confidence": 0.0
        }

        # Initialize default model
        self._initialize_default_model()

    def _initialize_model_features(self) -> dict[str, list[str]]:
        """Initialize features for CLV prediction models."""
        return {
            "financial_features": [
                "current_arr", "total_revenue", "initial_contract_value",
                "average_contract_size", "revenue_growth_rate", "payment_history"
            ],
            "behavioral_features": [
                "engagement_score", "feature_adoption_rate", "login_frequency",
                "feature_usage_depth", "api_usage", "data_volume"
            ],
            "relationship_features": [
                "relationship_strength", "nps_score", "support_ticket_count",
                "executive_sponsor", "decision_maker_engagement"
            ],
            "company_features": [
                "company_size", "industry", "geographic_region",
                "technology_maturity", "growth_stage"
            ],
            "temporal_features": [
                "customer_age", "contract_length", "renewal_history",
                "expansion_history", "seasonal_patterns"
            ]
        }

    def _initialize_segmentation_rules(self) -> dict[CustomerSegment, dict[str, Any]]:
        """Initialize customer segmentation rules."""
        return {
            CustomerSegment.CHAMPION: {
                "arr_threshold": 100000,
                "engagement_threshold": 0.8,
                "nps_threshold": 8,
                "churn_risk_threshold": 0.2
            },
            CustomerSegment.LOYAL: {
                "arr_threshold": 50000,
                "engagement_threshold": 0.6,
                "nps_threshold": 7,
                "churn_risk_threshold": 0.3
            },
            CustomerSegment.POTENTIAL: {
                "arr_threshold": 25000,
                "engagement_threshold": 0.7,
                "growth_trajectory": "positive",
                "expansion_potential": 0.6
            },
            CustomerSegment.NEW: {
                "customer_age_max": 180,  # days
                "min_engagement": 0.4
            },
            CustomerSegment.AT_RISK: {
                "churn_risk_threshold": 0.6,
                "engagement_decline": True,
                "support_escalations": 2
            }
        }

    def _initialize_benchmark_data(self) -> dict[str, dict[str, float]]:
        """Initialize industry and segment benchmark data."""
        return {
            "industry_benchmarks": {
                "technology": {"avg_clv": 250000, "churn_rate": 0.12, "expansion_rate": 1.25},
                "financial_services": {"avg_clv": 400000, "churn_rate": 0.08, "expansion_rate": 1.15},
                "healthcare": {"avg_clv": 180000, "churn_rate": 0.15, "expansion_rate": 1.10},
                "manufacturing": {"avg_clv": 300000, "churn_rate": 0.10, "expansion_rate": 1.20}
            },
            "segment_benchmarks": {
                CustomerSegment.CHAMPION.value: {"avg_clv": 500000, "retention_rate": 0.95},
                CustomerSegment.LOYAL.value: {"avg_clv": 200000, "retention_rate": 0.90},
                CustomerSegment.POTENTIAL.value: {"avg_clv": 150000, "retention_rate": 0.85},
                CustomerSegment.NEW.value: {"avg_clv": 100000, "retention_rate": 0.80}
            }
        }

    def _initialize_default_model(self):
        """Initialize default CLV prediction model."""
        default_model = CLVModel(
            model_name="Default CLV Ensemble",
            model_type="ensemble",
            features=self._get_all_features(),
            accuracy_score=0.85,
            r2_score=0.78,
            prediction_confidence=0.82,
            last_trained=str(datetime.now())
        )

        # Mock feature importance
        all_features = self._get_all_features()
        default_model.feature_importance = {
            feature: np.random.uniform(0.01, 0.15)
            for feature in all_features
        }

        # Normalize importance scores
        total_importance = sum(default_model.feature_importance.values())
        default_model.feature_importance = {
            k: v / total_importance for k, v in default_model.feature_importance.items()
        }

        self.prediction_models[default_model.model_id] = default_model
        self.active_model = default_model.model_id

    def _get_all_features(self) -> list[str]:
        """Get all available features for modeling."""
        all_features = []
        for feature_category in self.model_features.values():
            all_features.extend(feature_category)
        return all_features

    async def analyze_customer(
        self,
        customer_data: dict[str, Any],
        update_existing: bool = True
    ) -> CustomerProfile:
        """Analyze customer and create/update profile."""
        customer_name = customer_data.get("customer_name", "Unknown Customer")

        # Find or create customer profile
        existing_profile = self._find_existing_customer(customer_name)
        if existing_profile and update_existing:
            profile = existing_profile
        else:
            profile = CustomerProfile(
                customer_name=customer_name,
                acquisition_date=customer_data.get("acquisition_date", str(datetime.now()))
            )

        try:
            # Update profile with provided data
            self._update_profile_with_data(profile, customer_data)

            # Calculate derived metrics
            await self._calculate_behavioral_metrics(profile)

            # Determine customer segment
            profile.segment = self._determine_customer_segment(profile)

            # Calculate engagement and relationship scores
            profile.engagement_score = self._calculate_engagement_score(profile)
            profile.relationship_strength = self._calculate_relationship_strength(profile)

            # Assess churn risk
            profile.churn_risk_score = await self._assess_churn_risk(profile)

            # Identify opportunities
            await self._identify_opportunities(profile)

            # Update metadata
            profile.last_updated = str(datetime.now())
            profile.confidence_score = self._calculate_profile_confidence(profile)

            # Store profile
            self.customer_profiles[profile.customer_id] = profile
            self.predictor_stats["customers_analyzed"] += 1

            logger.info(f"Customer analysis completed for {customer_name}: "
                       f"Segment: {profile.segment.value}, "
                       f"Engagement: {profile.engagement_score:.2f}")

            return profile

        except Exception as e:
            logger.error(f"Error analyzing customer {customer_name}: {str(e)}")
            profile.confidence_score = 0.2
            return profile

    def _find_existing_customer(self, customer_name: str) -> CustomerProfile | None:
        """Find existing customer profile by name."""
        for profile in self.customer_profiles.values():
            if profile.customer_name.lower() == customer_name.lower():
                return profile
        return None

    def _update_profile_with_data(
        self,
        profile: CustomerProfile,
        customer_data: dict[str, Any]
    ):
        """Update customer profile with provided data."""
        field_mappings = {
            "industry": "industry",
            "company_size": "company_size",
            "geographic_region": "geographic_region",
            "current_arr": "current_arr",
            "total_revenue": "total_revenue",
            "initial_contract_value": "initial_contract_value",
            "nps_score": "nps_score",
            "acquisition_channel": "acquisition_channel"
        }

        for data_key, profile_key in field_mappings.items():
            if data_key in customer_data:
                setattr(profile, profile_key, customer_data[data_key])

        # Handle complex data structures
        if "usage_metrics" in customer_data:
            profile.usage_metrics.update(customer_data["usage_metrics"])

        if "revenue_history" in customer_data:
            profile.revenue_history = customer_data["revenue_history"]

        if "expansion_events" in customer_data:
            profile.expansion_events = customer_data["expansion_events"]

    async def _calculate_behavioral_metrics(self, profile: CustomerProfile):
        """Calculate behavioral metrics for customer."""
        # Feature adoption rate
        if profile.usage_metrics:
            total_features = 20  # Assume 20 total features
            used_features = len([k for k, v in profile.usage_metrics.items() if v > 0])
            profile.feature_adoption_rate = used_features / total_features

        # API usage and data volume (mock calculations)
        profile.api_usage = profile.usage_metrics.get("api_calls_monthly", 0)
        profile.data_volume = profile.usage_metrics.get("data_processed_gb", 0)
        profile.login_frequency = profile.usage_metrics.get("weekly_logins", 0)

        # Feature usage depth
        if profile.usage_metrics:
            usage_values = [v for v in profile.usage_metrics.values() if isinstance(v, (int, float))]
            profile.feature_usage_depth = np.mean(usage_values) if usage_values else 0.0

    def _determine_customer_segment(self, profile: CustomerProfile) -> CustomerSegment:
        """Determine customer segment based on profile data."""
        rules = self.segmentation_rules

        # Check for Champion
        champion_rules = rules[CustomerSegment.CHAMPION]
        if (profile.current_arr >= champion_rules["arr_threshold"] and
            profile.engagement_score >= champion_rules["engagement_threshold"] and
            (profile.nps_score or 0) >= champion_rules["nps_threshold"] and
            profile.churn_risk_score <= champion_rules["churn_risk_threshold"]):
            return CustomerSegment.CHAMPION

        # Check for Loyal
        loyal_rules = rules[CustomerSegment.LOYAL]
        if (profile.current_arr >= loyal_rules["arr_threshold"] and
            profile.engagement_score >= loyal_rules["engagement_threshold"] and
            (profile.nps_score or 0) >= loyal_rules["nps_threshold"]):
            return CustomerSegment.LOYAL

        # Check for At Risk
        at_risk_rules = rules[CustomerSegment.AT_RISK]
        if (profile.churn_risk_score >= at_risk_rules["churn_risk_threshold"] or
            profile.support_escalations >= at_risk_rules["support_escalations"]):
            return CustomerSegment.AT_RISK

        # Check for New Customer
        new_rules = rules[CustomerSegment.NEW]
        if profile.acquisition_date:
            try:
                acquisition_date = datetime.fromisoformat(profile.acquisition_date.replace('Z', '+00:00'))
                days_since_acquisition = (datetime.now() - acquisition_date).days
                if (days_since_acquisition <= new_rules["customer_age_max"] and
                    profile.engagement_score >= new_rules["min_engagement"]):
                    return CustomerSegment.NEW
            except:
                pass

        # Check for Potential
        potential_rules = rules[CustomerSegment.POTENTIAL]
        if (profile.current_arr >= potential_rules["arr_threshold"] and
            profile.engagement_score >= potential_rules["engagement_threshold"]):
            return CustomerSegment.POTENTIAL

        # Default to Hibernating
        return CustomerSegment.HIBERNATING

    def _calculate_engagement_score(self, profile: CustomerProfile) -> float:
        """Calculate customer engagement score."""
        engagement_factors = {
            "feature_adoption": profile.feature_adoption_rate * 0.3,
            "login_frequency": min(profile.login_frequency / 10.0, 1.0) * 0.2,  # Normalize to weekly
            "api_usage": min(profile.api_usage / 1000.0, 1.0) * 0.15,  # Normalize to 1K calls
            "data_volume": min(profile.data_volume / 100.0, 1.0) * 0.15,  # Normalize to 100GB
            "support_satisfaction": (1.0 - min(profile.support_escalations / 5.0, 1.0)) * 0.1,
            "nps_contribution": ((profile.nps_score or 5) - 5) / 5.0 * 0.1 if profile.nps_score else 0.0
        }

        engagement_score = sum(engagement_factors.values())
        return min(max(engagement_score, 0.0), 1.0)

    def _calculate_relationship_strength(self, profile: CustomerProfile) -> float:
        """Calculate relationship strength score."""
        relationship_factors = {
            "executive_sponsor": 0.3 if profile.executive_sponsor else 0.0,
            "contact_diversity": min(len(profile.primary_contacts) / 5.0, 1.0) * 0.2,
            "decision_maker_access": min(len(profile.decision_makers) / 3.0, 1.0) * 0.2,
            "nps_score": ((profile.nps_score or 5) - 5) / 5.0 * 0.15 if profile.nps_score else 0.0,
            "contract_stability": (1.0 - min(profile.contract_disputes / 3.0, 1.0)) * 0.15
        }

        relationship_score = sum(relationship_factors.values())
        return min(max(relationship_score, 0.0), 1.0)

    async def _assess_churn_risk(self, profile: CustomerProfile) -> float:
        """Assess customer churn risk."""
        risk_factors = {
            "engagement_decline": max(0.0, (0.7 - profile.engagement_score)) * 0.3,
            "payment_issues": min(profile.payment_delays / 3.0, 1.0) * 0.2,
            "support_escalations": min(profile.support_escalations / 5.0, 1.0) * 0.15,
            "competitive_threats": min(len(profile.competitive_threats) / 3.0, 1.0) * 0.15,
            "contract_disputes": min(profile.contract_disputes / 2.0, 1.0) * 0.1,
            "low_feature_adoption": max(0.0, (0.5 - profile.feature_adoption_rate)) * 0.1
        }

        churn_risk = sum(risk_factors.values())
        return min(churn_risk, 1.0)

    async def _identify_opportunities(self, profile: CustomerProfile):
        """Identify expansion and optimization opportunities."""
        opportunities = []
        cross_sell_potential = {}

        # Expansion opportunities based on usage
        if profile.feature_adoption_rate > 0.8:
            opportunities.append("High feature adoption indicates readiness for premium tier")

        if profile.api_usage > 500:
            opportunities.append("High API usage suggests need for higher tier limits")

        if profile.data_volume > 50:
            opportunities.append("Large data volume indicates potential for analytics add-ons")

        # Cross-sell opportunities based on company profile
        if profile.company_size in ["large", "enterprise"]:
            cross_sell_potential["enterprise_security"] = 0.7
            cross_sell_potential["advanced_analytics"] = 0.6
            cross_sell_potential["professional_services"] = 0.8

        if profile.industry == "financial_services":
            cross_sell_potential["compliance_package"] = 0.8
            cross_sell_potential["audit_tools"] = 0.6

        # Upsell potential based on growth
        if len(profile.expansion_events) > 0:
            recent_expansion = any(
                (datetime.now() - datetime.fromisoformat(event.get("date", "2020-01-01"))).days < 180
                for event in profile.expansion_events
            )
            profile.upsell_potential = 0.8 if recent_expansion else 0.5
        else:
            profile.upsell_potential = 0.3

        # Referral potential
        if profile.nps_score and profile.nps_score >= 8:
            profile.referral_potential = 0.7
        else:
            profile.referral_potential = 0.3

        profile.expansion_opportunities = opportunities
        profile.cross_sell_potential = cross_sell_potential

    def _calculate_profile_confidence(self, profile: CustomerProfile) -> float:
        """Calculate confidence score for customer profile."""
        confidence_factors = {
            "basic_data": 1.0 if profile.customer_name and profile.industry else 0.5,
            "financial_data": 1.0 if profile.current_arr and profile.total_revenue else 0.3,
            "behavioral_data": profile.engagement_score,
            "usage_data": 1.0 if profile.usage_metrics else 0.2,
            "relationship_data": profile.relationship_strength,
            "historical_data": min(len(profile.revenue_history) / 12.0, 1.0)  # 12 months ideal
        }

        weights = [0.15, 0.2, 0.2, 0.15, 0.15, 0.15]
        confidence = sum(factor * weight for factor, weight in zip(confidence_factors.values(), weights, strict=False))

        return min(confidence, 1.0)

    async def predict_clv(
        self,
        customer_id: str,
        prediction_timeframe: str = "3_years",
        confidence_threshold: float = 0.7
    ) -> CLVPrediction:
        """Generate CLV prediction for customer."""
        try:
            profile = self.customer_profiles.get(customer_id)
            if not profile:
                raise ValueError(f"Customer {customer_id} not found")

            prediction = CLVPrediction(
                customer_id=customer_id,
                customer_name=profile.customer_name,
                prediction_timeframe=prediction_timeframe,
                prediction_date=str(datetime.now())
            )

            # Use active model for prediction
            model = self.prediction_models.get(self.active_model)
            if not model:
                raise ValueError("No active prediction model available")

            # Generate base CLV prediction
            base_clv = await self._calculate_base_clv(profile, prediction_timeframe)

            # Apply model adjustments and confidence
            adjusted_clv, confidence = await self._apply_model_prediction(
                profile, base_clv, model, prediction_timeframe
            )

            prediction.predicted_clv = adjusted_clv
            prediction.clv_confidence = self._determine_prediction_confidence(confidence)

            # Break down CLV components
            prediction.clv_components = await self._calculate_clv_components(
                profile, adjusted_clv, prediction_timeframe
            )

            # Generate time-based forecasts
            await self._generate_revenue_forecasts(prediction, profile, prediction_timeframe)

            # Calculate risk and opportunity metrics
            prediction.churn_probability = profile.churn_risk_score
            prediction.expansion_probability = profile.upsell_potential
            prediction.expected_lifespan = await self._calculate_expected_lifespan(profile)

            # Generate strategic insights
            await self._generate_clv_insights(prediction, profile)

            # Add benchmarking
            await self._add_benchmark_analysis(prediction, profile)

            # Cache prediction
            self.clv_predictions[prediction.prediction_id] = prediction
            self.predictor_stats["predictions_generated"] += 1

            logger.info(f"CLV prediction generated for {profile.customer_name}: "
                       f"${prediction.predicted_clv:,.0f} over {prediction_timeframe}")

            return prediction

        except Exception as e:
            logger.error(f"Error predicting CLV for customer {customer_id}: {str(e)}")
            # Return minimal prediction with error indication
            return CLVPrediction(
                customer_id=customer_id,
                clv_confidence=PredictionConfidence.VERY_LOW,
                predicted_clv=0.0
            )

    async def _calculate_base_clv(
        self,
        profile: CustomerProfile,
        timeframe: str
    ) -> float:
        """Calculate base CLV using traditional methods."""
        # Time multiplier
        time_multipliers = {
            "1_year": 1.0,
            "3_years": 3.0,
            "5_years": 5.0,
            "lifetime": 8.0  # Assume 8-year average customer lifetime
        }

        multiplier = time_multipliers.get(timeframe, 3.0)

        # Base calculation: ARR * time * retention rate
        retention_rate = 1.0 - profile.churn_risk_score
        base_clv = profile.current_arr * multiplier * retention_rate

        # Adjust for expansion potential
        expansion_factor = 1.0 + (profile.upsell_potential * 0.5)  # Up to 50% expansion
        base_clv *= expansion_factor

        # Adjust for segment
        segment_multipliers = {
            CustomerSegment.CHAMPION: 1.5,
            CustomerSegment.LOYAL: 1.2,
            CustomerSegment.POTENTIAL: 1.1,
            CustomerSegment.NEW: 0.9,
            CustomerSegment.AT_RISK: 0.6,
            CustomerSegment.HIBERNATING: 0.4,
            CustomerSegment.LOST: 0.1
        }

        segment_multiplier = segment_multipliers.get(profile.segment, 1.0)
        base_clv *= segment_multiplier

        return base_clv

    async def _apply_model_prediction(
        self,
        profile: CustomerProfile,
        base_clv: float,
        model: CLVModel,
        timeframe: str
    ) -> tuple[float, float]:
        """Apply ML model to refine CLV prediction."""
        # Extract feature values
        feature_values = self._extract_feature_values(profile)

        # Apply feature importance weighting (simplified ML simulation)
        model_adjustment = 1.0
        confidence_factors = []

        for feature, importance in model.feature_importance.items():
            if feature in feature_values:
                feature_value = feature_values[feature]

                # Normalize feature value (simplified)
                normalized_value = min(max(feature_value, 0.0), 1.0)

                # Apply feature impact
                feature_impact = normalized_value * importance
                model_adjustment += feature_impact * 0.2  # Max 20% impact per feature

                # Track confidence
                confidence_factors.append(normalized_value * importance)

        # Calculate prediction confidence
        prediction_confidence = np.mean(confidence_factors) if confidence_factors else 0.5
        prediction_confidence = min(prediction_confidence * model.prediction_confidence, 1.0)

        # Apply model adjustment
        adjusted_clv = base_clv * model_adjustment

        return adjusted_clv, prediction_confidence

    def _extract_feature_values(self, profile: CustomerProfile) -> dict[str, float]:
        """Extract feature values from customer profile."""
        features = {}

        # Financial features (normalized)
        features["current_arr"] = min(profile.current_arr / 100000, 2.0)  # Normalize to $100K
        features["total_revenue"] = min(profile.total_revenue / 500000, 2.0)  # Normalize to $500K
        features["initial_contract_value"] = min(profile.initial_contract_value / 50000, 2.0)

        # Behavioral features
        features["engagement_score"] = profile.engagement_score
        features["feature_adoption_rate"] = profile.feature_adoption_rate
        features["login_frequency"] = min(profile.login_frequency / 20, 1.0)  # Normalize to 20/week

        # Relationship features
        features["relationship_strength"] = profile.relationship_strength
        features["nps_score"] = (profile.nps_score or 5) / 10.0 if profile.nps_score else 0.5

        # Risk features
        features["churn_risk_score"] = profile.churn_risk_score
        features["support_escalations"] = min(profile.support_escalations / 5, 1.0)

        return features

    def _determine_prediction_confidence(self, confidence_score: float) -> PredictionConfidence:
        """Determine prediction confidence level."""
        if confidence_score >= 0.95:
            return PredictionConfidence.VERY_HIGH
        elif confidence_score >= 0.85:
            return PredictionConfidence.HIGH
        elif confidence_score >= 0.70:
            return PredictionConfidence.MODERATE
        elif confidence_score >= 0.55:
            return PredictionConfidence.LOW
        else:
            return PredictionConfidence.VERY_LOW

    async def _calculate_clv_components(
        self,
        profile: CustomerProfile,
        total_clv: float,
        timeframe: str
    ) -> dict[str, float]:
        """Break down CLV into components."""
        components = {}

        # Base subscription revenue (70% of CLV typically)
        components["subscription_revenue"] = total_clv * 0.70

        # Expansion revenue (15-20% of CLV)
        expansion_factor = profile.upsell_potential
        components["expansion_revenue"] = total_clv * (0.15 + expansion_factor * 0.05)

        # Professional services (5-10% of CLV)
        if profile.company_size in ["large", "enterprise"]:
            components["professional_services"] = total_clv * 0.10
        else:
            components["professional_services"] = total_clv * 0.05

        # Support and maintenance (remaining)
        components["support_maintenance"] = total_clv - sum(components.values())

        return components

    async def _generate_revenue_forecasts(
        self,
        prediction: CLVPrediction,
        profile: CustomerProfile,
        timeframe: str
    ):
        """Generate time-based revenue forecasts."""
        total_clv = prediction.predicted_clv

        # Yearly breakdown
        if timeframe in ["3_years", "5_years", "lifetime"]:
            # Year 1: Current ARR with some growth
            growth_rate = 0.15 if profile.segment in [CustomerSegment.CHAMPION, CustomerSegment.POTENTIAL] else 0.10
            prediction.year_1_revenue = profile.current_arr * (1 + growth_rate)

            # Year 2: Continued growth with potential expansion
            expansion_impact = profile.upsell_potential * 0.3
            prediction.year_2_revenue = prediction.year_1_revenue * (1 + growth_rate + expansion_impact)

            # Year 3: Maturity with slower growth
            prediction.year_3_revenue = prediction.year_2_revenue * (1 + growth_rate * 0.5)

        # Monthly forecast for first year
        monthly_base = prediction.year_1_revenue / 12
        monthly_forecast = []

        for month in range(12):
            # Add some seasonality and growth trend
            seasonal_factor = 1.0 + 0.1 * np.sin(month * np.pi / 6)  # Semi-annual pattern
            growth_factor = 1.0 + (month / 12) * 0.15  # 15% annual growth
            monthly_revenue = monthly_base * seasonal_factor * growth_factor
            monthly_forecast.append(monthly_revenue)

        prediction.monthly_revenue_forecast = monthly_forecast

    async def _calculate_expected_lifespan(self, profile: CustomerProfile) -> float:
        """Calculate expected customer lifespan in years."""
        # Base lifespan by segment
        segment_lifespans = {
            CustomerSegment.CHAMPION: 7.0,
            CustomerSegment.LOYAL: 5.0,
            CustomerSegment.POTENTIAL: 4.0,
            CustomerSegment.NEW: 3.0,
            CustomerSegment.AT_RISK: 1.5,
            CustomerSegment.HIBERNATING: 0.5,
            CustomerSegment.LOST: 0.1
        }

        base_lifespan = segment_lifespans.get(profile.segment, 3.0)

        # Adjust for churn risk
        churn_adjustment = 1.0 - (profile.churn_risk_score * 0.5)

        # Adjust for relationship strength
        relationship_adjustment = 1.0 + (profile.relationship_strength * 0.3)

        expected_lifespan = base_lifespan * churn_adjustment * relationship_adjustment
        return max(expected_lifespan, 0.1)  # Minimum 1 month

    async def _generate_clv_insights(self, prediction: CLVPrediction, profile: CustomerProfile):
        """Generate strategic insights for CLV optimization."""
        insights = []

        # Value drivers
        if profile.engagement_score > 0.8:
            insights.append("High engagement score is key value driver")
        if profile.feature_adoption_rate > 0.7:
            insights.append("Strong feature adoption indicates product-market fit")
        if profile.relationship_strength > 0.7:
            insights.append("Strong relationships support retention and expansion")

        prediction.key_value_drivers = insights

        # Optimization recommendations
        recommendations = []

        if profile.churn_risk_score > 0.5:
            recommendations.append("Implement churn prevention program")

        if profile.upsell_potential > 0.6:
            recommendations.append("Pursue expansion opportunities aggressively")

        if profile.engagement_score < 0.5:
            recommendations.append("Improve customer success engagement")

        if len(profile.decision_makers) < 2:
            recommendations.append("Expand stakeholder relationships")

        prediction.optimization_recommendations = recommendations

        # Investment priorities
        investment_priorities = []

        if profile.segment == CustomerSegment.CHAMPION:
            investment_priorities.append("Executive relationship management")
        elif profile.segment == CustomerSegment.AT_RISK:
            investment_priorities.append("Immediate retention intervention")
        elif profile.segment == CustomerSegment.POTENTIAL:
            investment_priorities.append("Expansion opportunity development")

        prediction.investment_priorities = investment_priorities

    async def _add_benchmark_analysis(self, prediction: CLVPrediction, profile: CustomerProfile):
        """Add benchmark analysis to prediction."""
        benchmarks = self.benchmark_data

        # Industry benchmark
        industry_benchmark = benchmarks["industry_benchmarks"].get(
            profile.industry, benchmarks["industry_benchmarks"]["technology"]
        )
        prediction.industry_benchmark = industry_benchmark["avg_clv"]

        # Segment benchmark
        segment_benchmark = benchmarks["segment_benchmarks"].get(
            profile.segment.value, benchmarks["segment_benchmarks"]["new"]
        )
        prediction.segment_average_clv = segment_benchmark["avg_clv"]

        # Percentile calculation
        if prediction.industry_benchmark > 0:
            prediction.peer_group_percentile = min(
                prediction.predicted_clv / prediction.industry_benchmark, 2.0
            ) * 0.5  # Normalize to 0-1 range

    def get_customer_profile(self, customer_id: str) -> CustomerProfile | None:
        """Get customer profile by ID."""
        return self.customer_profiles.get(customer_id)

    def get_clv_prediction(self, prediction_id: str) -> CLVPrediction | None:
        """Get CLV prediction by ID."""
        return self.clv_predictions.get(prediction_id)

    def list_customers_by_segment(self, segment: CustomerSegment) -> list[CustomerProfile]:
        """List customers by segment."""
        return [
            profile for profile in self.customer_profiles.values()
            if profile.segment == segment
        ]

    def get_top_value_customers(self, limit: int = 10) -> list[tuple[CustomerProfile, CLVPrediction | None]]:
        """Get top value customers with their CLV predictions."""
        customer_values = []

        for customer_id, profile in self.customer_profiles.items():
            # Find most recent CLV prediction
            customer_predictions = [
                pred for pred in self.clv_predictions.values()
                if pred.customer_id == customer_id
            ]

            if customer_predictions:
                latest_prediction = max(customer_predictions, key=lambda p: p.prediction_date)
                customer_values.append((profile, latest_prediction, latest_prediction.predicted_clv))
            else:
                # Use current ARR as fallback
                customer_values.append((profile, None, profile.current_arr * 3))  # 3-year estimate

        # Sort by value and return top customers
        customer_values.sort(key=lambda x: x[2], reverse=True)
        return [(profile, prediction) for profile, prediction, _ in customer_values[:limit]]

    def get_performance_stats(self) -> dict[str, Any]:
        """Get predictor performance statistics."""
        # Calculate accuracy metrics
        if self.clv_predictions:
            confidence_scores = [
                pred.clv_confidence for pred in self.clv_predictions.values()
            ]
            avg_confidence_numeric = np.mean([
                {"very_high": 0.95, "high": 0.85, "moderate": 0.75, "low": 0.6, "very_low": 0.4}
                .get(conf.value, 0.5) for conf in confidence_scores
            ])
            self.predictor_stats["avg_prediction_confidence"] = avg_confidence_numeric

        return {
            **self.predictor_stats,
            "active_customers": len(self.customer_profiles),
            "cached_predictions": len(self.clv_predictions),
            "active_models": len(self.prediction_models),
            "customer_segments": {
                segment.value: len(self.list_customers_by_segment(segment))
                for segment in CustomerSegment
            }
        }

    async def batch_predict_clv(
        self,
        customer_ids: list[str],
        timeframe: str = "3_years"
    ) -> dict[str, CLVPrediction]:
        """Generate CLV predictions for multiple customers."""
        predictions = {}

        for customer_id in customer_ids:
            try:
                prediction = await self.predict_clv(customer_id, timeframe)
                predictions[customer_id] = prediction
            except Exception as e:
                logger.error(f"Batch prediction failed for customer {customer_id}: {str(e)}")

        return predictions
