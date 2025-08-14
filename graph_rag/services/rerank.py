from __future__ import annotations

import logging
import math
from enum import Enum
from typing import List

from graph_rag.core.interfaces import SearchResultData

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Lightweight reranker wrapper.

    If cross-encoder model is unavailable, acts as a no-op returning the top-k input.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._available = False
        try:  # optional dependency
            from sentence_transformers import CrossEncoder  # noqa: F401

            self._available = True
        except Exception:
            self._available = False

    async def rerank(
        self, query: str, items: List[SearchResultData], k: int
    ) -> List[SearchResultData]:
        if not items:
            return []
        if not self._available:
            # Best effort: return as-is
            return items[:k]
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(self.model_name)
            pairs = [(query, it.chunk.text) for it in items]
            scores = model.predict(pairs)
            # Attach scores and sort
            rescored: List[SearchResultData] = []
            for it, s in zip(items, scores):
                try:
                    it.score = float(s)  # type: ignore[attr-defined]
                    if hasattr(it, "chunk") and hasattr(it.chunk, "metadata"):
                        meta = it.chunk.metadata or {}
                        meta["score_rerank"] = float(s)
                        it.chunk.metadata = meta
                except Exception:
                    pass
                rescored.append(it)
            rescored.sort(key=lambda x: getattr(x, "score", 0.0), reverse=True)
            return rescored[:k]
        except Exception:
            # Fallback
            return items[:k]


class ReRankingStrategy(Enum):
    """Available re-ranking strategies."""
    SEMANTIC_SIMILARITY = "semantic_similarity"
    BM25_SCORING = "bm25_scoring"
    HYBRID_SCORING = "hybrid_scoring"
    QUERY_TERM_FREQUENCY = "query_term_frequency"
    CROSS_ENCODER = "cross_encoder"


