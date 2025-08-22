"""Content generation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from ...core.content_generation import ContentGenerationEngine, ContentType, GeneratedContent

router = APIRouter()


class ContentGenerationRequest(BaseModel):
    """Request model for content generation."""
    content_type: str = Field(..., description="Type of content to generate")
    topic: str = Field(..., description="Main topic for the content")
    target_audience: str = Field(default="technical_leaders", description="Target audience")
    consultation_focused: bool = Field(default=True, description="Optimize for consultation inquiries")
    target_engagement_rate: float = Field(default=0.035, description="Target engagement rate")


class ContentGenerationResponse(BaseModel):
    """Response model for generated content."""
    id: str
    content_type: str
    hook: str
    body: str
    call_to_action: str
    hashtags: str
    full_post: str
    character_count: int
    estimated_read_time_seconds: int
    engagement_prediction: float
    generation_metadata: dict
    created_at: datetime


# Dependency to get content generation engine
def get_content_engine() -> ContentGenerationEngine:
    """Get content generation engine instance."""
    return ContentGenerationEngine()


@router.post("/generate", response_model=ContentGenerationResponse)
async def generate_content(
    request: ContentGenerationRequest,
    engine: ContentGenerationEngine = Depends(get_content_engine)
):
    """
    Generate technical leadership content.
    
    Uses proven algorithms that generated €290K consultation pipeline.
    """
    try:
        # Validate content type
        try:
            content_type_enum = ContentType(request.content_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {request.content_type}. "
                       f"Available types: {[t.value for t in ContentType]}"
            )
        
        # Generate content
        generated_content = engine.generate_content(
            content_type=content_type_enum,
            topic=request.topic,
            target_audience=request.target_audience,
            consultation_focused=request.consultation_focused,
            target_engagement_rate=request.target_engagement_rate
        )
        
        # Return response
        return ContentGenerationResponse(
            id="temp-id",  # TODO: Generate actual ID when saving to database
            content_type=generated_content.content_type.value,
            hook=generated_content.hook,
            body=generated_content.body,
            call_to_action=generated_content.call_to_action,
            hashtags=generated_content.hashtags,
            full_post=generated_content.full_post,
            character_count=generated_content.character_count,
            estimated_read_time_seconds=generated_content.estimated_read_time_seconds,
            engagement_prediction=generated_content.engagement_prediction,
            generation_metadata=generated_content.generation_metadata,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.get("/types")
async def get_content_types():
    """Get available content types."""
    return {
        "content_types": [
            {
                "value": content_type.value,
                "name": content_type.value.replace("_", " ").title(),
                "description": f"Generates {content_type.value.replace('_', ' ')} content"
            }
            for content_type in ContentType
        ]
    }


@router.get("/templates/{content_type}")
async def get_content_template_info(content_type: str):
    """Get template information for a specific content type."""
    try:
        content_type_enum = ContentType(content_type)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Content type '{content_type}' not found"
        )
    
    # TODO: Get actual template info from content engine
    return {
        "content_type": content_type,
        "description": f"Template for {content_type.replace('_', ' ')} content",
        "structure": ["hook", "context", "insight", "example", "framework", "cta"],
        "optimal_length_range": [300, 500],
        "example_topics": ["technical leadership", "architecture decisions", "team building"]
    }