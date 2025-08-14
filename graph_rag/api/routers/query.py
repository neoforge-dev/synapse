import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

# Use the standardized dependency getter
from graph_rag.api.dependencies import get_graph_rag_engine
from graph_rag.api.metrics import (
    inc_llm_rel_inferred,
    inc_llm_rel_persisted,
)
from graph_rag.api.models import (
    AskRequest,
    ConfidenceMetricsResponse,
    ConversationContextResponse,
    EnhancedAskRequest,
    EnhancedQueryResponse,
    AnswerValidationResponse,
    QueryRequest,
    QueryResponse,
    QueryResultChunk,
    QueryResultGraphContext,
    StartConversationRequest,
    StartConversationResponse,
)
from graph_rag.core.graph_rag_engine import (
    GraphRAGEngine,
)
from graph_rag.core.graph_rag_engine import (
    QueryResult as DomainQueryResult,
)

# Import domain models needed for converting results

logger = logging.getLogger(__name__)


def create_query_router() -> APIRouter:
    """Factory to create the query API router."""
    router = APIRouter()

    @router.post(
        "",
        response_model=QueryResponse,
        summary="Submit a query to the GraphRAG engine",
        description="Processes a natural language query, retrieves relevant information from the graph and vector store, and generates an answer.",
    )
    async def execute_query(
        query_request: QueryRequest,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine),
    ):
        """Endpoint to handle user queries."""
        logger.info(
            f"Received query: {query_request.query_text[:100]}... (k={query_request.k})"
        )
        try:
            # FIX: Pass k within a config dictionary
            config = {"k": query_request.k}  # Create config dict
            query_result: DomainQueryResult = await engine.query(
                query_request.query_text, config=config
            )
            logger.info(
                f"Query successful. Found {len(query_result.relevant_chunks)} chunks."
            )

            # Adapt the domain QueryResult to the API QueryResponse model
            api_chunks = []
            for chunk in query_result.relevant_chunks:
                api_chunks.append(
                    QueryResultChunk(
                        id=chunk.id,
                        text=chunk.text,
                        document_id=chunk.document_id,
                        # Chunk inherits 'properties' from Node, not 'metadata'
                        metadata=chunk.properties or {},  # Use properties
                        score=chunk.properties.get(
                            "score"
                        ),  # Get score from properties
                    )
                )

            api_graph_context = None
            if query_result.graph_context:
                # Unpack only if graph_context is not None and is iterable (e.g., a tuple)
                try:
                    domain_entities, domain_relationships = query_result.graph_context
                    api_graph_context = QueryResultGraphContext(
                        # Convert domain Entity/Relationship objects to simple dicts for API
                        entities=[e.model_dump() for e in domain_entities]
                        if domain_entities
                        else [],
                        relationships=[r.model_dump() for r in domain_relationships]
                        if domain_relationships
                        else [],
                    )
                except (TypeError, ValueError) as unpack_error:
                    # Log if unpacking fails unexpectedly (e.g., not a 2-tuple)
                    logger.warning(
                        f"Could not unpack graph_context: {query_result.graph_context}. Error: {unpack_error}"
                    )
                    # Keep api_graph_context as None

            # Include citations in metadata (chunk_id, document_id)
            try:
                citations = [
                    {"chunk_id": c.id, "document_id": c.document_id}
                    for c in query_result.relevant_chunks
                ]
            except Exception:
                citations = []
            meta_with_citations = dict(query_result.metadata or {})
            if citations:
                meta_with_citations.setdefault("citations", citations)

            return QueryResponse(
                answer=query_result.answer,
                relevant_chunks=api_chunks,
                graph_context=api_graph_context,
                metadata=meta_with_citations,
                answer_with_citations=query_result.answer_with_citations,
                citations=query_result.citations,
                bibliography=query_result.bibliography,
            )

        except Exception as e:
            logger.error(
                f"Error processing query '{query_request.query_text}': {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process query: {e}",
            )

    @router.post(
        "/ask",
        response_model=QueryResponse,
        summary="Ask a question and get a synthesized answer",
        description="Retrieves context (optionally with graph) and synthesizes an answer using the configured LLM.",
    )
    async def ask(
        ask_request: AskRequest,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine),
        request: Request = None,
    ):
        logger.info(
            f"Received ask: {ask_request.text[:100]}... (k={ask_request.k}, graph={ask_request.include_graph})"
        )
        # Increment ask counter if app metrics are configured
        # no-op placeholder removed (was creating an unused variable)
        try:
            config = {
                "k": ask_request.k,
                "include_graph": ask_request.include_graph,
                "search_type": ask_request.search_type,
                "blend_vector_weight": ask_request.blend_vector_weight,
                "blend_keyword_weight": ask_request.blend_keyword_weight,
                "rerank": ask_request.rerank,
                "mmr_lambda": ask_request.mmr_lambda,
                "no_answer_min_score": ask_request.no_answer_min_score,
                "style": ask_request.style,
                "conversation_id": ask_request.conversation_id,
                # Relationship extraction controls
                "extract_relationships": True,
                "extract_relationships_persist": ask_request.extract_relationships_persist,
                "extract_relationships_dry_run": ask_request.extract_relationships_dry_run,
            }
            result: DomainQueryResult = await engine.query(
                ask_request.text, config=config
            )
            # Increment LLM relationship counters if present in config (best effort)
            try:
                inferred = int(config.get("llm_relations_inferred_total", 0))
                persisted = int(config.get("llm_relations_persisted_total", 0))
                inc_llm_rel_inferred(inferred)
                inc_llm_rel_persisted(persisted)
            except Exception:
                pass

            # Include citations in metadata
            try:
                citations = [
                    {"chunk_id": c.id, "document_id": c.document_id}
                    for c in result.relevant_chunks
                ]
            except Exception:
                citations = []
            meta_with_citations = dict(result.metadata or {})
            if citations:
                meta_with_citations.setdefault("citations", citations)

            return QueryResponse(
                answer=result.answer,
                relevant_chunks=_to_api_chunks(result),
                graph_context=_to_api_graph_context(result),
                metadata=meta_with_citations,
                answer_with_citations=result.answer_with_citations,
                citations=result.citations,
                bibliography=result.bibliography,
            )
        except Exception as e:
            logger.error(
                f"Error processing ask '{ask_request.text}': {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process ask: {e}",
            )

    @router.post(
        "/ask/enhanced",
        response_model=EnhancedQueryResponse,
        summary="Ask with confidence scoring",
        description="Retrieves context and synthesizes an answer with detailed confidence metrics.",
    )
    async def ask_enhanced(
        ask_request: EnhancedAskRequest,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine),
        request: Request = None,
    ):
        logger.info(
            f"Received enhanced ask: {ask_request.text[:100]}... (k={ask_request.k}, graph={ask_request.include_graph})"
        )
        try:
            config = {
                "k": ask_request.k,
                "include_graph": ask_request.include_graph,
                "search_type": ask_request.search_type,
                "blend_vector_weight": ask_request.blend_vector_weight,
                "blend_keyword_weight": ask_request.blend_keyword_weight,
                "rerank": ask_request.rerank,
                "mmr_lambda": ask_request.mmr_lambda,
                "no_answer_min_score": ask_request.no_answer_min_score,
                "style": ask_request.style,
                "conversation_id": ask_request.conversation_id,
                # Relationship extraction controls
                "extract_relationships": True,
                "extract_relationships_persist": ask_request.extract_relationships_persist,
                "extract_relationships_dry_run": ask_request.extract_relationships_dry_run,
            }

            # Use enhanced query method
            enhanced_result = await engine.answer_query_enhanced(
                ask_request.text, config=config
            )

            # Convert domain model to API model
            confidence_api = ConfidenceMetricsResponse(
                overall_score=enhanced_result.confidence.overall_score,
                level=enhanced_result.confidence.level.value,
                context_coverage=enhanced_result.confidence.context_coverage,
                context_relevance=enhanced_result.confidence.context_relevance,
                uncertainty_indicators=enhanced_result.confidence.uncertainty_indicators,
                source_count=enhanced_result.confidence.source_count,
                source_quality_score=enhanced_result.confidence.source_quality_score,
                answer_completeness=enhanced_result.confidence.answer_completeness,
                factual_consistency=enhanced_result.confidence.factual_consistency,
                reasoning=enhanced_result.confidence.reasoning,
            )

            # Get basic query result for chunks and graph context
            basic_result = await engine.query(ask_request.text, config=config)

            # Include citations in metadata
            try:
                citations = [
                    {"chunk_id": c.id, "document_id": c.document_id}
                    for c in basic_result.relevant_chunks
                ]
            except Exception:
                citations = []
            meta_with_citations = dict(basic_result.metadata or {})
            if citations:
                meta_with_citations.setdefault("citations", citations)

            # Convert validation results to API model if available
            validation_api = None
            if basic_result.metadata.get("validation"):
                validation_data = basic_result.metadata["validation"]
                validation_api = AnswerValidationResponse(
                    is_valid=validation_data["is_valid"],
                    validation_score=validation_data["validation_score"],
                    validation_level=validation_data["validation_level"],
                    total_claims=validation_data["total_claims"],
                    supported_claims=validation_data["supported_claims"],
                    unsupported_claims=validation_data["unsupported_claims"],
                    conflicting_claims=validation_data["conflicting_claims"],
                    chunk_coverage=validation_data["chunk_coverage"],
                    answer_coverage=validation_data["answer_coverage"],
                    citation_completeness=validation_data["citation_completeness"],
                    hallucination_risk=validation_data["hallucination_risk"],
                    requires_fact_check=validation_data["requires_fact_check"],
                    num_issues=len(validation_data.get("issues", [])),
                    recommendations=validation_data.get("recommendations", []),
                )

            return EnhancedQueryResponse(
                answer=enhanced_result.answer,
                confidence=confidence_api,
                validation=validation_api,
                relevant_chunks=_to_api_chunks(basic_result),
                graph_context=_to_api_graph_context(basic_result),
                metadata=meta_with_citations,
                answer_with_citations=basic_result.answer_with_citations,
                citations=basic_result.citations,
                bibliography=basic_result.bibliography,
                input_tokens=enhanced_result.input_tokens,
                output_tokens=enhanced_result.output_tokens,
                processing_time=enhanced_result.processing_time,
                model_name=enhanced_result.model_name,
                temperature=enhanced_result.temperature,
                has_hallucination_risk=enhanced_result.has_hallucination_risk,
                requires_verification=enhanced_result.requires_verification,
            )

        except Exception as e:
            logger.error(
                f"Error processing enhanced ask '{ask_request.text}': {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process enhanced ask: {e}",
            )

    @router.post(
        "/ask/stream",
        summary="Ask with streaming response",
        description="Streams synthesized answer chunks (NDJSON).",
    )
    async def ask_stream(
        ask_request: AskRequest,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine),
    ):
        from fastapi.responses import StreamingResponse

        async def _gen():
            try:
                config = {
                    "k": ask_request.k,
                    "include_graph": ask_request.include_graph,
                    "conversation_id": ask_request.conversation_id,
                    "extract_relationships": True,
                    "extract_relationships_persist": ask_request.extract_relationships_persist,
                }
                async for token in engine.stream_answer(ask_request.text, config=config):
                    yield token
            except Exception as e:  # pragma: no cover - safety
                yield f"\n[error] {e}"

        return StreamingResponse(_gen(), media_type="text/plain; charset=utf-8")

    @router.post(
        "/conversations/start",
        response_model=StartConversationResponse,
        summary="Start a new conversation",
        description="Start a new conversation session for context-aware responses.",
    )
    async def start_conversation(
        request: StartConversationRequest,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine),
    ):
        """Start a new conversation session."""
        try:
            # Check if engine has context manager
            if not hasattr(engine, '_context_manager') or not engine._context_manager:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Conversation memory is not available. Context manager not configured."
                )

            conversation_id = await engine._context_manager.start_conversation(request.user_id)

            return StartConversationResponse(
                conversation_id=conversation_id,
                message=f"Conversation started for user {request.user_id}"
            )

        except Exception as e:
            logger.error(f"Error starting conversation for user {request.user_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start conversation: {e}",
            )

    @router.get(
        "/conversations/{conversation_id}/context",
        response_model=ConversationContextResponse,
        summary="Get conversation context",
        description="Retrieve the formatted context for a conversation.",
    )
    async def get_conversation_context(
        conversation_id: str,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine),
    ):
        """Get conversation context."""
        try:
            if not hasattr(engine, '_context_manager') or not engine._context_manager:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Conversation memory is not available. Context manager not configured."
                )

            context = await engine._context_manager.get_conversation_context(conversation_id)
            summary = await engine._context_manager.get_conversation_summary(conversation_id)

            return ConversationContextResponse(
                conversation_id=conversation_id,
                context=context,
                has_summary=bool(summary)
            )

        except Exception as e:
            logger.error(f"Error getting context for conversation {conversation_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get conversation context: {e}",
            )

    @router.delete(
        "/conversations/{conversation_id}",
        summary="Delete a conversation",
        description="Delete a conversation and all its history.",
    )
    async def delete_conversation(
        conversation_id: str,
        engine: GraphRAGEngine = Depends(get_graph_rag_engine),
    ):
        """Delete a conversation."""
        try:
            if not hasattr(engine, '_context_manager') or not engine._context_manager:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Conversation memory is not available. Context manager not configured."
                )

            deleted = await engine._context_manager.delete_conversation(conversation_id)

            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found"
                )

            return {"message": f"Conversation {conversation_id} deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete conversation: {e}",
            )

    return router


