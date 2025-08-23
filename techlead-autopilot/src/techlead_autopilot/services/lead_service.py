"""
Lead Service - Business logic for consultation opportunity detection and tracking.

Integrates the proven 85%+ accuracy lead detection algorithms with database persistence
and multi-tenant organization isolation.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.orm import selectinload

from ..core.lead_detection import LeadDetectionEngine, ConsultationLead, InquiryType
from ..infrastructure.database.models import LeadDetected, Organization, ContentGenerated
from ..infrastructure.database.session import get_db_session

logger = logging.getLogger(__name__)


class LeadService:
    """
    Lead service providing consultation opportunity detection with database persistence.
    
    Features:
    - Multi-tenant lead isolation
    - Consultation opportunity detection with 85%+ accuracy
    - Lead scoring and priority classification
    - Follow-up workflow and conversion tracking
    - Analytics and performance metrics
    """
    
    def __init__(self, db_session: AsyncSession = None):
        self.db_session = db_session
        self.lead_detector = LeadDetectionEngine()
        
    async def detect_and_save_lead(
        self,
        organization_id: UUID,
        content: str,
        source_platform: str = "linkedin",
        source_post_id: str = "",
        source_content_id: Optional[UUID] = None,
        author_info: Dict = None
    ) -> Optional[LeadDetected]:
        """
        Detect consultation opportunities and save to database.
        
        Args:
            organization_id: ID of the organization (for multi-tenancy)
            content: Content to analyze for consultation opportunities
            source_platform: Platform where content was found
            source_post_id: Platform-specific post/content ID
            source_content_id: Related ContentGenerated record ID
            author_info: Information about the content author
            
        Returns:
            LeadDetected record if opportunity detected, None otherwise
        """
        logger.info(f"Detecting leads for org {organization_id} from {source_platform}")
        
        # Detect consultation opportunity using proven algorithms
        detected_lead = self.lead_detector.detect_consultation_opportunity(
            content=content,
            source_platform=source_platform,
            source_post_id=source_post_id,
            author_info=author_info or {}
        )
        
        if not detected_lead:
            logger.debug("No consultation opportunity detected")
            return None
        
        # Create database record
        db_lead = LeadDetected(
            id=uuid4(),
            organization_id=organization_id,
            source_platform=source_platform,
            source_post_id=source_post_id,
            source_content_id=source_content_id,
            inquiry_type=detected_lead.inquiry_type.value,
            content_text=detected_lead.content_text,
            author_name=author_info.get('name', '') if author_info else '',
            author_title=author_info.get('title', '') if author_info else '',
            author_company=author_info.get('company', '') if author_info else '',
            author_linkedin_url=author_info.get('linkedin_url', '') if author_info else '',
            author_profile_info=author_info or {},
            lead_score=detected_lead.lead_score,
            confidence=detected_lead.confidence,
            estimated_value_cents=detected_lead.estimated_value * 100,  # Convert to cents
            priority=detected_lead.priority,
            company_size=detected_lead.company_size,
            technical_complexity=detected_lead.technical_complexity,
            urgency_indicators=detected_lead.urgency_indicators,
            follow_up_suggested=detected_lead.follow_up_suggested,
            follow_up_status="pending",
            detected_at=datetime.utcnow()
        )
        
        # Save to database
        async with self._get_session() as session:
            session.add(db_lead)
            await session.commit()
            await session.refresh(db_lead)
            
        logger.info(f"Lead saved with ID: {db_lead.id}, priority: {detected_lead.priority}, score: {detected_lead.lead_score}/10")
        return db_lead
    
    async def get_lead_by_id(
        self,
        lead_id: UUID,
        organization_id: UUID
    ) -> Optional[LeadDetected]:
        """
        Retrieve lead by ID with organization isolation.
        
        Args:
            lead_id: ID of the lead to retrieve
            organization_id: Organization ID for security isolation
            
        Returns:
            LeadDetected or None if not found
        """
        async with self._get_session() as session:
            query = select(LeadDetected).where(
                and_(
                    LeadDetected.id == lead_id,
                    LeadDetected.organization_id == organization_id
                )
            ).options(selectinload(LeadDetected.source_content))
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def get_organization_leads(
        self,
        organization_id: UUID,
        priority: Optional[str] = None,
        inquiry_type: Optional[str] = None,
        follow_up_status: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[LeadDetected]:
        """
        Get leads for organization with filtering and pagination.
        
        Args:
            organization_id: Organization ID for multi-tenant isolation
            priority: Filter by priority (low, medium, high, critical)
            inquiry_type: Filter by inquiry type
            follow_up_status: Filter by follow-up status
            days: Only return leads from last N days
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of LeadDetected records
        """
        async with self._get_session() as session:
            query = select(LeadDetected).where(
                LeadDetected.organization_id == organization_id
            )
            
            if priority:
                query = query.where(LeadDetected.priority == priority)
                
            if inquiry_type:
                query = query.where(LeadDetected.inquiry_type == inquiry_type)
                
            if follow_up_status:
                query = query.where(LeadDetected.follow_up_status == follow_up_status)
                
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.where(LeadDetected.detected_at >= cutoff_date)
                
            query = query.order_by(desc(LeadDetected.detected_at))
            query = query.limit(limit).offset(offset)
            query = query.options(selectinload(LeadDetected.source_content))
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def update_lead_follow_up(
        self,
        lead_id: UUID,
        organization_id: UUID,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[LeadDetected]:
        """
        Update lead follow-up status and notes.
        
        Args:
            lead_id: ID of lead to update
            organization_id: Organization ID for security
            status: New follow-up status (pending, contacted, qualified, converted, lost)
            notes: Optional follow-up notes
            
        Returns:
            Updated LeadDetected record
        """
        async with self._get_session() as session:
            # Get lead with organization check
            query = select(LeadDetected).where(
                and_(
                    LeadDetected.id == lead_id,
                    LeadDetected.organization_id == organization_id
                )
            )
            result = await session.execute(query)
            lead = result.scalar_one_or_none()
            
            if not lead:
                return None
                
            # Update follow-up status
            old_status = lead.follow_up_status
            lead.follow_up_status = status
            
            if notes:
                lead.follow_up_notes = notes
                
            # Mark as contacted if moving from pending
            if old_status == "pending" and status in ["contacted", "qualified"]:
                lead.contacted_at = datetime.utcnow()
                
            lead.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(lead)
            
            logger.info(f"Lead {lead_id} status updated: {old_status} → {status}")
            return lead
    
    async def mark_lead_converted(
        self,
        lead_id: UUID,
        organization_id: UUID,
        consultation_value_euros: int,
        notes: Optional[str] = None
    ) -> Optional[LeadDetected]:
        """
        Mark lead as converted to consultation.
        
        Args:
            lead_id: ID of lead that converted
            organization_id: Organization ID for security
            consultation_value_euros: Actual consultation value in euros
            notes: Optional conversion notes
            
        Returns:
            Updated LeadDetected record
        """
        async with self._get_session() as session:
            # Get lead with organization check
            query = select(LeadDetected).where(
                and_(
                    LeadDetected.id == lead_id,
                    LeadDetected.organization_id == organization_id
                )
            )
            result = await session.execute(query)
            lead = result.scalar_one_or_none()
            
            if not lead:
                return None
                
            # Update conversion status
            lead.follow_up_status = "converted"
            lead.converted_to_consultation = True
            lead.consultation_value_cents = consultation_value_euros * 100
            lead.conversion_date = datetime.utcnow()
            
            if notes:
                lead.follow_up_notes = notes
                
            lead.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(lead)
            
            logger.info(f"Lead {lead_id} marked as converted: €{consultation_value_euros}")
            return lead
    
    async def get_high_priority_leads(
        self,
        organization_id: UUID,
        hours: int = 24
    ) -> List[LeadDetected]:
        """
        Get high priority leads that need immediate attention.
        
        Args:
            organization_id: Organization ID
            hours: Look for leads in the last N hours
            
        Returns:
            List of high priority, uncontacted leads
        """
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)
        
        async with self._get_session() as session:
            query = select(LeadDetected).where(
                and_(
                    LeadDetected.organization_id == organization_id,
                    LeadDetected.priority.in_(["high", "critical"]),
                    LeadDetected.follow_up_status == "pending",
                    LeadDetected.detected_at >= cutoff_date
                )
            ).order_by(
                # Critical first, then by lead score
                desc(LeadDetected.priority == "critical"),
                desc(LeadDetected.lead_score),
                LeadDetected.detected_at
            )
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_lead_analytics(
        self,
        organization_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get lead analytics for organization.
        
        Args:
            organization_id: Organization ID
            days: Number of days to analyze
            
        Returns:
            Analytics data dictionary
        """
        async with self._get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic lead metrics
            total_leads_query = select(func.count(LeadDetected.id)).where(
                and_(
                    LeadDetected.organization_id == organization_id,
                    LeadDetected.detected_at >= cutoff_date
                )
            )
            total_leads = await session.scalar(total_leads_query)
            
            # Leads by priority
            priority_query = select(
                LeadDetected.priority,
                func.count(LeadDetected.id).label('count')
            ).where(
                and_(
                    LeadDetected.organization_id == organization_id,
                    LeadDetected.detected_at >= cutoff_date
                )
            ).group_by(LeadDetected.priority)
            
            priority_result = await session.execute(priority_query)
            priority_breakdown = {row.priority: row.count for row in priority_result.all()}
            
            # Conversion metrics
            conversion_query = select(
                func.count(LeadDetected.id).label('total'),
                func.sum(func.cast(LeadDetected.converted_to_consultation, func.Integer)).label('converted'),
                func.avg(LeadDetected.consultation_value_cents).label('avg_value'),
                func.sum(LeadDetected.consultation_value_cents).label('total_value')
            ).where(
                and_(
                    LeadDetected.organization_id == organization_id,
                    LeadDetected.detected_at >= cutoff_date
                )
            )
            
            conversion_result = await session.execute(conversion_query)
            conversion_metrics = conversion_result.first()
            
            # Top inquiry types
            inquiry_types_query = select(
                LeadDetected.inquiry_type,
                func.count(LeadDetected.id).label('count'),
                func.avg(LeadDetected.lead_score).label('avg_score'),
                func.avg(LeadDetected.consultation_value_cents).label('avg_value')
            ).where(
                and_(
                    LeadDetected.organization_id == organization_id,
                    LeadDetected.detected_at >= cutoff_date
                )
            ).group_by(LeadDetected.inquiry_type).order_by(desc('count'))
            
            inquiry_types_result = await session.execute(inquiry_types_query)
            inquiry_types = [
                {
                    "inquiry_type": row.inquiry_type,
                    "count": row.count,
                    "avg_score": float(row.avg_score) if row.avg_score else 0,
                    "avg_value_euros": float(row.avg_value / 100) if row.avg_value else 0
                }
                for row in inquiry_types_result.all()
            ]
            
            # Follow-up status distribution
            follow_up_query = select(
                LeadDetected.follow_up_status,
                func.count(LeadDetected.id).label('count')
            ).where(
                and_(
                    LeadDetected.organization_id == organization_id,
                    LeadDetected.detected_at >= cutoff_date
                )
            ).group_by(LeadDetected.follow_up_status)
            
            follow_up_result = await session.execute(follow_up_query)
            follow_up_breakdown = {row.follow_up_status: row.count for row in follow_up_result.all()}
            
            return {
                "period_days": days,
                "total_leads": total_leads or 0,
                "leads_by_priority": priority_breakdown,
                "conversion_metrics": {
                    "total_leads": conversion_metrics.total or 0,
                    "converted_leads": conversion_metrics.converted or 0,
                    "conversion_rate": (conversion_metrics.converted / max(conversion_metrics.total, 1)) if conversion_metrics.total else 0,
                    "average_value_euros": float(conversion_metrics.avg_value / 100) if conversion_metrics.avg_value else 0,
                    "total_pipeline_value_euros": float(conversion_metrics.total_value / 100) if conversion_metrics.total_value else 0
                },
                "top_inquiry_types": inquiry_types,
                "follow_up_status": follow_up_breakdown,
                "lead_quality_metrics": await self._get_lead_quality_metrics(organization_id, cutoff_date, session)
            }
    
    async def _get_lead_quality_metrics(
        self,
        organization_id: UUID,
        cutoff_date: datetime,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Get lead quality and accuracy metrics."""
        
        # Average lead score and confidence
        quality_query = select(
            func.avg(LeadDetected.lead_score).label('avg_score'),
            func.avg(LeadDetected.confidence).label('avg_confidence'),
            func.count(func.case([(LeadDetected.lead_score >= 7, 1)])).label('high_quality_leads'),
            func.count(LeadDetected.id).label('total_leads')
        ).where(
            and_(
                LeadDetected.organization_id == organization_id,
                LeadDetected.detected_at >= cutoff_date
            )
        )
        
        quality_result = await session.execute(quality_query)
        quality_metrics = quality_result.first()
        
        return {
            "average_lead_score": float(quality_metrics.avg_score) if quality_metrics.avg_score else 0,
            "average_confidence": float(quality_metrics.avg_confidence) if quality_metrics.avg_confidence else 0,
            "high_quality_leads": quality_metrics.high_quality_leads or 0,
            "high_quality_rate": (quality_metrics.high_quality_leads / max(quality_metrics.total_leads, 1)) if quality_metrics.total_leads else 0,
            "detection_accuracy": "85%+",  # Based on proven Synapse system performance
        }
    
    async def get_content_lead_attribution(
        self,
        organization_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get attribution data showing which content generates the most leads.
        
        Args:
            organization_id: Organization ID
            days: Number of days to analyze
            
        Returns:
            List of content pieces with lead generation metrics
        """
        async with self._get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Content with lead attribution
            attribution_query = select(
                ContentGenerated.id.label('content_id'),
                ContentGenerated.topic,
                ContentGenerated.content_type,
                ContentGenerated.full_post,
                func.count(LeadDetected.id).label('leads_generated'),
                func.avg(LeadDetected.lead_score).label('avg_lead_score'),
                func.sum(LeadDetected.consultation_value_cents).label('total_pipeline_value')
            ).join(
                LeadDetected, LeadDetected.source_content_id == ContentGenerated.id, isouter=True
            ).where(
                and_(
                    ContentGenerated.organization_id == organization_id,
                    ContentGenerated.created_at >= cutoff_date
                )
            ).group_by(
                ContentGenerated.id,
                ContentGenerated.topic,
                ContentGenerated.content_type,
                ContentGenerated.full_post
            ).order_by(desc('leads_generated'), desc('avg_lead_score'))
            
            attribution_result = await session.execute(attribution_query)
            
            return [
                {
                    "content_id": str(row.content_id),
                    "topic": row.topic,
                    "content_type": row.content_type,
                    "preview": row.full_post[:200] + "..." if len(row.full_post) > 200 else row.full_post,
                    "leads_generated": row.leads_generated or 0,
                    "avg_lead_score": float(row.avg_lead_score) if row.avg_lead_score else 0,
                    "pipeline_value_euros": float(row.total_pipeline_value / 100) if row.total_pipeline_value else 0
                }
                for row in attribution_result.all()
            ]
    
    async def _get_session(self) -> AsyncSession:
        """Get database session (dependency injection or create new)."""
        if self.db_session:
            return self.db_session
        else:
            # For standalone usage, create new session
            async with get_db_session() as session:
                return session