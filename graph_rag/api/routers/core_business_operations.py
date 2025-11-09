#!/usr/bin/env python3
"""
Epic 15 Phase 2: Core Business Operations Consolidated Router
Mission: Consolidate documents, ingestion, search, query + Epic 7 CRM integration
Business Protection: $1.158M consultation pipeline with 16 contacts

This router consolidates:
- Documents management (from documents.py)
- Document ingestion pipeline (from ingestion.py)
- Vector and graph search (from search.py)
- GraphRAG query processing (from query.py)
- Epic 7 Sales Automation CRM (from epic7_sales_automation.py)
"""

import inspect
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any

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
from pydantic import BaseModel

# Import all necessary schemas and dependencies
from graph_rag.api import schemas
from graph_rag.api.auth.dependencies import get_current_user_optional
from graph_rag.api.auth.models import User
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
    AskRequest,
    IngestRequest,
    IngestResponse,
    QueryResponse,
    QueryResultChunk,
    QueryResultGraphContext,
)
from graph_rag.core.graph_rag_engine import QueryResult
from graph_rag.core.graph_rag_engine import QueryResult as DomainQueryResult
from graph_rag.core.interfaces import GraphRAGEngine, GraphRepository, SearchResultData, VectorStore
from graph_rag.domain.models import Entity
from graph_rag.services.ingestion import IngestionService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Helper functions for ask endpoint
def _to_api_chunks(query_result: DomainQueryResult) -> list[QueryResultChunk]:
    """Convert domain QueryResult chunks to API QueryResultChunk models.

    Args:
        query_result: Domain query result containing relevant chunks

    Returns:
        List of API-compatible QueryResultChunk models
    """
    api_chunks: list[QueryResultChunk] = []
    for chunk in query_result.relevant_chunks:
        # Handle both chunk model types: domain.models.Chunk (has properties) and models.Chunk (has metadata)
        chunk_metadata = {}
        chunk_score = None

        # Try to get metadata/properties from chunk
        if hasattr(chunk, 'properties') and chunk.properties:
            chunk_metadata = chunk.properties
            chunk_score = chunk.properties.get("score")
        elif hasattr(chunk, 'metadata') and chunk.metadata:
            chunk_metadata = chunk.metadata
            chunk_score = chunk.metadata.get("score")

        # Get text content - handle both 'text' and 'content' attributes
        chunk_text = getattr(chunk, 'text', None) or getattr(chunk, 'content', '')

        api_chunks.append(
            QueryResultChunk(
                id=chunk.id,
                text=chunk_text,
                document_id=chunk.document_id,
                metadata=chunk_metadata,
                score=chunk_score,
            )
        )
    return api_chunks


def _to_api_graph_context(query_result: DomainQueryResult):
    """Convert domain graph context to API QueryResultGraphContext model.

    Args:
        query_result: Domain query result containing graph context

    Returns:
        API-compatible QueryResultGraphContext model or None if no graph context
    """
    if not query_result.graph_context:
        return None
    try:
        domain_entities, domain_relationships = query_result.graph_context
        return QueryResultGraphContext(
            entities=[e.model_dump() for e in domain_entities]
            if domain_entities
            else [],
            relationships=[r.model_dump() for r in domain_relationships]
            if domain_relationships
            else [],
        )
    except (TypeError, ValueError):
        return None


def _get_error_guidance(error: Exception) -> str:
    """Provide user-friendly error guidance based on exception type."""
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Check for common error patterns
    if "chunk" in error_str and ("properties" in error_str or "metadata" in error_str):
        return "There's a data model mismatch. The system is trying to access chunk properties that don't exist."

    elif "connection" in error_str or "timeout" in error_str:
        return "There's a connectivity issue with the underlying services (database or LLM)."

    elif "memory" in error_str or "out of memory" in error_str:
        return "The system is running out of memory. Try reducing query complexity or chunk size."

    elif "llm" in error_str or "language model" in error_str:
        return "There's an issue with the language model service. Check LLM configuration and connectivity."

    elif error_type == "AttributeError":
        return "A required attribute or method is missing. This may indicate a configuration or version mismatch."

    elif error_type == "ValueError":
        return "Invalid input value provided. Check the request parameters and data format."

    elif error_type == "TypeError":
        return "Data type mismatch detected. This may indicate an internal data processing issue."

    elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
        return "A required module or dependency is missing or not properly installed."

    else:
        return "An unexpected error occurred. Check the system logs for more details."


def _get_recovery_suggestions(error: Exception) -> list[str]:
    """Provide specific recovery suggestions based on the error."""
    error_str = str(error).lower()
    error_type = type(error).__name__
    suggestions = []

    # Check for common error patterns and provide suggestions
    if "chunk" in error_str and ("properties" in error_str or "metadata" in error_str):
        suggestions.extend([
            "Restart the API server to ensure latest data models are loaded",
            "Check if recent data was ingested with incompatible chunk formats",
            "Clear the vector store and re-ingest documents if the issue persists"
        ])

    elif "connection" in error_str or "timeout" in error_str:
        suggestions.extend([
            "Check if Memgraph is running: 'docker ps' or 'synapse up'",
            "Verify network connectivity to external services",
            "Check service logs for more detailed error information",
            "Try again in a few moments as this may be a temporary issue"
        ])

    elif "rate limit" in error_str:
        suggestions.extend([
            "Wait a few minutes before making additional requests",
            "Reduce the frequency of your requests",
            "Contact support if you need higher rate limits"
        ])

    elif "api key" in error_str or "unauthorized" in error_str:
        suggestions.extend([
            "Check environment variables for API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)",
            "Verify API key permissions and quotas",
            "Ensure you're using the correct API endpoint"
        ])

    elif "not found" in error_str:
        suggestions.extend([
            "Ingest some documents first using the /api/v1/ingestion/documents endpoint",
            "Check if the requested resource ID is correct",
            "Verify that the data was successfully stored"
        ])

    elif "vector store" in error_str or "embedding" in error_str:
        suggestions.extend([
            "Check if the embedding service is properly configured",
            "Verify that the vector store path is accessible and writable",
            "Try switching to a different vector store type (simple/faiss)"
        ])

    elif "graph" in error_str or "memgraph" in error_str:
        suggestions.extend([
            "Start Memgraph: 'make up' or 'docker run -p 7687:7687 memgraph/memgraph'",
            "Check Memgraph connection settings in environment variables",
            "Switch to vector-only mode if graph features aren't required"
        ])

    elif "llm" in error_str:
        suggestions.extend([
            "Check LLM service configuration and API keys",
            "Try switching to mock LLM service for testing",
            "Verify internet connectivity for external LLM services"
        ])

    elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
        suggestions.extend([
            "Install missing dependencies: 'pip install -e .'",
            "Check if optional dependencies are needed for your configuration",
            "Verify Python environment and virtual environment setup"
        ])

    else:
        suggestions.extend([
            "Check system logs for more detailed error information",
            "Try with a simpler query to isolate the issue",
            "Restart the API server if the problem persists",
            "Contact support with the error details if issues continue"
        ])

    return suggestions

