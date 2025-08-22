"""
Content Service - Business logic layer for content generation and management.

Integrates the proven €290K content generation algorithms with database persistence
and multi-tenant organization isolation.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from ..core.content_generation import ContentGenerationEngine, ContentType, GeneratedContent
from ..infrastructure.database.models import ContentGenerated, User, Organization
from ..infrastructure.database.session import get_async_session

logger = logging.getLogger(__name__)


class ContentService:
    """
    Content service providing content generation with database persistence.
    
    Features:
    - Multi-tenant content isolation
    - Content approval workflow  
    - Performance tracking and analytics
    - Integration with proven €290K algorithms
    """
    
    def __init__(self, db_session: AsyncSession = None):
        self.db_session = db_session
        self.content_engine = ContentGenerationEngine()
        
    async def generate_and_save_content(
        self,
        user_id: UUID,
        organization_id: UUID,
        content_type: ContentType,
        topic: str,
        target_audience: str = "technical_leaders",
        consultation_focused: bool = True,
        target_engagement_rate: float = 0.035
    ) -> ContentGenerated:
        """
        Generate content using proven algorithms and save to database.
        
        Args:
            user_id: ID of the user generating content
            organization_id: ID of the organization (for multi-tenancy)
            content_type: Type of content to generate
            topic: Main topic for the content
            target_audience: Target audience for the content
            consultation_focused: Whether to optimize for consultation inquiries
            target_engagement_rate: Target engagement rate
            
        Returns:
            ContentGenerated: Saved content record with database ID
        """
        logger.info(f"Generating content for org {organization_id}, topic: {topic}")
        
        # Generate content using proven algorithms
        generated_content = self.content_engine.generate_content(
            content_type=content_type,
            topic=topic,
            target_audience=target_audience,
            consultation_focused=consultation_focused,
            target_engagement_rate=target_engagement_rate
        )
        
        # Create database record
        db_content = ContentGenerated(
            id=uuid4(),
            organization_id=organization_id,
            user_id=user_id,
            content_type=content_type.value,
            topic=topic,
            target_audience=target_audience,
            hook=generated_content.hook,
            body=generated_content.body,
            call_to_action=generated_content.call_to_action,
            hashtags=generated_content.hashtags,
            full_post=generated_content.full_post,
            character_count=generated_content.character_count,
            estimated_read_time_seconds=generated_content.estimated_read_time_seconds,
            engagement_prediction=generated_content.engagement_prediction,
            consultation_focused=consultation_focused,
            generation_metadata=generated_content.generation_metadata,
            status="draft",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        async with self._get_session() as session:
            session.add(db_content)
            await session.commit()
            await session.refresh(db_content)
            
        logger.info(f"Content saved with ID: {db_content.id}")
        return db_content
    
    async def get_content_by_id(
        self,
        content_id: UUID,
        organization_id: UUID
    ) -> Optional[ContentGenerated]:
        """
        Retrieve content by ID with organization isolation.
        
        Args:
            content_id: ID of the content to retrieve
            organization_id: Organization ID for security isolation
            
        Returns:
            ContentGenerated or None if not found
        """
        async with self._get_session() as session:
            query = select(ContentGenerated).where(
                and_(
                    ContentGenerated.id == content_id,
                    ContentGenerated.organization_id == organization_id
                )
            ).options(selectinload(ContentGenerated.user))
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def get_organization_content(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ContentGenerated]:
        """
        Get content for organization with filtering and pagination.
        
        Args:
            organization_id: Organization ID for multi-tenant isolation
            status: Filter by status (draft, approved, posted, archived)
            content_type: Filter by content type
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of ContentGenerated records
        """
        async with self._get_session() as session:
            query = select(ContentGenerated).where(
                ContentGenerated.organization_id == organization_id
            )
            
            if status:
                query = query.where(ContentGenerated.status == status)
                
            if content_type:
                query = query.where(ContentGenerated.content_type == content_type)
                
            query = query.order_by(desc(ContentGenerated.created_at))
            query = query.limit(limit).offset(offset)
            query = query.options(selectinload(ContentGenerated.user))
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def approve_content(
        self,
        content_id: UUID,
        organization_id: UUID,
        approved_by_user_id: UUID
    ) -> Optional[ContentGenerated]:
        """
        Approve content for posting.
        
        Args:
            content_id: ID of content to approve
            organization_id: Organization ID for security
            approved_by_user_id: ID of user approving the content
            
        Returns:
            Updated ContentGenerated record
        """
        async with self._get_session() as session:
            # Get content with organization check
            query = select(ContentGenerated).where(
                and_(
                    ContentGenerated.id == content_id,
                    ContentGenerated.organization_id == organization_id
                )
            )
            result = await session.execute(query)
            content = result.scalar_one_or_none()
            
            if not content:
                return None
                
            # Update approval status
            content.status = "approved"
            content.approved_by_user_id = approved_by_user_id
            content.approved_at = datetime.utcnow()
            content.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(content)
            
            logger.info(f"Content {content_id} approved by user {approved_by_user_id}")
            return content
    
    async def mark_as_posted(
        self,
        content_id: UUID,
        organization_id: UUID,
        platform: str,
        platform_post_id: str
    ) -> Optional[ContentGenerated]:
        """
        Mark content as posted to social media platform.
        
        Args:
            content_id: ID of content that was posted
            organization_id: Organization ID for security
            platform: Platform where posted (linkedin, twitter)
            platform_post_id: Platform-specific post ID
            
        Returns:
            Updated ContentGenerated record
        """
        async with self._get_session() as session:
            # Get content with organization check
            query = select(ContentGenerated).where(
                and_(
                    ContentGenerated.id == content_id,
                    ContentGenerated.organization_id == organization_id
                )
            )
            result = await session.execute(query)
            content = result.scalar_one_or_none()
            
            if not content:
                return None
                
            # Update posting status
            content.status = "posted"
            
            if platform.lower() == "linkedin":
                content.posted_to_linkedin = True
                content.linkedin_post_id = platform_post_id
                content.linkedin_posted_at = datetime.utcnow()
                
            content.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(content)
            
            logger.info(f"Content {content_id} marked as posted to {platform}")
            return content
    
    async def update_engagement_metrics(
        self,
        content_id: UUID,
        organization_id: UUID,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        impressions: int = 0
    ) -> Optional[ContentGenerated]:
        """
        Update engagement metrics from social media platforms.
        
        Args:
            content_id: ID of content to update
            organization_id: Organization ID for security
            likes: Number of likes/reactions
            comments: Number of comments
            shares: Number of shares/reposts
            impressions: Number of impressions
            
        Returns:
            Updated ContentGenerated record
        """
        async with self._get_session() as session:
            # Get content with organization check
            query = select(ContentGenerated).where(
                and_(
                    ContentGenerated.id == content_id,
                    ContentGenerated.organization_id == organization_id
                )
            )
            result = await session.execute(query)
            content = result.scalar_one_or_none()
            
            if not content:
                return None
                
            # Update metrics
            content.linkedin_likes = likes
            content.linkedin_comments = comments
            content.linkedin_shares = shares
            content.linkedin_impressions = impressions
            
            # Calculate engagement rate
            if impressions > 0:
                total_engagement = likes + comments + shares
                content.engagement_rate = total_engagement / impressions
            
            content.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(content)
            
            logger.info(f"Updated engagement metrics for content {content_id}")
            return content
    
    async def get_content_analytics(
        self,
        organization_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get content analytics for organization.
        
        Args:
            organization_id: Organization ID
            days: Number of days to analyze
            
        Returns:
            Analytics data dictionary
        """
        async with self._get_session() as session:
            # Get content created in the last N days
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic metrics
            total_content_query = select(func.count(ContentGenerated.id)).where(
                and_(
                    ContentGenerated.organization_id == organization_id,
                    ContentGenerated.created_at >= cutoff_date
                )
            )
            total_content = await session.scalar(total_content_query)
            
            # Posted content
            posted_content_query = select(func.count(ContentGenerated.id)).where(
                and_(
                    ContentGenerated.organization_id == organization_id,
                    ContentGenerated.status == "posted",
                    ContentGenerated.created_at >= cutoff_date
                )
            )
            posted_content = await session.scalar(posted_content_query)
            
            # Average engagement metrics
            avg_metrics_query = select(
                func.avg(ContentGenerated.linkedin_likes).label('avg_likes'),
                func.avg(ContentGenerated.linkedin_comments).label('avg_comments'),
                func.avg(ContentGenerated.linkedin_shares).label('avg_shares'),
                func.avg(ContentGenerated.linkedin_impressions).label('avg_impressions'),
                func.avg(ContentGenerated.engagement_rate).label('avg_engagement_rate'),
                func.avg(ContentGenerated.engagement_prediction).label('avg_predicted_engagement')
            ).where(
                and_(
                    ContentGenerated.organization_id == organization_id,
                    ContentGenerated.status == "posted",
                    ContentGenerated.linkedin_posted_at >= cutoff_date
                )
            )
            
            result = await session.execute(avg_metrics_query)
            avg_metrics = result.first()
            
            # Top performing content types
            top_content_types_query = select(
                ContentGenerated.content_type,
                func.count(ContentGenerated.id).label('count'),
                func.avg(ContentGenerated.engagement_rate).label('avg_engagement')
            ).where(
                and_(
                    ContentGenerated.organization_id == organization_id,
                    ContentGenerated.status == "posted",
                    ContentGenerated.linkedin_posted_at >= cutoff_date
                )
            ).group_by(ContentGenerated.content_type).order_by(desc('avg_engagement'))
            
            top_content_types_result = await session.execute(top_content_types_query)
            top_content_types = [
                {
                    "content_type": row.content_type,
                    "count": row.count,
                    "avg_engagement": float(row.avg_engagement) if row.avg_engagement else 0
                }
                for row in top_content_types_result.all()
            ]
            
            return {
                "period_days": days,
                "total_content_generated": total_content or 0,
                "content_posted": posted_content or 0,
                "posting_rate": (posted_content / max(total_content, 1)) if total_content else 0,
                "average_engagement": {
                    "likes": float(avg_metrics.avg_likes) if avg_metrics.avg_likes else 0,
                    "comments": float(avg_metrics.avg_comments) if avg_metrics.avg_comments else 0,
                    "shares": float(avg_metrics.avg_shares) if avg_metrics.avg_shares else 0,
                    "impressions": float(avg_metrics.avg_impressions) if avg_metrics.avg_impressions else 0,
                    "engagement_rate": float(avg_metrics.avg_engagement_rate) if avg_metrics.avg_engagement_rate else 0,
                    "predicted_vs_actual": {
                        "predicted": float(avg_metrics.avg_predicted_engagement) if avg_metrics.avg_predicted_engagement else 0,
                        "actual": float(avg_metrics.avg_engagement_rate) if avg_metrics.avg_engagement_rate else 0
                    }
                },
                "top_content_types": top_content_types,
                "consultation_focus_performance": await self._get_consultation_performance_metrics(
                    organization_id, cutoff_date, session
                )
            }
    
    async def _get_consultation_performance_metrics(
        self,
        organization_id: UUID,
        cutoff_date: datetime,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get consultation-focused content performance metrics."""
        
        # Consultation-focused vs general content performance
        consultation_query = select(
            func.avg(ContentGenerated.engagement_rate).label('consultation_engagement'),
            func.count(ContentGenerated.id).label('consultation_count')
        ).where(
            and_(
                ContentGenerated.organization_id == organization_id,
                ContentGenerated.consultation_focused == True,
                ContentGenerated.status == "posted",
                ContentGenerated.linkedin_posted_at >= cutoff_date
            )
        )
        
        general_query = select(
            func.avg(ContentGenerated.engagement_rate).label('general_engagement'),
            func.count(ContentGenerated.id).label('general_count')
        ).where(
            and_(
                ContentGenerated.organization_id == organization_id,
                ContentGenerated.consultation_focused == False,
                ContentGenerated.status == "posted",  
                ContentGenerated.linkedin_posted_at >= cutoff_date
            )
        )
        
        consultation_result = await session.execute(consultation_query)
        general_result = await session.execute(general_query)
        
        consultation_metrics = consultation_result.first()
        general_metrics = general_result.first()
        
        return {
            "consultation_focused": {
                "avg_engagement": float(consultation_metrics.consultation_engagement) if consultation_metrics.consultation_engagement else 0,
                "content_count": consultation_metrics.consultation_count or 0
            },
            "general_content": {
                "avg_engagement": float(general_metrics.general_engagement) if general_metrics.general_engagement else 0,
                "content_count": general_metrics.general_count or 0
            }
        }
    
    async def _get_session(self) -> AsyncSession:
        """Get database session (dependency injection or create new)."""
        if self.db_session:
            return self.db_session
        else:
            # For standalone usage, create new session
            async with get_async_session() as session:
                return session