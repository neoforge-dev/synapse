"""
SQLAlchemy models for Epic 16 Fortune 500 acquisition system.
These models provide the database schema and ORM mappings for:
- Fortune 500 prospect acquisition
- Account-Based Marketing (ABM) campaigns
- Enterprise onboarding and success management

Database: synapse_business_core (PostgreSQL)
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
import uuid

from sqlalchemy import Column, String, Integer, DECIMAL, TIMESTAMP, Text, ForeignKey, Index, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, CHAR

from graph_rag.infrastructure.persistence.models.base import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36) for SQLite.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return uuid.UUID(value)
            return value


class JSONType(TypeDecorator):
    """Platform-independent JSON type.

    Uses PostgreSQL's JSONB type when available, otherwise uses JSON for SQLite.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


# ============================================================================
# Fortune 500 Acquisition Models
# ============================================================================

class Fortune500ProspectModel(Base):
    """SQLAlchemy model for Fortune 500 prospects table"""
    __tablename__ = "f500_prospects"

    prospect_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    revenue_billions = Column(DECIMAL(10, 2))
    industry = Column(String(100))
    headquarters = Column(String(255))
    employees = Column(Integer)
    stock_symbol = Column(String(10))
    market_cap_billions = Column(DECIMAL(12, 2))
    ceo_name = Column(String(255))
    cto_name = Column(String(255))
    engineering_headcount = Column(Integer)
    tech_stack = Column(JSONType, default=list)  # JSON array of technologies
    digital_transformation_score = Column(DECIMAL(3, 1))  # 0.0 to 10.0
    acquisition_score = Column(DECIMAL(5, 1))
    contact_priority = Column(String(20), nullable=False, default='silver')  # platinum, gold, silver
    estimated_contract_value = Column(Integer)
    pain_points = Column(JSONType, default=list)  # JSON array of pain points
    decision_makers = Column(JSONType, default=list)  # JSON array of decision maker objects
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    lead_scoring = relationship("F500LeadScoringModel", back_populates="prospect", cascade="all, delete-orphan")
    business_cases = relationship("F500BusinessCaseModel", back_populates="prospect", cascade="all, delete-orphan")
    sales_sequences = relationship("F500SalesSequenceModel", back_populates="prospect", cascade="all, delete-orphan")
    roi_tracking = relationship("F500ROITrackingModel", back_populates="prospect", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_f500_prospects_company_name', 'company_name'),
        Index('idx_f500_prospects_industry', 'industry'),
        Index('idx_f500_prospects_acquisition_score', 'acquisition_score'),
        Index('idx_f500_prospects_priority', 'contact_priority'),
        Index('idx_f500_prospects_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Fortune500Prospect(company_name='{self.company_name}', priority='{self.contact_priority}', score={self.acquisition_score})>"


class F500LeadScoringModel(Base):
    """SQLAlchemy model for Fortune 500 lead scoring history"""
    __tablename__ = "f500_lead_scoring"

    scoring_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    prospect_id = Column(GUID, ForeignKey('f500_prospects.prospect_id'), nullable=False)
    base_score = Column(DECIMAL(5, 2))
    revenue_multiplier = Column(DECIMAL(5, 2))
    industry_fit_score = Column(DECIMAL(5, 2))
    technology_readiness = Column(DECIMAL(5, 2))
    decision_maker_accessibility = Column(DECIMAL(5, 2))
    timing_signals = Column(DECIMAL(5, 2))
    competitive_landscape = Column(DECIMAL(5, 2))
    final_score = Column(DECIMAL(6, 2), nullable=False)
    confidence_level = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    scoring_rationale = Column(JSONType, default=list)  # JSON array of rationale strings
    scored_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    prospect = relationship("Fortune500ProspectModel", back_populates="lead_scoring")

    # Indexes
    __table_args__ = (
        Index('idx_f500_scoring_prospect_id', 'prospect_id'),
        Index('idx_f500_scoring_final_score', 'final_score'),
        Index('idx_f500_scoring_date', 'scored_at'),
    )

    def __repr__(self):
        return f"<F500LeadScoring(prospect_id='{self.prospect_id}', final_score={self.final_score}, confidence={self.confidence_level})>"


class F500BusinessCaseModel(Base):
    """SQLAlchemy model for Fortune 500 business cases"""
    __tablename__ = "f500_business_cases"

    case_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    prospect_id = Column(GUID, ForeignKey('f500_prospects.prospect_id'), nullable=False)
    problem_quantification = Column(JSONType, default=dict)  # JSON object with problem metrics
    solution_benefits = Column(JSONType, default=dict)  # JSON object with benefit metrics
    roi_calculation = Column(JSONType, default=dict)  # JSON object with ROI metrics
    risk_assessment = Column(JSONType, default=dict)  # JSON object with risk factors
    implementation_timeline = Column(JSONType, default=dict)  # JSON object with timeline phases
    investment_options = Column(JSONType, default=dict)  # JSON object with tiered options
    projected_savings = Column(Integer)  # Annual savings in dollars
    payback_months = Column(Integer)
    confidence_score = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    prospect = relationship("Fortune500ProspectModel", back_populates="business_cases")

    # Indexes
    __table_args__ = (
        Index('idx_f500_cases_prospect_id', 'prospect_id'),
        Index('idx_f500_cases_projected_savings', 'projected_savings'),
        Index('idx_f500_cases_payback', 'payback_months'),
        Index('idx_f500_cases_generated_at', 'generated_at'),
    )

    def __repr__(self):
        return f"<F500BusinessCase(prospect_id='{self.prospect_id}', savings=${self.projected_savings}, payback={self.payback_months}mo)>"


class F500SalesSequenceModel(Base):
    """SQLAlchemy model for Fortune 500 sales sequences"""
    __tablename__ = "f500_sales_sequences"

    sequence_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    prospect_id = Column(GUID, ForeignKey('f500_prospects.prospect_id'), nullable=False)
    sequence_type = Column(String(50), nullable=False)  # c_level_approach, technical_decision_maker, etc.
    touch_points = Column(JSONType, nullable=False, default=list)  # JSON array of touchpoint objects
    current_step = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default='active')  # active, paused, completed, converted
    personalization_data = Column(JSONType, default=dict)  # JSON object with personalization details
    engagement_metrics = Column(JSONType, default=dict)  # JSON object with engagement stats
    conversion_probability = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_interaction = Column(TIMESTAMP(timezone=True))

    # Relationships
    prospect = relationship("Fortune500ProspectModel", back_populates="sales_sequences")

    # Indexes
    __table_args__ = (
        Index('idx_f500_sequences_prospect_id', 'prospect_id'),
        Index('idx_f500_sequences_type', 'sequence_type'),
        Index('idx_f500_sequences_status', 'status'),
        Index('idx_f500_sequences_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<F500SalesSequence(prospect_id='{self.prospect_id}', type='{self.sequence_type}', status='{self.status}')>"


class F500ROITrackingModel(Base):
    """SQLAlchemy model for Fortune 500 ROI tracking"""
    __tablename__ = "f500_roi_tracking"

    roi_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    prospect_id = Column(GUID, ForeignKey('f500_prospects.prospect_id'), nullable=False)
    engagement_type = Column(String(50), nullable=False)  # initial_contact, demo, pilot, contract
    investment_stage = Column(String(50), nullable=False)  # prospect, qualified, proposal, negotiation, closed
    actual_investment = Column(Integer)  # Actual dollars invested
    projected_value = Column(Integer)  # Projected contract value
    time_investment_hours = Column(Integer)  # Hours spent on prospect
    success_probability = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    current_roi = Column(DECIMAL(6, 2))  # Current ROI percentage
    lifetime_value_projection = Column(Integer)  # Projected lifetime value
    tracked_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    prospect = relationship("Fortune500ProspectModel", back_populates="roi_tracking")

    # Indexes
    __table_args__ = (
        Index('idx_f500_roi_prospect_id', 'prospect_id'),
        Index('idx_f500_roi_engagement_type', 'engagement_type'),
        Index('idx_f500_roi_investment_stage', 'investment_stage'),
        Index('idx_f500_roi_tracked_at', 'tracked_at'),
    )

    def __repr__(self):
        return f"<F500ROITracking(prospect_id='{self.prospect_id}', stage='{self.investment_stage}', roi={self.current_roi}%)>"


# ============================================================================
# Account-Based Marketing (ABM) Models
# ============================================================================

class ABMCampaignModel(Base):
    """SQLAlchemy model for ABM campaigns"""
    __tablename__ = "abm_campaigns"

    campaign_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    campaign_name = Column(String(255), nullable=False)
    target_accounts = Column(JSONType, default=list)  # JSON array of prospect IDs
    campaign_type = Column(String(50), nullable=False)  # thought_leadership, executive_briefing, etc.
    personalization_level = Column(String(20), nullable=False, default='standard')  # high, medium, standard
    content_assets = Column(JSONType, default=list)  # JSON array of content asset objects
    distribution_channels = Column(JSONType, default=list)  # JSON array of channel names
    budget_allocated = Column(Integer)
    expected_engagement = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    conversion_target = Column(Integer)
    roi_target = Column(DECIMAL(6, 2))  # ROI percentage
    campaign_status = Column(String(20), nullable=False, default='planning')  # planning, active, completed, paused
    launch_date = Column(TIMESTAMP(timezone=True))
    end_date = Column(TIMESTAMP(timezone=True))
    performance_metrics = Column(JSONType, default=dict)  # JSON object with performance data
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    content_assets_rel = relationship("ABMContentAssetModel", back_populates="campaigns", secondary="abm_campaign_assets")
    touchpoints = relationship("ABMTouchpointModel", back_populates="campaign", cascade="all, delete-orphan")
    performance = relationship("ABMPerformanceModel", back_populates="campaign", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_abm_campaigns_name', 'campaign_name'),
        Index('idx_abm_campaigns_type', 'campaign_type'),
        Index('idx_abm_campaigns_status', 'campaign_status'),
        Index('idx_abm_campaigns_dates', 'launch_date', 'end_date'),
        Index('idx_abm_campaigns_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ABMCampaign(name='{self.campaign_name}', type='{self.campaign_type}', status='{self.campaign_status}')>"


class ABMContentAssetModel(Base):
    """SQLAlchemy model for ABM content assets"""
    __tablename__ = "abm_content_assets"

    asset_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    asset_type = Column(String(50), nullable=False)  # whitepaper, case_study, executive_brief, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text)
    target_persona = Column(String(50), nullable=False)  # ceo, cto, vp_engineering, technical_lead
    industry_focus = Column(String(100))
    personalization_data = Column(JSONType, default=dict)  # JSON object with personalization options
    content_url = Column(String(1000))
    engagement_score = Column(DECIMAL(3, 1), default=Decimal('7.0'))  # 0.0 to 10.0
    conversion_rate = Column(DECIMAL(3, 2), default=Decimal('0.20'))  # 0.00 to 1.00
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships (many-to-many with campaigns)
    campaigns = relationship("ABMCampaignModel", back_populates="content_assets_rel", secondary="abm_campaign_assets")

    # Indexes
    __table_args__ = (
        Index('idx_abm_assets_type', 'asset_type'),
        Index('idx_abm_assets_persona', 'target_persona'),
        Index('idx_abm_assets_industry', 'industry_focus'),
        Index('idx_abm_assets_engagement', 'engagement_score'),
        Index('idx_abm_assets_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ABMContentAsset(title='{self.title}', type='{self.asset_type}', persona='{self.target_persona}')>"


# Association table for many-to-many relationship between campaigns and content assets
from sqlalchemy import Table
abm_campaign_assets = Table(
    'abm_campaign_assets_assoc',
    Base.metadata,
    Column('campaign_id', GUID, ForeignKey('abm_campaigns.campaign_id'), primary_key=True),
    Column('asset_id', GUID, ForeignKey('abm_content_assets.asset_id'), primary_key=True),
    Column('added_at', TIMESTAMP(timezone=True), server_default=func.now())
)


class ABMTouchpointModel(Base):
    """SQLAlchemy model for ABM campaign touchpoints"""
    __tablename__ = "abm_touchpoints"

    touchpoint_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    campaign_id = Column(GUID, ForeignKey('abm_campaigns.campaign_id'), nullable=False)
    prospect_id = Column(GUID)  # References f500_prospects.prospect_id (not enforced FK for flexibility)
    touchpoint_type = Column(String(50), nullable=False)  # email, social, direct_mail, webinar, event
    content_asset_id = Column(GUID, ForeignKey('abm_content_assets.asset_id'))
    scheduled_date = Column(TIMESTAMP(timezone=True))
    executed_date = Column(TIMESTAMP(timezone=True))
    personalization_applied = Column(JSONType, default=dict)  # JSON object with personalization details
    engagement_metrics = Column(JSONType, default=dict)  # JSON object with engagement data
    status = Column(String(20), nullable=False, default='scheduled')  # scheduled, sent, opened, clicked, responded
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("ABMCampaignModel", back_populates="touchpoints")
    content_asset = relationship("ABMContentAssetModel")

    # Indexes
    __table_args__ = (
        Index('idx_abm_touchpoints_campaign_id', 'campaign_id'),
        Index('idx_abm_touchpoints_prospect_id', 'prospect_id'),
        Index('idx_abm_touchpoints_type', 'touchpoint_type'),
        Index('idx_abm_touchpoints_status', 'status'),
        Index('idx_abm_touchpoints_scheduled_date', 'scheduled_date'),
        Index('idx_abm_touchpoints_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<ABMTouchpoint(campaign_id='{self.campaign_id}', type='{self.touchpoint_type}', status='{self.status}')>"


class ABMPerformanceModel(Base):
    """SQLAlchemy model for ABM campaign performance tracking"""
    __tablename__ = "abm_performance"

    performance_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    campaign_id = Column(GUID, ForeignKey('abm_campaigns.campaign_id'), nullable=False)
    measurement_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    accounts_engaged = Column(Integer, default=0)
    total_touchpoints = Column(Integer, default=0)
    engagement_rate = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    response_rate = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    conversion_rate = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    pipeline_generated = Column(Integer)  # Pipeline value in dollars
    roi_achieved = Column(DECIMAL(6, 2))  # ROI percentage
    cost_per_engagement = Column(DECIMAL(10, 2))

    # Relationships
    campaign = relationship("ABMCampaignModel", back_populates="performance")

    # Indexes
    __table_args__ = (
        Index('idx_abm_performance_campaign_id', 'campaign_id'),
        Index('idx_abm_performance_measurement_date', 'measurement_date'),
        Index('idx_abm_performance_roi', 'roi_achieved'),
    )

    def __repr__(self):
        return f"<ABMPerformance(campaign_id='{self.campaign_id}', engagement_rate={self.engagement_rate}, roi={self.roi_achieved}%)>"


# ============================================================================
# Enterprise Onboarding Models
# ============================================================================

class OnboardingClientModel(Base):
    """SQLAlchemy model for enterprise onboarding clients"""
    __tablename__ = "onboarding_clients"

    client_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    contract_value = Column(Integer, nullable=False)
    contract_start_date = Column(TIMESTAMP(timezone=True), nullable=False)
    expected_completion_date = Column(TIMESTAMP(timezone=True))
    actual_completion_date = Column(TIMESTAMP(timezone=True))
    onboarding_status = Column(String(50), nullable=False, default='initiated')  # initiated, in_progress, completed, at_risk
    success_plan_template = Column(String(100))  # References onboarding_success_templates
    primary_contact_name = Column(String(255))
    primary_contact_email = Column(String(255))
    technical_lead_name = Column(String(255))
    executive_sponsor_name = Column(String(255))
    team_size = Column(Integer)
    implementation_complexity = Column(String(20))  # low, medium, high
    custom_requirements = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    milestones = relationship("OnboardingMilestoneModel", back_populates="client", cascade="all, delete-orphan")
    health_metrics = relationship("OnboardingHealthMetricModel", back_populates="client", cascade="all, delete-orphan")
    communications = relationship("OnboardingCommunicationModel", back_populates="client", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_onboarding_clients_company_name', 'company_name'),
        Index('idx_onboarding_clients_status', 'onboarding_status'),
        Index('idx_onboarding_clients_contract_dates', 'contract_start_date', 'expected_completion_date'),
        Index('idx_onboarding_clients_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<OnboardingClient(company_name='{self.company_name}', status='{self.onboarding_status}', value=${self.contract_value})>"


class OnboardingMilestoneModel(Base):
    """SQLAlchemy model for onboarding milestones"""
    __tablename__ = "onboarding_milestones"

    milestone_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    client_id = Column(GUID, ForeignKey('onboarding_clients.client_id'), nullable=False)
    milestone_name = Column(String(255), nullable=False)
    milestone_type = Column(String(50), nullable=False)  # kickoff, discovery, implementation, training, launch
    planned_date = Column(TIMESTAMP(timezone=True))
    actual_date = Column(TIMESTAMP(timezone=True))
    status = Column(String(20), nullable=False, default='pending')  # pending, in_progress, completed, delayed, blocked
    completion_percentage = Column(Integer, default=0)  # 0 to 100
    dependencies = Column(JSONType, default=list)  # JSON array of milestone_ids that must complete first
    deliverables = Column(JSONType, default=list)  # JSON array of deliverable descriptions
    assigned_to = Column(String(255))
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("OnboardingClientModel", back_populates="milestones")

    # Indexes
    __table_args__ = (
        Index('idx_onboarding_milestones_client_id', 'client_id'),
        Index('idx_onboarding_milestones_type', 'milestone_type'),
        Index('idx_onboarding_milestones_status', 'status'),
        Index('idx_onboarding_milestones_planned_date', 'planned_date'),
        Index('idx_onboarding_milestones_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<OnboardingMilestone(name='{self.milestone_name}', type='{self.milestone_type}', status='{self.status}')>"


class OnboardingHealthMetricModel(Base):
    """SQLAlchemy model for onboarding health metrics"""
    __tablename__ = "onboarding_health_metrics"

    metric_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    client_id = Column(GUID, ForeignKey('onboarding_clients.client_id'), nullable=False)
    measurement_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    overall_health_score = Column(DECIMAL(3, 1))  # 0.0 to 10.0
    engagement_score = Column(DECIMAL(3, 1))  # 0.0 to 10.0
    progress_score = Column(DECIMAL(3, 1))  # 0.0 to 10.0
    satisfaction_score = Column(DECIMAL(3, 1))  # 0.0 to 10.0
    risk_level = Column(String(20), nullable=False, default='low')  # low, medium, high, critical
    risk_factors = Column(JSONType, default=list)  # JSON array of risk factor descriptions
    success_indicators = Column(JSONType, default=list)  # JSON array of positive indicators
    recommended_actions = Column(JSONType, default=list)  # JSON array of recommended action items
    stakeholder_sentiment = Column(String(20))  # positive, neutral, negative, unknown
    notes = Column(Text)

    # Relationships
    client = relationship("OnboardingClientModel", back_populates="health_metrics")

    # Indexes
    __table_args__ = (
        Index('idx_onboarding_health_client_id', 'client_id'),
        Index('idx_onboarding_health_overall_score', 'overall_health_score'),
        Index('idx_onboarding_health_risk_level', 'risk_level'),
        Index('idx_onboarding_health_measurement_date', 'measurement_date'),
    )

    def __repr__(self):
        return f"<OnboardingHealthMetric(client_id='{self.client_id}', health={self.overall_health_score}, risk='{self.risk_level}')>"


class OnboardingSuccessTemplateModel(Base):
    """SQLAlchemy model for onboarding success plan templates"""
    __tablename__ = "onboarding_success_templates"

    template_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    template_name = Column(String(255), nullable=False, unique=True)
    template_type = Column(String(50), nullable=False)  # standard, accelerated, enterprise_scale
    target_duration_days = Column(Integer, nullable=False)
    target_complexity = Column(String(20), nullable=False)  # low, medium, high
    milestone_templates = Column(JSONType, nullable=False, default=list)  # JSON array of milestone definitions
    success_criteria = Column(JSONType, default=list)  # JSON array of success criteria
    risk_mitigation_strategies = Column(JSONType, default=list)  # JSON array of risk mitigation approaches
    resource_requirements = Column(JSONType, default=dict)  # JSON object with resource needs
    description = Column(Text)
    is_active = Column(String(10), default='true')  # Using string for SQLite compatibility
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_onboarding_templates_name', 'template_name'),
        Index('idx_onboarding_templates_type', 'template_type'),
        Index('idx_onboarding_templates_complexity', 'target_complexity'),
        Index('idx_onboarding_templates_active', 'is_active'),
    )

    def __repr__(self):
        return f"<OnboardingSuccessTemplate(name='{self.template_name}', type='{self.template_type}', duration={self.target_duration_days}d)>"


class OnboardingCommunicationModel(Base):
    """SQLAlchemy model for onboarding communication log"""
    __tablename__ = "onboarding_communications"

    communication_id = Column(GUID, primary_key=True, default=uuid.uuid4)
    client_id = Column(GUID, ForeignKey('onboarding_clients.client_id'), nullable=False)
    communication_type = Column(String(50), nullable=False)  # email, call, meeting, slack, status_update
    communication_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    subject = Column(String(500))
    summary = Column(Text)
    participants = Column(JSONType, default=list)  # JSON array of participant names
    action_items = Column(JSONType, default=list)  # JSON array of action items
    sentiment = Column(String(20))  # positive, neutral, negative, escalation
    follow_up_required = Column(String(10), default='false')  # Using string for SQLite compatibility
    follow_up_date = Column(TIMESTAMP(timezone=True))
    attachments = Column(JSONType, default=list)  # JSON array of attachment metadata
    created_by = Column(String(255))

    # Relationships
    client = relationship("OnboardingClientModel", back_populates="communications")

    # Indexes
    __table_args__ = (
        Index('idx_onboarding_comms_client_id', 'client_id'),
        Index('idx_onboarding_comms_type', 'communication_type'),
        Index('idx_onboarding_comms_date', 'communication_date'),
        Index('idx_onboarding_comms_sentiment', 'sentiment'),
        Index('idx_onboarding_comms_follow_up', 'follow_up_required', 'follow_up_date'),
    )

    def __repr__(self):
        return f"<OnboardingCommunication(client_id='{self.client_id}', type='{self.communication_type}', date='{self.communication_date}')>"


# Export all models
__all__ = [
    'GUID',
    'JSONType',
    'Fortune500ProspectModel',
    'F500LeadScoringModel',
    'F500BusinessCaseModel',
    'F500SalesSequenceModel',
    'F500ROITrackingModel',
    'ABMCampaignModel',
    'ABMContentAssetModel',
    'ABMTouchpointModel',
    'ABMPerformanceModel',
    'OnboardingClientModel',
    'OnboardingMilestoneModel',
    'OnboardingHealthMetricModel',
    'OnboardingSuccessTemplateModel',
    'OnboardingCommunicationModel',
]
