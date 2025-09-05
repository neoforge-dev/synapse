#!/usr/bin/env python3
"""
Epic 10 Core Business Operations Router
Consolidates: documents + ingestion + search + query + Epic 7 sales automation
CRITICAL: Epic 7 pipeline protection ($1.158M value) - ZERO disruption to sales automation
"""

import inspect
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Core API schemas and dependencies
from graph_rag.api import schemas
from graph_rag.api.dependencies import (
    get_graph_rag_engine,
    get_graph_repository,
    get_vector_store,
)
from graph_rag.api.metrics import (
    inc_llm_rel_inferred,
    inc_llm_rel_persisted,
    observe_query_latency,
)
from graph_rag.api.models import (
    AnswerValidationResponse,
    AskRequest,
    ConfidenceMetricsResponse,
    ConversationContextResponse,
    EnhancedAskRequest,
    EnhancedQueryResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    QueryResultChunk,
    QueryResultGraphContext,
    StartConversationRequest,
    StartConversationResponse,
)

# Core interfaces and engines
from graph_rag.core.graph_rag_engine import GraphRAGEngine, QueryResult
from graph_rag.core.improved_synapse_engine import ImprovedSynapseEngine
from graph_rag.core.interfaces import GraphRepository, SearchResultData, VectorStore
from graph_rag.domain.models import Entity
from graph_rag.models import (
    ConsolidatedAnswerResponse,
    ConsolidatedQueryRequest,
    VectorStoreStatusResponse,
)
from graph_rag.services.ingestion import IngestionService

# Epic 7 Sales Automation imports and models (CRITICAL PIPELINE PROTECTION)
from graph_rag.api.auth.dependencies import get_current_user_optional
from graph_rag.api.auth.models import User

logger = logging.getLogger(__name__)

# Epic 7 Sales Automation Models (PROTECTED - $1.158M Pipeline Value)
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


# Dependency getters for state management
def _state_get_graph_repository(request: Request) -> "GraphRepository":
    from graph_rag.api.main import get_graph_repository as _getter
    return _getter(request)

def _state_get_vector_store(request: Request) -> "VectorStore":
    from graph_rag.api.main import get_vector_store as _getter
    return _getter(request)

def _state_get_ingestion_service(request: Request):
    from graph_rag.api.main import get_ingestion_service as _getter
    return _getter(request)

# Epic 7 Sales Engine Dependency (CRITICAL PROTECTION)
def get_sales_automation_engine(request: Request):
    """Get Epic 7 sales automation engine from app state (PROTECTED)"""
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

# Background processing functions
async def process_document_with_service(
    document_id: str, content: str, metadata: dict, ingestion_service: IngestionService
):
    """Background task to process a document using the IngestionService."""
    logger.info(f"DEBUG: process_document_with_service called for doc {document_id}")
    logger.info(f"DEBUG: ingestion_service type: {type(ingestion_service)}")
    logger.info(f"DEBUG: content length: {len(content)}")
    try:
        logger.info(f"DEBUG: Calling ingestion_service.ingest_document for doc {document_id}")
        await ingestion_service.ingest_document(
            document_id=document_id,
            content=content,
            metadata=metadata,
            generate_embeddings=True,
        )
        logger.info(f"DEBUG: Successfully processed document {document_id}")
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)

