import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from graph_rag.core.interfaces import GraphRepository, SearchResultData, VectorStore
from graph_rag.domain.models import Chunk
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.services.embedding import EmbeddingService


class SearchResult(BaseModel):
    """Represents a single search result, typically a chunk."""

    chunk_id: str
    document_id: str
    content: str
    score: float  # Relevance score (e.g., keyword match, similarity)


class SearchService:
    """Service for performing search operations over the graph."""

    def __init__(
        self, repository: MemgraphRepository, embedding_service: EmbeddingService
    ):
        self.repository = repository
        self.embedding_service = embedding_service  # Store the passed instance

    async def search_chunks(self, query: str, limit: int = 10) -> list[SearchResult]:
        """
        Search for relevant chunks based on a query string.

        Args:
            query: The search query string.
            limit: Maximum number of results to return.

        Returns:
            A list of SearchResult objects.
        """
        # 1. Call repository to get matching chunks
        matching_chunks: list[Chunk] = await self.repository.search_chunks_by_content(
            query, limit
        )

        # 2. Map chunks to SearchResult objects
        search_results = []
        for chunk in matching_chunks:
            # Simple scoring for now: 1.0 for any keyword match
            # Real implementation would use more sophisticated scoring
            score = 1.0
            search_results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.text,
                    score=score,
                )
            )

        # 3. Return results
        return search_results

    async def search_chunks_by_similarity(
        self, query: str, limit: int = 10
    ) -> list[SearchResult]:
        """
        Search for relevant chunks based on semantic similarity.

        Args:
            query: The search query string.
            limit: Maximum number of results to return.

        Returns:
            A list of SearchResult objects ordered by similarity score.
        """
        # 1. Generate embedding for the query
        query_vector = self.embedding_service.encode(query)
        if not isinstance(query_vector, list):
            # Handle potential errors during encoding if needed, though encode raises
            return []

        # 2. Call repository for similarity search
        # Repository returns List[tuple[Chunk, float]]
        results_with_scores = await self.repository.search_chunks_by_similarity(
            query_vector=query_vector, limit=limit
        )

        # 3. Map results to SearchResult objects
        search_results = [
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.text,
                score=score,  # Score is the similarity from the repository
            )
            for chunk, score in results_with_scores
        ]

        return search_results


class SearchStrategy(Enum):
    """Search strategy options for different types of retrieval."""
    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    GRAPH_ENHANCED = "graph_enhanced"


class QueryExpansion(BaseModel):
    """Represents an expanded query with additional terms."""
    original_query: str
    expanded_terms: list[str]
    expansion_strategy: str


class HybridSearchResult(BaseModel):
    """Result from hybrid search with metadata."""
    results: list[SearchResultData]
    strategy: SearchStrategy
    query: str
    total_vector_results: int
    total_keyword_results: int
    execution_time_ms: float
    reranked: bool = False
    clustered: bool = False
    cluster_count: int | None = None

    @property
    def total_results(self) -> int:
        return len(self.results)

    @property
    def avg_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)


class QueryExpansionService:
    """Service for expanding queries with synonyms and related terms."""

    def __init__(self):
        # Simple synonym/expansion mappings for common terms
        self.expansions = {
            "ml": ["machine learning", "artificial intelligence", "AI"],
            "ai": ["artificial intelligence", "machine learning", "ML"],
            "neural networks": ["deep learning", "artificial neural networks", "neural nets"],
            "deep learning": ["neural networks", "deep neural networks", "DNN"],
            "nlp": ["natural language processing", "text processing", "language models"],
            "computer vision": ["image processing", "visual recognition", "CV"],
            "data science": ["data analysis", "analytics", "data mining"],
            "python": ["programming", "coding", "software development"],
            "api": ["application programming interface", "service interface", "endpoint"],
            "database": ["db", "data storage", "persistence", "data store"],
        }

    def expand_query(self, query: str) -> QueryExpansion:
        """Expand a query with synonyms and related terms."""
        expanded_terms = []
        query_lower = query.lower()

        # Check for exact matches
        if query_lower in self.expansions:
            expanded_terms.extend(self.expansions[query_lower])

        # Check for partial matches
        for key, expansions in self.expansions.items():
            if key in query_lower:
                expanded_terms.extend(expansions)

        # Remove duplicates and terms already in query
        expanded_terms = list(set(expanded_terms))
        expanded_terms = [term for term in expanded_terms if term.lower() not in query_lower]

        return QueryExpansion(
            original_query=query,
            expanded_terms=expanded_terms,
            expansion_strategy="synonym_mapping"
        )


