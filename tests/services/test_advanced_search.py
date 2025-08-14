"""Tests for advanced search functionality including hybrid search and re-ranking."""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import List

from graph_rag.services.search import AdvancedSearchService, HybridSearchResult, SearchStrategy
from graph_rag.services.rerank import ReRankingService, ReRankingStrategy
from graph_rag.core.interfaces import SearchResultData, VectorStore, GraphRepository, ChunkData


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock = AsyncMock(spec=VectorStore)
    
    # Mock vector search results
    vector_results = [
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="AI and machine learning concepts", embedding=[0.1, 0.2]),
            score=0.95
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk2", document_id="doc1", text="Neural networks are powerful", embedding=[0.2, 0.3]),
            score=0.87
        ),
    ]
    mock.search.return_value = vector_results
    return mock


@pytest.fixture
def mock_graph_repository():
    """Mock graph repository for testing."""
    mock = AsyncMock(spec=GraphRepository)
    
    # Mock keyword search results
    keyword_results = [
        SearchResultData(
            chunk=ChunkData(id="chunk3", document_id="doc2", text="Machine learning algorithms for data analysis", embedding=[0.3, 0.4]),
            score=0.92
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="AI and machine learning concepts", embedding=[0.1, 0.2]),
            score=0.78
        ),
    ]
    mock.keyword_search.return_value = keyword_results
    return mock


@pytest.fixture
def mock_rerank_service():
    """Mock re-ranking service."""
    mock = Mock(spec=ReRankingService)
    
    # Mock re-ranking to return results in different order
    def rerank_results(query: str, results: List[SearchResultData], strategy: ReRankingStrategy):
        # Simple mock: reverse order and adjust scores
        reranked = list(reversed(results))
        for i, result in enumerate(reranked):
            result.score = 0.95 - (i * 0.1)  # Decreasing scores
        return reranked
    
    mock.rerank.side_effect = rerank_results
    return mock


@pytest.mark.asyncio
async def test_hybrid_search_combines_vector_and_keyword():
    """Test that hybrid search properly combines vector and keyword results."""
    from graph_rag.services.search import AdvancedSearchService
    
    # Create mocks
    vector_store = AsyncMock()
    graph_repo = AsyncMock()
    rerank_service = Mock()
    
    # Mock vector search results
    vector_results = [
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="AI concepts", embedding=[0.1]),
            score=0.95
        ),
    ]
    vector_store.search.return_value = vector_results
    
    # Mock keyword search results
    keyword_results = [
        SearchResultData(
            chunk=ChunkData(id="chunk2", document_id="doc2", text="Machine learning", embedding=[0.2]),
            score=0.88
        ),
    ]
    graph_repo.keyword_search.return_value = keyword_results
    
    # Mock re-ranking (no change for simplicity)
    rerank_service.rerank.return_value = vector_results + keyword_results
    
    # Create service and test
    service = AdvancedSearchService(vector_store, graph_repo, rerank_service)
    results = await service.hybrid_search("AI machine learning", limit=10)
    
    # Assertions
    assert len(results.results) == 2
    assert results.strategy == SearchStrategy.HYBRID
    assert results.total_vector_results == 1
    assert results.total_keyword_results == 1
    
    # Verify both stores were called
    vector_store.search.assert_called_once()
    graph_repo.keyword_search.assert_called_once()
    rerank_service.rerank.assert_called_once()


@pytest.mark.asyncio
async def test_hybrid_search_deduplication():
    """Test that hybrid search removes duplicate results."""
    from graph_rag.services.search import AdvancedSearchService
    
    vector_store = AsyncMock()
    graph_repo = AsyncMock()
    rerank_service = Mock()
    
    # Both searches return the same chunk
    same_chunk = SearchResultData(
        chunk=ChunkData(id="chunk1", document_id="doc1", text="AI concepts", embedding=[0.1]),
        score=0.95
    )
    
    vector_results = [same_chunk]
    keyword_results = [same_chunk]  # Same chunk from keyword search
    
    vector_store.search.return_value = vector_results
    graph_repo.keyword_search.return_value = keyword_results
    
    # Mock re-ranking to return deduplicated results
    rerank_service.rerank.return_value = [same_chunk]  # Should be deduplicated
    
    service = AdvancedSearchService(vector_store, graph_repo, rerank_service)
    results = await service.hybrid_search("AI concepts", limit=10)
    
    # Should have only one result after deduplication
    assert len(results.results) == 1
    assert results.results[0].chunk.id == "chunk1"


