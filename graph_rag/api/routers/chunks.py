import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from graph_rag.api.dependencies import get_graph_repository
from graph_rag.api.schemas import ChunkResultSchema, CreateResponse, ErrorDetail
from graph_rag.core.interfaces import GraphRepository
from graph_rag.domain.models import Chunk, Entity

router = APIRouter(prefix="/chunks", tags=["Chunks"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=CreateResponse, status_code=status.HTTP_201_CREATED)
async def create_chunk(
    chunk_in: ChunkResultSchema,
    repo: Annotated[GraphRepository, Depends(get_graph_repository)],
):
    """Create a new chunk node in the graph."""
    chunk_id = chunk_in.id
    logger.info(
        f"Attempting to create chunk {chunk_id} for document {chunk_in.document_id}"
    )
    # TODO: Validate that the document_id exists?
    chunk = Chunk(
        id=chunk_id,
        content=chunk_in.text,
        document_id=chunk_in.document_id,
        embedding=None,
    )
    try:
        await repo.add_entity(
            Entity(
                id=chunk.id,
                type="Chunk",
                properties=chunk.model_dump(exclude={"id", "type"}),
            )
        )
        created_chunk_id = chunk.id
        logger.info(f"Successfully created chunk {created_chunk_id}")
        # TODO: Create relationship to parent document here? (Now done in IngestionService)
        return CreateResponse(id=created_chunk_id)
    except Exception as e:
        logger.error(f"API Error: Failed to save chunk {chunk_id}. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save chunk. Check logs for details.",
        )


@router.get("/by_document/{document_id}", response_model=list[ChunkResultSchema])
async def get_chunks_by_document(
    document_id: str, repo: Annotated[GraphRepository, Depends(get_graph_repository)]
):
    """Retrieve all chunks associated with a specific document ID."""
    logger.info(f"Attempting to retrieve chunks for document {document_id}")
    try:
        chunk_entities = await repo.search_entities_by_properties(
            {"type": "Chunk", "document_id": document_id}
        )
        logger.info(f"Found {len(chunk_entities)} chunks for document {document_id}")
        # Map domain models to response schemas
        return [
            ChunkResultSchema(
                id=entity.id,
                text=entity.properties.get("content", ""),
                document_id=entity.properties.get("document_id", ""),
            )
            for entity in chunk_entities
        ]
    except Exception as e:
        logger.error(
            f"API Error: Failed to retrieve chunks for document {document_id}. Error: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chunks. Check logs for details.",
        )


@router.get(
    "/",
    response_model=list[ChunkResultSchema],
    summary="List all chunks (use with caution)",
    description="Retrieves all chunk nodes from the graph. Warning: potentially large response.",
)
async def list_all_chunks(
    repo: Annotated[GraphRepository, Depends(get_graph_repository)],
    limit: Optional[int] = Query(
        100, description="Limit the number of chunks returned", ge=1, le=1000
    ),
):
    """Fetches all chunks, potentially paginated or limited."""
    try:
        chunks_as_entities = await repo.search_entities_by_properties(
            {"type": "Chunk"}, limit=limit
        )
        return [
            ChunkResultSchema.model_validate(entity) for entity in chunks_as_entities
        ]
    except Exception as e:
        logger.error(f"Error listing chunks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chunks",
        )


@router.get(
    "/{chunk_id}",
    response_model=ChunkResultSchema,
    summary="Get chunk by ID",
    responses={
        404: {"model": ErrorDetail, "description": "Chunk not found"},
        500: {"model": ErrorDetail},
    },
)
async def get_chunk(
    chunk_id: str, repo: Annotated[GraphRepository, Depends(get_graph_repository)]
):
    """Retrieve a specific chunk by its unique ID."""
    chunk_entity = await repo.get_entity_by_id(chunk_id)
    if not chunk_entity or chunk_entity.type != "Chunk":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk with id '{chunk_id}' not found",
        )
    return ChunkResultSchema.model_validate(chunk_entity)


# POST /chunks/bulk - Placeholder for potential bulk creation (complex)
# Might be better handled by ingestion service

# GET /chunks/{chunk_id}/entities - Placeholder for linked entities
# GET /chunks/{chunk_id}/relationships - Placeholder for relationships involving chunk
# DELETE /chunks/{chunk_id} - Placeholder
