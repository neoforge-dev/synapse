"""Advanced retrieval patterns for sophisticated information retrieval."""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from collections import defaultdict, Counter

from pydantic import BaseModel

from graph_rag.core.interfaces import SearchResultData, ChunkData, VectorStore, GraphRepository
from graph_rag.services.search import AdvancedSearchService, SearchStrategy
from graph_rag.services.clustering import SemanticClusteringService, ClusteringStrategy

logger = logging.getLogger(__name__)


class RetrievalStrategy(Enum):
    """Advanced retrieval strategies."""
    MULTI_HOP = "multi_hop"
    ADAPTIVE = "adaptive" 
    CONTEXT_AWARE = "context_aware"
    ENSEMBLE = "ensemble"
    INCREMENTAL = "incremental"
    CONCEPT_EXPANSION = "concept_expansion"
    RELEVANCE_FEEDBACK = "relevance_feedback"


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    MULTI_FACETED = "multi_faceted"


@dataclass
class RetrievalContext:
    """Context for retrieval operations."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_history: List[str] = None
    preferences: Dict[str, Any] = None
    previous_results: List[SearchResultData] = None
    domain_context: Optional[str] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.preferences is None:
            self.preferences = {}
        if self.previous_results is None:
            self.previous_results = []


class RetrievalResult(BaseModel):
    """Result from advanced retrieval operation."""
    results: List[SearchResultData]
    strategy_used: RetrievalStrategy
    query: str
    execution_time_ms: float
    confidence_score: float
    explanation: str
    hops_performed: int = 0
    strategies_tried: List[str] = []
    context_factors: Dict[str, Any] = {}
    
    @property
    def result_count(self) -> int:
        return len(self.results)
    
    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)


class QueryAnalyzer:
    """Analyzes queries to determine appropriate retrieval strategies."""
    
    def __init__(self):
        # Keywords that indicate query complexity
        self.complex_indicators = {
            "compare", "contrast", "difference", "similar", "relationship",
            "how", "why", "what", "explain", "describe", "analyze",
            "multiple", "various", "different", "several"
        }
        
        self.temporal_indicators = {
            "before", "after", "during", "when", "since", "until",
            "recent", "latest", "current", "previous", "historical"
        }
        
        self.causal_indicators = {
            "because", "cause", "effect", "result", "lead to", "due to",
            "reason", "impact", "influence", "consequence"
        }
    
    def analyze_query(self, query: str, context: RetrievalContext) -> Dict[str, Any]:
        """Analyze query characteristics to inform retrieval strategy."""
        query_lower = query.lower()
        words = query_lower.split()
        
        analysis = {
            "complexity": self._assess_complexity(query, words),
            "intent": self._determine_intent(query_lower, words),
            "entities": self._extract_entities(query),
            "temporal_aspects": self._has_temporal_aspects(query_lower),
            "causal_aspects": self._has_causal_aspects(query_lower),
            "requires_multi_hop": self._requires_multi_hop(query_lower),
            "recommended_strategies": []
        }
        
        # Recommend strategies based on analysis
        analysis["recommended_strategies"] = self._recommend_strategies(analysis, context)
        
        return analysis
    
    def _assess_complexity(self, query: str, words: List[str]) -> QueryComplexity:
        """Assess the complexity of the query."""
        # Simple heuristics for complexity assessment
        if len(words) <= 3:
            return QueryComplexity.SIMPLE
        
        complex_count = sum(1 for word in words if word in self.complex_indicators)
        
        if complex_count >= 2 or len(words) > 15:
            return QueryComplexity.COMPLEX
        elif complex_count >= 1 or len(words) > 8:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE
    
    def _determine_intent(self, query_lower: str, words: List[str]) -> str:
        """Determine the intent of the query."""
        if any(word in query_lower for word in ["compare", "contrast", "difference"]):
            return "comparison"
        elif any(word in query_lower for word in ["explain", "how", "why"]):
            return "explanation"
        elif any(word in query_lower for word in ["list", "show", "find", "get"]):
            return "factual"
        elif any(word in query_lower for word in ["similar", "related", "like"]):
            return "similarity"
        else:
            return "general"
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential entities from the query."""
        import re
        entities = []
        
        # Find capitalized words (potential proper nouns)
        capitalized = re.findall(r'\b[A-Z][a-zA-Z]*\b', query)
        # Filter out common words
        common_words = {"What", "Where", "When", "Who", "Why", "How", "The", "This", "That", "And", "Or"}
        entities.extend([word for word in capitalized if word not in common_words and len(word) > 2])
        
        # Quoted phrases
        quoted = re.findall(r'"([^"]*)"', query)
        entities.extend(quoted)
        
        return entities
    
    def _has_temporal_aspects(self, query_lower: str) -> bool:
        """Check if query has temporal aspects."""
        return any(indicator in query_lower for indicator in self.temporal_indicators)
    
    def _has_causal_aspects(self, query_lower: str) -> bool:
        """Check if query has causal aspects."""
        return any(indicator in query_lower for indicator in self.causal_indicators)
    
    def _requires_multi_hop(self, query_lower: str) -> bool:
        """Determine if query requires multi-hop retrieval."""
        multi_hop_indicators = [
            "relationship", "connection", "related to", "caused by",
            "impact of", "influence on", "dependency", "interaction"
        ]
        return any(indicator in query_lower for indicator in multi_hop_indicators)
    
    def _recommend_strategies(
        self, 
        analysis: Dict[str, Any], 
        context: RetrievalContext
    ) -> List[RetrievalStrategy]:
        """Recommend retrieval strategies based on analysis."""
        strategies = []
        
        # Multi-hop for relationship queries
        if analysis["requires_multi_hop"] or analysis["intent"] == "similarity":
            strategies.append(RetrievalStrategy.MULTI_HOP)
        
        # Context-aware if we have history
        if context.conversation_history or context.previous_results:
            strategies.append(RetrievalStrategy.CONTEXT_AWARE)
        
        # Adaptive for complex queries
        if analysis["complexity"] in [QueryComplexity.COMPLEX, QueryComplexity.MULTI_FACETED]:
            strategies.append(RetrievalStrategy.ADAPTIVE)
        
        # Ensemble for comprehensive coverage
        if analysis["complexity"] == QueryComplexity.COMPLEX:
            strategies.append(RetrievalStrategy.ENSEMBLE)
        
        # Default to incremental if no specific strategy
        if not strategies:
            strategies.append(RetrievalStrategy.INCREMENTAL)
        
        return strategies


