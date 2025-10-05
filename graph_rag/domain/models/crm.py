"""
Domain models for CRM entities in the consolidated architecture.
These models represent the business domain with proper validation and business rules.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class Contact(BaseModel):
    """Domain model for business contacts"""
    contact_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    linkedin_profile: Optional[str] = Field(None, max_length=500)
    lead_score: int = Field(default=0, ge=0, le=100)
    estimated_value: Decimal = Field(default=Decimal('0.00'), ge=0)
    priority_tier: str = Field(default="bronze", pattern="^(bronze|silver|gold|platinum)$")
    qualification_status: str = Field(
        default="prospect",
        pattern="^(prospect|qualified|disqualified|customer)$"
    )
    next_action: Optional[str] = Field(None, max_length=1000)
    next_action_date: Optional[datetime] = None
    notes: str = Field(default="", max_length=5000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()

    @validator('lead_score')
    def validate_lead_score(cls, v):
        if not (0 <= v <= 100):
            raise ValueError('Lead score must be between 0 and 100')
        return v

    def is_high_value(self) -> bool:
        """Business rule: Determine if contact is high-value"""
        return (
            self.lead_score >= 80 or
            self.estimated_value >= Decimal('50000') or
            self.priority_tier in ['gold', 'platinum']
        )

    def requires_followup(self) -> bool:
        """Business rule: Determine if contact needs immediate follow-up"""
        if not self.next_action_date:
            return False
        return self.next_action_date <= datetime.utcnow()


class SalesPipeline(BaseModel):
    """Domain model for sales pipeline entries"""
    pipeline_id: UUID = Field(default_factory=uuid4)
    contact_id: UUID
    stage: str = Field(
        ...,
        pattern="^(prospect|qualified|proposal|negotiation|closed_won|closed_lost)$"
    )
    probability: float = Field(..., ge=0.0, le=1.0)
    expected_close_date: Optional[datetime] = None
    deal_value: Decimal = Field(default=Decimal('0.00'), ge=0)
    notes: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('probability')
    def validate_probability(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError('Probability must be between 0.0 and 1.0')
        return v

    def get_weighted_value(self) -> Decimal:
        """Calculate weighted pipeline value"""
        return self.deal_value * Decimal(str(self.probability))

    def is_closed(self) -> bool:
        """Check if pipeline entry is in a closed state"""
        return self.stage in ['closed_won', 'closed_lost']


class LeadQualification(BaseModel):
    """Domain model for lead qualification data"""
    qualification_id: UUID = Field(default_factory=uuid4)
    contact_id: UUID
    qualification_date: datetime = Field(default_factory=datetime.utcnow)
    qualification_criteria: dict = Field(default_factory=dict)
    calculated_score: int = Field(..., ge=0, le=100)
    qualification_notes: str = Field(default="", max_length=2000)
    qualified_by: str = Field(..., max_length=255)  # User/system identifier

    def meets_qualification_threshold(self, threshold: int = 70) -> bool:
        """Check if lead meets qualification threshold"""
        return self.calculated_score >= threshold


class Proposal(BaseModel):
    """Domain model for sales proposals"""
    proposal_id: UUID = Field(default_factory=uuid4)
    contact_id: UUID
    template_used: str = Field(..., max_length=255)
    proposal_value: Decimal = Field(..., ge=0)
    estimated_close_probability: float = Field(..., ge=0.0, le=1.0)
    roi_analysis: dict = Field(default_factory=dict)
    custom_requirements: str = Field(default="", max_length=5000)
    status: str = Field(
        default="draft",
        pattern="^(draft|sent|accepted|rejected|expired)$"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if proposal has expired (30 days old)"""
        expiry_date = self.generated_at.replace(day=self.generated_at.day + 30)
        return datetime.utcnow() > expiry_date

    def get_expected_value(self) -> Decimal:
        """Calculate expected value based on probability"""
        return self.proposal_value * Decimal(str(self.estimated_close_probability))