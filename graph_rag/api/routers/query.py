import logging
from typing import Callable, Any

from fastapi import APIRouter, Depends, HTTPException, Body, status, Request

from graph_rag.api.models import QueryRequest, QueryResponse, QueryResultChunk, QueryResultGraphContext
from graph_rag.core.graph_rag_engine import GraphRAGEngine
from graph_rag.models import Chunk, Entity, Relationship # Core models

logger = logging.getLogger(__name__)

# Define a factory function type for dependencies
DependencyFactory = Callable[[], Any]

def create_query_router(
    rag_engine_dep: DependencyFactory
) -> APIRouter:
    """Factory function to create the query router with dependencies."""
    
    router = APIRouter()

    @router.post(
        "/", # POST to /api/v1/query/
        response_model=QueryResponse,
        status_code=status.HTTP_200_OK,
        summary="Submit a Query",
        description="Receives a natural language query, processes it using the GraphRAGEngine, and returns an answer with supporting context (relevant chunks and graph data)."
    )
    async def submit_query(
        request: Request, # Access app state via request
        payload: QueryRequest = Body(...),
        # Use Depends with the provided dependency factory
        # The factory should return Depends(get_rag_engine) where get_rag_engine retrieves from state
        rag_engine: GraphRAGEngine = Depends(rag_engine_dep())
    ):
        """Processes a user query using the injected RAG engine."""
        request_id = request.headers.get("X-Request-ID", "unknown")
        logger.info(f"[Req ID: {request_id}] Received query request: '{payload.query_text}'")
        
        try:
            # Call the engine's query method
            engine_result = rag_engine.query(
                query_text=payload.query_text,
                config=payload.config
            )
            logger.info(f"[Req ID: {request_id}] Query processed by engine. Answer: {engine_result.answer[:100]}..." ) # Log snippet

            # Convert engine result (using core models) to API response model
            api_chunks = [
                QueryResultChunk(
                    id=chunk.id,
                    text=chunk.text,
                    document_id=chunk.document_id,
                    metadata=chunk.metadata,
                    # score=chunk.score # Add score if available from vector store result
                ) for chunk in engine_result.relevant_chunks
            ]
            
            api_graph_context = None
            if engine_result.graph_context:
                graph_entities, graph_relationships = engine_result.graph_context
                api_graph_context = QueryResultGraphContext(
                    # Convert Entity/Relationship objects to simple dicts for the API
                    entities=[entity.model_dump() if hasattr(entity, 'model_dump') else entity.__dict__ for entity in graph_entities],
                    relationships=[rel.model_dump() if hasattr(rel, 'model_dump') else rel.__dict__ for rel in graph_relationships]
                )

            response = QueryResponse(
                answer=engine_result.answer,
                relevant_chunks=api_chunks,
                graph_context=api_graph_context,
                metadata=engine_result.metadata
            )
            
            return response

        except Exception as e:
            logger.error(f"[Req ID: {request_id}] Failed to process query '{payload.query_text}': {e}", exc_info=True)
            # Raise HTTPException to be caught by the handler in main.py
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process query. Error: {str(e)}"
            )
            
    return router 