"""Content generation API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from ...core.content_generation import ContentType
from ...services.content_service import ContentService
from ...infrastructure.database.session import get_db_session
from ..auth.dependencies import get_current_user, get_current_organization
from ...infrastructure.database.models import User, Organization

logger = logging.getLogger(__name__)

router = APIRouter()


class ContentGenerationRequest(BaseModel):
    """Request model for content generation."""
    content_type: str = Field(..., description="Type of content to generate")
    topic: str = Field(..., description="Main topic for the content")
    target_audience: str = Field(default="technical_leaders", description="Target audience")
    consultation_focused: bool = Field(default=True, description="Optimize for consultation inquiries")
    target_engagement_rate: float = Field(default=0.035, description="Target engagement rate")


class ContentResponse(BaseModel):
    """Response model for generated content."""
    id: str
    content_type: str
    topic: str
    target_audience: str
    hook: str
    body: str
    call_to_action: str
    hashtags: str
    full_post: str
    character_count: int
    estimated_read_time_seconds: int
    engagement_prediction: float
    generation_metadata: dict
    status: str
    created_at: datetime
    updated_at: datetime


class ContentListResponse(BaseModel):
    """Response model for content list."""
    content: List[ContentResponse]
    total: int
    page: int
    page_size: int


class ContentAnalyticsResponse(BaseModel):
    """Response model for content analytics."""
    period_days: int
    total_content_generated: int
    content_posted: int
    posting_rate: float
    average_engagement: dict
    top_content_types: List[dict]
    consultation_focus_performance: dict


# Dependency to get content service
async def get_content_service(db=Depends(get_db_session)) -> ContentService:
    """Get content service with database session."""
    return ContentService(db_session=db)


@router.post("/generate", response_model=ContentResponse)
async def generate_content(
    request: ContentGenerationRequest,
    content_service: ContentService = Depends(get_content_service),
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization)
):
    """
    Generate technical leadership content using proven €290K algorithms.
    
    Generates content optimized for consultation pipeline generation and saves
    to database with proper multi-tenant isolation.
    """
    try:
        # Validate content type
        try:
            content_type_enum = ContentType(request.content_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content type: {request.content_type}. "
                       f"Available types: {[t.value for t in ContentType]}"
            )
        
        # Generate and save content
        db_content = await content_service.generate_and_save_content(
            user_id=current_user.id,
            organization_id=current_organization.id,
            content_type=content_type_enum,
            topic=request.topic,
            target_audience=request.target_audience,
            consultation_focused=request.consultation_focused,
            target_engagement_rate=request.target_engagement_rate
        )
        
        # Return response
        return ContentResponse(
            id=str(db_content.id),
            content_type=db_content.content_type,
            topic=db_content.topic,
            target_audience=db_content.target_audience,
            hook=db_content.hook,
            body=db_content.body,
            call_to_action=db_content.call_to_action,
            hashtags=db_content.hashtags,
            full_post=db_content.full_post,
            character_count=db_content.character_count,
            estimated_read_time_seconds=db_content.estimated_read_time_seconds,
            engagement_prediction=db_content.engagement_prediction,
            generation_metadata=db_content.generation_metadata,
            status=db_content.status,
            created_at=db_content.created_at,
            updated_at=db_content.updated_at
        )
        
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}"
        )


@router.get("/", response_model=ContentListResponse)
async def get_content(
    status: Optional[str] = Query(None, description="Filter by status"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    content_service: ContentService = Depends(get_content_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get organization's content with filtering and pagination."""
    content_list = await content_service.get_organization_content(
        organization_id=current_organization.id,
        status=status,
        content_type=content_type,
        limit=limit,
        offset=offset
    )
    
    # Convert to response format
    content_responses = [
        ContentResponse(
            id=str(content.id),
            content_type=content.content_type,
            topic=content.topic,
            target_audience=content.target_audience,
            hook=content.hook,
            body=content.body,
            call_to_action=content.call_to_action,
            hashtags=content.hashtags,
            full_post=content.full_post,
            character_count=content.character_count,
            estimated_read_time_seconds=content.estimated_read_time_seconds,
            engagement_prediction=content.engagement_prediction,
            generation_metadata=content.generation_metadata,
            status=content.status,
            created_at=content.created_at,
            updated_at=content.updated_at
        )
        for content in content_list
    ]
    
    return ContentListResponse(
        content=content_responses,
        total=len(content_responses),
        page=offset // limit + 1,
        page_size=limit
    )


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content_by_id(
    content_id: UUID,
    content_service: ContentService = Depends(get_content_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get specific content by ID."""
    content = await content_service.get_content_by_id(
        content_id=content_id,
        organization_id=current_organization.id
    )
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    return ContentResponse(
        id=str(content.id),
        content_type=content.content_type,
        topic=content.topic,
        target_audience=content.target_audience,
        hook=content.hook,
        body=content.body,
        call_to_action=content.call_to_action,
        hashtags=content.hashtags,
        full_post=content.full_post,
        character_count=content.character_count,
        estimated_read_time_seconds=content.estimated_read_time_seconds,
        engagement_prediction=content.engagement_prediction,
        generation_metadata=content.generation_metadata,
        status=content.status,
        created_at=content.created_at,
        updated_at=content.updated_at
    )


@router.post("/{content_id}/approve", response_model=ContentResponse)
async def approve_content(
    content_id: UUID,
    content_service: ContentService = Depends(get_content_service),
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization)
):
    """Approve content for posting."""
    content = await content_service.approve_content(
        content_id=content_id,
        organization_id=current_organization.id,
        approved_by_user_id=current_user.id
    )
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    return ContentResponse(
        id=str(content.id),
        content_type=content.content_type,
        topic=content.topic,
        target_audience=content.target_audience,
        hook=content.hook,
        body=content.body,
        call_to_action=content.call_to_action,
        hashtags=content.hashtags,
        full_post=content.full_post,
        character_count=content.character_count,
        estimated_read_time_seconds=content.estimated_read_time_seconds,
        engagement_prediction=content.engagement_prediction,
        generation_metadata=content.generation_metadata,
        status=content.status,
        created_at=content.created_at,
        updated_at=content.updated_at
    )


@router.get("/analytics/overview", response_model=ContentAnalyticsResponse)
async def get_content_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    content_service: ContentService = Depends(get_content_service),
    current_organization: Organization = Depends(get_current_organization)
):
    """Get content analytics overview."""
    analytics = await content_service.get_content_analytics(
        organization_id=current_organization.id,
        days=days
    )
    
    return ContentAnalyticsResponse(**analytics)


@router.get("/types")
async def get_content_types():
    """Get available content types with descriptions."""
    from ...core.content_generation.content_templates import get_template_library
    
    template_library = get_template_library()
    
    return {
        "content_types": [
            {
                "value": content_type.value,
                "name": content_type.value.replace("_", " ").title(),
                "description": f"Generates {content_type.value.replace('_', ' ')} content",
                "optimal_length": f"{template_library[content_type].optimal_length_range[0]}-{template_library[content_type].optimal_length_range[1]} characters",
                "target_audience": template_library[content_type].target_audience,
                "example_topics": template_library[content_type].example_topics[:3]
            }
            for content_type in ContentType
        ]
    }


@router.get("/templates/{content_type}")
async def get_content_template_info(content_type: str):
    """Get detailed template information for a specific content type."""
    try:
        content_type_enum = ContentType(content_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content type '{content_type}' not found"
        )
    
    from ...core.content_generation.content_templates import get_template_library
    template_library = get_template_library()
    template = template_library[content_type_enum]
    
    return {
        "content_type": content_type,
        "name": content_type.replace("_", " ").title(),
        "description": f"Template for {content_type.replace('_', ' ')} content",
        "structure": template.structure,
        "engagement_drivers": template.engagement_drivers,
        "consultation_hooks": template.consultation_hooks,
        "optimal_length_range": template.optimal_length_range,
        "target_audience": template.target_audience,
        "example_topics": template.example_topics
    }