# Epic 7 CRM Models
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
    inquiry_type: str | None = None
    custom_requirements: str | None = None

class ProposalResponse(BaseModel):
    """Proposal API response model"""
    proposal_id: str
    contact_name: str
    company: str
    template_used: str
    proposal_value: int
    estimated_close_probability: float
    roi_analysis: dict
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
    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None

class LeadScoringResponse(BaseModel):
    """Lead scoring analysis response"""
    contact_id: str
    current_score: int
    previous_score: int | None = None
    scoring_factors: dict
    score_change: int
    recommendations: list[str]

# Define a factory function type for dependencies
DependencyFactory = Callable[[], Any]

# Lazy wrappers to avoid circular import with app factory
def _state_get_graph_repository(request: Request) -> "GraphRepository":
    from graph_rag.api.main import get_graph_repository as _getter
    return _getter(request)

def _state_get_vector_store(request: Request) -> "VectorStore":
    from graph_rag.api.main import get_vector_store as _getter
    return _getter(request)

def _state_get_ingestion_service(request: Request):
    from graph_rag.api.main import get_ingestion_service as _getter
    return _getter(request)

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
        ) from e

async def process_document_with_service(
    document_id: str,
    content: str,
    metadata: dict,
    ingestion_service: IngestionService,
    generate_embeddings: bool = True,
    replace_existing: bool = True,
):
    """Background task to process a document using the IngestionService."""
    logger.info(f"DEBUG: process_document_with_service called for doc {document_id}")
    logger.info(f"DEBUG: ingestion_service type: {type(ingestion_service)}")
    logger.info(f"DEBUG: content length: {len(content)}")
    try:
        logger.info(
            f"DEBUG: Calling ingestion_service.ingest_document for doc {document_id}"
        )
        await ingestion_service.ingest_document(
            document_id=document_id,
            content=content,
            metadata=metadata,
            generate_embeddings=generate_embeddings,
            replace_existing=replace_existing,
        )
        logger.info(f"DEBUG: Document {document_id} processed successfully.")
    except Exception as e:
        logger.error(
            f"DEBUG: Processing failed for document {document_id}: {e}", exc_info=True
        )
        raise

