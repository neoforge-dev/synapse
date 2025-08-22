"""
Database models for TechLead AutoPilot multi-tenant SaaS platform.

Designed for horizontal scaling with proper tenant isolation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Organization(Base):
    """
    Organization/tenant table for multi-tenant architecture.
    
    Each organization represents a customer account with subscription.
    """
    __tablename__ = "organizations"
    
    # Primary key
    id = Column(PostgreSQL_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Basic info
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)  # For domain-based tenant identification
    
    # Subscription info
    subscription_tier = Column(String(50), nullable=False, default="pro")  # pro, agency, enterprise
    subscription_status = Column(String(50), nullable=False, default="active")  # active, canceled, suspended
    subscription_started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    subscription_ends_at = Column(DateTime)
    
    # Billing
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255))
    monthly_price_cents = Column(Integer, default=29700)  # €297 in cents
    
    # Usage tracking
    monthly_content_generated = Column(Integer, default=0)
    monthly_leads_detected = Column(Integer, default=0)
    content_generation_limit = Column(Integer, default=100)  # Per month
    
    # Settings
    settings = Column(JSON, default=dict)  # Organization-specific settings
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)  # Soft delete
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    content_generated = relationship("ContentGenerated", back_populates="organization")
    leads_detected = relationship("LeadDetected", back_populates="organization")
    
    # Indexes
    __table_args__ = (
        Index('idx_organizations_domain', 'domain'),
        Index('idx_organizations_subscription_status', 'subscription_status'),
        Index('idx_organizations_deleted_at', 'deleted_at'),
    )


class User(Base):
    """
    User table with organization-based multi-tenancy.
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(PostgreSQL_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Authentication
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255))  # Nullable for OAuth-only users
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Profile
    first_name = Column(String(255))
    last_name = Column(String(255))
    job_title = Column(String(255))
    company_name = Column(String(255))
    
    # Role within organization
    role = Column(String(50), default="member")  # owner, admin, member
    
    # LinkedIn integration
    linkedin_user_id = Column(String(255))
    linkedin_access_token = Column(Text)  # Encrypted
    linkedin_token_expires_at = Column(DateTime)
    linkedin_connected = Column(Boolean, default=False)
    
    # API access
    api_key = Column(String(255), unique=True)
    api_key_created_at = Column(DateTime)
    
    # Preferences
    content_preferences = Column(JSON, default=dict)
    notification_preferences = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    deleted_at = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('organization_id', 'email', name='uq_org_email'),
        Index('idx_users_email', 'email'),
        Index('idx_users_organization_id', 'organization_id'),
        Index('idx_users_api_key', 'api_key'),
        Index('idx_users_linkedin_user_id', 'linkedin_user_id'),
        Index('idx_users_deleted_at', 'deleted_at'),
    )


