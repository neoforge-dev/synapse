from fastapi import APIRouter, HTTPException, status, Depends
import logging
from typing import List

from graph_rag.api import schemas
from graph_rag.api.dependencies import GraphRAGEngineDep
from graph_rag.core.interfaces import SearchResultData

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/query", 
    response_model=schemas.SearchQueryResponse,
    summary="Unified Context Retrieval Query",
    description="Retrieves relevant context chunks using vector or keyword search based on the specified `search_type`."
)
async def unified_search(
    request: schemas.SearchQueryRequest,
    engine: GraphRAGEngineDep
):
    """Performs context retrieval using the GraphRAGEngine."""
    logger.info(f"Received search request: query='{request.query}', type='{request.search_type}', limit={request.limit}")
    try:
        results: List[SearchResultData] = await engine.retrieve_context(
            query=request.query, 
            search_type=request.search_type,
            limit=request.limit
        )
        
        response_results = []
        for r in results:
            chunk_schema = schemas.ChunkResultSchema(
                id=r.chunk.id,
                text=r.chunk.text,
                document_id=r.chunk.document_id
            )
            doc_schema = None
            if r.document:
                doc_schema = schemas.DocumentResultSchema(
                    id=r.document.id,
                    metadata=r.document.metadata
                )
                
            response_results.append(schemas.SearchResultSchema(
                chunk=chunk_schema,
                score=r.score,
                document=doc_schema
            ))
        
        logger.info(f"Search for '{request.query}' ({request.search_type}) returned {len(response_results)} results.")
        return schemas.SearchQueryResponse(
            query=request.query, 
            search_type=request.search_type,
            results=response_results
        )
        
    except ValueError as ve:
        logger.warning(f"Search validation error for query '{request.query}': {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except RuntimeError as re:
        logger.error(f"Runtime error during search for query '{request.query}': {re}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Search backend error: {re}"
        )
    except Exception as e:
        logger.error(f"API Error: Unified search failed for query '{request.query}'. Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed due to an internal server error."
        )

# TODO: Add endpoints for graph traversal search, etc. 