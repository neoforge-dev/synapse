"""Enhanced Synapse Engine with persistent vector store and dual-purpose responses."""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from graph_rag.api.performance_optimization import (
    get_performance_monitor,
    get_query_optimizer,
)
from graph_rag.config import get_settings
from graph_rag.core.interfaces import (
    ChunkData,
    EmbeddingService,
    ExtractedEntity,
    GraphRAGEngine,
    GraphRepository,
    SearchResultData,
    VectorStore,
)
from graph_rag.infrastructure.vector_stores.shared_persistent_vector_store import (
    SharedPersistentVectorStore,
)
from graph_rag.llm.protocols import LLMService
from graph_rag.llm.response_models import EnhancedLLMResponse
from graph_rag.models import Chunk, Entity, Relationship
from graph_rag.observability import (
    ComponentType,
    LogContext,
    PerformanceTimer,
    get_component_logger,
)
from graph_rag.services.answer_validation import AnswerValidator, ValidationLevel
from graph_rag.services.citation import CitationService, CitationStyle
from graph_rag.services.experiment_consolidator import SynapseExperimentConsolidator
from graph_rag.services.memory import ContextManager
from graph_rag.services.prompt_optimization import PromptOptimizer
from graph_rag.services.rerank import CrossEncoderReranker

logger = get_component_logger(ComponentType.ENGINE, "improved_synapse_engine")
settings = get_settings()


@dataclass
class ConsolidatedAnswer:
    """Dual-purpose response format for both human and machine consumption."""
    
    # Human-readable content
    answer: str
    answer_with_citations: Optional[str] = None
    
    # Consolidated knowledge components
    consolidated_chunks: List[ChunkData] = field(default_factory=list)
    architectural_patterns: List[Dict[str, Any]] = field(default_factory=list)
    success_metrics: List[Dict[str, Any]] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    
    # Quality metrics
    confidence_score: float = 0.0
    consolidation_confidence: float = 0.0
    evidence_ranking: float = 0.0
    
    # Source information
    sources: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    bibliography: Dict[str, Any] = field(default_factory=dict)
    
    # Machine-readable structured data
    machine_readable: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        # Convert chunks to dictionaries
        chunks_dict = []
        for chunk in self.consolidated_chunks:
            if hasattr(chunk, 'to_dict'):
                chunks_dict.append(chunk.to_dict())
            elif hasattr(chunk, '__dict__'):
                chunk_dict = chunk.__dict__.copy()
                # Ensure all values are serializable
                for key, value in chunk_dict.items():
                    if hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict)):
                        chunk_dict[key] = str(value)
                chunks_dict.append(chunk_dict)
            else:
                chunks_dict.append(str(chunk))
        
        return {
            "answer": self.answer,
            "answer_with_citations": self.answer_with_citations,
            "consolidated_chunks": chunks_dict,
            "architectural_patterns": self.architectural_patterns,
            "success_metrics": self.success_metrics,
            "best_practices": self.best_practices,
            "confidence_score": self.confidence_score,
            "consolidation_confidence": self.consolidation_confidence,
            "evidence_ranking": self.evidence_ranking,
            "sources": self.sources,
            "citations": self.citations,
            "bibliography": self.bibliography,
            "machine_readable": self.machine_readable,
            "metadata": self.metadata,
        }


