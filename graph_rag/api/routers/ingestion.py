import logging
import uuid
from collections.abc import Callable
from typing import Any

# Use state-aware getter from main so tests can clear overrides and hit 503
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Request,
    status,
)

from graph_rag.api.models import IngestRequest, IngestResponse
from graph_rag.services.ingestion import IngestionService


# Lazy wrapper to avoid circular import at module import time
def _state_get_ingestion_service(request: Request):
    from graph_rag.api.main import get_ingestion_service as _getter

    return _getter(request)



logger = logging.getLogger(__name__)

# Define a factory function type for dependencies to allow different ways of providing them
DependencyFactory = Callable[[], Any]


async def process_document_with_service(
    document_id: str, content: str, metadata: dict, ingestion_service: IngestionService
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
            generate_embeddings=True,
        )
        logger.info(f"DEBUG: Document {document_id} processed successfully.")
    except Exception as e:
        logger.error(
            f"DEBUG: Processing failed for document {document_id}: {e}", exc_info=True
        )
        raise


def create_ingestion_router(
    doc_processor_dep: DependencyFactory,
    entity_extractor_dep: DependencyFactory,
    kg_builder_dep: DependencyFactory,
    graph_repository_dep: DependencyFactory,
) -> APIRouter:
    """Factory function to create the ingestion router with dependencies."""

    router = APIRouter()

    @router.post(
        "/documents",
        response_model=IngestResponse,
        status_code=status.HTTP_202_ACCEPTED,  # Revert to 202 Accepted for async
        summary="Ingest a Single Document",
        description="Accepts text content and metadata, processes it, extracts entities/relationships, and adds them to the knowledge graph.",
    )
    async def ingest_document(
        background_tasks: BackgroundTasks,  # Re-enable BackgroundTasks dependency
        payload: IngestRequest = Body(...),
        ingestion_service: IngestionService = Depends(_state_get_ingestion_service),
    ):
        """Asynchronous endpoint to ingest a document."""

        request_id = str(uuid.uuid4())  # Unique ID for this ingestion operation
        logger.info(f"[Req ID: {request_id}] Received ingestion request.")

        # --- Input Validation ---
        if not payload.content or payload.content.isspace():
            logger.warning(
                f"[Req ID: {request_id}] Ingestion request rejected: Content is empty or whitespace."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document content cannot be empty or whitespace.",
            )
        # --- End Validation ---

        # Create document with explicit ID
        doc_id = payload.document_id or f"doc-{uuid.uuid4()}"
        logger.debug(f"[Req ID: {request_id}] Using document ID: {doc_id}")

        # Always schedule background task; tests patch BackgroundTasks.add_task
        logger.info(
            f"[Req ID: {request_id}] Scheduling background ingestion task for document {doc_id}."
        )
        background_tasks.add_task(
            process_document_with_service,
            document_id=doc_id,
            content=payload.content,
            metadata=payload.metadata or {},
            ingestion_service=ingestion_service,
        )

        return IngestResponse(
            message="Document ingestion accepted for background processing.",  # Update message
            document_id=doc_id,
            task_id=request_id,
            status="processing",  # Keep status as processing
        )

    return router
