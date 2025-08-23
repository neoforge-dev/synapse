"""Lead detection API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from ...core.lead_detection import InquiryType
from ...services.lead_service import LeadService
from ...infrastructure.database.session import get_db_session
from ..auth.dependencies import get_current_user, get_current_organization
from ...infrastructure.database.models import User, Organization

logger = logging.getLogger(__name__)
router = APIRouter()


class LeadDetectionRequest(BaseModel):
    """Request model for lead detection."""
    content: str = Field(..., description="Content to analyze for consultation opportunities")
    source_platform: str = Field(default="linkedin", description="Source platform")
    source_post_id: str = Field(default="", description="Source post ID")
    source_content_id: Optional[str] = Field(None, description="Related content ID")
    author_info: dict = Field(default_factory=dict, description="Author information")


class LeadResponse(BaseModel):
    """Response model for detected leads."""
    id: str
    inquiry_type: str
    content_text: str
    source_platform: str
    source_post_id: str
    author_name: str
    author_title: str
    author_company: str
    lead_score: int
    confidence: float
    estimated_value_euros: int
    priority: str
    company_size: str
    technical_complexity: str
    urgency_indicators: List[str]
    follow_up_suggested: str
    follow_up_status: str
    follow_up_notes: Optional[str]
    detected_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    """Response model for lead list."""
    leads: List[LeadResponse]
    total: int
    page: int
    page_size: int


class LeadAnalyticsResponse(BaseModel):
    """Response model for lead analytics."""
    period_days: int
    total_leads: int
    leads_by_priority: dict
    conversion_metrics: dict
    top_inquiry_types: List[dict]
    follow_up_status: dict
    lead_quality_metrics: dict


class LeadUpdateRequest(BaseModel):
    """Request model for lead follow-up updates."""
    status: str = Field(..., description="New follow-up status")
    notes: Optional[str] = Field(None, description="Follow-up notes")


class LeadConversionRequest(BaseModel):
    """Request model for lead conversion."""
    consultation_value_euros: int = Field(..., description="Consultation value in euros")
    notes: Optional[str] = Field(None, description="Conversion notes")


# Dependency to get lead service
async def get_lead_service(db=Depends(get_db_session)) -> LeadService:
    """Get lead service with database session."""
    return LeadService(db_session=db)


@router.post("/detect", response_model=Optional[LeadResponse])
async def detect_lead(
    request: LeadDetectionRequest,
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """
    Detect consultation opportunities in content using 85%+ accuracy AI algorithms.
    
    Analyzes content for consultation inquiries and saves detected leads
    to database with proper multi-tenant isolation.
    """
    try:
        # Convert source_content_id if provided
        source_content_id = None
        if request.source_content_id:
            try:
                source_content_id = UUID(request.source_content_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid source_content_id format"
                )
        
        # Detect and save consultation opportunity
        detected_lead = await lead_service.detect_and_save_lead(
            organization_id=current_organization.id,
            content=request.content,
            source_platform=request.source_platform,
            source_post_id=request.source_post_id,
            source_content_id=source_content_id,
            author_info=request.author_info
        )
        
        if not detected_lead:
            return None
        
        # Return detected lead
        return LeadResponse(
            id=str(detected_lead.id),
            inquiry_type=detected_lead.inquiry_type,
            content_text=detected_lead.content_text,
            source_platform=detected_lead.source_platform,
            source_post_id=detected_lead.source_post_id or "",
            author_name=detected_lead.author_name or "",
            author_title=detected_lead.author_title or "",
            author_company=detected_lead.author_company or "",
            lead_score=detected_lead.lead_score,
            confidence=detected_lead.confidence,
            estimated_value_euros=detected_lead.estimated_value_cents // 100,
            priority=detected_lead.priority,
            company_size=detected_lead.company_size or "",
            technical_complexity=detected_lead.technical_complexity or "",
            urgency_indicators=detected_lead.urgency_indicators or [],
            follow_up_suggested=detected_lead.follow_up_suggested or "",
            follow_up_status=detected_lead.follow_up_status,
            follow_up_notes=detected_lead.follow_up_notes,
            detected_at=detected_lead.detected_at,
            updated_at=detected_lead.updated_at
        )
        
    except Exception as e:
        logger.error(f"Lead detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lead detection failed: {str(e)}"
        )


@router.get("/", response_model=LeadListResponse)
async def get_leads(
    priority: Optional[str] = Query(None, description="Filter by priority"),
    inquiry_type: Optional[str] = Query(None, description="Filter by inquiry type"),
    follow_up_status: Optional[str] = Query(None, description="Filter by follow-up status"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Days to look back"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get organization's detected leads with filtering and pagination."""
    leads_list = await lead_service.get_organization_leads(
        organization_id=current_organization.id,
        priority=priority,
        inquiry_type=inquiry_type,
        follow_up_status=follow_up_status,
        days=days,
        limit=limit,
        offset=offset
    )
    
    # Convert to response format
    lead_responses = [
        LeadResponse(
            id=str(lead.id),
            inquiry_type=lead.inquiry_type,
            content_text=lead.content_text,
            source_platform=lead.source_platform,
            source_post_id=lead.source_post_id or "",
            author_name=lead.author_name or "",
            author_title=lead.author_title or "",
            author_company=lead.author_company or "",
            lead_score=lead.lead_score,
            confidence=lead.confidence,
            estimated_value_euros=lead.estimated_value_cents // 100,
            priority=lead.priority,
            company_size=lead.company_size or "",
            technical_complexity=lead.technical_complexity or "",
            urgency_indicators=lead.urgency_indicators or [],
            follow_up_suggested=lead.follow_up_suggested or "",
            follow_up_status=lead.follow_up_status,
            follow_up_notes=lead.follow_up_notes,
            detected_at=lead.detected_at,
            updated_at=lead.updated_at
        )
        for lead in leads_list
    ]
    
    return LeadListResponse(
        leads=lead_responses,
        total=len(lead_responses),
        page=offset // limit + 1,
        page_size=limit
    )


