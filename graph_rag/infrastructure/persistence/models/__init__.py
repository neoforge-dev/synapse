"""
SQLAlchemy ORM models for 3 PostgreSQL databases.

Database Organization:
1. Core Platform (synapse_core): Document management, graph metadata
2. Business Operations (synapse_business): Epic 7 CRM, LinkedIn automation
3. Analytics Intelligence (synapse_analytics): Performance metrics, A/B testing
"""

from graph_rag.infrastructure.persistence.models.base import Base
from graph_rag.infrastructure.persistence.models.consultation import (
    ABTestCampaign,
    ABTestResult,
    CRMContact,
    GeneratedProposal,
    LeadScoringHistory,
    LinkedInAutomationTracking,
    ROITemplate,
    SalesPipeline,
)
from graph_rag.infrastructure.persistence.models.linkedin import (
    BusinessPipeline,
    ConsultationInquiry,
    LinkedInPost,
)

__all__ = [
    "Base",
    # Epic 7 Models
    "CRMContact",
    "LeadScoringHistory",
    "GeneratedProposal",
    "SalesPipeline",
    "ROITemplate",
    "LinkedInAutomationTracking",
    "ABTestCampaign",
    "ABTestResult",
    # LinkedIn Business Development Models
    "LinkedInPost",
    "ConsultationInquiry",
    "BusinessPipeline",
]