class ReRankingService:
    """Service for re-ranking search results to improve relevance."""

    def __init__(self):
        """Initialize the re-ranking service."""
        self.cross_encoder = CrossEncoderReranker()

    def rerank(
        self,
        query: str,
        results: List[SearchResultData],
        strategy: ReRankingStrategy = ReRankingStrategy.SEMANTIC_SIMILARITY,
    ) -> List[SearchResultData]:
        """Re-rank search results based on relevance to the query.
        
        Args:
            query: The original search query
            results: List of search results to re-rank
            strategy: Re-ranking strategy to use
            
        Returns:
            Re-ranked list of search results
        """
        if not results:
            return results
            
        if strategy == ReRankingStrategy.CROSS_ENCODER:
            # Use existing cross-encoder implementation
            import asyncio
            return asyncio.run(self.cross_encoder.rerank(query, results, len(results)))
        elif strategy == ReRankingStrategy.SEMANTIC_SIMILARITY:
            return self._semantic_rerank(query, results)
        elif strategy == ReRankingStrategy.BM25_SCORING:
            return self._bm25_rerank(query, results)
        elif strategy == ReRankingStrategy.HYBRID_SCORING:
            return self._hybrid_rerank(query, results)
        else:
            return self._query_term_frequency_rerank(query, results)

    def _semantic_rerank(self, query: str, results: List[SearchResultData]) -> List[SearchResultData]:
        """Re-rank based on semantic similarity to query."""
        query_terms = set(query.lower().split())
        
        def semantic_score(result: SearchResultData) -> float:
            text = result.chunk.text.lower()
            text_terms = set(text.split())
            
            # Calculate Jaccard similarity
            intersection = len(query_terms.intersection(text_terms))
            union = len(query_terms.union(text_terms))
            jaccard = intersection / union if union > 0 else 0
            
            # Calculate query coverage (how much of query is covered)
            coverage = intersection / len(query_terms) if query_terms else 0
            
            # Calculate text relevance (inverse document frequency-like measure)
            text_length = len(text_terms)
            relevance = intersection / math.sqrt(text_length) if text_length > 0 else 0
            
            # Combine scores with original search score
            combined = (result.score * 0.4) + (jaccard * 0.2) + (coverage * 0.3) + (relevance * 0.1)
            return combined
        
        reranked = sorted(results, key=semantic_score, reverse=True)
        
        # Update scores
        for result in reranked:
            result.score = semantic_score(result)
            
        return reranked

    def _bm25_rerank(self, query: str, results: List[SearchResultData]) -> List[SearchResultData]:
        """Re-rank using BM25-inspired scoring."""
        query_terms = query.lower().split()
        
        # Calculate document frequency for each term across all results
        term_doc_freq = {}
        total_docs = len(results)
        
        for result in results:
            text_terms = set(result.chunk.text.lower().split())
            for term in query_terms:
                if term in text_terms:
                    term_doc_freq[term] = term_doc_freq.get(term, 0) + 1
        
        def bm25_score(result: SearchResultData) -> float:
            text = result.chunk.text.lower()
            text_terms = text.split()
            text_length = len(text_terms)
            
            # BM25 parameters
            k1 = 1.5
            b = 0.75
            avg_doc_length = sum(len(r.chunk.text.split()) for r in results) / len(results)
            
            score = 0.0
            for term in query_terms:
                if term in text:
                    # Term frequency
                    tf = text_terms.count(term)
                    # Document frequency
                    df = term_doc_freq.get(term, 0)
                    if df == 0:
                        continue
                        
                    # IDF calculation
                    idf = math.log((total_docs - df + 0.5) / (df + 0.5))
                    
                    # BM25 formula
                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (text_length / avg_doc_length))
                    score += idf * (numerator / denominator)
            
            # Combine with original score
            return (result.score * 0.3) + (score * 0.7)
        
        reranked = sorted(results, key=bm25_score, reverse=True)
        
        # Update scores
        for result in reranked:
            result.score = bm25_score(result)
            
        return reranked

    def _hybrid_rerank(self, query: str, results: List[SearchResultData]) -> List[SearchResultData]:
        """Combine multiple re-ranking strategies."""
        # Apply semantic re-ranking first
        semantic_results = self._semantic_rerank(query, results.copy())
        
        # Apply BM25 re-ranking
        bm25_results = self._bm25_rerank(query, results.copy())
        
        # Create ranking position maps
        semantic_ranks = {r.chunk.id: i for i, r in enumerate(semantic_results)}
        bm25_ranks = {r.chunk.id: i for i, r in enumerate(bm25_results)}
        
        def hybrid_score(result: SearchResultData) -> float:
            semantic_rank = semantic_ranks.get(result.chunk.id, len(results))
            bm25_rank = bm25_ranks.get(result.chunk.id, len(results))
            
            # Rank fusion using reciprocal rank
            semantic_score = 1.0 / (semantic_rank + 1)
            bm25_score = 1.0 / (bm25_rank + 1)
            
            # Combine with original score
            return (result.score * 0.4) + (semantic_score * 0.3) + (bm25_score * 0.3)
        
        reranked = sorted(results, key=hybrid_score, reverse=True)
        
        # Update scores
        for result in reranked:
            result.score = hybrid_score(result)
            
        return reranked

    def _query_term_frequency_rerank(self, query: str, results: List[SearchResultData]) -> List[SearchResultData]:
        """Simple re-ranking based on query term frequency."""
        query_terms = query.lower().split()
        
        def term_frequency_score(result: SearchResultData) -> float:
            text = result.chunk.text.lower()
            
            # Count occurrences of each query term
            total_matches = sum(text.count(term) for term in query_terms)
            
            # Normalize by text length
            text_length = len(text.split())
            normalized_tf = total_matches / text_length if text_length > 0 else 0
            
            # Combine with original score
            return (result.score * 0.6) + (normalized_tf * 0.4)
        
        reranked = sorted(results, key=term_frequency_score, reverse=True)
        
        # Update scores
        for result in reranked:
            result.score = term_frequency_score(result)
            
        return reranked

    async def rerank_results(
        self,
        query: str,
        results: List[SearchResultData],
        strategy: str = "semantic_similarity",
    ) -> List[SearchResultData]:
        """Legacy async method for backwards compatibility."""
        strategy_enum = ReRankingStrategy.SEMANTIC_SIMILARITY
        try:
            strategy_enum = ReRankingStrategy(strategy)
        except ValueError:
            logger.warning(f"Unknown strategy {strategy}, using semantic_similarity")
            
        return self.rerank(query, results, strategy_enum)