@router.get("/high-priority")
async def get_high_priority_leads(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get high priority leads that need immediate attention."""
    leads = await lead_service.get_high_priority_leads(
        organization_id=current_organization.id,
        hours=hours
    )
    
    return {
        "leads": [
            {
                "id": str(lead.id),
                "inquiry_type": lead.inquiry_type,
                "priority": lead.priority,
                "lead_score": lead.lead_score,
                "author_name": lead.author_name,
                "company_size": lead.company_size,
                "estimated_value_euros": lead.estimated_value_cents // 100,
                "follow_up_suggested": lead.follow_up_suggested,
                "detected_at": lead.detected_at
            }
            for lead in leads
        ],
        "count": len(leads),
        "hours_back": hours
    }


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead_by_id(
    lead_id: UUID,
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get specific lead by ID."""
    lead = await lead_service.get_lead_by_id(
        lead_id=lead_id,
        organization_id=current_organization.id
    )
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )
    
    return LeadResponse(
        id=str(lead.id),
        inquiry_type=lead.inquiry_type,
        content_text=lead.content_text,
        source_platform=lead.source_platform,
        source_post_id=lead.source_post_id or "",
        author_name=lead.author_name or "",
        author_title=lead.author_title or "",
        author_company=lead.author_company or "",
        lead_score=lead.lead_score,
        confidence=lead.confidence,
        estimated_value_euros=lead.estimated_value_cents // 100,
        priority=lead.priority,
        company_size=lead.company_size or "",
        technical_complexity=lead.technical_complexity or "",
        urgency_indicators=lead.urgency_indicators or [],
        follow_up_suggested=lead.follow_up_suggested or "",
        follow_up_status=lead.follow_up_status,
        follow_up_notes=lead.follow_up_notes,
        detected_at=lead.detected_at,
        updated_at=lead.updated_at
    )


