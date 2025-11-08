"""
SQLAlchemy ORM models for PostgreSQL CRM database.

Database Organization:
- Business CRM (synapse_business_crm): Epic 7 CRM, sales pipeline, proposals
"""

from graph_rag.infrastructure.persistence.models.base import Base
from graph_rag.infrastructure.persistence.models.crm import (
    ABTestCampaignModel,
    ContactModel,
    LeadQualificationModel,
    ProposalModel,
    RevenueForecastModel,
    SalesPipelineModel,
)

__all__ = [
    "Base",
    # CRM Models
    "ContactModel",
    "LeadQualificationModel",
    "ProposalModel",
    "SalesPipelineModel",
    "ABTestCampaignModel",
    "RevenueForecastModel",
]
