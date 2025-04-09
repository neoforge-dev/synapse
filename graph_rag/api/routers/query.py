import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body, status
from pydantic import BaseModel, Field
from typing import Annotated, Optional

from graph_rag.core.entity_extractor import EntityExtractor
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.config.settings import Settings
from graph_rag.api.dependencies import get_settings, get_entity_extractor
from graph_rag.api.dependencies import get_graph_repo
from graph_rag.api.models import QueryRequest, QueryResult, ResultItem, QueryResponse, QueryResultGraphContext, QueryResultChunk
from graph_rag.core.interfaces import EntityExtractor
from graph_rag.llm.loader import load_llm
from graph_rag.llm.types import LLM

logger = logging.getLogger(__name__)

def create_query_router() -> APIRouter:
    """Factory to create the query router with explicit dependency injection."""
    
    query_router = APIRouter()

    @query_router.post("/", response_model=QueryResponse)
    async def handle_query(
        request: QueryRequest,
        graph_repository: Annotated[MemgraphRepository, Depends(get_graph_repo)],
        entity_extractor: Annotated[EntityExtractor, Depends(get_entity_extractor)],
        llm: Annotated[LLM, Depends(load_llm)]
    ) -> QueryResponse:
        """
        Handles a user query by extracting entities, querying the graph,
        retrieving relevant chunks, and generating a response.
        """
        logger.info(f"Received query: {request.query_text[:100]}...") # Truncate long queries

        try:
            # 1. Extract Entities (Simplified - using query text directly for now)
            # In a real scenario, use an NER model or keyword extraction
            query_entities = [request.query_text] # Placeholder

            # 2. Query Graph Repository
            # This might involve finding nodes matching entities and expanding to get context
            graph_data = await graph_repository.get_context_for_entities(query_entities)
            logger.debug(f"Retrieved graph data: {graph_data}")

            # 3. Query Vector Store (Assuming relevant chunks are linked in the graph or retrieved separately)
            # For simplicity, let's assume graph_data contains relevant chunk IDs or text
            # In a more complex setup, you might query a vector index based on the query or graph context
            relevant_chunks_data = graph_data.get("chunks", []) # Example structure

            # 4. Format Graph Context for Response
            graph_context_response = None
            if graph_data.get("entities") or graph_data.get("relationships"):
                 graph_context_response = QueryResultGraphContext(
                     entities=graph_data.get("entities", []),
                     relationships=graph_data.get("relationships", [])
                 )

            # 5. Format Chunks for Response
            relevant_chunks_response = [
                QueryResultChunk(
                    id=chunk.get("id", "unknown"),
                    text=chunk.get("text", ""),
                    document_id=chunk.get("document_id", "unknown"),
                    metadata=chunk.get("metadata", {}),
                    score=chunk.get("score")
                )
                for chunk in relevant_chunks_data
            ]

            # 6. Generate Answer using LLM
            # Prepare context for LLM
            llm_context = f"User Query: {request.query_text}\n\n"
            if relevant_chunks_response:
                llm_context += "Relevant Information:\n"
                for chunk in relevant_chunks_response[:3]: # Limit context size
                    llm_context += f"- {chunk.text}\n"
            if graph_context_response:
                 llm_context += "\nGraph Context:\n"
                 # Simplified representation for LLM prompt
                 llm_context += f"Entities: {[e.get('id', e.get('name', 'unknown')) for e in graph_context_response.entities[:5]]}\n" # Limit context

            logger.debug(f"Context for LLM: {llm_context[:200]}...")

            # Generate answer
            # TODO: Implement actual LLM call - using placeholder for now
            # answer = llm.generate_response(prompt=f"Answer the following query based on the provided context:\n{llm_context}")
            answer = f"Placeholder answer for query: '{request.query_text}'. Context includes {len(relevant_chunks_response)} chunk(s)." # Placeholder

            # 7. Construct Final Response
            response = QueryResponse(
                answer=answer,
                relevant_chunks=relevant_chunks_response,
                graph_context=graph_context_response,
                metadata={"query_entities": query_entities} # Example metadata
            )

            logger.info(f"Successfully processed query: {request.query_text[:50]}...")
            return response

        except Exception as e:
            logger.exception(f"Error processing query '{request.query_text[:50]}...': {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

    return query_router 