class ImprovedSynapseEngine(GraphRAGEngine):
    """Enhanced GraphRAG engine with persistent vector store and consolidated responses."""

    def __init__(
        self,
        graph_store: GraphRepository,
        vector_store: VectorStore,
        entity_extractor,
        llm_service: LLMService = None,
        context_manager: ContextManager = None,
        citation_style: CitationStyle = CitationStyle.NUMERIC,
        validation_level: ValidationLevel = ValidationLevel.MODERATE,
        storage_path: str = "data/vector_store",
        embedding_service: EmbeddingService = None,
    ):
        """Initialize the improved engine with persistent storage and consolidation."""
        
        # Validate required components
        if not isinstance(graph_store, GraphRepository):
            raise TypeError("graph_store must implement the GraphRepository protocol")
        if not isinstance(vector_store, VectorStore):
            raise TypeError("vector_store must be an instance of VectorStore")
            
        # Core components
        self._graph_store = graph_store
        self._entity_extractor = entity_extractor
        self._llm_service = llm_service
        self._reranker = CrossEncoderReranker()
        self._context_manager = context_manager
        self._citation_service = CitationService(citation_style)
        self._answer_validator = AnswerValidator(validation_level)
        self._prompt_optimizer = PromptOptimizer()
        
        # Enhanced vector store with persistence
        if isinstance(vector_store, SharedPersistentVectorStore):
            self._vector_store = vector_store
            logger.info("Using existing SharedPersistentVectorStore")
        else:
            # Wrap existing vector store with persistent functionality
            if embedding_service is None:
                raise ValueError("embedding_service is required when not using SharedPersistentVectorStore")
            self._vector_store = SharedPersistentVectorStore(
                embedding_service=embedding_service,
                storage_path=storage_path
            )
            logger.info(f"Created new SharedPersistentVectorStore at {storage_path}")
        
        # Experiment consolidation
        self._experiment_consolidator = SynapseExperimentConsolidator()
        
        # Performance optimization
        self._performance_monitor = get_performance_monitor()
        self._query_optimizer = get_query_optimizer()
        
        # Initialize and load existing data
        self._initialize_storage()
        
        # Log initialization
        context = LogContext(
            component=ComponentType.ENGINE,
            operation="initialization",
            metadata={
                "engine_type": "ImprovedSynapseEngine",
                "graph_store_type": type(graph_store).__name__,
                "vector_store_type": type(self._vector_store).__name__,
                "storage_path": storage_path,
                "citation_style": citation_style.value,
                "validation_level": validation_level.value,
            }
        )
        logger.info("ImprovedSynapseEngine initialized successfully", context)

    def _initialize_storage(self):
        """Initialize persistent storage and load existing data."""
        try:
            # This will be called asynchronously when first query is made
            # to ensure data is loaded from persistent storage
            logger.debug("Storage initialization deferred to first query")
        except Exception as e:
            logger.error(f"Error during storage initialization: {e}", exc_info=True)

    async def _ensure_vector_store_loaded(self):
        """Ensure vector store is loaded with persistent data."""
        try:
            await self._vector_store._ensure_loaded()
            size = await self._vector_store.get_vector_store_size()
            logger.info(f"Vector store loaded with {size} vectors")
        except Exception as e:
            logger.error(f"Error loading vector store: {e}", exc_info=True)

    async def retrieve_context(
        self, query: str, search_type: str = "vector", limit: int = 5
    ) -> List[SearchResultData]:
        """Retrieve relevant context chunks with persistent storage support."""
        logger.info(f"Retrieving context for query: '{query}' (limit={limit}, type={search_type})")
        
        # Ensure vector store is loaded
        await self._ensure_vector_store_loaded()
        
        config = {
            "k": limit,
            "search_type": search_type,
            "include_graph": False,
        }
        
        retrieved_chunks, _ = await self._retrieve_and_build_context(query, config)
        
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks from persistent storage")
        return retrieved_chunks

    async def _retrieve_and_build_context(
        self, query_text: str, config: Dict[str, Any] = None
    ) -> Tuple[List[SearchResultData], Optional[Tuple[List[Entity], List[Relationship]]]]:
        """Enhanced context retrieval with persistent storage and consolidation."""
        
        retrieval_context = LogContext(
            component=ComponentType.ENGINE,
            operation="enhanced_context_retrieval",
            metadata={
                "query_length": len(query_text),
                "config": config or {},
            }
        )
        logger.info("Starting enhanced context retrieval", retrieval_context)
        
        config = config or {}
        k = config.get("k", 5)
        include_graph = config.get("include_graph", True)
        search_type = config.get("search_type", "vector").lower()
        
        # Ensure vector store is loaded
        await self._ensure_vector_store_loaded()
        
        # Check if vector store has data
        vector_store_size = await self._vector_store.get_vector_store_size()
        if vector_store_size == 0:
            logger.warning("Vector store is empty - no data has been ingested yet")
            return [], None
        
        logger.info(f"Vector store contains {vector_store_size} vectors")
        
        try:
            # Enhanced search with multiple strategies
            if search_type == "hybrid":
                # Hybrid search with consolidation
                retrieved_chunks = await self._hybrid_search_with_consolidation(
                    query_text, k, config
                )
            elif search_type == "keyword":
                retrieved_chunks = await self._vector_store.search(
                    query_text, top_k=k, search_type="keyword"
                )
            else:  # vector
                retrieved_chunks = await self._vector_store.search(
                    query_text, top_k=k, search_type="vector"
                )
            
            if not retrieved_chunks:
                logger.warning(f"No chunks retrieved for query: '{query_text}'")
                return [], None
            
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks via {search_type} search")
            
            # Graph context retrieval (if enabled)
            graph_context_tuple = None
            if include_graph and retrieved_chunks:
                graph_context_tuple = await self._get_enhanced_graph_context(retrieved_chunks)
            
            # Update context with results
            retrieval_context.chunk_count = len(retrieved_chunks)
            retrieval_context.metadata.update({
                "chunks_found": len(retrieved_chunks),
                "vector_store_size": vector_store_size,
                "search_type": search_type,
            })
            
            logger.info("Enhanced context retrieval completed", retrieval_context)
            return retrieved_chunks, graph_context_tuple
            
        except Exception as e:
            logger.error("Error during enhanced context retrieval", retrieval_context, error=e)
            return [], None

    async def _hybrid_search_with_consolidation(
        self, query_text: str, k: int, config: Dict[str, Any]
    ) -> List[SearchResultData]:
        """Enhanced hybrid search with overlapping content consolidation."""
        
        # Get both vector and keyword results
        vector_results = await self._vector_store.search(
            query_text, top_k=k*2, search_type="vector"  # Get more for better blending
        )
        keyword_results = await self._vector_store.search(
            query_text, top_k=k*2, search_type="keyword"
        )
        
        # Blend results with intelligent deduplication
        blend_weight = config.get("blend_keyword_weight", 0.3)
        combined_results = self._blend_and_deduplicate_results(
            vector_results, keyword_results, blend_weight
        )
        
        # Apply consolidation if we have overlapping content
        if len(combined_results) > k:
            consolidated_results = await self._consolidate_overlapping_chunks(
                combined_results[:k*2]  # Work with more chunks for better consolidation
            )
            return consolidated_results[:k]
        
        return combined_results[:k]

    def _blend_and_deduplicate_results(
        self, 
        vector_results: List[SearchResultData], 
        keyword_results: List[SearchResultData],
        blend_weight: float
    ) -> List[SearchResultData]:
        """Blend vector and keyword results with intelligent deduplication."""
        
        # Create score maps
        vec_scores = {r.chunk.id: r.score for r in vector_results if r and r.chunk}
        kw_scores = {r.chunk.id: r.score for r in keyword_results if r and r.chunk}
        
        # Combine all unique chunks
        combined = {}
        for r in vector_results:
            if r and r.chunk:
                combined[r.chunk.id] = r
        for r in keyword_results:
            if r and r.chunk:
                combined.setdefault(r.chunk.id, r)
        
        # Calculate blended scores
        alpha = 1.0 - blend_weight  # vector weight
        beta = blend_weight  # keyword weight
        
        blended_results = []
        for chunk_id, result in combined.items():
            vs = vec_scores.get(chunk_id, 0.0)
            ks = kw_scores.get(chunk_id, 0.0)
            blended_score = alpha * vs + beta * ks
            
            # Create new result with blended score
            chunk = result.chunk
            enhanced_metadata = dict(chunk.metadata or {})
            enhanced_metadata.update({
                "score_vector": vs,
                "score_keyword": ks,
                "score_blended": blended_score,
                "search_method": "hybrid_enhanced"
            })
            
            blended_chunk = ChunkData(
                id=chunk.id,
                text=chunk.text,
                document_id=chunk.document_id,
                metadata=enhanced_metadata,
                embedding=chunk.embedding,
                score=blended_score,
            )
            
            blended_results.append(SearchResultData(chunk=blended_chunk, score=blended_score))
        
        # Sort by blended score
        blended_results.sort(key=lambda r: r.score, reverse=True)
        return blended_results

    async def _consolidate_overlapping_chunks(
        self, chunks: List[SearchResultData]
    ) -> List[SearchResultData]:
        """Consolidate overlapping or similar chunks using the experiment consolidator."""
        
        try:
            # Convert chunks to consolidation candidates
            candidates = []
            for i, chunk_result in enumerate(chunks):
                chunk = chunk_result.chunk
                candidate = type('ConsolidationCandidate', (), {
                    'document_id': chunk.id,
                    'file_path': f"chunk_{chunk.id}",
                    'content_hash': str(hash(chunk.text)),
                    'title': chunk.text[:100],
                    'content_preview': chunk.text[:500],
                    'extracted_metrics': [],
                    'architectural_patterns': [],
                    'metadata': chunk.metadata or {},
                    'content_type': 'chunk',
                })()
                candidates.append(candidate)
            
            # Find similar documents
            similarity_matches = await self._experiment_consolidator.find_similar_documents(
                candidates, similarity_threshold=0.7  # Lower threshold for chunk consolidation
            )
            
            if not similarity_matches:
                return chunks  # No consolidation needed
            
            # Consolidate similar chunks
            consolidated_experiments = await self._experiment_consolidator.consolidate_experiments(
                similarity_matches
            )
            
            # Convert back to SearchResultData, keeping the best representative from each group
            final_chunks = []
            processed_chunk_ids = set()
            
            for experiment in consolidated_experiments:
                # Find the best chunk from this consolidation group
                best_chunk = None
                best_score = 0.0
                
                for candidate in experiment.source_candidates:
                    chunk_id = candidate.document_id
                    if chunk_id not in processed_chunk_ids:
                        # Find original chunk
                        for chunk_result in chunks:
                            if chunk_result.chunk.id == chunk_id:
                                if chunk_result.score > best_score:
                                    best_chunk = chunk_result
                                    best_score = chunk_result.score
                                processed_chunk_ids.add(chunk_id)
                                break
                
                if best_chunk:
                    # Enhance with consolidation metadata
                    enhanced_metadata = dict(best_chunk.chunk.metadata or {})
                    enhanced_metadata.update({
                        "consolidation_group": experiment.consolidated_id,
                        "consolidation_confidence": experiment.consolidation_confidence,
                        "evidence_ranking": experiment.evidence_ranking,
                        "consolidated_from": len(experiment.source_candidates),
                    })
                    
                    enhanced_chunk = ChunkData(
                        id=best_chunk.chunk.id,
                        text=best_chunk.chunk.text,
                        document_id=best_chunk.chunk.document_id,
                        metadata=enhanced_metadata,
                        embedding=best_chunk.chunk.embedding,
                        score=best_chunk.score,
                    )
                    
                    final_chunks.append(SearchResultData(chunk=enhanced_chunk, score=best_chunk.score))
            
            # Add any chunks that weren't part of consolidation
            for chunk_result in chunks:
                if chunk_result.chunk.id not in processed_chunk_ids:
                    final_chunks.append(chunk_result)
            
            # Sort by score
            final_chunks.sort(key=lambda r: r.score, reverse=True)
            
            logger.info(f"Consolidated {len(chunks)} chunks into {len(final_chunks)} results")
            return final_chunks
            
        except Exception as e:
            logger.error(f"Error during chunk consolidation: {e}", exc_info=True)
            return chunks  # Return original chunks if consolidation fails

    async def _get_enhanced_graph_context(
        self, chunks: List[SearchResultData]
    ) -> Optional[Tuple[List[Entity], List[Relationship]]]:
        """Enhanced graph context retrieval with entity consolidation."""
        
        if not chunks:
            return None
        
        try:
            # Extract entities from chunks
            combined_text = " ".join([c.chunk.text for c in chunks if c.chunk])
            extraction_result = await self._entity_extractor.extract_from_text(combined_text)
            
            if not extraction_result or not extraction_result.entities:
                return None
            
            # Find entities in graph with property search
            graph_entities = []
            for entity in extraction_result.entities:
                search_props = {"name": entity.text, "type": entity.label}
                try:
                    results = await self._graph_store.search_entities_by_properties(
                        search_props, limit=1
                    )
                    if results:
                        graph_entities.extend(results)
                except NotImplementedError:
                    logger.debug("Graph store doesn't support property search")
                    break
            
            if not graph_entities:
                return None
            
            # Get neighborhood context
            return await self._get_neighborhood_context(graph_entities)
            
        except Exception as e:
            logger.error(f"Error getting enhanced graph context: {e}", exc_info=True)
            return None

    async def _get_neighborhood_context(
        self, entities: List[Entity]
    ) -> Tuple[List[Entity], List[Relationship]]:
        """Get enhanced neighborhood context around seed entities."""
        
        all_entities = {e.id: e for e in entities}
        all_relationships = {}
        
        # Get neighbors for each entity
        neighbor_tasks = [
            self._graph_store.get_neighbors(entity.id) for entity in entities
        ]
        neighbor_results = await asyncio.gather(*neighbor_tasks, return_exceptions=True)
        
        for result in neighbor_results:
            if isinstance(result, Exception):
                continue
                
            neighbor_entities, neighbor_relationships = result
            
            # Add entities
            for entity in neighbor_entities:
                all_entities[entity.id] = entity
            
            # Add relationships
            for rel in neighbor_relationships:
                key = (rel.source_id, rel.type, rel.target_id)
                all_relationships[key] = rel
        
        return list(all_entities.values()), list(all_relationships.values())

    async def answer_query_consolidated(
        self,
        query_text: str,
        config: Dict[str, Any] = None,
        conversation_id: str = None,
    ) -> ConsolidatedAnswer:
        """Generate a consolidated answer with dual-purpose format."""
        
        logger.info(f"Generating consolidated answer for query: '{query_text}'")
        config = config or {}
        
        try:
            # Retrieve and build context
            retrieved_chunks, graph_context = await self._retrieve_and_build_context(
                query_text, config
            )
            
            if not retrieved_chunks:
                return ConsolidatedAnswer(
                    answer="No relevant information found to answer the query.",
                    confidence_score=0.0,
                    metadata={"error": "no_context_found", "query": query_text}
                )
            
            # Generate enhanced answer
            enhanced_result = await self._generate_enhanced_answer(
                query_text, retrieved_chunks, graph_context, config, conversation_id
            )
            
            # Extract architectural patterns and metrics from consolidated chunks
            architectural_patterns = await self._extract_architectural_patterns(retrieved_chunks)
            success_metrics = await self._extract_success_metrics(retrieved_chunks)
            best_practices = await self._extract_best_practices(retrieved_chunks)
            
            # Build machine-readable format
            machine_readable = self._build_machine_readable_format(
                retrieved_chunks, graph_context, architectural_patterns, success_metrics
            )
            
            # Calculate consolidated confidence
            consolidation_confidence = self._calculate_consolidation_confidence(
                retrieved_chunks, architectural_patterns, success_metrics
            )
            
            # Prepare sources and citations
            sources = self._prepare_sources(retrieved_chunks)
            citations = getattr(enhanced_result, 'citations', [])
            bibliography = getattr(enhanced_result, 'bibliography', {})
            
            return ConsolidatedAnswer(
                answer=enhanced_result.text if hasattr(enhanced_result, 'text') else str(enhanced_result),
                answer_with_citations=getattr(enhanced_result, 'answer_with_citations', None),
                consolidated_chunks=[chunk.chunk for chunk in retrieved_chunks],
                architectural_patterns=architectural_patterns,
                success_metrics=success_metrics,
                best_practices=best_practices,
                confidence_score=getattr(enhanced_result, 'confidence_score', 0.5),
                consolidation_confidence=consolidation_confidence,
                evidence_ranking=self._calculate_evidence_ranking(architectural_patterns, success_metrics),
                sources=sources,
                citations=citations,
                bibliography=bibliography,
                machine_readable=machine_readable,
                metadata={
                    "query": query_text,
                    "chunks_count": len(retrieved_chunks),
                    "patterns_count": len(architectural_patterns),
                    "metrics_count": len(success_metrics),
                    "engine_type": "ImprovedSynapseEngine",
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating consolidated answer: {e}", exc_info=True)
            return ConsolidatedAnswer(
                answer=f"Error generating answer: {e}",
                confidence_score=0.0,
                metadata={"error": str(e), "query": query_text}
            )

    async def _generate_enhanced_answer(
        self,
        query_text: str,
        chunks: List[SearchResultData],
        graph_context: Optional[Tuple[List[Entity], List[Relationship]]],
        config: Dict[str, Any],
        conversation_id: str = None,
    ):
        """Generate enhanced answer using LLM service."""
        
        # Prepare context
        context_str = self._prepare_context_string(chunks, graph_context)
        
        # Get conversation context if available
        conversation_context = ""
        if conversation_id and self._context_manager:
            try:
                conversation_context = await self._context_manager.get_conversation_context(conversation_id)
                if conversation_context:
                    conversation_context = f"\n\n{conversation_context}\n\n"
            except Exception as e:
                logger.warning(f"Failed to get conversation context: {e}")
        
        # Create optimized prompt
        style = self._prompt_optimizer.get_style_from_string(config.get("style", "analytical"))
        prompt = self._prompt_optimizer.optimize_prompt_for_context(
            query=query_text,
            context=context_str,
            style=style,
            conversation_history=conversation_context,
            confidence_scoring=True,
            citation_required=True,
            max_length=config.get("max_response_length")
        )
        
        # Generate response
        if hasattr(self._llm_service, 'generate_enhanced_response'):
            context_chunks = [c.chunk for c in chunks]
            return await self._llm_service.generate_enhanced_response(
                prompt=prompt,
                context=context_str,
                context_chunks=context_chunks,
                query=query_text,
                context_texts=[c.chunk.text for c in chunks]
            )
        else:
            # Fallback to standard response
            return await self._llm_service.generate_response(prompt)

    def _prepare_context_string(
        self, 
        chunks: List[SearchResultData], 
        graph_context: Optional[Tuple[List[Entity], List[Relationship]]]
    ) -> str:
        """Prepare context string from chunks and graph data."""
        
        context_parts = []
        
        # Add chunk contexts
        if chunks:
            context_parts.append("Relevant Information:")
            for i, chunk_result in enumerate(chunks, 1):
                chunk = chunk_result.chunk
                metadata_info = ""
                if chunk.metadata:
                    if chunk.metadata.get("consolidation_group"):
                        metadata_info = f" [Consolidated from {chunk.metadata.get('consolidated_from', 1)} sources]"
                    if chunk.metadata.get("score_blended"):
                        metadata_info += f" [Relevance: {chunk.metadata.get('score_blended', 0):.2f}]"
                
                context_parts.append(f"{i}. {chunk.text}{metadata_info}")
        
        # Add graph context
        if graph_context:
            entities, relationships = graph_context
            if entities:
                context_parts.append("\nRelated Entities:")
                for entity in entities[:10]:  # Limit to avoid context overflow
                    context_parts.append(f"- {entity.id} ({entity.type}): {getattr(entity, 'name', 'N/A')}")
            
            if relationships:
                context_parts.append("\nRelated Relationships:")
                for rel in relationships[:10]:  # Limit to avoid context overflow
                    context_parts.append(f"- ({rel.source_id}) -[{rel.type}]-> ({rel.target_id})")
        
        return "\n".join(context_parts)

    async def _extract_architectural_patterns(
        self, chunks: List[SearchResultData]
    ) -> List[Dict[str, Any]]:
        """Extract architectural patterns from retrieved chunks."""
        
        try:
            combined_text = " ".join([chunk.chunk.text for chunk in chunks])
            patterns = await self._experiment_consolidator.pattern_recognizer.identify_patterns(combined_text)
            
            return [
                {
                    "pattern_name": pattern.pattern_name,
                    "description": pattern.description,
                    "benefits": pattern.benefits,
                    "challenges": pattern.challenges,
                    "use_cases": pattern.use_cases,
                    "evidence_strength": pattern.evidence_strength,
                }
                for pattern in patterns
            ]
        except Exception as e:
            logger.error(f"Error extracting architectural patterns: {e}")
            return []

    async def _extract_success_metrics(
        self, chunks: List[SearchResultData]
    ) -> List[Dict[str, Any]]:
        """Extract success metrics from retrieved chunks."""
        
        try:
            combined_text = " ".join([chunk.chunk.text for chunk in chunks])
            metrics = await self._experiment_consolidator.metrics_extractor.extract_metrics(combined_text)
            
            return [
                {
                    "metric_type": metric.metric_type.value if hasattr(metric.metric_type, 'value') else str(metric.metric_type),
                    "value": metric.value,
                    "unit": metric.unit,
                    "context": metric.context,
                    "source_location": metric.source_location,
                    "confidence_score": metric.confidence_score,
                }
                for metric in metrics
            ]
        except Exception as e:
            logger.error(f"Error extracting success metrics: {e}")
            return []

    async def _extract_best_practices(
        self, chunks: List[SearchResultData]
    ) -> List[str]:
        """Extract best practices from retrieved chunks."""
        
        try:
            combined_text = " ".join([chunk.chunk.text for chunk in chunks])
            return await self._experiment_consolidator.pattern_recognizer.extract_best_practices(combined_text)
        except Exception as e:
            logger.error(f"Error extracting best practices: {e}")
            return []

    def _build_machine_readable_format(
        self,
        chunks: List[SearchResultData],
        graph_context: Optional[Tuple[List[Entity], List[Relationship]]],
        patterns: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build machine-readable structured data format."""
        
        machine_readable = {
            "concepts": [],
            "relationships": [],
            "evidence": [],
            "patterns": patterns,
            "metrics": metrics,
        }
        
        # Extract concepts from chunks
        for chunk in chunks:
            machine_readable["concepts"].append({
                "id": chunk.chunk.id,
                "text": chunk.chunk.text[:200],  # Truncate for machine processing
                "document_id": chunk.chunk.document_id,
                "score": chunk.score,
                "metadata": chunk.chunk.metadata,
            })
        
        # Add graph relationships
        if graph_context:
            entities, relationships = graph_context
            for rel in relationships:
                machine_readable["relationships"].append({
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    "type": rel.type,
                    "properties": getattr(rel, 'properties', {}),
                })
        
        # Add evidence
        for metric in metrics:
            machine_readable["evidence"].append({
                "type": "metric",
                "value": metric["value"],
                "unit": metric["unit"],
                "confidence": metric["confidence_score"],
                "context": metric["context"][:100],  # Truncate for machine processing
            })
        
        return machine_readable

    def _calculate_consolidation_confidence(
        self,
        chunks: List[SearchResultData],
        patterns: List[Dict[str, Any]],
        metrics: List[Dict[str, Any]],
    ) -> float:
        """Calculate confidence in the consolidation process."""
        
        # Base confidence from chunk scores
        chunk_confidence = 0.0
        if chunks:
            avg_score = sum(chunk.score for chunk in chunks) / len(chunks)
            chunk_confidence = min(1.0, avg_score)
        
        # Pattern confidence
        pattern_confidence = 0.0
        if patterns:
            avg_evidence = sum(p["evidence_strength"] for p in patterns) / len(patterns)
            pattern_confidence = avg_evidence
        
        # Metrics confidence
        metrics_confidence = 0.0
        if metrics:
            avg_confidence = sum(m["confidence_score"] for m in metrics) / len(metrics)
            metrics_confidence = avg_confidence
        
        # Weighted combination
        total_confidence = (
            chunk_confidence * 0.4 +
            pattern_confidence * 0.3 +
            metrics_confidence * 0.3
        )
        
        return min(1.0, total_confidence)

    def _calculate_evidence_ranking(
        self, patterns: List[Dict[str, Any]], metrics: List[Dict[str, Any]]
    ) -> float:
        """Calculate evidence ranking for the consolidated answer."""
        
        if not patterns and not metrics:
            return 0.0
        
        # High-confidence metrics weight
        high_conf_metrics = [m for m in metrics if m["confidence_score"] > 0.7]
        metrics_score = len(high_conf_metrics) * 0.2
        
        # Strong evidence patterns weight
        strong_patterns = [p for p in patterns if p["evidence_strength"] > 0.6]
        patterns_score = len(strong_patterns) * 0.15
        
        return min(1.0, metrics_score + patterns_score)

    def _prepare_sources(self, chunks: List[SearchResultData]) -> List[Dict[str, Any]]:
        """Prepare source information for citations."""
        
        sources = []
        for chunk in chunks:
            source = {
                "id": chunk.chunk.id,
                "document_id": chunk.chunk.document_id,
                "score": chunk.score,
                "text_preview": chunk.chunk.text[:100],
            }
            
            if chunk.chunk.metadata:
                source["metadata"] = chunk.chunk.metadata
                if chunk.chunk.metadata.get("consolidation_group"):
                    source["consolidated_from"] = chunk.chunk.metadata.get("consolidated_from", 1)
            
            sources.append(source)
        
        return sources

    # Implement required abstract methods from GraphRAGEngine
    async def query(self, query_text: str, config: Dict[str, Any] = None) -> Any:
        """Standard query interface - returns consolidated answer."""
        return await self.answer_query_consolidated(query_text, config)

    async def stream_context(self, query: str, search_type: str = "vector", limit: int = 5):
        """Stream context chunks."""
        chunks = await self.retrieve_context(query, search_type, limit)
        for chunk in chunks:
            yield chunk

    # Additional convenience methods
    async def get_vector_store_status(self) -> Dict[str, Any]:
        """Get status information about the vector store."""
        try:
            size = await self._vector_store.get_vector_store_size()
            return {
                "vector_count": size,
                "store_type": type(self._vector_store).__name__,
                "is_persistent": isinstance(self._vector_store, SharedPersistentVectorStore),
                "storage_path": getattr(self._vector_store, 'storage_path', None),
            }
        except Exception as e:
            return {"error": str(e), "vector_count": 0}

    async def add_chunks_to_store(self, chunks: List[ChunkData]) -> None:
        """Add chunks to the persistent vector store."""
        await self._vector_store.add_chunks(chunks)
        logger.info(f"Added {len(chunks)} chunks to persistent vector store")