@pytest.mark.asyncio
async def test_search_strategy_selection():
    """Test that different search strategies work correctly."""
    from graph_rag.services.search import AdvancedSearchService, SearchStrategy
    
    vector_store = AsyncMock()
    graph_repo = AsyncMock()
    rerank_service = Mock()
    
    vector_results = [SearchResultData(
        chunk=ChunkData(id="chunk1", document_id="doc1", text="test", embedding=[0.1]),
        score=0.9
    )]
    keyword_results = [SearchResultData(
        chunk=ChunkData(id="chunk2", document_id="doc2", text="test", embedding=[0.2]),
        score=0.8
    )]
    
    vector_store.search.return_value = vector_results
    graph_repo.keyword_search.return_value = keyword_results
    rerank_service.rerank.return_value = vector_results
    
    service = AdvancedSearchService(vector_store, graph_repo, rerank_service)
    
    # Test vector-only strategy
    results = await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
    assert results.strategy == SearchStrategy.VECTOR_ONLY
    vector_store.search.assert_called()
    
    # Reset mocks
    vector_store.reset_mock()
    graph_repo.reset_mock()
    
    # Test keyword-only strategy  
    rerank_service.rerank.return_value = keyword_results
    results = await service.search("test query", strategy=SearchStrategy.KEYWORD_ONLY, limit=5)
    assert results.strategy == SearchStrategy.KEYWORD_ONLY
    graph_repo.keyword_search.assert_called()
    vector_store.search.assert_not_called()


@pytest.mark.asyncio
async def test_reranking_improves_results():
    """Test that re-ranking improves result quality."""
    from graph_rag.services.rerank import ReRankingService, ReRankingStrategy
    
    # Mock results in suboptimal order
    initial_results = [
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="Irrelevant content", embedding=[0.1]),
            score=0.9  # High score but irrelevant
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk2", document_id="doc2", text="Machine learning and AI are powerful technologies", embedding=[0.2]),
            score=0.7  # Lower score but very relevant
        ),
    ]
    
    service = ReRankingService()
    
    # Test semantic re-ranking
    reranked = service.rerank(
        "machine learning AI", 
        initial_results, 
        ReRankingStrategy.SEMANTIC_SIMILARITY
    )
    
    # The more relevant result should now be first
    assert reranked[0].chunk.id == "chunk2"
    assert reranked[0].score > reranked[1].score


@pytest.mark.asyncio  
async def test_query_expansion():
    """Test query expansion functionality."""
    from graph_rag.services.search import QueryExpansionService
    
    service = QueryExpansionService()
    
    # Test synonym expansion
    expanded = service.expand_query("ML")
    assert "machine learning" in expanded.expanded_terms
    assert "artificial intelligence" in expanded.expanded_terms
    
    # Test concept expansion
    expanded = service.expand_query("neural networks")
    assert "deep learning" in expanded.expanded_terms or "artificial neural networks" in expanded.expanded_terms


def test_search_result_aggregation():
    """Test search result aggregation and scoring."""
    from graph_rag.services.search import HybridSearchResult, SearchStrategy
    
    # Create sample results
    results = [
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="test", embedding=[0.1]),
            score=0.9
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk2", document_id="doc2", text="test", embedding=[0.2]),
            score=0.8
        ),
    ]
    
    # Create hybrid search result
    hybrid_result = HybridSearchResult(
        results=results,
        strategy=SearchStrategy.HYBRID,
        query="test query",
        total_vector_results=1,
        total_keyword_results=1,
        execution_time_ms=150.0,
        reranked=True
    )
    
    assert hybrid_result.total_results == 2
    assert abs(hybrid_result.avg_score - 0.85) < 1e-10  # Use tolerance for floating point comparison
    assert hybrid_result.reranked is True
    assert hybrid_result.strategy == SearchStrategy.HYBRID