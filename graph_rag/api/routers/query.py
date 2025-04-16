import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from graph_rag.api.models import QueryRequest, QueryResponse, QueryResultGraphContext, QueryResultChunk
from graph_rag.core.graph_rag_engine import GraphRAGEngine, QueryResult as DomainQueryResult
# Use the standardized dependency getter
from graph_rag.api.dependencies import get_graph_rag_engine
# Import domain models needed for converting results
from graph_rag.domain.models import Entity, Relationship 

logger = logging.getLogger(__name__)

def create_query_router() -> APIRouter:
    """Factory to create the query API router."""
    router = APIRouter()

    @router.post(
        "", 
        response_model=QueryResponse,
        summary="Submit a query to the GraphRAG engine",
        description="Processes a natural language query, retrieves relevant information from the graph and vector store, and generates an answer."
    )
    async def execute_query(
        query_request: QueryRequest,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine)
    ):
        """Endpoint to handle user queries."""
        logger.info(f"Received query: {query_request.query_text[:100]}... (k={query_request.k})")
        try:
            # Call the engine's query method
            query_result: DomainQueryResult = await engine.query(query_request.query_text, k=query_request.k)
            logger.info(f"Query successful. Found {len(query_result.relevant_chunks)} chunks.")
            
            # Adapt the domain QueryResult to the API QueryResponse model
            api_chunks = []
            for chunk in query_result.relevant_chunks:
                api_chunks.append(QueryResultChunk(
                    id=chunk.id,
                    text=chunk.text,
                    document_id=chunk.document_id,
                    # Chunk inherits 'properties' from Node, not 'metadata'
                    metadata=chunk.properties or {}, # Use properties
                    score=chunk.properties.get('score') # Get score from properties
                ))

            api_graph_context = None
            if query_result.graph_context:
                domain_entities, domain_relationships = query_result.graph_context
                api_graph_context = QueryResultGraphContext(
                    # Convert domain Entity/Relationship objects to simple dicts for API
                    entities=[e.model_dump() for e in domain_entities] if domain_entities else [],
                    relationships=[r.model_dump() for r in domain_relationships] if domain_relationships else []
                )

            return QueryResponse(
                answer=query_result.answer,
                relevant_chunks=api_chunks,
                graph_context=api_graph_context,
                metadata=query_result.metadata # Pass engine metadata through
            )
            
        except Exception as e:
            logger.error(f"Error processing query '{query_request.query_text}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process query: {e}"
            )

    return router 