def create_core_business_operations_router() -> APIRouter:
    """Factory function to create the consolidated core business operations router."""
    router = APIRouter()

    # ===============================
    # DOCUMENT MANAGEMENT ENDPOINTS
    # ===============================

    @router.post(
        "/documents",
        response_model=schemas.CreateResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Add a single document",
        description="Adds a new document node to the graph.",
        tags=["Document Management"]
    )
    async def add_document(
        doc_in: schemas.DocumentCreate,
        repo: Annotated[GraphRepository, Depends(_state_get_graph_repository)],
    ):
        """Creates a new document entity in the graph. Uses provided ID if available, otherwise generates one."""
        try:
            # Use provided ID or generate a new one
            document_id = doc_in.id if doc_in.id else str(uuid.uuid4())

            # Ensure metadata is a dict, even if None was provided
            doc_metadata = doc_in.metadata or {}

            document_entity = Entity(
                id=document_id, type="Document", properties=doc_metadata
            )
            await repo.add_entity(document_entity)
            logger.info(f"Document added with ID: {document_id}")
            return schemas.CreateResponse(id=document_id)
        except Exception as e:
            logger.error(f"Error adding document: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add document",
            ) from e

    @router.get(
        "/documents",
        response_model=list[schemas.DocumentResponse],
        summary="List all documents",
        description="Retrieves all document nodes from the graph. Warning: potentially large response.",
        tags=["Document Management"]
    )
    async def list_all_documents(
        repo: Annotated[GraphRepository, Depends(_state_get_graph_repository)],
        limit: int | None = Query(
            100, description="Limit the number of documents returned", ge=1, le=1000
        ),
    ):
        """Fetches all documents, potentially limited."""
        try:
            doc_entities = await repo.search_entities_by_properties(
                {"type": "Document"}, limit=limit
            )
            responses: list[schemas.DocumentResponse] = []
            for entity in doc_entities:
                meta = dict(entity.properties.get("metadata") or {})
                if "id_source" in entity.properties and "id_source" not in meta:
                    meta["id_source"] = entity.properties["id_source"]
                responses.append(
                    schemas.DocumentResponse(
                        id=entity.id,
                        metadata=meta,
                        type=entity.type,
                        created_at=entity.properties.get("created_at"),
                        updated_at=entity.properties.get("updated_at"),
                    )
                )
            return responses
        except Exception as e:
            logger.error(f"Error listing documents: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents",
            ) from e

    @router.get(
        "/documents/{document_id}",
        response_model=schemas.DocumentResponse,
        summary="Get document by ID",
        responses={
            404: {"model": schemas.ErrorDetail, "description": "Document not found"},
            500: {"model": schemas.ErrorDetail},
        },
        tags=["Document Management"]
    )
    async def get_document(
        document_id: str,
        repo: Annotated[GraphRepository, Depends(_state_get_graph_repository)],
    ):
        """Retrieve a specific document by its unique ID."""
        doc_entity = await repo.get_entity_by_id(document_id)
        if not doc_entity or doc_entity.type != "Document":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id '{document_id}' not found",
            )
        # Map properties to metadata in the response
        meta = dict(doc_entity.properties.get("metadata") or {})
        if "id_source" in doc_entity.properties and "id_source" not in meta:
            meta["id_source"] = doc_entity.properties["id_source"]
        return schemas.DocumentResponse(
            id=doc_entity.id,
            metadata=meta,
            type=doc_entity.type,
            created_at=doc_entity.properties.get("created_at"),
            updated_at=doc_entity.properties.get("updated_at"),
        )

    @router.delete(
        "/documents/{document_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Delete Document and Associated Chunks",
        tags=["Document Management"]
    )
    async def delete_document(
        document_id: str,
        repo: Annotated[GraphRepository, Depends(_state_get_graph_repository)],
        vector_store: Annotated[VectorStore, Depends(_state_get_vector_store)],
        response: Response,
    ):
        """Delete a document and all chunks directly associated with it from both the graph and vector store."""
        logger.info(f"--- ENTERING delete_document HANDLER for doc_id: {document_id} ---")
        logger.info(f"Attempting to delete document {document_id} and its chunks.")
        try:
            # First, get all chunks belonging to this document
            try:
                chunks = await repo.get_chunks_by_document_id(document_id)
                chunk_ids = [chunk.id for chunk in chunks]
                logger.info(
                    f"Found {len(chunk_ids)} chunks to delete from vector store for document {document_id}"
                )

                # Remove chunks from vector store
                if chunk_ids:
                    try:
                        await vector_store.delete_chunks(chunk_ids)
                        logger.info(f"Deleted {len(chunk_ids)} chunks from vector store")
                    except Exception as vs_e:
                        logger.warning(
                            f"Failed to delete chunks from vector store: {vs_e}. Continuing with graph deletion."
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve chunks for document {document_id}: {e}. Continuing with document deletion."
                )

            # Then delete the document (and its chunks) from the graph
            deleted = await repo.delete_document(document_id)
            if not deleted:
                logger.warning(f"Document {document_id} not found for deletion.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with id {document_id} not found or could not be deleted.",
                )

            logger.info(f"Successfully deleted document {document_id}")
            return

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"API Error: Failed to delete document {document_id}. Error: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document {document_id}. Check logs for details.",
            ) from e

    @router.patch(
        "/documents/{document_id}/metadata",
        response_model=schemas.DocumentResponse,
        summary="Update document metadata",
        description="Updates the metadata properties of an existing document node.",
        responses={
            404: {"model": schemas.ErrorDetail, "description": "Document not found"},
            500: {"model": schemas.ErrorDetail},
        },
        tags=["Document Management"]
    )
    async def update_document_metadata(
        document_id: str,
        metadata_update: schemas.DocumentMetadataUpdate,
        graph_repo: Annotated[GraphRepository, Depends(_state_get_graph_repository)],
    ):
        try:
            existing_entity = await graph_repo.get_entity_by_id(document_id)
            if not existing_entity or existing_entity.type != "Document":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with id '{document_id}' not found",
                )
            updated_properties = existing_entity.properties.copy()
            update_data = metadata_update.model_dump(exclude_unset=True).get(
                "properties", {}
            )
            updated_properties.update(update_data)
            updated_entity = Entity(
                id=document_id, type="Document", properties=updated_properties
            )
            await graph_repo.add_entity(updated_entity)
            logger.info(f"Updated metadata for document {document_id}")
            # Return the merged/updated entity directly (do not re-fetch)
            return schemas.DocumentResponse(
                id=updated_entity.id,
                metadata=updated_entity.properties,
                type=updated_entity.type,
                created_at=getattr(updated_entity, "created_at", None),
                updated_at=getattr(updated_entity, "updated_at", None),
            )
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(
                f"Error updating metadata for document {document_id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update document metadata",
            ) from e

    # ===============================
    # DOCUMENT INGESTION ENDPOINTS
    # ===============================

    @router.post(
        "/ingestion/documents",
        response_model=IngestResponse,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Ingest a Single Document",
        description="Accepts text content and metadata, processes it, extracts entities/relationships, and adds them to the knowledge graph.",
        tags=["Document Ingestion"]
    )
    async def ingest_document(
        background_tasks: BackgroundTasks,
        payload: IngestRequest = Body(...),
        ingestion_service: IngestionService = Depends(_state_get_ingestion_service),
    ):
        """Asynchronous endpoint to ingest a document."""
        request_id = str(uuid.uuid4())
        logger.info(f"[Req ID: {request_id}] Received ingestion request.")

        # Input Validation
        if not payload.content or payload.content.isspace():
            logger.warning(
                f"[Req ID: {request_id}] Ingestion request rejected: Content is empty or whitespace."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document content cannot be empty or whitespace.",
            )

        # Create document with explicit ID
        doc_id = payload.document_id or f"doc-{uuid.uuid4()}"
        logger.debug(f"[Req ID: {request_id}] Using document ID: {doc_id}")

        # Always schedule background task
        logger.info(
            f"[Req ID: {request_id}] Scheduling background ingestion task for document {doc_id}."
        )
        background_tasks.add_task(
            process_document_with_service,
            document_id=doc_id,
            content=payload.content,
            metadata=payload.metadata or {},
            ingestion_service=ingestion_service,
            generate_embeddings=payload.generate_embeddings,
            replace_existing=payload.replace_existing,
        )

        return IngestResponse(
            message="Document ingestion accepted for background processing.",
            document_id=doc_id,
            task_id=request_id,
            status="processing",
        )

    # ===============================
    # SEARCH & RETRIEVAL ENDPOINTS
    # ===============================

    @router.post(
        "/search",
        response_model=schemas.SearchQueryResponse,
        summary="Perform a search",
        description="Performs a search (vector or keyword) against the graph and returns relevant chunks.",
        responses={
            status.HTTP_501_NOT_IMPLEMENTED: {"model": schemas.ErrorDetail},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": schemas.ErrorDetail},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": schemas.ErrorDetail},
        },
        tags=["Search & Retrieval"]
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

                # Adapt SearchResultData to schemas.SearchResultSchema
                results = [
                    schemas.SearchResultSchema(
                        chunk=schemas.ChunkResultSchema(
                            id=data.chunk.id,
                            text=data.chunk.text,
                            document_id=data.chunk.document_id,
                            metadata=data.chunk.metadata or {},
                        ),
                        score=data.score,
                        document=None,  # Document info not readily available here
                    )
                    for data in results_data
                ]
            elif request.search_type == "keyword":
                logger.warning(
                    f"Keyword search not implemented yet for query: {request.query}"
                )
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Keyword search is not yet implemented.",
                )
            else:
                logger.error(f"Unsupported search type: {request.search_type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported search type: {request.search_type}",
                )

            logger.info(
                f"Search for '{request.query}' ({request.search_type}) returned {len(results)} results."
            )
            return schemas.SearchQueryResponse(
                query=request.query, search_type=request.search_type, results=results
            )

        except HTTPException as http_exc:
            raise http_exc
        except NotImplementedError:
            logger.warning(
                f"Search type '{request.search_type}' requested but not implemented."
            )
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Search type '{request.search_type}' is not implemented.",
            ) from None
        except Exception as e:
            logger.error(
                f"Error during search for query '{request.query}': {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during search.",
            ) from e

    @router.post(
        "/search/query",
        response_model=schemas.SearchQueryResponse,
        summary="Unified Context Retrieval Query",
        description="Retrieves relevant context chunks using vector or keyword search based on the specified `search_type`. Can return results as a batch or a stream.",
        tags=["Search & Retrieval"]
    )
    async def unified_search(
        request: schemas.SearchQueryRequest,
        engine: Annotated[GraphRAGEngine, Depends(get_graph_rag_engine)],
        graph_store=Depends(get_graph_repository),
        stream: bool = Query(False, description="Whether to stream results as NDJSON"),
    ):
        """Performs context retrieval using the GraphRAGEngine, supporting batch and streaming."""
        logger.info(
            f"Received search request: query='{request.query}', type='{request.search_type}', limit={request.limit}, stream={stream}"
        )

        try:
            if stream:
                # Keyword streaming behind feature flag
                if request.search_type == "keyword":
                    try:
                        from graph_rag.config import get_settings
                        settings = get_settings()
                        if not getattr(settings, "enable_keyword_streaming", False):
                            raise HTTPException(
                                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                                detail="Streaming is only implemented for vector searches."
                            )
                    except HTTPException:
                        raise
                    except Exception as settings_err:
                        # If settings cannot be loaded, default to disabled
                        raise HTTPException(
                            status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="Streaming is only implemented for vector searches."
                        ) from settings_err

                # Set up streaming response
                async def stream_search_results():
                    try:
                        result_iter = engine.stream_context(
                            request.query, request.search_type, request.limit
                        )
                        if inspect.iscoroutine(result_iter):
                            result_iter = await result_iter
                        async for item in result_iter:
                            score_val = 0.0
                            chunk_obj = item
                            # If SearchResultData-like
                            if hasattr(item, "chunk") and hasattr(item, "score"):
                                chunk_obj = item.chunk
                                score_val = float(getattr(item, "score", 0.0))
                            else:
                                # If ChunkData-like with optional score attr
                                score_val = float(getattr(item, "score", 0.0))

                            # Convert chunk to API schema
                            chunk_schema = schemas.ChunkResultSchema(
                                id=chunk_obj.id,
                                text=chunk_obj.text,
                                document_id=chunk_obj.document_id,
                            )

                            # Create search result
                            result = schemas.SearchResultSchema(
                                chunk=chunk_schema,
                                score=score_val,
                                document=None,  # Omit document for streaming responses
                            ).model_dump()

                            # Yield as JSON lines
                            yield json.dumps(result) + "\n"
                    except Exception as e:
                        logger.error(f"Error in streaming response: {e}", exc_info=True)
                        yield json.dumps({"error": str(e)}) + "\n"

                return StreamingResponse(
                    stream_search_results(), media_type="application/x-ndjson"
                )

            else:  # Batch processing
                import time as _time
                _start = _time.monotonic()
                # Call engine.query with positional query text and config
                query_result: QueryResult = await engine.query(
                    request.query,
                    config={
                        "k": request.limit,
                        "search_type": request.search_type,
                        "include_graph": False,
                    },
                )
                try:
                    observe_query_latency(_time.monotonic() - _start)
                except Exception:
                    pass

                # Directly map domain Chunk objects to API schema objects
                response_results = []
                for chunk in query_result.relevant_chunks:
                    # Create ChunkResultSchema directly from Chunk properties
                    chunk_schema = schemas.ChunkResultSchema(
                        id=chunk.id, text=chunk.text, document_id=chunk.document_id
                    )

                    # Create SearchResultSchema with proper document information
                    try:
                        document = await graph_store.get_document_by_id(
                            chunk.document_id
                        )
                        doc_schema = (
                            schemas.DocumentResultSchema(
                                id=document.id, metadata=document.metadata
                            )
                            if document
                            else None
                        )
                        logger.info(
                            f"DEBUG: Document ID {chunk.document_id} -> Fetched document: {document}"
                        )
                        logger.info(
                            f"DEBUG: Document ID {chunk.document_id} -> Created doc_schema: {doc_schema}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to get document {chunk.document_id}: {e}"
                        )
                        doc_schema = None

                    search_result = schemas.SearchResultSchema(
                        chunk=chunk_schema,
                        score=chunk.score if hasattr(chunk, "score") else 0.0,
                        document=doc_schema,
                    )
                    response_results.append(search_result)

                logger.info(
                    f"Search for '{request.query}' ({request.search_type}) returned {len(response_results)} results."
                )
                return schemas.SearchQueryResponse(
                    query=request.query,
                    search_type=request.search_type,
                    results=response_results,
                    llm_response=query_result.llm_response,
                    graph_context=query_result.graph_context
                    if isinstance(query_result.graph_context, str)
                    else "",
                )

        except ValueError as ve:
            logger.warning(f"Search validation error for query '{request.query}': {ve}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)) from ve
        except HTTPException as http_exc:
            raise http_exc
        except RuntimeError as re:
            logger.error(
                f"Runtime error during search for query '{request.query}': {re}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Search backend error: {re}",
            ) from re
        except Exception as e:
            logger.error(
                f"API Error: Unified search failed for query '{request.query}'. Error: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Search failed due to an internal server error.",
            ) from e

    @router.post(
        "/search/batch",
        response_model=list[schemas.SearchQueryResponse],
        summary="Batch Search Processing",
        description="Process multiple search queries in a single request.",
        tags=["Search & Retrieval"]
    )
    async def batch_search(
        request: schemas.SearchBatchQueryRequest,
        engine: Annotated[GraphRAGEngine, Depends(get_graph_rag_engine)],
        response: Response,
        graph_store=Depends(get_graph_repository),
    ) -> list[schemas.SearchQueryResponse]:
        """Process multiple search queries in a single batch request."""
        logger.info(
            f"Received batch search request with {len(request.queries)} queries"
        )

        results = []
        any_failed = False
        for query_request in request.queries:
            status_code = status.HTTP_200_OK
            error_detail = None
            query_response = None
            try:
                # Use the engine's query method for each query in the batch
                query_result: QueryResult = await engine.query(
                    query_text=query_request.query,
                    config={
                        "k": query_request.limit,
                        "search_type": query_request.search_type,
                        "include_graph": False,  # Default for batch endpoint
                    },
                )

                # Transform the query results into the expected response format
                response_results = []
                for chunk in query_result.relevant_chunks:
                    # Create schema objects from chunk data
                    chunk_schema = schemas.ChunkResultSchema(
                        id=chunk.id, text=chunk.text, document_id=chunk.document_id
                    )

                    # Create search result with score from the chunk
                    search_result = schemas.SearchResultSchema(
                        chunk=chunk_schema,
                        score=chunk.score if hasattr(chunk, "score") else 0.0,
                        document=None,  # Document details not included in batch responses
                    )
                    response_results.append(search_result)

                # Create the response for this query
                query_response = schemas.SearchQueryResponse(
                    query=query_request.query,
                    search_type=query_request.search_type,
                    results=response_results,
                    llm_response=query_result.llm_response,
                    graph_context=query_result.graph_context
                    if isinstance(query_result.graph_context, str)
                    else "",
                )

            except Exception as e:
                logger.error(
                    f"Error processing query '{query_request.query}': {e}",
                    exc_info=True,
                )
                # Add a failed response for this query and mark partial failure
                any_failed = True
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                error_detail = schemas.ErrorDetail(
                    message=str(e), type=type(e).__name__
                )
                # Create a failed response object
                query_response = schemas.SearchQueryResponse(
                    query=query_request.query,
                    search_type=query_request.search_type,
                    results=[],
                    llm_response="",
                    graph_context="",
                )

            # Add status_code and error to the response object
            if query_response:
                query_response.status_code = status_code
                query_response.error = error_detail
                results.append(query_response)
            else:
                # Handle unexpected case where query_response is None
                logger.error(
                    f"Unexpected error: query_response is None for query '{query_request.query}'"
                )
                results.append(
                    schemas.SearchQueryResponse(
                        query=query_request.query,
                        search_type=query_request.search_type,
                        results=[],
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        error=schemas.ErrorDetail(
                            message="Internal server error: Failed to generate response."
                        ),
                    )
                )
                any_failed = True

        logger.info(f"Batch search completed with {len(results)} results")
        # If any query failed, use 207 Multi-Status
        if any_failed:
            response.status_code = status.HTTP_207_MULTI_STATUS
        return results

    # ===============================
    # EPIC 7 CRM ENDPOINTS
    # Business Critical: $1.158M Pipeline Protection
    # ===============================

    @router.get("/crm/pipeline/summary", response_model=PipelineSummaryResponse, tags=["Sales Pipeline"])
    async def get_pipeline_summary(
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get comprehensive sales pipeline summary"""
        try:
            summary = engine.get_sales_pipeline_summary()
            return PipelineSummaryResponse(**summary)
        except Exception as e:
            logger.error(f"Failed to get pipeline summary: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve pipeline summary") from e

    @router.get("/crm/contacts", response_model=list[CRMContactResponse], tags=["CRM"])
    async def list_contacts(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        priority_tier: str | None = None,
        qualification_status: str | None = None,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """List CRM contacts with filtering options"""
        try:
            # Use CRM service layer via engine
            contacts = engine.list_contacts(
                skip=skip,
                limit=limit,
                priority_tier=priority_tier,
                qualification_status=qualification_status
            )

            # Convert to API response models
            contact_list = []
            for contact in contacts:
                contact_list.append(CRMContactResponse(
                    contact_id=str(contact.contact_id),
                    name=contact.name,
                    company=contact.company or "",
                    company_size=contact.company_size or "",
                    title=contact.title or "",
                    email=contact.email,
                    linkedin_profile=contact.linkedin_profile or "",
                    phone=contact.phone or "",
                    lead_score=contact.lead_score,
                    qualification_status=contact.qualification_status,
                    estimated_value=int(contact.estimated_value),
                    priority_tier=contact.priority_tier,
                    next_action=contact.next_action or "",
                    next_action_date=contact.next_action_date.isoformat() if contact.next_action_date else "",
                    created_at=contact.created_at.isoformat(),
                    updated_at=contact.updated_at.isoformat(),
                    notes=contact.notes or ""
                ))

            return contact_list

        except Exception as e:
            logger.error(f"Failed to list contacts: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve contacts") from e

    @router.get("/crm/contacts/{contact_id}", response_model=CRMContactResponse, tags=["CRM"])
    async def get_contact(
        contact_id: str,
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get individual contact details"""
        try:
            # Use CRM service layer via engine
            contact = engine.get_contact(contact_id)

            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")

            # Convert to API response model
            return CRMContactResponse(
                contact_id=str(contact.contact_id),
                name=contact.name,
                company=contact.company or "",
                company_size=contact.company_size or "",
                title=contact.title or "",
                email=contact.email,
                linkedin_profile=contact.linkedin_profile or "",
                phone=contact.phone or "",
                lead_score=contact.lead_score,
                qualification_status=contact.qualification_status,
                estimated_value=int(contact.estimated_value),
                priority_tier=contact.priority_tier,
                next_action=contact.next_action or "",
                next_action_date=contact.next_action_date.isoformat() if contact.next_action_date else "",
                created_at=contact.created_at.isoformat(),
                updated_at=contact.updated_at.isoformat(),
                notes=contact.notes or ""
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get contact {contact_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve contact") from e

    @router.put("/crm/contacts/{contact_id}", response_model=CRMContactResponse, tags=["CRM"])
    async def update_contact(
        contact_id: str,
        contact_update: ContactUpdateRequest,
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Update contact information"""
        try:
            # Build update dictionary from request
            update_data = contact_update.dict(exclude_unset=True)

            if update_data:
                # Use CRM service layer via engine
                updated_contact = engine.update_contact(contact_id, **update_data)

                if not updated_contact:
                    raise HTTPException(status_code=404, detail="Contact not found")

                # Convert to API response model
                return CRMContactResponse(
                    contact_id=str(updated_contact.contact_id),
                    name=updated_contact.name,
                    company=updated_contact.company or "",
                    company_size=updated_contact.company_size or "",
                    title=updated_contact.title or "",
                    email=updated_contact.email,
                    linkedin_profile=updated_contact.linkedin_profile or "",
                    phone=updated_contact.phone or "",
                    lead_score=updated_contact.lead_score,
                    qualification_status=updated_contact.qualification_status,
                    estimated_value=int(updated_contact.estimated_value),
                    priority_tier=updated_contact.priority_tier,
                    next_action=updated_contact.next_action or "",
                    next_action_date=updated_contact.next_action_date.isoformat() if updated_contact.next_action_date else "",
                    created_at=updated_contact.created_at.isoformat(),
                    updated_at=updated_contact.updated_at.isoformat(),
                    notes=updated_contact.notes or ""
                )
            else:
                # No updates provided, just return existing contact
                contact = engine.get_contact(contact_id)
                if not contact:
                    raise HTTPException(status_code=404, detail="Contact not found")

                return CRMContactResponse(
                    contact_id=str(contact.contact_id),
                    name=contact.name,
                    company=contact.company or "",
                    company_size=contact.company_size or "",
                    title=contact.title or "",
                    email=contact.email,
                    linkedin_profile=contact.linkedin_profile or "",
                    phone=contact.phone or "",
                    lead_score=contact.lead_score,
                    qualification_status=contact.qualification_status,
                    estimated_value=int(contact.estimated_value),
                    priority_tier=contact.priority_tier,
                    next_action=contact.next_action or "",
                    next_action_date=contact.next_action_date.isoformat() if contact.next_action_date else "",
                    created_at=contact.created_at.isoformat(),
                    updated_at=contact.updated_at.isoformat(),
                    notes=contact.notes or ""
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update contact {contact_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update contact") from e

    @router.post("/crm/proposals/generate", response_model=ProposalResponse, tags=["Proposals"])
    async def generate_proposal(
        proposal_request: ProposalGenerationRequest,
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Generate automated proposal for contact"""
        try:
            # Use engine's proposal generation method
            proposal = engine.generate_automated_proposal(
                contact_id=proposal_request.contact_id,
                inquiry_type=proposal_request.inquiry_type
            )

            if 'error' in proposal:
                raise HTTPException(status_code=404, detail=proposal['error'])

            # Proposal generation should return all necessary data
            # The engine method already handles both contact and proposal data
            return ProposalResponse(
                proposal_id=proposal['proposal_id'],
                contact_name=proposal['content']['client_name'],
                company=proposal['content']['company_name'],
                template_used=proposal['content']['template_title'],
                proposal_value=proposal['content']['investment_proposal']['recommended']['price'],
                estimated_close_probability=proposal['content']['close_probability'],
                roi_analysis=proposal['content']['roi_analysis'],
                status='draft',
                generated_at=datetime.now().isoformat()
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate proposal: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate proposal") from e

    @router.get("/crm/proposals", response_model=list[ProposalResponse], tags=["Proposals"])
    async def list_proposals(
        request: Request,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """List generated proposals with filtering options"""
        try:
            # Use CRM service layer via engine
            proposals = engine.list_proposals(
                skip=skip,
                limit=limit,
                status=status
            )

            proposal_list = []
            for proposal in proposals:
                proposal_list.append(ProposalResponse(
                    proposal_id=str(proposal.proposal_id),
                    contact_name=proposal.contact.name,
                    company=proposal.contact.company or "",
                    template_used=proposal.template_used,
                    proposal_value=int(proposal.proposal_value),
                    estimated_close_probability=float(proposal.estimated_close_probability),
                    roi_analysis=proposal.roi_calculation or {},
                    status=proposal.status,
                    generated_at=proposal.generated_at.isoformat()
                ))

            return proposal_list

        except Exception as e:
            logger.error(f"Failed to list proposals: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve proposals") from e

    @router.post("/crm/proposals/{proposal_id}/send", tags=["Proposals"])
    async def send_proposal(
        proposal_id: str,
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Mark proposal as sent"""
        try:
            # Use CRM service layer via engine
            success = engine.send_proposal(proposal_id)

            if not success:
                raise HTTPException(status_code=404, detail="Proposal not found")

            return {"success": True, "message": "Proposal marked as sent"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send proposal {proposal_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to send proposal") from e

    @router.post("/crm/import-inquiries", tags=["Data Import"])
    async def import_consultation_inquiries(
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
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
            raise HTTPException(status_code=500, detail="Failed to import consultation inquiries") from e

    @router.get("/crm/lead-scoring/{contact_id}", response_model=LeadScoringResponse, tags=["Lead Scoring"])
    async def get_lead_scoring(
        contact_id: str,
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get lead scoring analysis for contact"""
        try:
            # Use CRM service layer via engine
            lead_scoring = engine.get_lead_scoring_analysis(contact_id)

            if not lead_scoring:
                raise HTTPException(status_code=404, detail="Contact not found")

            return LeadScoringResponse(**lead_scoring)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get lead scoring for {contact_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve lead scoring") from e

    @router.get("/crm/analytics/conversion-funnel", tags=["Analytics"])
    async def get_conversion_funnel(
        request: Request,
        current_user: User | None = Depends(get_current_user_optional),
        engine = Depends(get_sales_automation_engine)
    ):
        """Get sales conversion funnel analytics"""
        try:
            # Use CRM service layer via engine
            funnel_analytics = engine.get_conversion_funnel_analytics()

            return funnel_analytics

        except Exception as e:
            logger.error(f"Failed to get conversion funnel: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve conversion funnel analytics") from e

    @router.post(
        "/ask",
        response_model=QueryResponse,
        summary="Ask a question and get a synthesized answer",
        description="Retrieves context (optionally with graph) and synthesizes an answer using the configured LLM.",
        tags=["Query & Ask"]
    )
    async def ask(
        ask_request: AskRequest,
        engine: Annotated[GraphRAGEngine, Depends(get_graph_rag_engine)],
        request: Request = None,
    ):
        logger.info(
            f"Received ask: {ask_request.text[:100]}... (k={ask_request.k}, graph={ask_request.include_graph})"
        )
        # Increment ask counter if app metrics are configured
        # no-op placeholder removed (was creating an unused variable)
        try:
            config = {
                "k": ask_request.k,
                "include_graph": ask_request.include_graph,
                "search_type": ask_request.search_type,
                "blend_vector_weight": ask_request.blend_vector_weight,
                "blend_keyword_weight": ask_request.blend_keyword_weight,
                "rerank": ask_request.rerank,
                "mmr_lambda": ask_request.mmr_lambda,
                "no_answer_min_score": ask_request.no_answer_min_score,
                "style": ask_request.style,
                "conversation_id": ask_request.conversation_id,
                # Relationship extraction controls
                "extract_relationships": True,
                "extract_relationships_persist": ask_request.extract_relationships_persist,
                "extract_relationships_dry_run": ask_request.extract_relationships_dry_run,
            }
            result: DomainQueryResult = await engine.query(
                ask_request.text, config=config
            )
            # Increment LLM relationship counters if present in config (best effort)
            try:
                inferred = int(config.get("llm_relations_inferred_total", 0))
                persisted = int(config.get("llm_relations_persisted_total", 0))
                inc_llm_rel_inferred(inferred)
                inc_llm_rel_persisted(persisted)
            except Exception:
                pass

            # Include citations in metadata
            try:
                citations = [
                    {"chunk_id": c.id, "document_id": getattr(c, 'document_id', None)}
                    for c in result.relevant_chunks
                    if hasattr(c, 'id')
                ]
            except Exception:
                citations = []
            meta_with_citations = dict(result.metadata or {})
            if citations:
                meta_with_citations.setdefault("citations", citations)

            return QueryResponse(
                answer=result.answer,
                relevant_chunks=_to_api_chunks(result),
                graph_context=_to_api_graph_context(result),
                metadata=meta_with_citations,
                answer_with_citations=getattr(result, "answer_with_citations", None),
                citations=(getattr(result, "citations", None) or []),
                bibliography=(getattr(result, "bibliography", None) or {}),
            )
        except Exception as e:
            logger.error(
                f"Error processing ask '{ask_request.text}': {e}", exc_info=True
            )

            # Provide specific error guidance based on error type
            error_guidance = _get_error_guidance(e)
            error_detail = {
                "error": str(e),
                "type": type(e).__name__,
                "guidance": error_guidance,
                "suggestions": _get_recovery_suggestions(e)
            }

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail,
            ) from e

    return router


# Factory function for use in main.py
def create_core_business_operations_router_factory() -> APIRouter:
    """Create and configure the Core Business Operations consolidated router"""
    return create_core_business_operations_router()


# Helper functions for ask endpoint
def _to_api_chunks(query_result: DomainQueryResult) -> list[QueryResultChunk]:
    """Convert domain QueryResult chunks to API QueryResultChunk models.

    Args:
        query_result: Domain query result containing relevant chunks

    Returns:
        List of API-compatible QueryResultChunk models
    """
    api_chunks: list[QueryResultChunk] = []
    for chunk in query_result.relevant_chunks:
        # Handle both chunk model types: domain.models.Chunk (has properties) and models.Chunk (has metadata)
        chunk_metadata = {}
        chunk_score = None

        # Try to get metadata/properties from chunk
        if hasattr(chunk, 'properties') and chunk.properties:
            chunk_metadata = chunk.properties
            chunk_score = chunk.properties.get("score")
        elif hasattr(chunk, 'metadata') and chunk.metadata:
            chunk_metadata = chunk.metadata
            chunk_score = chunk.metadata.get("score")

        # Get text content - handle both 'text' and 'content' attributes
        chunk_text = getattr(chunk, 'text', None) or getattr(chunk, 'content', '')

        api_chunks.append(
            QueryResultChunk(
                id=chunk.id,
                text=chunk_text,
                document_id=chunk.document_id,
                metadata=chunk_metadata,
                score=chunk_score,
            )
        )
    return api_chunks


def _to_api_graph_context(query_result: DomainQueryResult):
    """Convert domain graph context to API QueryResultGraphContext model.

    Args:
        query_result: Domain query result containing graph context

    Returns:
        API-compatible QueryResultGraphContext model or None if no graph context
    """
    if not query_result.graph_context:
        return None
    try:
        domain_entities, domain_relationships = query_result.graph_context
        return QueryResultGraphContext(
            entities=[e.model_dump() for e in domain_entities]
            if domain_entities
            else [],
            relationships=[r.model_dump() for r in domain_relationships]
            if domain_relationships
            else [],
        )
    except (TypeError, ValueError):
        return None


def _get_error_guidance(error: Exception) -> str:
    """Provide user-friendly error guidance based on exception type."""
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Check for common error patterns
    if "chunk" in error_str and ("properties" in error_str or "metadata" in error_str):
        return "There's a data model mismatch. The system is trying to access chunk properties that don't exist."

    elif "connection" in error_str or "timeout" in error_str:
        return "There's a connectivity issue with the underlying services (database or LLM)."

    elif "memory" in error_str or "out of memory" in error_str:
        return "The system is running out of memory. Try reducing query complexity or chunk size."

    elif "llm" in error_str or "language model" in error_str:
        return "There's an issue with the language model service. Check LLM configuration and connectivity."

    elif error_type == "AttributeError":
        return "A required attribute or method is missing. This may indicate a configuration or version mismatch."

    elif error_type == "ValueError":
        return "Invalid input value provided. Check the request parameters and data format."

    elif error_type == "TypeError":
        return "Data type mismatch detected. This may indicate an internal data processing issue."

    elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
        return "A required module or dependency is missing or not properly installed."

    else:
        return "An unexpected error occurred. Check the system logs for more details."


def _get_recovery_suggestions(error: Exception) -> list[str]:
    """Provide specific recovery suggestions based on the error."""
    error_str = str(error).lower()
    error_type = type(error).__name__
    suggestions = []

    # Check for common error patterns and provide suggestions
    if "chunk" in error_str and ("properties" in error_str or "metadata" in error_str):
        suggestions.extend([
            "Restart the API server to ensure latest data models are loaded",
            "Check if recent data was ingested with incompatible chunk formats",
            "Clear the vector store and re-ingest documents if the issue persists"
        ])

    elif "connection" in error_str or "timeout" in error_str:
        suggestions.extend([
            "Check if Memgraph is running: 'docker ps' or 'synapse up'",
            "Verify network connectivity to external services",
            "Check service logs for more detailed error information",
            "Try again in a few moments as this may be a temporary issue"
        ])

    elif "rate limit" in error_str:
        suggestions.extend([
            "Wait a few minutes before making additional requests",
            "Reduce the frequency of your requests",
            "Contact support if you need higher rate limits"
        ])

    elif "api key" in error_str or "unauthorized" in error_str:
        suggestions.extend([
            "Check environment variables for API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)",
            "Verify API key permissions and quotas",
            "Ensure you're using the correct API endpoint"
        ])

    elif "not found" in error_str:
        suggestions.extend([
            "Ingest some documents first using the /api/v1/ingestion/documents endpoint",
            "Check if the requested resource ID is correct",
            "Verify that the data was successfully stored"
        ])

    elif "vector store" in error_str or "embedding" in error_str:
        suggestions.extend([
            "Check if the embedding service is properly configured",
            "Verify that the vector store path is accessible and writable",
            "Try switching to a different vector store type (simple/faiss)"
        ])

    elif "graph" in error_str or "memgraph" in error_str:
        suggestions.extend([
            "Start Memgraph: 'make up' or 'docker run -p 7687:7687 memgraph/memgraph'",
            "Check Memgraph connection settings in environment variables",
            "Switch to vector-only mode if graph features aren't required"
        ])

    elif "llm" in error_str:
        suggestions.extend([
            "Check LLM service configuration and API keys",
            "Try switching to mock LLM service for testing",
            "Verify internet connectivity for external LLM services"
        ])

    elif error_type == "ImportError" or error_type == "ModuleNotFoundError":
        suggestions.extend([
            "Install missing dependencies: 'pip install -e .'",
            "Check if optional dependencies are needed for your configuration",
            "Verify Python environment and virtual environment setup"
        ])

    else:
        suggestions.extend([
            "Check system logs for more detailed error information",
            "Try with a simpler query to isolate the issue",
            "Restart the API server if the problem persists",
            "Contact support with the error details if issues continue"
        ])

    return suggestions
