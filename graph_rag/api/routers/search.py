import inspect
import json  # Import json for NDJSON serialization
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from graph_rag.api import schemas
from graph_rag.api.dependencies import (
    get_graph_rag_engine,
    get_graph_repository,
    get_vector_store,
)
from graph_rag.core.graph_rag_engine import QueryResult  # Import QueryResult
from graph_rag.core.interfaces import GraphRAGEngine, SearchResultData, VectorStore

router = APIRouter()
logger = logging.getLogger(__name__)


def create_search_router() -> APIRouter:
    """Factory function to create the search router with its endpoints."""
    router = APIRouter()  # Create router inside factory

    @router.post(
        "/",
        response_model=schemas.SearchQueryResponse,
        summary="Perform a search",
        description="Performs a search (vector or keyword) against the graph and returns relevant chunks.",
        responses={
            status.HTTP_501_NOT_IMPLEMENTED: {"model": schemas.ErrorDetail},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": schemas.ErrorDetail},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": schemas.ErrorDetail},
        },
    )
    async def perform_search(
        request: schemas.SearchQueryRequest,
        vector_store: Annotated[
            VectorStore, Depends(get_vector_store)
        ],  # Depend on VectorStore directly
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
                # TODO: Need to potentially fetch Document metadata if required by schema?
                # For now, map directly, assuming SearchResultData has compatible fields or can be adapted.
                # Assuming SearchResultData has chunk and score
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
                # Keyword search might not be implemented yet
                # results = await engine.search(query=request.query, search_type='keyword')
                logger.warning(
                    f"Keyword search not implemented yet for query: {request.query}"
                )
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Keyword search is not yet implemented.",
                )
            else:
                # Should be caught by Pydantic validation, but handle defensively
                logger.error(f"Unsupported search type: {request.search_type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported search type: {request.search_type}",
                )

            logger.info(
                f"Search for '{request.query}' ({request.search_type}) returned {len(results)} results."
            )
            # Ensure the structure matches SearchQueryResponse
            return schemas.SearchQueryResponse(
                query=request.query, search_type=request.search_type, results=results
            )

        except HTTPException as http_exc:  # Re-raise HTTP exceptions
            raise http_exc
        except NotImplementedError:
            logger.warning(
                f"Search type '{request.search_type}' requested but not implemented."
            )
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Search type '{request.search_type}' is not implemented.",
            )
        except Exception as e:
            logger.error(
                f"Error during search for query '{request.query}': {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during search.",
            )

    @router.post(
        "/query",
        response_model=schemas.SearchQueryResponse,
        summary="Unified Context Retrieval Query",
        description="Retrieves relevant context chunks using vector or keyword search based on the specified `search_type`. Can return results as a batch or a stream.",
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
                                detail=(
                                    "Streaming is only implemented for vector searches."
                                ),
                            )
                    except HTTPException:
                        raise
                    except Exception:
                        # If settings cannot be loaded, default to disabled
                        raise HTTPException(
                            status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail=(
                                "Streaming is only implemented for vector searches."
                            ),
                        )

                # Set up streaming response
                async def stream_search_results():
                    try:
                        # Use stream_context if available
                        result_iter = engine.stream_context(
                            request.query, request.search_type, request.limit
                        )
                        if inspect.iscoroutine(result_iter):
                            result_iter = await result_iter
                        async for item in result_iter:
                            # Support both SearchResultData and ChunkData yields
                            score_val = 0.0
                            chunk_obj = item
                            # If SearchResultData-like
                            if hasattr(item, "chunk") and hasattr(item, "score"):
                                chunk_obj = getattr(item, "chunk")
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
                # Call engine.query with positional query text and config
                query_result: QueryResult = await engine.query(
                    request.query,
                    config={
                        "k": request.limit,
                        "search_type": request.search_type,
                        "include_graph": False,
                    },
                )

                # FIXED: Directly map domain Chunk objects to API schema objects
                # This avoids the SearchResultData validation error
                response_results = []
                for chunk in query_result.relevant_chunks:
                    # Create ChunkResultSchema directly from Chunk properties
                    chunk_schema = schemas.ChunkResultSchema(
                        id=chunk.id, text=chunk.text, document_id=chunk.document_id
                    )

                    # Create SearchResultSchema with proper document information
                    # Try to get the document from graph store to include its metadata
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
                        # ---- START DEBUG LOGGING ----
                        logger.info(
                            f"DEBUG: Document ID {chunk.document_id} -> Fetched document: {document}"
                        )
                        logger.info(
                            f"DEBUG: Document ID {chunk.document_id} -> Created doc_schema: {doc_schema}"
                        )
                        # ---- END DEBUG LOGGING ----
                    except Exception as e:
                        logger.warning(
                            f"Failed to get document {chunk.document_id}: {e}"
                        )
                        doc_schema = None

                    search_result = schemas.SearchResultSchema(
                        chunk=chunk_schema,
                        score=chunk.score
                        if hasattr(chunk, "score")
                        else 0.0,  # Use chunk score if available
                        document=doc_schema,  # Include document information if available
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
        except HTTPException as http_exc:
            # Propagate intentional HTTP errors (e.g., 501 for unsupported streaming)
            raise http_exc
        except RuntimeError as re:
            logger.error(
                f"Runtime error during search for query '{request.query}': {re}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Search backend error: {re}",
            )
        except Exception as e:
            logger.error(
                f"API Error: Unified search failed for query '{request.query}'. Error: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Search failed due to an internal server error.",
            )

    @router.post(
        "/batch",
        response_model=list[schemas.SearchQueryResponse],
        summary="Batch Search Processing",
        description="Process multiple search queries in a single request.",
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
                any_failed = True  # Ensure multi-status is set

        logger.info(f"Batch search completed with {len(results)} results")
        # If any query failed, use 207 Multi-Status
        if any_failed:
            response.status_code = status.HTTP_207_MULTI_STATUS
        return results

    return router  # Return the configured router instance


# TODO: Add endpoints for graph traversal search, etc.