def create_core_business_router() -> APIRouter:
    """
    Factory function to create Epic 10 Core Business Operations router.
    Consolidates: documents + ingestion + search + query + Epic 7 sales automation
    CRITICAL: Epic 7 pipeline protection ($1.158M value)
    """
    router = APIRouter()

    # ===========================================
    # DOCUMENTS ENDPOINTS (Legacy Compatibility)
    # ===========================================
    @router.post(
        "/documents",
        response_model=schemas.CreateResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Add a single document",
        description="Adds a new document node to the graph.",
        tags=["Documents"]
    )
    async def add_document(
        doc_in: schemas.DocumentCreate,
        repo: Annotated[GraphRepository, Depends(_state_get_graph_repository)],
    ) -> schemas.CreateResponse:
        """Add a new document to the knowledge graph."""
        doc_id = str(uuid.uuid4()) if not doc_in.id else doc_in.id

        try:
            # Convert the Pydantic model to the domain model
            domain_doc = doc_in.to_domain()
            domain_doc.id = doc_id  # Ensure ID is set

            await repo.add_document(domain_doc)
            logger.info(f"Successfully added document with ID: {doc_id}")
            return schemas.CreateResponse(id=doc_id, message="Document added successfully")
        except Exception as e:
            logger.error(f"Error adding document: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to add document: {e}")

    @router.get(
        "/documents/{document_id}",
        response_model=schemas.DocumentResponse,
        summary="Get a specific document by ID",
        description="Retrieves a document from the graph by its unique identifier.",
        tags=["Documents"]
    )
    async def get_document(
        document_id: str,
        repo: Annotated[GraphRepository, Depends(_state_get_graph_repository)],
    ) -> schemas.DocumentResponse:
        """Retrieve a document by its ID."""
        try:
            document = await repo.get_document_by_id(document_id)
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            return schemas.DocumentResponse(
                id=document.id,
                content=document.content,
                metadata=document.metadata,
                created_at=document.created_at,
                updated_at=document.updated_at
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve document")

    # ===========================================
    # INGESTION ENDPOINTS (Legacy Compatibility)
    # ===========================================
    @router.post(
        "/ingestion/documents",
        response_model=IngestResponse,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Ingest a document",
        description="Process and ingest a document with metadata into the knowledge graph.",
        tags=["Ingestion"]
    )
    async def ingest_document(
        request: IngestRequest,
        background_tasks: BackgroundTasks,
        ingestion_service: Annotated[IngestionService, Depends(_state_get_ingestion_service)],
    ) -> IngestResponse:
        """Ingest a document for processing."""
        document_id = request.document_id or str(uuid.uuid4())

        try:
            # Add background task for document processing
            background_tasks.add_task(
                process_document_with_service,
                document_id,
                request.content,
                request.metadata,
                ingestion_service,
            )

            logger.info(f"Document {document_id} queued for processing")
            return IngestResponse(
                document_id=document_id,
                status="queued",
                message="Document queued for processing"
            )
        except Exception as e:
            logger.error(f"Failed to queue document for ingestion: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to queue document for ingestion")

    # ===========================================
    # SEARCH ENDPOINTS (Legacy Compatibility)
    # ===========================================
    @router.post(
        "/search",
        response_model=schemas.SearchQueryResponse,
        summary="Perform a search",
        description="Performs a search (vector or keyword) against the graph and returns relevant chunks.",
        tags=["Search"]
    )
    async def perform_search(
        request: schemas.SearchQueryRequest,
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    ) -> schemas.SearchQueryResponse:
        """Search for chunks based on the query and search type."""
        logger.info(f"Received search request: {request.model_dump()}")
        try:
            if request.search_type == "vector":
                # Call vector_store directly
                results_data: list[SearchResultData] = await vector_store.search(
                    request.query, top_k=request.limit
                )
                
                # Convert to schema format
                results = [
                    schemas.SearchResult(
                        chunk_id=result.chunk_id,
                        content=result.content,
                        score=result.score,
                        metadata=result.metadata,
                    )
                    for result in results_data
                ]
                
                return schemas.SearchQueryResponse(results=results, total=len(results))
            else:
                raise HTTPException(
                    status_code=501,
                    detail=f"Search type '{request.search_type}' not implemented"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Search operation failed")

    # ===========================================
    # QUERY ENDPOINTS (Legacy Compatibility)  
    # ===========================================
    @router.post(
        "/query",
        response_model=QueryResponse,
        summary="Submit a query to the GraphRAG engine",
        description="Process a query using the GraphRAG engine and return results.",
        tags=["Query"]
    )
    async def submit_query(
        request: QueryRequest,
        graph_rag_engine: Annotated[GraphRAGEngine, Depends(get_graph_rag_engine)],
    ) -> QueryResponse:
        """Submit a query to the GraphRAG engine."""
        try:
            logger.info(f"Processing query: {request.query[:100]}...")
            
            # Use the GraphRAG engine to process the query
            query_result: QueryResult = await graph_rag_engine.query(request.query)
            
            # Convert result chunks
            result_chunks = [
                QueryResultChunk(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    score=chunk.score,
                    metadata=chunk.metadata or {},
                )
                for chunk in query_result.chunks
            ]
            
            # Convert graph context
            graph_context = QueryResultGraphContext(
                entities=[],  # Simplified for consolidation
                relationships=[],  # Simplified for consolidation
            )
            
            return QueryResponse(
                answer=query_result.answer,
                chunks=result_chunks,
                graph_context=graph_context,
                metadata={"query_id": str(uuid.uuid4())},
            )
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Query processing failed")

    # =======================================================================
    # EPIC 7 SALES AUTOMATION ENDPOINTS (CRITICAL PIPELINE PROTECTION)
    # $1.158M Pipeline Value - ZERO Disruption Allowed
    # =======================================================================
    @router.get(
        "/sales/pipeline/summary", 
        response_model=PipelineSummaryResponse, 
        summary="Get Epic 7 sales pipeline summary",
        description="Retrieve comprehensive sales pipeline analytics and metrics",
        tags=["Epic 7 Sales Automation"]
    )
    async def get_pipeline_summary(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get comprehensive sales pipeline summary (PROTECTED)"""
        try:
            summary = engine.get_sales_pipeline_summary()
            return PipelineSummaryResponse(**summary)
        except Exception as e:
            logger.error(f"Failed to get pipeline summary: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve pipeline summary")

    @router.get(
        "/sales/contacts", 
        response_model=List[CRMContactResponse], 
        summary="List Epic 7 CRM contacts",
        description="Retrieve filtered list of CRM contacts from Epic 7 system",
        tags=["Epic 7 Sales Automation"]
    )
    async def list_contacts(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        priority_tier: Optional[str] = None,
        qualification_status: Optional[str] = None,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """List CRM contacts with filtering options (PROTECTED)"""
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

    @router.get(
        "/sales/contacts/{contact_id}", 
        response_model=CRMContactResponse, 
        summary="Get specific Epic 7 contact",
        description="Retrieve individual contact details from Epic 7 CRM system",
        tags=["Epic 7 Sales Automation"]
    )
    async def get_contact(
        contact_id: str,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get individual contact details (PROTECTED)"""
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

    @router.post(
        "/sales/proposals/generate", 
        response_model=ProposalResponse, 
        summary="Generate Epic 7 automated proposal",
        description="Generate automated proposal for contact using Epic 7 system",
        tags=["Epic 7 Sales Automation"]
    )
    async def generate_proposal(
        proposal_request: ProposalGenerationRequest,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Generate automated proposal for contact (PROTECTED)"""
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

    @router.get(
        "/sales/analytics/conversion-funnel", 
        summary="Get Epic 7 conversion funnel analytics",
        description="Retrieve sales conversion funnel analytics from Epic 7 system",
        tags=["Epic 7 Sales Automation"]
    )
    async def get_conversion_funnel(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get sales conversion funnel analytics (PROTECTED)"""
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

    @router.post(
        "/sales/import-inquiries", 
        summary="Import Epic 7 consultation inquiries",
        description="Import consultation inquiries from existing business development system",
        tags=["Epic 7 Sales Automation"]
    )
    async def import_consultation_inquiries(
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Import consultation inquiries from existing business development system (PROTECTED)"""
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

    return router

# Factory function for backward compatibility
def create_documents_router() -> APIRouter:
    """Legacy compatibility - redirects to core business router"""
    return create_core_business_router()

def create_ingestion_router(*args, **kwargs) -> APIRouter:
    """Legacy compatibility - redirects to core business router"""
    return create_core_business_router()

def create_search_router() -> APIRouter:
    """Legacy compatibility - redirects to core business router"""
    return create_core_business_router()

def create_query_router() -> APIRouter:
    """Legacy compatibility - redirects to core business router"""
    return create_core_business_router()

def create_epic7_sales_automation_router() -> APIRouter:
    """Legacy compatibility - redirects to core business router"""
    return create_core_business_router()