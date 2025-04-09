from fastapi import APIRouter, HTTPException, status
from typing import List
import uuid
import logging

from graph_rag.api import schemas
from graph_rag.domain.models import Chunk
from graph_rag.api.dependencies import GraphRepositoryDep

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/", 
    response_model=schemas.CreateResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_chunk(
    chunk_in: schemas.ChunkCreate,
    repo: GraphRepositoryDep
):
    """Create a new chunk node in the graph."""
    chunk_id = chunk_in.id or str(uuid.uuid4())
    logger.info(f"Attempting to create chunk {chunk_id} for document {chunk_in.document_id}")
    # TODO: Validate that the document_id exists?
    chunk = Chunk(
        id=chunk_id,
        content=chunk_in.content,
        document_id=chunk_in.document_id,
        embedding=chunk_in.embedding
    )
    try:
        created_chunk_id = await repo.save_chunk(chunk)
        logger.info(f"Successfully created chunk {created_chunk_id}")
        # TODO: Create relationship to parent document here? (Now done in IngestionService)
        return schemas.CreateResponse(id=created_chunk_id)
    except Exception as e:
        logger.error(f"API Error: Failed to save chunk {chunk_id}. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save chunk. Check logs for details."
        )

@router.get("/by_document/{document_id}", response_model=List[schemas.ChunkResponse])
async def get_chunks_by_document(
    document_id: str,
    repo: GraphRepositoryDep
):
    """Retrieve all chunks associated with a specific document ID."""
    logger.info(f"Attempting to retrieve chunks for document {document_id}")
    try:
        chunks = await repo.get_chunks_by_document(document_id)
        logger.info(f"Found {len(chunks)} chunks for document {document_id}")
        # Map domain models to response schemas
        return [
            schemas.ChunkResponse(
                id=c.id,
                text=c.content,
                document_id=c.document_id,
                metadata=c.metadata
            ) for c in chunks
        ]
    except Exception as e:
        logger.error(f"API Error: Failed to retrieve chunks for document {document_id}. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chunks. Check logs for details."
        )

# TODO: Add endpoints for getting individual chunks, updating, deleting 