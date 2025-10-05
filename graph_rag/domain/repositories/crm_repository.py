"""
Repository interfaces for CRM domain operations.
These define the contracts for data access in the domain layer.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from graph_rag.domain.models.crm import Contact, SalesPipeline, LeadQualification, Proposal


class ICRMRepository(ABC):
    """Interface for CRM contact operations"""

    @abstractmethod
    async def get_contact_by_id(self, contact_id: UUID) -> Optional[Contact]:
        """Retrieve a contact by ID"""
        pass

    @abstractmethod
    async def get_contacts_by_email(self, email: str) -> List[Contact]:
        """Retrieve contacts by email address"""
        pass

    @abstractmethod
    async def get_contacts_by_lead_score(self, min_score: int) -> List[Contact]:
        """Retrieve contacts with lead score above threshold"""
        pass

    @abstractmethod
    async def get_high_value_contacts(self) -> List[Contact]:
        """Retrieve high-value contacts (business rule)"""
        pass

    @abstractmethod
    async def create_contact(self, contact: Contact) -> Contact:
        """Create a new contact"""
        pass

    @abstractmethod
    async def update_contact(self, contact: Contact) -> Contact:
        """Update an existing contact"""
        pass

    @abstractmethod
    async def delete_contact(self, contact_id: UUID) -> bool:
        """Delete a contact"""
        pass


class ISalesPipelineRepository(ABC):
    """Interface for sales pipeline operations"""

    @abstractmethod
    async def get_pipeline_by_contact(self, contact_id: UUID) -> List[SalesPipeline]:
        """Get all pipeline entries for a contact"""
        pass

    @abstractmethod
    async def get_pipeline_by_stage(self, stage: str) -> List[SalesPipeline]:
        """Get pipeline entries by stage"""
        pass

    @abstractmethod
    async def create_pipeline_entry(self, pipeline: SalesPipeline) -> SalesPipeline:
        """Create a new pipeline entry"""
        pass

    @abstractmethod
    async def update_pipeline_entry(self, pipeline: SalesPipeline) -> SalesPipeline:
        """Update a pipeline entry"""
        pass

    @abstractmethod
    async def get_total_pipeline_value(self) -> float:
        """Calculate total weighted pipeline value"""
        pass


class ILeadQualificationRepository(ABC):
    """Interface for lead qualification operations"""

    @abstractmethod
    async def get_qualifications_by_contact(self, contact_id: UUID) -> List[LeadQualification]:
        """Get qualification history for a contact"""
        pass

    @abstractmethod
    async def create_qualification(self, qualification: LeadQualification) -> LeadQualification:
        """Create a new qualification record"""
        pass

    @abstractmethod
    async def get_recent_qualifications(self, days: int = 30) -> List[LeadQualification]:
        """Get qualifications from the last N days"""
        pass


class IProposalRepository(ABC):
    """Interface for proposal operations"""

    @abstractmethod
    async def get_proposals_by_contact(self, contact_id: UUID) -> List[Proposal]:
        """Get all proposals for a contact"""
        pass

    @abstractmethod
    async def get_proposals_by_status(self, status: str) -> List[Proposal]:
        """Get proposals by status"""
        pass

    @abstractmethod
    async def create_proposal(self, proposal: Proposal) -> Proposal:
        """Create a new proposal"""
        pass

    @abstractmethod
    async def update_proposal(self, proposal: Proposal) -> Proposal:
        """Update a proposal"""
        pass

    @abstractmethod
    async def get_proposal_value_by_status(self) -> dict:
        """Get total proposal values grouped by status"""
        pass