@router.put("/{lead_id}/follow-up", response_model=LeadResponse)
async def update_lead_follow_up(
    lead_id: UUID,
    request: LeadUpdateRequest,
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Update lead follow-up status and notes."""
    # Validate status
    valid_statuses = ["pending", "contacted", "qualified", "converted", "lost"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    lead = await lead_service.update_lead_follow_up(
        lead_id=lead_id,
        organization_id=current_organization.id,
        status=request.status,
        notes=request.notes
    )
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )
    
    return LeadResponse(
        id=str(lead.id),
        inquiry_type=lead.inquiry_type,
        content_text=lead.content_text,
        source_platform=lead.source_platform,
        source_post_id=lead.source_post_id or "",
        author_name=lead.author_name or "",
        author_title=lead.author_title or "",
        author_company=lead.author_company or "",
        lead_score=lead.lead_score,
        confidence=lead.confidence,
        estimated_value_euros=lead.estimated_value_cents // 100,
        priority=lead.priority,
        company_size=lead.company_size or "",
        technical_complexity=lead.technical_complexity or "",
        urgency_indicators=lead.urgency_indicators or [],
        follow_up_suggested=lead.follow_up_suggested or "",
        follow_up_status=lead.follow_up_status,
        follow_up_notes=lead.follow_up_notes,
        detected_at=lead.detected_at,
        updated_at=lead.updated_at
    )


@router.post("/{lead_id}/convert", response_model=LeadResponse)
async def convert_lead(
    lead_id: UUID,
    request: LeadConversionRequest,
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Mark lead as converted to consultation."""
    if request.consultation_value_euros <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consultation value must be positive"
        )
    
    lead = await lead_service.mark_lead_converted(
        lead_id=lead_id,
        organization_id=current_organization.id,
        consultation_value_euros=request.consultation_value_euros,
        notes=request.notes
    )
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found"
        )
    
    return LeadResponse(
        id=str(lead.id),
        inquiry_type=lead.inquiry_type,
        content_text=lead.content_text,
        source_platform=lead.source_platform,
        source_post_id=lead.source_post_id or "",
        author_name=lead.author_name or "",
        author_title=lead.author_title or "",
        author_company=lead.author_company or "",
        lead_score=lead.lead_score,
        confidence=lead.confidence,
        estimated_value_euros=lead.estimated_value_cents // 100,
        priority=lead.priority,
        company_size=lead.company_size or "",
        technical_complexity=lead.technical_complexity or "",
        urgency_indicators=lead.urgency_indicators or [],
        follow_up_suggested=lead.follow_up_suggested or "",
        follow_up_status=lead.follow_up_status,
        follow_up_notes=lead.follow_up_notes,
        detected_at=lead.detected_at,
        updated_at=lead.updated_at
    )


@router.get("/analytics/overview", response_model=LeadAnalyticsResponse)
async def get_lead_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get lead analytics overview."""
    analytics = await lead_service.get_lead_analytics(
        organization_id=current_organization.id,
        days=days
    )
    
    return LeadAnalyticsResponse(**analytics)


@router.get("/analytics/attribution")
async def get_content_lead_attribution(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    lead_service: LeadService = Depends(get_lead_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get attribution data showing which content generates the most leads."""
    attribution_data = await lead_service.get_content_lead_attribution(
        organization_id=current_organization.id,
        days=days
    )
    
    return {
        "period_days": days,
        "content_performance": attribution_data
    }


@router.get("/inquiry-types")
async def get_inquiry_types():
    """Get available inquiry types with descriptions."""
    return {
        "inquiry_types": [
            {
                "value": inquiry_type.value,
                "name": inquiry_type.value.replace("_", " ").title(),
                "description": f"Consultation opportunities related to {inquiry_type.value.replace('_', ' ')}"
            }
            for inquiry_type in InquiryType
        ]
    }