class AdvancedRetrievalService:
    """Service implementing advanced retrieval patterns."""
    
    def __init__(
        self,
        search_service: AdvancedSearchService,
        vector_store: VectorStore,
        graph_repository: GraphRepository,
        clustering_service: Optional[SemanticClusteringService] = None,
        max_hops: int = 3,
        max_results_per_hop: int = 10,
        relevance_threshold: float = 0.5
    ):
        """Initialize advanced retrieval service.
        
        Args:
            search_service: Advanced search service
            vector_store: Vector store for embeddings
            graph_repository: Graph repository for relationships
            clustering_service: Optional clustering service
            max_hops: Maximum number of hops for multi-hop retrieval
            max_results_per_hop: Maximum results to consider per hop
            relevance_threshold: Minimum relevance score to consider
        """
        self.search_service = search_service
        self.vector_store = vector_store
        self.graph_repository = graph_repository
        self.clustering_service = clustering_service
        self.max_hops = max_hops
        self.max_results_per_hop = max_results_per_hop
        self.relevance_threshold = relevance_threshold
        self.query_analyzer = QueryAnalyzer()
    
    async def advanced_retrieve(
        self,
        query: str,
        strategy: Optional[RetrievalStrategy] = None,
        context: Optional[RetrievalContext] = None,
        limit: int = 10
    ) -> RetrievalResult:
        """Perform advanced retrieval with sophisticated strategies.
        
        Args:
            query: Search query
            strategy: Specific strategy to use (if None, will be determined automatically)
            context: Retrieval context
            limit: Maximum number of results to return
            
        Returns:
            RetrievalResult with advanced retrieval results
        """
        start_time = time.time()
        
        if context is None:
            context = RetrievalContext()
        
        # Analyze query to determine best strategy
        analysis = self.query_analyzer.analyze_query(query, context)
        
        if strategy is None:
            # Use the first recommended strategy
            strategy = analysis["recommended_strategies"][0] if analysis["recommended_strategies"] else RetrievalStrategy.ADAPTIVE
        
        logger.info(f"Using {strategy.value} strategy for query: {query}")
        
        # Execute the chosen strategy
        if strategy == RetrievalStrategy.MULTI_HOP:
            results, hops, explanation = await self._multi_hop_retrieval(query, context, limit)
        elif strategy == RetrievalStrategy.ADAPTIVE:
            results, hops, explanation = await self._adaptive_retrieval(query, context, limit)
        elif strategy == RetrievalStrategy.CONTEXT_AWARE:
            results, hops, explanation = await self._context_aware_retrieval(query, context, limit)
        elif strategy == RetrievalStrategy.ENSEMBLE:
            results, hops, explanation = await self._ensemble_retrieval(query, context, limit)
        elif strategy == RetrievalStrategy.INCREMENTAL:
            results, hops, explanation = await self._incremental_retrieval(query, context, limit)
        elif strategy == RetrievalStrategy.CONCEPT_EXPANSION:
            results, hops, explanation = await self._concept_expansion_retrieval(query, context, limit)
        else:
            # Fallback to basic search
            search_result = await self.search_service.search(query, limit=limit)
            results = search_result.results
            hops = 0
            explanation = "Used basic search as fallback"
        
        execution_time = (time.time() - start_time) * 1000
        
        # Calculate confidence score
        confidence = self._calculate_confidence(results, analysis, strategy)
        
        return RetrievalResult(
            results=results[:limit],
            strategy_used=strategy,
            query=query,
            execution_time_ms=execution_time,
            confidence_score=confidence,
            explanation=explanation,
            hops_performed=hops,
            strategies_tried=[strategy.value],
            context_factors=analysis
        )
    
    async def _multi_hop_retrieval(
        self,
        query: str,
        context: RetrievalContext,
        limit: int
    ) -> Tuple[List[SearchResultData], int, str]:
        """Perform multi-hop retrieval to find related information."""
        all_results = []
        visited_entities = set()
        current_query = query
        
        for hop in range(self.max_hops):
            logger.debug(f"Multi-hop retrieval hop {hop + 1}: {current_query}")
            
            # Search for current query
            search_result = await self.search_service.search(
                current_query,
                strategy=SearchStrategy.HYBRID,
                limit=self.max_results_per_hop
            )
            
            hop_results = [r for r in search_result.results if r.score >= self.relevance_threshold]
            all_results.extend(hop_results)
            
            if not hop_results:
                break
            
            # Extract entities from results for next hop
            new_entities = self._extract_entities_from_results(hop_results)
            
            # Filter out already visited entities
            new_entities = [e for e in new_entities if e not in visited_entities]
            visited_entities.update(new_entities)
            
            if not new_entities:
                break
            
            # Prepare query for next hop using discovered entities
            current_query = self._build_entity_query(new_entities[:3])  # Use top 3 entities
        
        # Deduplicate and rank results
        unique_results = self._deduplicate_results(all_results)
        ranked_results = sorted(unique_results, key=lambda x: x.score, reverse=True)
        
        explanation = f"Performed {hop + 1} hops, found {len(unique_results)} unique results"
        return ranked_results, hop + 1, explanation
    
    async def _adaptive_retrieval(
        self,
        query: str,
        context: RetrievalContext,
        limit: int
    ) -> Tuple[List[SearchResultData], int, str]:
        """Adaptive retrieval that adjusts strategy based on intermediate results."""
        strategies_tried = []
        all_results = []
        
        # Start with hybrid search
        strategies_tried.append("hybrid")
        search_result = await self.search_service.search(
            query,
            strategy=SearchStrategy.HYBRID,
            limit=limit * 2  # Get more for adaptation
        )
        
        initial_results = search_result.results
        all_results.extend(initial_results)
        
        # Analyze quality of initial results
        avg_score = sum(r.score for r in initial_results) / len(initial_results) if initial_results else 0
        
        # If results are poor, try different strategies
        if avg_score < 0.7 and len(initial_results) < limit:
            # Try vector-only search
            strategies_tried.append("vector_only")
            vector_result = await self.search_service.search(
                query,
                strategy=SearchStrategy.VECTOR_ONLY,
                limit=limit
            )
            all_results.extend(vector_result.results)
            
            # If still poor, try query expansion
            if avg_score < 0.5:
                strategies_tried.append("query_expansion")
                expanded_result = await self.search_service.search(
                    query,
                    strategy=SearchStrategy.HYBRID,
                    expand_query=True,
                    limit=limit
                )
                all_results.extend(expanded_result.results)
        
        # Deduplicate and rank
        unique_results = self._deduplicate_results(all_results)
        ranked_results = sorted(unique_results, key=lambda x: x.score, reverse=True)
        
        explanation = f"Adaptive strategy tried: {', '.join(strategies_tried)}"
        return ranked_results, 0, explanation
    
    async def _context_aware_retrieval(
        self,
        query: str,
        context: RetrievalContext,
        limit: int
    ) -> Tuple[List[SearchResultData], int, str]:
        """Context-aware retrieval using conversation history and preferences."""
        # Expand query with context
        expanded_query = self._expand_query_with_context(query, context)
        
        # Perform search with expanded query
        search_result = await self.search_service.search(
            expanded_query,
            strategy=SearchStrategy.HYBRID,
            limit=limit * 2
        )
        
        results = search_result.results
        
        # Re-rank based on context relevance
        context_ranked = self._rerank_by_context(results, context)
        
        explanation = f"Context-aware search with expanded query, re-ranked {len(results)} results"
        return context_ranked, 0, explanation
    
    async def _ensemble_retrieval(
        self,
        query: str,
        context: RetrievalContext,
        limit: int
    ) -> Tuple[List[SearchResultData], int, str]:
        """Ensemble retrieval combining multiple strategies."""
        # Run multiple strategies in parallel
        tasks = [
            self.search_service.search(query, strategy=SearchStrategy.VECTOR_ONLY, limit=limit),
            self.search_service.search(query, strategy=SearchStrategy.KEYWORD_ONLY, limit=limit),
            self.search_service.search(query, strategy=SearchStrategy.HYBRID, limit=limit),
        ]
        
        # Add query expansion if available
        tasks.append(
            self.search_service.search(query, strategy=SearchStrategy.HYBRID, 
                                     expand_query=True, limit=limit)
        )
        
        # Execute all strategies
        strategy_results = await asyncio.gather(*tasks)
        
        # Combine results with weighted scores
        all_results = []
        weights = [0.3, 0.2, 0.4, 0.1]  # Vector, keyword, hybrid, expanded
        
        for i, result in enumerate(strategy_results):
            for r in result.results:
                # Create weighted copy
                weighted_result = SearchResultData(
                    chunk=r.chunk,
                    score=r.score * weights[i],
                    document=r.document
                )
                all_results.append(weighted_result)
        
        # Deduplicate and rank
        unique_results = self._deduplicate_results(all_results)
        ranked_results = sorted(unique_results, key=lambda x: x.score, reverse=True)
        
        explanation = f"Ensemble of {len(strategy_results)} strategies, combined {len(unique_results)} unique results"
        return ranked_results, 0, explanation
    
    async def _incremental_retrieval(
        self,
        query: str,
        context: RetrievalContext,
        limit: int
    ) -> Tuple[List[SearchResultData], int, str]:
        """Incremental retrieval with progressive refinement."""
        results = []
        current_limit = min(5, limit)  # Start small
        
        while len(results) < limit and current_limit <= limit * 2:
            # Search with current limit
            search_result = await self.search_service.search(
                query,
                strategy=SearchStrategy.HYBRID,
                limit=current_limit
            )
            
            new_results = search_result.results
            
            # Check if we have enough high-quality results
            high_quality = [r for r in new_results if r.score >= self.relevance_threshold]
            
            if len(high_quality) >= limit:
                results = high_quality[:limit]
                break
            
            # Add good results and increase search scope
            results.extend(high_quality)
            current_limit = min(current_limit * 2, limit * 2)
            
            # If no new high-quality results, stop
            if not high_quality:
                break
        
        # Deduplicate
        unique_results = self._deduplicate_results(results)
        
        explanation = f"Incremental retrieval with progressive limits, final: {len(unique_results)} results"
        return unique_results[:limit], 0, explanation
    
    async def _concept_expansion_retrieval(
        self,
        query: str,
        context: RetrievalContext,
        limit: int
    ) -> Tuple[List[SearchResultData], int, str]:
        """Concept expansion retrieval using semantic relationships."""
        # Get initial results
        initial_result = await self.search_service.search(
            query,
            strategy=SearchStrategy.VECTOR_ONLY,
            limit=limit // 2
        )
        
        initial_results = initial_result.results
        
        # Extract concepts from initial results
        concepts = self._extract_concepts_from_results(initial_results)
        
        # Search for each concept
        concept_results = []
        for concept in concepts[:5]:  # Limit concept expansion
            concept_result = await self.search_service.search(
                concept,
                strategy=SearchStrategy.VECTOR_ONLY,
                limit=5
            )
            concept_results.extend(concept_result.results)
        
        # Combine and deduplicate
        all_results = initial_results + concept_results
        unique_results = self._deduplicate_results(all_results)
        ranked_results = sorted(unique_results, key=lambda x: x.score, reverse=True)
        
        explanation = f"Concept expansion with {len(concepts)} concepts, found {len(unique_results)} results"
        return ranked_results, 0, explanation
    
    def _extract_entities_from_results(self, results: List[SearchResultData]) -> List[str]:
        """Extract entities from search results for multi-hop."""
        entities = []
        
        for result in results:
            # Extract from metadata if available
            if result.chunk.metadata:
                chunk_entities = result.chunk.metadata.get("entities", [])
                if isinstance(chunk_entities, list):
                    entities.extend(chunk_entities)
            
            # Simple entity extraction from text
            text_entities = self._extract_entities_from_text(result.chunk.text)
            entities.extend(text_entities)
        
        # Return most frequent entities
        entity_counts = Counter(entities)
        return [entity for entity, count in entity_counts.most_common(10)]
    
    def _extract_entities_from_text(self, text: str) -> List[str]:
        """Simple entity extraction from text."""
        import re
        
        # Find capitalized words including compound proper nouns
        entities = re.findall(r'\b[A-Z][a-zA-Z]*\b', text)
        
        # Filter common words
        common_words = {"The", "This", "That", "These", "Those", "A", "An", "And", "Or", "But", "In", "On", "At", "To", "For", "Of", "With", "By"}
        entities = [e for e in entities if e not in common_words and len(e) > 2]
        
        return entities[:5]  # Return top 5
    
    def _build_entity_query(self, entities: List[str]) -> str:
        """Build a query from extracted entities."""
        return " OR ".join(f'"{entity}"' for entity in entities)
    
    def _extract_concepts_from_results(self, results: List[SearchResultData]) -> List[str]:
        """Extract key concepts from search results."""
        concepts = []
        
        for result in results:
            # Extract from metadata topics
            if result.chunk.metadata:
                topics = result.chunk.metadata.get("topics", [])
                if isinstance(topics, list):
                    concepts.extend(topics)
            
            # Extract keywords from text
            text_concepts = self._extract_keywords_from_text(result.chunk.text)
            concepts.extend(text_concepts)
        
        # Return most frequent concepts
        concept_counts = Counter(concepts)
        return [concept for concept, count in concept_counts.most_common(10)]
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction - could be enhanced with NLP
        words = text.lower().split()
        
        # Filter out common words and short words
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "about", "into", "through",
            "during", "before", "after", "above", "below", "up", "down",
            "out", "off", "over", "under", "again", "further", "then", "once"
        }
        
        keywords = [word for word in words 
                   if len(word) > 3 and word not in common_words and word.isalpha()]
        
        return keywords[:10]
    
    def _expand_query_with_context(self, query: str, context: RetrievalContext) -> str:
        """Expand query using conversation context."""
        expanded_terms = []
        
        # Add terms from conversation history
        for previous_query in context.conversation_history[-3:]:  # Last 3 queries
            # Extract key terms
            key_terms = self._extract_keywords_from_text(previous_query)
            expanded_terms.extend(key_terms[:2])  # Top 2 terms per query
        
        # Add domain context
        if context.domain_context:
            expanded_terms.append(context.domain_context)
        
        # Add preference-based terms
        if context.preferences:
            pref_terms = context.preferences.get("topics", [])
            if isinstance(pref_terms, list):
                expanded_terms.extend(pref_terms[:2])
        
        # Combine with original query
        if expanded_terms:
            unique_terms = list(set(expanded_terms))
            return f"{query} {' '.join(unique_terms[:3])}"  # Add top 3 unique terms
        
        return query
    
    def _rerank_by_context(
        self, 
        results: List[SearchResultData], 
        context: RetrievalContext
    ) -> List[SearchResultData]:
        """Re-rank results based on context relevance."""
        if not results:
            return results
        
        # Calculate context relevance for each result
        for result in results:
            context_score = self._calculate_context_relevance(result, context)
            # Combine with original score
            result.score = (result.score * 0.7) + (context_score * 0.3)
        
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def _calculate_context_relevance(
        self, 
        result: SearchResultData, 
        context: RetrievalContext
    ) -> float:
        """Calculate how relevant a result is given the context."""
        relevance = 0.0
        
        # Check similarity to conversation history
        if context.conversation_history:
            for previous_query in context.conversation_history:
                similarity = self._text_similarity(result.chunk.text, previous_query)
                relevance += similarity * 0.3
        
        # Check match with preferences
        if context.preferences and result.chunk.metadata:
            result_topics = result.chunk.metadata.get("topics", [])
            pref_topics = context.preferences.get("topics", [])
            
            if result_topics and pref_topics:
                topic_overlap = len(set(result_topics) & set(pref_topics))
                relevance += topic_overlap * 0.2
        
        # Check domain relevance
        if context.domain_context:
            domain_similarity = self._text_similarity(result.chunk.text, context.domain_context)
            relevance += domain_similarity * 0.2
        
        return min(relevance, 1.0)
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _deduplicate_results(self, results: List[SearchResultData]) -> List[SearchResultData]:
        """Remove duplicate results based on chunk ID."""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.chunk.id not in seen_ids:
                seen_ids.add(result.chunk.id)
                unique_results.append(result)
        
        return unique_results
    
    def _calculate_confidence(
        self,
        results: List[SearchResultData],
        analysis: Dict[str, Any],
        strategy: RetrievalStrategy
    ) -> float:
        """Calculate confidence score for the retrieval."""
        if not results:
            return 0.0
        
        # Base confidence on result quality
        avg_score = sum(r.score for r in results) / len(results)
        confidence = avg_score
        
        # Adjust based on query complexity
        complexity = analysis.get("complexity", QueryComplexity.SIMPLE)
        if complexity == QueryComplexity.SIMPLE:
            confidence *= 1.1
        elif complexity == QueryComplexity.COMPLEX:
            confidence *= 0.9
        
        # Adjust based on strategy appropriateness
        if strategy in analysis.get("recommended_strategies", []):
            confidence *= 1.1
        
        # Adjust based on result count
        if len(results) < 3:
            confidence *= 0.8
        elif len(results) > 10:
            confidence *= 1.05
        
        return min(confidence, 1.0)