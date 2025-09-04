#!/usr/bin/env python3
"""
Epic 7 Week 1 Sales Automation API Router
Integrates sales automation system with unified platform endpoints
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from graph_rag.api.auth.dependencies import get_current_user_optional
from graph_rag.api.auth.models import User

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pydantic models for API requests and responses
class CRMContactResponse(BaseModel):
    """CRM contact API response model"""
    contact_id: str
    name: str
    company: str
    company_size: str
    title: str
    email: str
    linkedin_profile: str
    phone: str
    lead_score: int
    qualification_status: str
    estimated_value: int
    priority_tier: str
    next_action: str
    next_action_date: str
    created_at: str
    updated_at: str
    notes: str

class ProposalGenerationRequest(BaseModel):
    """Request model for proposal generation"""
    contact_id: str
    inquiry_type: Optional[str] = None
    custom_requirements: Optional[str] = None

class ProposalResponse(BaseModel):
    """Proposal API response model"""
    proposal_id: str
    contact_name: str
    company: str
    template_used: str
    proposal_value: int
    estimated_close_probability: float
    roi_analysis: Dict
    status: str
    generated_at: str

class PipelineSummaryResponse(BaseModel):
    """Sales pipeline summary response"""
    total_contacts: int
    qualified_leads: int
    platinum_leads: int
    gold_leads: int
    total_pipeline_value: int
    total_proposals: int
    avg_close_probability: float
    pipeline_health_score: float
    projected_annual_revenue: int

class ContactUpdateRequest(BaseModel):
    """Request model for contact updates"""
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

class LeadScoringResponse(BaseModel):
    """Lead scoring analysis response"""
    contact_id: str
    current_score: int
    previous_score: Optional[int] = None
    scoring_factors: Dict
    score_change: int
    recommendations: List[str]

def create_epic7_sales_router() -> APIRouter:
    """Factory function to create Epic 7 Sales Automation router"""
    router = APIRouter()

    def get_sales_automation_engine(request: Request):
        """Get sales automation engine from app state"""
        try:
            # Import and initialize the engine
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent.parent / "business_development"))
            
            from epic7_sales_automation import SalesAutomationEngine
            
            # Check if already initialized in app state
            if hasattr(request.app.state, 'sales_automation_engine') and request.app.state.sales_automation_engine:
                return request.app.state.sales_automation_engine
            
            # Initialize and cache in app state
            engine = SalesAutomationEngine()
            request.app.state.sales_automation_engine = engine
            return engine
            
        except Exception as e:
            logger.error(f"Failed to initialize Sales Automation Engine: {e}")
            raise HTTPException(
                status_code=503,
                detail="Sales automation system temporarily unavailable"
            )

    @router.get("/pipeline/summary", response_model=PipelineSummaryResponse, tags=["Sales Pipeline"])
    async def get_pipeline_summary(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get comprehensive sales pipeline summary"""
        try:
            summary = engine.get_sales_pipeline_summary()
            return PipelineSummaryResponse(**summary)
        except Exception as e:
            logger.error(f"Failed to get pipeline summary: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve pipeline summary")

    @router.get("/contacts", response_model=List[CRMContactResponse], tags=["CRM"])
    async def list_contacts(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        priority_tier: Optional[str] = None,
        qualification_status: Optional[str] = None,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """List CRM contacts with filtering options"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            # Build query with filters
            query = "SELECT * FROM crm_contacts WHERE 1=1"
            params = []
            
            if priority_tier:
                query += " AND priority_tier = ?"
                params.append(priority_tier)
            
            if qualification_status:
                query += " AND qualification_status = ?"
                params.append(qualification_status)
            
            query += " ORDER BY lead_score DESC, created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, skip])
            
            cursor.execute(query, params)
            contacts = cursor.fetchall()
            
            # Convert to response models
            columns = [description[0] for description in cursor.description]
            contact_list = []
            
            for contact_data in contacts:
                contact_dict = dict(zip(columns, contact_data, strict=False))
                contact_list.append(CRMContactResponse(**contact_dict))
            
            conn.close()
            return contact_list
            
        except Exception as e:
            logger.error(f"Failed to list contacts: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve contacts")

    @router.get("/contacts/{contact_id}", response_model=CRMContactResponse, tags=["CRM"])
    async def get_contact(
        contact_id: str,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get individual contact details"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM crm_contacts WHERE contact_id = ?", (contact_id,))
            contact_data = cursor.fetchone()
            
            if not contact_data:
                raise HTTPException(status_code=404, detail="Contact not found")
            
            columns = [description[0] for description in cursor.description]
            contact_dict = dict(zip(columns, contact_data, strict=False))
            
            conn.close()
            return CRMContactResponse(**contact_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get contact {contact_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve contact")

    @router.put("/contacts/{contact_id}", response_model=CRMContactResponse, tags=["CRM"])
    async def update_contact(
        contact_id: str,
        contact_update: ContactUpdateRequest,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Update contact information"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            # Build update query
            updates = []
            values = []
            
            for field, value in contact_update.dict(exclude_unset=True).items():
                if value is not None:
                    updates.append(f"{field} = ?")
                    values.append(value)
            
            if updates:
                updates.append("updated_at = ?")
                values.append(datetime.now().isoformat())
                values.append(contact_id)
                
                query = f"UPDATE crm_contacts SET {', '.join(updates)} WHERE contact_id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            # Return updated contact
            cursor.execute("SELECT * FROM crm_contacts WHERE contact_id = ?", (contact_id,))
            contact_data = cursor.fetchone()
            
            if not contact_data:
                raise HTTPException(status_code=404, detail="Contact not found")
            
            columns = [description[0] for description in cursor.description]
            contact_dict = dict(zip(columns, contact_data, strict=False))
            
            conn.close()
            return CRMContactResponse(**contact_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update contact {contact_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update contact")

    @router.post("/proposals/generate", response_model=ProposalResponse, tags=["Proposals"])
    async def generate_proposal(
        proposal_request: ProposalGenerationRequest,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Generate automated proposal for contact"""
        try:
            proposal = engine.generate_automated_proposal(
                contact_id=proposal_request.contact_id,
                inquiry_type=proposal_request.inquiry_type
            )
            
            if 'error' in proposal:
                raise HTTPException(status_code=404, detail=proposal['error'])
            
            # Get contact information for response
            import sqlite3
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, company FROM crm_contacts WHERE contact_id = ?", (proposal_request.contact_id,))
            contact_info = cursor.fetchone()
            
            # Get generated proposal details
            cursor.execute("""
                SELECT proposal_id, template_used, proposal_value, estimated_close_probability, 
                       roi_calculation, status, generated_at
                FROM generated_proposals 
                WHERE proposal_id = ?
            """, (proposal['proposal_id'],))
            
            proposal_data = cursor.fetchone()
            conn.close()
            
            if not proposal_data or not contact_info:
                raise HTTPException(status_code=500, detail="Failed to retrieve generated proposal")
            
            # Parse ROI calculation
            import json
            roi_analysis = json.loads(proposal_data[4])
            
            return ProposalResponse(
                proposal_id=proposal_data[0],
                contact_name=contact_info[0],
                company=contact_info[1],
                template_used=proposal_data[1],
                proposal_value=proposal_data[2],
                estimated_close_probability=proposal_data[3],
                roi_analysis=roi_analysis,
                status=proposal_data[5],
                generated_at=proposal_data[6]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate proposal: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate proposal")

    @router.get("/proposals", response_model=List[ProposalResponse], tags=["Proposals"])
    async def list_proposals(
        request: Request,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """List generated proposals with filtering options"""
        try:
            import sqlite3
            import json
            
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT p.proposal_id, c.name, c.company, p.template_used, p.proposal_value,
                       p.estimated_close_probability, p.roi_calculation, p.status, p.generated_at
                FROM generated_proposals p
                JOIN crm_contacts c ON p.contact_id = c.contact_id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND p.status = ?"
                params.append(status)
            
            query += " ORDER BY p.generated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, skip])
            
            cursor.execute(query, params)
            proposals = cursor.fetchall()
            
            proposal_list = []
            for proposal_data in proposals:
                roi_analysis = json.loads(proposal_data[6])
                
                proposal_list.append(ProposalResponse(
                    proposal_id=proposal_data[0],
                    contact_name=proposal_data[1],
                    company=proposal_data[2],
                    template_used=proposal_data[3],
                    proposal_value=proposal_data[4],
                    estimated_close_probability=proposal_data[5],
                    roi_analysis=roi_analysis,
                    status=proposal_data[7],
                    generated_at=proposal_data[8]
                ))
            
            conn.close()
            return proposal_list
            
        except Exception as e:
            logger.error(f"Failed to list proposals: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve proposals")

    @router.post("/proposals/{proposal_id}/send", tags=["Proposals"])
    async def send_proposal(
        proposal_id: str,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Mark proposal as sent"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE generated_proposals 
                SET status = 'sent', sent_at = ?
                WHERE proposal_id = ?
            """, (datetime.now().isoformat(), proposal_id))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Proposal not found")
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Proposal marked as sent"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send proposal {proposal_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to send proposal")

    @router.post("/import-inquiries", tags=["Data Import"])
    async def import_consultation_inquiries(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Import consultation inquiries from existing business development system"""
        try:
            contacts = engine.import_consultation_inquiries()
            return {
                "success": True,
                "imported_count": len(contacts),
                "message": f"Successfully imported {len(contacts)} consultation inquiries into CRM system"
            }
        except Exception as e:
            logger.error(f"Failed to import inquiries: {e}")
            raise HTTPException(status_code=500, detail="Failed to import consultation inquiries")

    @router.get("/lead-scoring/{contact_id}", response_model=LeadScoringResponse, tags=["Lead Scoring"])
    async def get_lead_scoring(
        contact_id: str,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get lead scoring analysis for contact"""
        try:
            import sqlite3
            import json
            
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            # Get current contact score
            cursor.execute("SELECT lead_score, notes FROM crm_contacts WHERE contact_id = ?", (contact_id,))
            contact_data = cursor.fetchone()
            
            if not contact_data:
                raise HTTPException(status_code=404, detail="Contact not found")
            
            current_score = contact_data[0]
            notes = contact_data[1]
            
            # Get scoring history
            cursor.execute("""
                SELECT previous_score, scoring_factors 
                FROM lead_scoring_history 
                WHERE contact_id = ? 
                ORDER BY scored_at DESC 
                LIMIT 1
            """, (contact_id,))
            
            history_data = cursor.fetchone()
            previous_score = history_data[0] if history_data else None
            scoring_factors = json.loads(history_data[1]) if history_data else {}
            
            # Generate recommendations
            recommendations = []
            
            if current_score < 50:
                recommendations.append("Contact requires additional qualification before proposal generation")
                recommendations.append("Gather more information about company size and technical challenges")
            elif current_score < 70:
                recommendations.append("Good candidate for discovery call to increase qualification score")
                recommendations.append("Focus on understanding specific pain points and ROI potential")
            else:
                recommendations.append("High-priority lead ready for proposal generation")
                recommendations.append("Schedule consultation call within 24-48 hours")
            
            if "enterprise" in notes.lower() or "series b" in notes.lower():
                recommendations.append("Enterprise prospect - consider premium service offerings")
            
            conn.close()
            
            return LeadScoringResponse(
                contact_id=contact_id,
                current_score=current_score,
                previous_score=previous_score,
                scoring_factors=scoring_factors,
                score_change=current_score - previous_score if previous_score else 0,
                recommendations=recommendations
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get lead scoring for {contact_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve lead scoring")

    @router.get("/analytics/conversion-funnel", tags=["Analytics"])
    async def get_conversion_funnel(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get sales conversion funnel analytics"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            
            # Total leads by stage
            cursor.execute("SELECT COUNT(*) FROM crm_contacts")
            total_leads = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM crm_contacts WHERE qualification_status = 'qualified'")
            qualified_leads = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM generated_proposals")
            proposals_sent = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM generated_proposals WHERE status = 'sent'")
            active_proposals = cursor.fetchone()[0]
            
            # Calculate conversion rates
            qualification_rate = (qualified_leads / total_leads * 100) if total_leads > 0 else 0
            proposal_rate = (proposals_sent / qualified_leads * 100) if qualified_leads > 0 else 0
            
            # Value analysis
            cursor.execute("SELECT AVG(estimated_value) FROM crm_contacts WHERE qualification_status = 'qualified'")
            avg_deal_size = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT AVG(estimated_close_probability) FROM generated_proposals")
            avg_close_rate = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                "funnel_stages": {
                    "total_leads": total_leads,
                    "qualified_leads": qualified_leads,
                    "proposals_generated": proposals_sent,
                    "active_proposals": active_proposals
                },
                "conversion_rates": {
                    "qualification_rate": round(qualification_rate, 1),
                    "proposal_rate": round(proposal_rate, 1),
                    "overall_conversion": round(qualification_rate * proposal_rate / 100, 1)
                },
                "value_metrics": {
                    "average_deal_size": int(avg_deal_size),
                    "average_close_probability": round(avg_close_rate * 100, 1),
                    "projected_monthly_revenue": int(avg_deal_size * avg_close_rate * qualified_leads / 12)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversion funnel: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve conversion funnel analytics")

    return router

# Factory function for use in main.py
def create_epic7_sales_automation_router() -> APIRouter:
    """Create and configure the Epic 7 Sales Automation router"""
    return create_epic7_sales_router()