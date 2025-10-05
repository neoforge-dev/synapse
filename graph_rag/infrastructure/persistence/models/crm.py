"""
SQLAlchemy models for CRM entities in the consolidated PostgreSQL database.
These models provide the database schema and ORM mappings.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from sqlalchemy import Column, String, Integer, DECIMAL, TIMESTAMP, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from graph_rag.infrastructure.persistence.models.base import Base


class ContactModel(Base):
    """SQLAlchemy model for contacts table"""
    __tablename__ = "crm_contacts"

    contact_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    company = Column(String(255))
    title = Column(String(255))
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50))
    linkedin_profile = Column(String(500))
    lead_score = Column(Integer, nullable=False, default=0)
    estimated_value = Column(DECIMAL(12, 2), nullable=False, default=Decimal('0.00'))
    priority_tier = Column(String(20), nullable=False, default='bronze')
    qualification_status = Column(String(20), nullable=False, default='prospect')
    next_action = Column(Text)
    next_action_date = Column(TIMESTAMP(timezone=True))
    notes = Column(Text, default='')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    pipeline_entries = relationship("SalesPipelineModel", back_populates="contact", cascade="all, delete-orphan")
    qualifications = relationship("LeadQualificationModel", back_populates="contact", cascade="all, delete-orphan")
    proposals = relationship("ProposalModel", back_populates="contact", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_contacts_email', 'email'),
        Index('idx_contacts_lead_score', 'lead_score'),
        Index('idx_contacts_priority_tier', 'priority_tier'),
        Index('idx_contacts_qualification_status', 'qualification_status'),
        Index('idx_contacts_created_at', 'created_at'),
    )


class SalesPipelineModel(Base):
    """SQLAlchemy model for sales pipeline table"""
    __tablename__ = "sales_pipeline"

    pipeline_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contact_id = Column(UUID(as_uuid=True), ForeignKey('crm_contacts.contact_id'), nullable=False)
    stage = Column(String(20), nullable=False)
    probability = Column(DECIMAL(3, 2), nullable=False)  # 0.00 to 1.00
    expected_close_date = Column(TIMESTAMP(timezone=True))
    deal_value = Column(DECIMAL(12, 2), nullable=False, default=Decimal('0.00'))
    notes = Column(Text, default='')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    contact = relationship("ContactModel", back_populates="pipeline_entries")

    # Indexes
    __table_args__ = (
        Index('idx_pipeline_contact_id', 'contact_id'),
        Index('idx_pipeline_stage', 'stage'),
        Index('idx_pipeline_expected_close', 'expected_close_date'),
        Index('idx_pipeline_created_at', 'created_at'),
    )


class LeadQualificationModel(Base):
    """SQLAlchemy model for lead qualification history"""
    __tablename__ = "lead_qualifications"

    qualification_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contact_id = Column(UUID(as_uuid=True), ForeignKey('crm_contacts.contact_id'), nullable=False)
    qualification_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    qualification_criteria = Column(JSONB, default=dict)
    calculated_score = Column(Integer, nullable=False)
    qualification_notes = Column(Text, default='')
    qualified_by = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    contact = relationship("ContactModel", back_populates="qualifications")

    # Indexes
    __table_args__ = (
        Index('idx_qualifications_contact_id', 'contact_id'),
        Index('idx_qualifications_date', 'qualification_date'),
        Index('idx_qualifications_score', 'calculated_score'),
    )


class ProposalModel(Base):
    """SQLAlchemy model for sales proposals"""
    __tablename__ = "proposals"

    proposal_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contact_id = Column(UUID(as_uuid=True), ForeignKey('crm_contacts.contact_id'), nullable=False)
    template_used = Column(String(255), nullable=False)
    proposal_value = Column(DECIMAL(12, 2), nullable=False)
    estimated_close_probability = Column(DECIMAL(3, 2), nullable=False)
    roi_analysis = Column(JSONB, default=dict)
    custom_requirements = Column(Text, default='')
    status = Column(String(20), nullable=False, default='draft')
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    sent_at = Column(TIMESTAMP(timezone=True))
    responded_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    contact = relationship("ProposalModel", back_populates="proposals")

    # Indexes
    __table_args__ = (
        Index('idx_proposals_contact_id', 'contact_id'),
        Index('idx_proposals_status', 'status'),
        Index('idx_proposals_generated_at', 'generated_at'),
        Index('idx_proposals_value', 'proposal_value'),
    )


class ABTestCampaignModel(Base):
    """SQLAlchemy model for A/B testing campaigns"""
    __tablename__ = "ab_test_campaigns"

    campaign_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    description = Column(Text)
    test_type = Column(String(50), nullable=False)  # linkedin_post, email_subject, etc.
    status = Column(String(20), nullable=False, default='draft')
    start_date = Column(TIMESTAMP(timezone=True))
    end_date = Column(TIMESTAMP(timezone=True))
    target_metric = Column(String(100), nullable=False)
    variants = Column(JSONB, nullable=False)  # Array of variant definitions
    results = Column(JSONB, default=dict)
    winner_variant = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_ab_campaigns_status', 'status'),
        Index('idx_ab_campaigns_type', 'test_type'),
        Index('idx_ab_campaigns_dates', 'start_date', 'end_date'),
    )


class RevenueForecastModel(Base):
    """SQLAlchemy model for revenue forecasting"""
    __tablename__ = "revenue_forecasts"

    forecast_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    contact_id = Column(UUID(as_uuid=True), ForeignKey('crm_contacts.contact_id'))
    forecast_period = Column(String(20), nullable=False)  # monthly, quarterly, annual
    forecast_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    predicted_revenue = Column(DECIMAL(12, 2), nullable=False)
    confidence_level = Column(DECIMAL(3, 2), nullable=False)  # 0.00 to 1.00
    forecast_model = Column(String(100), nullable=False)
    input_parameters = Column(JSONB, default=dict)
    actual_revenue = Column(DECIMAL(12, 2))
    accuracy_score = Column(DECIMAL(5, 4))  # Prediction accuracy
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    contact = relationship("ContactModel")

    # Indexes
    __table_args__ = (
        Index('idx_forecasts_contact_id', 'contact_id'),
        Index('idx_forecasts_period', 'forecast_period'),
        Index('idx_forecasts_date', 'forecast_date'),
    )