def _to_api_chunks(query_result: DomainQueryResult) -> list[QueryResultChunk]:
    """Convert domain QueryResult chunks to API QueryResultChunk models.
    
    Args:
        query_result: Domain query result containing relevant chunks
        
    Returns:
        List of API-compatible QueryResultChunk models
    """
    api_chunks: list[QueryResultChunk] = []
    for chunk in query_result.relevant_chunks:
        api_chunks.append(
            QueryResultChunk(
                id=chunk.id,
                text=chunk.text,
                document_id=chunk.document_id,
                metadata=chunk.properties or {},
                score=chunk.properties.get("score") if chunk.properties else None,
            )
        )
    return api_chunks


def _to_api_graph_context(query_result: DomainQueryResult):
    """Convert domain graph context to API QueryResultGraphContext model.
    
    Args:
        query_result: Domain query result containing graph context
        
    Returns:
        API-compatible QueryResultGraphContext model or None if no graph context
    """
    if not query_result.graph_context:
        return None
    try:
        domain_entities, domain_relationships = query_result.graph_context
        return QueryResultGraphContext(
            entities=[e.model_dump() for e in domain_entities]
            if domain_entities
            else [],
            relationships=[r.model_dump() for r in domain_relationships]
            if domain_relationships
            else [],
        )
    except (TypeError, ValueError):
        return None
