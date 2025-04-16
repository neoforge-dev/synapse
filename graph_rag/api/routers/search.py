from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
import logging
from typing import List, Dict, Any
import json # Import json for NDJSON serialization

from graph_rag.api import schemas
from graph_rag.api.dependencies import GraphRAGEngineDep
from graph_rag.core.interfaces import SearchResultData
from graph_rag.api.dependencies import LLMServiceDep

router = APIRouter()
logger = logging.getLogger(__name__)

def create_search_router() -> APIRouter:
    """Factory function to create the search router with its endpoints."""
    router = APIRouter() # Create router inside factory

    @router.post(
        "/",
        response_model=schemas.SearchQueryResponse,
        summary="Perform a search",
        description="Performs a search (vector or keyword) against the graph and returns relevant chunks.",
        responses={
            status.HTTP_501_NOT_IMPLEMENTED: {"model": schemas.ErrorDetail},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": schemas.ErrorDetail},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": schemas.ErrorDetail},
        }
    )
    async def perform_search(
        request: schemas.SearchQueryRequest,
        engine: GraphRAGEngineDep,
    ) -> schemas.SearchQueryResponse:
        """Search for chunks based on the query and search type."""
        logger.info(f"Received search request: {request.model_dump()}")
        try:
            if not engine:
                logger.error("GraphRAGEngine dependency not available.")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                    detail="Search engine is not available."
                )

            if request.search_type == "vector":
                # Assume search returns a list of SearchResultSchema compatible objects
                results = await engine.search(
                    query=request.query, 
                    search_type='vector', # Pass type explicitly
                    limit=request.limit
                ) # Pass limit
            elif request.search_type == "keyword":
                # Keyword search might not be implemented yet
                # results = await engine.search(query=request.query, search_type='keyword')
                logger.warning(f"Keyword search not implemented yet for query: {request.query}")
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED, 
                    detail="Keyword search is not yet implemented."
                )
            else:
                # Should be caught by Pydantic validation, but handle defensively
                logger.error(f"Unsupported search type: {request.search_type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported search type: {request.search_type}"
                )

            logger.info(f"Search for '{request.query}' ({request.search_type}) returned {len(results)} results.")
            # Ensure the structure matches SearchQueryResponse
            return schemas.SearchQueryResponse(query=request.query, search_type=request.search_type, results=results)

        except HTTPException as http_exc: # Re-raise HTTP exceptions
            raise http_exc
        except NotImplementedError:
            logger.warning(f"Search type '{request.search_type}' requested but not implemented.")
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Search type '{request.search_type}' is not implemented."
            )
        except Exception as e:
            logger.error(f"Error during search for query '{request.query}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during search."
            )

    @router.post(
        "/query", 
        response_model=schemas.SearchQueryResponse,
        summary="Unified Context Retrieval Query",
        description="Retrieves relevant context chunks using vector or keyword search based on the specified `search_type`. Can return results as a batch or a stream."
    )
    async def unified_search(
        request: schemas.SearchQueryRequest,
        engine: GraphRAGEngineDep,
        stream: bool = Query(False, description="Whether to stream results as NDJSON")
    ):
        """Performs context retrieval using the GraphRAGEngine, supporting batch and streaming."""
        logger.info(f"Received search request: query='{request.query}', type='{request.search_type}', limit={request.limit}, stream={stream}")

        async def format_result(r: SearchResultData) -> schemas.SearchResultSchema:
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
            return schemas.SearchResultSchema(
                chunk=chunk_schema,
                score=r.score,
                document=doc_schema
            )

        try:
            if stream:
                # Assume engine has a stream_context method that returns an async generator
                async def stream_results():
                    try:
                        async for result in await engine.stream_context(
                            query=request.query, 
                            search_type=request.search_type,
                            limit=request.limit
                        ):
                            formatted = await format_result(result)
                            yield json.dumps(formatted.model_dump()) + "\n"
                        logger.info(f"Streaming search completed for '{request.query}'.")
                    except Exception as e:
                         logger.error(f"Error during search streaming for query '{request.query}': {e}", exc_info=True)
                         # Yielding an error message might be complex with NDJSON, 
                         # often connection is just closed. Logging is crucial.
                         # Consider adding a specific error message format if needed.
                         # yield json.dumps({"error": "Internal server error during streaming"}) + "\n" 
                         # For now, just log and let the stream end.
            
                return StreamingResponse(stream_results(), media_type="application/x-ndjson")
            
            else: # Batch processing
                results: List[SearchResultData] = await engine.retrieve_context(
                    query=request.query, 
                    search_type=request.search_type,
                    limit=request.limit
                )
                
                response_results = []
                for r in results:
                    response_results.append(await format_result(r))
                
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

    return router # Return the configured router instance

# TODO: Add endpoints for graph traversal search, etc. 