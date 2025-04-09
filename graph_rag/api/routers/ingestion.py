import logging
import uuid
from typing import Callable
from fastapi import APIRouter, Depends, HTTPException, Body, status, BackgroundTasks

from graph_rag.api.models import IngestRequest, IngestResponse
from graph_rag.models import Document # Import core model
from graph_rag.core.document_processor import DocumentProcessor
from graph_rag.core.entity_extractor import EntityExtractor
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository

logger = logging.getLogger(__name__)

# Define a factory function type for dependencies to allow different ways of providing them
DependencyFactory = Callable[[], Any]

async def process_document(
    document: Document,
    doc_processor: DocumentProcessor,
    entity_extractor: EntityExtractor,
    kg_builder: KnowledgeGraphBuilder,
    graph_repository: GraphRepository
):
    """Background task to process a document."""
    try:
        # First, store the document in the graph
        await graph_repository.create_document(document.id, document.content, document.metadata)
        logger.info(f"Document {document.id} stored in graph.")

        # Process document
        processed_doc_chunks = doc_processor.process(document)
        logger.info(f"Document {document.id} processed into {len(processed_doc_chunks.chunks)} chunks.")

        # Extract entities
        processed_doc_entities = entity_extractor.extract(processed_doc_chunks)
        logger.info(f"Extracted {len(processed_doc_entities.entities)} entities and {len(processed_doc_entities.relationships)} relationships.")

        # Build knowledge graph
        if processed_doc_entities.entities or processed_doc_entities.relationships:
            kg_builder.build(processed_doc_entities)
            logger.info(f"Knowledge graph updated for document {document.id}.")
        else:
            logger.info(f"No entities/relationships found for document {document.id}, skipping graph build.")

    except Exception as e:
        logger.error(f"Background processing failed for document {document.id}: {e}", exc_info=True)

def create_ingestion_router(
    doc_processor_dep: DependencyFactory,
    entity_extractor_dep: DependencyFactory,
    kg_builder_dep: DependencyFactory,
    graph_repository_dep: DependencyFactory
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
        background_tasks: BackgroundTasks,
        payload: IngestRequest = Body(...),
        doc_processor: DocumentProcessor = Depends(doc_processor_dep),
        entity_extractor: EntityExtractor = Depends(entity_extractor_dep),
        kg_builder: KnowledgeGraphBuilder = Depends(kg_builder_dep),
        graph_repository: GraphRepository = Depends(graph_repository_dep)
    ):
        """Asynchronous endpoint to ingest a document."""
        
        request_id = str(uuid.uuid4()) # Unique ID for this ingestion operation
        logger.info(f"[Req ID: {request_id}] Received ingestion request.")
        
        # Create document with explicit ID
        doc_id = payload.document_id or f"doc-{uuid.uuid4()}"
        document = Document(
            id=doc_id,
            content=payload.content,
            metadata=payload.metadata or {}
        )
        logger.debug(f"[Req ID: {request_id}] Created document object with id: {doc_id}")
        
        # Add background task
        background_tasks.add_task(
            process_document,
            document=document,
            doc_processor=doc_processor,
            entity_extractor=entity_extractor,
            kg_builder=kg_builder,
            graph_repository=graph_repository
        )
        
        return IngestResponse(
            message="Document ingestion started",
            document_id=doc_id,
            task_id=request_id,
            status="processing"
        )
            
    return router 