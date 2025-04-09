import logging
import uuid
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Body, status

from graph_rag.api.models import IngestRequest, IngestResponse
from graph_rag.models import Document # Import core model
from graph_rag.core.document_processor import DocumentProcessor
from graph_rag.core.entity_extractor import EntityExtractor
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder

logger = logging.getLogger(__name__)

# Define a factory function type for dependencies to allow different ways of providing them
DependencyFactory = Callable[[], Any]

def create_ingestion_router(
    doc_processor_dep: DependencyFactory,
    entity_extractor_dep: DependencyFactory,
    kg_builder_dep: DependencyFactory
) -> APIRouter:
    """Factory function to create the ingestion router with dependencies."""
    
    router = APIRouter()

    @router.post(
        "/documents",
        response_model=IngestResponse,
        status_code=status.HTTP_202_ACCEPTED, # Use 202 Accepted for async/long tasks
        summary="Ingest a Single Document",
        description="Accepts text content and metadata, processes it, extracts entities/relationships, and adds them to the knowledge graph."
    )
    async def ingest_document(
        # Use Body for the request model
        payload: IngestRequest = Body(...),
        # Use Depends with the provided dependency factories
        doc_processor: DocumentProcessor = Depends(doc_processor_dep),
        entity_extractor: EntityExtractor = Depends(entity_extractor_dep),
        kg_builder: KnowledgeGraphBuilder = Depends(kg_builder_dep)
    ):
        """Asynchronous endpoint to ingest a document."""
        
        request_id = str(uuid.uuid4()) # Unique ID for this ingestion operation
        logger.info(f"[Req ID: {request_id}] Received ingestion request.")
        
        # 1. Create Document Object
        doc_id = payload.document_id or f"doc-{uuid.uuid4()}"
        document = Document(
            id=doc_id,
            content=payload.content,
            metadata=payload.metadata or {}
        )
        logger.debug(f"[Req ID: {request_id}] Created document object with id: {doc_id}")
        
        # Simple synchronous processing for now.
        # Consider background tasks (e.g., Celery, ARQ, FastAPI BackgroundTasks) for production.
        try:
            # 2. Process Document (Chunking)
            logger.info(f"[Req ID: {request_id}] Processing document {doc_id}...")
            # Process modifies the document in-place by adding chunks
            processed_doc_chunks = doc_processor.process(document)
            logger.info(f"[Req ID: {request_id}] Document {doc_id} processed into {len(processed_doc_chunks.chunks)} chunks.")

            # 3. Extract Entities and Relationships
            logger.info(f"[Req ID: {request_id}] Extracting entities/relationships from document {doc_id}...")
            # Extractor takes the Document (with chunks) and returns ProcessedDocument
            processed_doc_entities = entity_extractor.extract(processed_doc_chunks)
            logger.info(f"[Req ID: {request_id}] Extracted {len(processed_doc_entities.entities)} entities and {len(processed_doc_entities.relationships)} relationships for document {doc_id}.")

            # 4. Build Knowledge Graph
            if processed_doc_entities.entities or processed_doc_entities.relationships:
                logger.info(f"[Req ID: {request_id}] Building knowledge graph for document {doc_id}...")
                kg_builder.build(processed_doc_entities)
                logger.info(f"[Req ID: {request_id}] Knowledge graph updated for document {doc_id}.")
            else:
                logger.info(f"[Req ID: {request_id}] No entities/relationships found for document {doc_id}, skipping graph build step.")

            # 5. Return Response
            logger.info(f"[Req ID: {request_id}] Ingestion successful for document {doc_id}.")
            return IngestResponse(document_id=doc_id)
            
        except Exception as e:
            logger.error(f"[Req ID: {request_id}] Ingestion failed for document {doc_id}: {e}", exc_info=True)
            # Raise HTTPException to be caught by the handler in main.py
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ingestion failed for document {doc_id}. Error: {str(e)}"
            )
            
    return router 