class AdvancedSearchService:
    """Advanced search service with hybrid search, re-ranking, query expansion, and clustering."""

    def __init__(
        self,
        vector_store: VectorStore,
        graph_repository: GraphRepository,
        rerank_service: Optional['ReRankingService'] = None,
        clustering_service: Optional['SemanticClusteringService'] = None
    ):
        self.vector_store = vector_store
        self.graph_repository = graph_repository
        self.rerank_service = rerank_service
        self.clustering_service = clustering_service
        self.query_expansion_service = QueryExpansionService()

    async def search(
        self,
        query: str,
        strategy: SearchStrategy = SearchStrategy.HYBRID,
        limit: int = 10,
        expand_query: bool = True,
        rerank: bool = True,
        cluster: bool = False,
        cluster_strategy: str | None = None,
        diversify_clusters: bool = True,
        threshold: float | None = None
    ) -> HybridSearchResult:
        """Perform advanced search with the specified strategy."""
        start_time = time.time()

        # Expand query if requested
        expanded_query = query
        if expand_query:
            expansion = self.query_expansion_service.expand_query(query)
            if expansion.expanded_terms:
                expanded_query = f"{query} {' '.join(expansion.expanded_terms[:3])}"  # Add top 3 terms

        # Perform search based on strategy
        if strategy == SearchStrategy.VECTOR_ONLY:
            results = await self._vector_search(expanded_query, limit, threshold)
            vector_count = len(results)
            keyword_count = 0
        elif strategy == SearchStrategy.KEYWORD_ONLY:
            results = await self._keyword_search(expanded_query, limit)
            vector_count = 0
            keyword_count = len(results)
        elif strategy == SearchStrategy.HYBRID:
            results, vector_count, keyword_count = await self._hybrid_search(expanded_query, limit, threshold)
        else:
            # Default to hybrid for unsupported strategies
            results, vector_count, keyword_count = await self._hybrid_search(expanded_query, limit, threshold)

        # Re-rank results if requested and service is available
        reranked = False
        if rerank and self.rerank_service and len(results) > 1:
            from graph_rag.services.rerank import ReRankingStrategy
            results = self.rerank_service.rerank(query, results, ReRankingStrategy.SEMANTIC_SIMILARITY)
            reranked = True

        # Cluster results if requested and service is available
        clustered = False
        cluster_count = None
        if cluster and self.clustering_service and len(results) > 3:
            from graph_rag.services.clustering import ClusteringStrategy

            # Map string strategy to enum
            strategy_map = {
                "similarity_threshold": ClusteringStrategy.SIMILARITY_THRESHOLD,
                "kmeans": ClusteringStrategy.KMEANS,
                "topic_based": ClusteringStrategy.TOPIC_BASED,
                "hierarchical": ClusteringStrategy.HIERARCHICAL
            }

            clustering_strategy = strategy_map.get(
                cluster_strategy, ClusteringStrategy.SIMILARITY_THRESHOLD
            )

            # Cluster the results
            cluster_result = self.clustering_service.cluster_results(
                results, strategy=clustering_strategy
            )

            # Optionally diversify clusters to get representative results
            if diversify_clusters:
                cluster_result = self.clustering_service.diversify_clusters(
                    cluster_result, max_per_cluster=max(1, limit // cluster_result.total_clusters)
                )

            # Flatten clusters back to list while preserving cluster information
            flattened_results = []
            for cluster in cluster_result.clusters:
                flattened_results.extend(cluster)

            results = flattened_results
            clustered = True
            cluster_count = cluster_result.total_clusters

        execution_time = (time.time() - start_time) * 1000

        return HybridSearchResult(
            results=results[:limit],  # Ensure limit is respected
            strategy=strategy,
            query=query,
            total_vector_results=vector_count,
            total_keyword_results=keyword_count,
            execution_time_ms=execution_time,
            reranked=reranked,
            clustered=clustered,
            cluster_count=cluster_count
        )

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        threshold: float | None = None
    ) -> HybridSearchResult:
        """Convenience method for hybrid search."""
        return await self.search(query, SearchStrategy.HYBRID, limit, threshold=threshold)

    async def _vector_search(
        self,
        query: str,
        limit: int,
        threshold: float | None = None
    ) -> list[SearchResultData]:
        """Perform vector similarity search."""
        # Increase limit for vector search to allow for filtering
        search_limit = min(limit * 2, 50)
        results = await self.vector_store.search(query, search_limit)

        # Apply threshold filtering if specified
        if threshold is not None:
            results = [r for r in results if r.score >= threshold]

        return results[:limit]

    async def _keyword_search(self, query: str, limit: int) -> list[SearchResultData]:
        """Perform keyword search using graph repository."""
        try:
            results = await self.graph_repository.keyword_search(query, limit)
            return results
        except AttributeError:
            # Fallback if keyword_search is not implemented
            return []

    async def _hybrid_search(
        self,
        query: str,
        limit: int,
        threshold: float | None = None
    ) -> tuple[list[SearchResultData], int, int]:
        """Perform hybrid search combining vector and keyword results."""
        # Perform both searches concurrently for better performance
        import asyncio

        # Use higher limits to get more diverse results before combining
        vector_limit = min(limit * 2, 30)
        keyword_limit = min(limit * 2, 30)

        vector_task = asyncio.create_task(self._vector_search(query, vector_limit, threshold))
        keyword_task = asyncio.create_task(self._keyword_search(query, keyword_limit))

        vector_results, keyword_results = await asyncio.gather(vector_task, keyword_task)

        # Deduplicate results by chunk ID
        seen_chunks = set()
        combined_results = []

        # Add vector results first (typically higher quality)
        for result in vector_results:
            if result.chunk.id not in seen_chunks:
                seen_chunks.add(result.chunk.id)
                combined_results.append(result)

        # Add keyword results that aren't already included
        for result in keyword_results:
            if result.chunk.id not in seen_chunks:
                seen_chunks.add(result.chunk.id)
                combined_results.append(result)

        return combined_results, len(vector_results), len(keyword_results)