class ContentGenerated(Base):
    """
    Table tracking all generated content for analytics and optimization.
    """
    __tablename__ = "content_generated"
    
    # Primary key
    id = Column(PostgreSQL_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Content details
    content_type = Column(String(50), nullable=False)  # technical_insight, leadership_story, etc.
    topic = Column(String(255), nullable=False)
    target_audience = Column(String(100), default="technical_leaders")
    
    # Generated content
    hook = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    call_to_action = Column(Text, nullable=False)
    hashtags = Column(String(500))
    full_post = Column(Text, nullable=False)
    
    # Metadata
    character_count = Column(Integer)
    estimated_read_time_seconds = Column(Integer)
    engagement_prediction = Column(Float)
    consultation_focused = Column(Boolean, default=True)
    generation_metadata = Column(JSON, default=dict)
    
    # Performance tracking
    posted_to_linkedin = Column(Boolean, default=False)
    linkedin_post_id = Column(String(255))
    linkedin_posted_at = Column(DateTime)
    
    # Engagement metrics (updated from LinkedIn API)
    linkedin_likes = Column(Integer, default=0)
    linkedin_comments = Column(Integer, default=0)
    linkedin_shares = Column(Integer, default=0)
    linkedin_impressions = Column(Integer, default=0)
    engagement_rate = Column(Float)  # Calculated engagement rate
    
    # Lead generation tracking
    consultation_inquiries_generated = Column(Integer, default=0)
    estimated_pipeline_value_cents = Column(Integer, default=0)
    
    # Status
    status = Column(String(50), default="draft")  # draft, approved, posted, archived
    approved_by_user_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="content_generated")
    user = relationship("User", foreign_keys=[user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_content_organization_id', 'organization_id'),
        Index('idx_content_user_id', 'user_id'),
        Index('idx_content_created_at', 'created_at'),
        Index('idx_content_status', 'status'),
        Index('idx_content_content_type', 'content_type'),
        Index('idx_content_linkedin_post_id', 'linkedin_post_id'),
    )


class LeadDetected(Base):
    """
    Table tracking all detected consultation opportunities.
    """
    __tablename__ = "leads_detected"
    
    # Primary key
    id = Column(PostgreSQL_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Lead source
    source_platform = Column(String(50), default="linkedin")
    source_post_id = Column(String(255))  # LinkedIn post ID or other source identifier
    source_content_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("content_generated.id"))
    
    # Lead details
    inquiry_type = Column(String(50), nullable=False)  # fractional_cto, technical_architecture, etc.
    content_text = Column(Text, nullable=False)  # The comment/message that triggered detection
    
    # Author information
    author_name = Column(String(255))
    author_title = Column(String(255))
    author_company = Column(String(255))
    author_linkedin_url = Column(String(500))
    author_profile_info = Column(JSON, default=dict)
    
    # Scoring
    lead_score = Column(Integer, nullable=False)  # 1-10 scale
    confidence = Column(Float, nullable=False)  # 0.0-1.0
    estimated_value_cents = Column(Integer, default=0)  # Estimated consultation value in cents
    priority = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Context
    company_size = Column(String(100))
    technical_complexity = Column(String(20))  # Low, Medium, High
    urgency_indicators = Column(JSON, default=list)  # List of urgency signals detected
    
    # Follow-up
    follow_up_suggested = Column(Text)
    follow_up_status = Column(String(50), default="pending")  # pending, contacted, qualified, converted, lost
    follow_up_notes = Column(Text)
    contacted_at = Column(DateTime)
    
    # Conversion tracking
    converted_to_consultation = Column(Boolean, default=False)
    consultation_value_cents = Column(Integer, default=0)  # Actual consultation value if converted
    conversion_date = Column(DateTime)
    
    # Timestamps
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="leads_detected")
    source_content = relationship("ContentGenerated")
    
    # Indexes
    __table_args__ = (
        Index('idx_leads_organization_id', 'organization_id'),
        Index('idx_leads_detected_at', 'detected_at'),
        Index('idx_leads_priority', 'priority'),
        Index('idx_leads_inquiry_type', 'inquiry_type'),
        Index('idx_leads_lead_score', 'lead_score'),
        Index('idx_leads_follow_up_status', 'follow_up_status'),
        Index('idx_leads_source_platform', 'source_platform'),
    )


class LinkedInIntegration(Base):
    """
    LinkedIn integration status and analytics per organization.
    """
    __tablename__ = "linkedin_integrations"
    
    # Primary key
    id = Column(PostgreSQL_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(PostgreSQL_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # OAuth credentials (encrypted)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    
    # LinkedIn profile info
    linkedin_user_id = Column(String(255), unique=True)
    profile_data = Column(JSON, default=dict)
    
    # Integration status
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    sync_status = Column(String(50), default="active")  # active, error, paused
    sync_error_message = Column(Text)
    
    # Analytics
    total_posts = Column(Integer, default=0)
    total_impressions = Column(Integer, default=0)
    total_engagements = Column(Integer, default=0)
    total_leads_generated = Column(Integer, default=0)
    
    # Timestamps
    connected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_linkedin_organization_id', 'organization_id'),
        Index('idx_linkedin_user_id_platform', 'linkedin_user_id'),
        Index('idx_linkedin_is_active', 'is_active'),
    )