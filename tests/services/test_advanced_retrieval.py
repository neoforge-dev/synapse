"""Tests for advanced retrieval patterns."""

from unittest.mock import AsyncMock, Mock

import pytest

from graph_rag.core.interfaces import ChunkData, GraphRepository, SearchResultData, VectorStore
from graph_rag.services.advanced_retrieval import (
    AdvancedRetrievalService,
    QueryAnalyzer,
    QueryComplexity,
    RetrievalContext,
    RetrievalResult,
    RetrievalStrategy,
)
from graph_rag.services.search import AdvancedSearchService, HybridSearchResult, SearchStrategy


@pytest.fixture
def mock_search_service():
    """Mock advanced search service."""
    mock = AsyncMock(spec=AdvancedSearchService)

    # Default search result
    def create_search_result(query, **kwargs):
        return HybridSearchResult(
            results=[
                SearchResultData(
                    chunk=ChunkData(
                        id=f"chunk_{hash(query) % 1000}",
                        document_id="doc1",
                        text=f"Result for query: {query}",
                        embedding=[0.1, 0.2, 0.3],
                        metadata={"topics": ["machine_learning"], "entities": ["Python"]}
                    ),
                    score=0.8
                ),
                SearchResultData(
                    chunk=ChunkData(
                        id=f"chunk_{(hash(query) + 1) % 1000}",
                        document_id="doc2",
                        text=f"Another result for: {query}",
                        embedding=[0.2, 0.3, 0.4],
                        metadata={"topics": ["data_science"], "entities": ["TensorFlow"]}
                    ),
                    score=0.7
                )
            ],
            strategy=SearchStrategy.HYBRID,
            query=query,
            total_vector_results=1,
            total_keyword_results=1,
            execution_time_ms=100.0
        )

    mock.search.side_effect = create_search_result
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    return AsyncMock(spec=VectorStore)


@pytest.fixture
def mock_graph_repository():
    """Mock graph repository."""
    return AsyncMock(spec=GraphRepository)


@pytest.fixture
def advanced_retrieval_service(mock_search_service, mock_vector_store, mock_graph_repository):
    """Create advanced retrieval service with mocked dependencies."""
    return AdvancedRetrievalService(
        search_service=mock_search_service,
        vector_store=mock_vector_store,
        graph_repository=mock_graph_repository,
        max_hops=3,
        max_results_per_hop=5
    )


@pytest.fixture
def sample_context():
    """Create sample retrieval context."""
    return RetrievalContext(
        user_id="user123",
        session_id="session456",
        conversation_history=["What is machine learning?", "How does deep learning work?"],
        preferences={"topics": ["artificial_intelligence", "programming"]},
        domain_context="computer_science"
    )


def test_query_analyzer():
    """Test query analysis functionality."""
    analyzer = QueryAnalyzer()
    context = RetrievalContext()

    # Test simple query
    simple_analysis = analyzer.analyze_query("Python", context)
    assert simple_analysis["complexity"] == QueryComplexity.SIMPLE
    assert simple_analysis["intent"] == "general"

    # Test complex query
    complex_analysis = analyzer.analyze_query(
        "Compare the differences between machine learning and deep learning approaches",
        context
    )
    assert complex_analysis["complexity"] in [QueryComplexity.MODERATE, QueryComplexity.COMPLEX]
    assert complex_analysis["intent"] == "comparison"
    assert not complex_analysis["requires_multi_hop"]  # No explicit relationship indicators

    # Test multi-hop query
    multihop_analysis = analyzer.analyze_query(
        "What is the relationship between neural networks and deep learning?",
        context
    )
    assert multihop_analysis["requires_multi_hop"]
    assert RetrievalStrategy.MULTI_HOP in multihop_analysis["recommended_strategies"]


def test_query_complexity_assessment():
    """Test query complexity assessment."""
    analyzer = QueryAnalyzer()

    # Simple queries
    assert analyzer._assess_complexity("Python", ["python"]) == QueryComplexity.SIMPLE
    assert analyzer._assess_complexity("Hello world", ["hello", "world"]) == QueryComplexity.SIMPLE

    # Moderate queries
    moderate_query = "How machine learning works"  # Shorter query with one complex indicator
    moderate_words = moderate_query.lower().split()
    assert analyzer._assess_complexity(moderate_query, moderate_words) == QueryComplexity.MODERATE

    # Complex queries
    complex_query = "Compare and contrast different machine learning algorithms and explain their various applications"
    complex_words = complex_query.lower().split()
    assert analyzer._assess_complexity(complex_query, complex_words) == QueryComplexity.COMPLEX


def test_entity_extraction():
    """Test entity extraction from queries."""
    analyzer = QueryAnalyzer()

    # Test with proper nouns
    entities = analyzer._extract_entities("What is TensorFlow and PyTorch?")
    assert "TensorFlow" in entities
    assert "PyTorch" in entities

    # Test with quoted phrases
    entities = analyzer._extract_entities('Explain "machine learning" concepts')
    assert "machine learning" in entities


@pytest.mark.asyncio
async def test_multi_hop_retrieval(advanced_retrieval_service, mock_search_service):
    """Test multi-hop retrieval strategy."""
    query = "What is the relationship between Python and machine learning?"
    context = RetrievalContext()

    result = await advanced_retrieval_service.advanced_retrieve(
        query,
        strategy=RetrievalStrategy.MULTI_HOP,
        context=context,
        limit=5
    )

    assert isinstance(result, RetrievalResult)
    assert result.strategy_used == RetrievalStrategy.MULTI_HOP
    assert result.hops_performed >= 1
    assert len(result.results) > 0
    assert result.confidence_score > 0
    assert "hop" in result.explanation.lower()

    # Verify search service was called multiple times
    assert mock_search_service.search.call_count >= 1


@pytest.mark.asyncio
async def test_adaptive_retrieval(advanced_retrieval_service, mock_search_service):
    """Test adaptive retrieval strategy."""
    # Mock search service to return low-quality results first
    def adaptive_search_side_effect(query, **kwargs):
        if mock_search_service.search.call_count == 1:
            # First call - low quality results
            return HybridSearchResult(
                results=[
                    SearchResultData(
                        chunk=ChunkData(id="chunk1", document_id="doc1", text="Poor result", embedding=[0.1]),
                        score=0.3  # Low score
                    )
                ],
                strategy=SearchStrategy.HYBRID,
                query=query,
                total_vector_results=1,
                total_keyword_results=0,
                execution_time_ms=50.0
            )
        else:
            # Subsequent calls - better results
            return HybridSearchResult(
                results=[
                    SearchResultData(
                        chunk=ChunkData(id="chunk2", document_id="doc2", text="Better result", embedding=[0.2]),
                        score=0.8
                    )
                ],
                strategy=SearchStrategy.VECTOR_ONLY,
                query=query,
                total_vector_results=1,
                total_keyword_results=0,
                execution_time_ms=50.0
            )

    mock_search_service.search.side_effect = adaptive_search_side_effect

    query = "Machine learning concepts"
    result = await advanced_retrieval_service.advanced_retrieve(
        query,
        strategy=RetrievalStrategy.ADAPTIVE,
        context=RetrievalContext(),
        limit=5
    )

    assert result.strategy_used == RetrievalStrategy.ADAPTIVE
    assert "adaptive" in result.explanation.lower()
    assert len(result.results) > 0

    # Should have tried multiple strategies due to poor initial results
    assert mock_search_service.search.call_count > 1


@pytest.mark.asyncio
async def test_context_aware_retrieval(advanced_retrieval_service, sample_context):
    """Test context-aware retrieval strategy."""
    query = "neural networks"

    result = await advanced_retrieval_service.advanced_retrieve(
        query,
        strategy=RetrievalStrategy.CONTEXT_AWARE,
        context=sample_context,
        limit=5
    )

    assert result.strategy_used == RetrievalStrategy.CONTEXT_AWARE
    assert "context" in result.explanation.lower()
    assert len(result.results) > 0

    # Verify search was called with expanded query
    advanced_retrieval_service.search_service.search.assert_called()
    call_args = advanced_retrieval_service.search_service.search.call_args[1]
    # Query should be expanded with context
    assert len(call_args.get('query', query)) >= len(query)


@pytest.mark.asyncio
async def test_ensemble_retrieval(advanced_retrieval_service, mock_search_service):
    """Test ensemble retrieval strategy."""
    query = "data science concepts"

    result = await advanced_retrieval_service.advanced_retrieve(
        query,
        strategy=RetrievalStrategy.ENSEMBLE,
        context=RetrievalContext(),
        limit=5
    )

    assert result.strategy_used == RetrievalStrategy.ENSEMBLE
    assert "ensemble" in result.explanation.lower()
    assert len(result.results) > 0

    # Should have called search multiple times with different strategies
    assert mock_search_service.search.call_count >= 3


@pytest.mark.asyncio
async def test_incremental_retrieval(advanced_retrieval_service, mock_search_service):
    """Test incremental retrieval strategy."""
    # Mock to return different results based on limit
    def incremental_search_side_effect(query, **kwargs):
        limit = kwargs.get('limit', 10)
        num_results = min(limit // 2, 3)  # Return fewer results initially

        results = []
        for i in range(num_results):
            results.append(SearchResultData(
                chunk=ChunkData(
                    id=f"chunk_{i}",
                    document_id=f"doc_{i}",
                    text=f"Result {i} for {query}",
                    embedding=[0.1 * i]
                ),
                score=0.8 - (i * 0.1)
            ))

        return HybridSearchResult(
            results=results,
            strategy=SearchStrategy.HYBRID,
            query=query,
            total_vector_results=num_results,
            total_keyword_results=0,
            execution_time_ms=50.0
        )

    mock_search_service.search.side_effect = incremental_search_side_effect

    query = "programming languages"
    result = await advanced_retrieval_service.advanced_retrieve(
        query,
        strategy=RetrievalStrategy.INCREMENTAL,
        context=RetrievalContext(),
        limit=5
    )

    assert result.strategy_used == RetrievalStrategy.INCREMENTAL
    assert "incremental" in result.explanation.lower()
    assert len(result.results) > 0


@pytest.mark.asyncio
async def test_concept_expansion_retrieval(advanced_retrieval_service, mock_search_service):
    """Test concept expansion retrieval strategy."""
    query = "artificial intelligence"

    result = await advanced_retrieval_service.advanced_retrieve(
        query,
        strategy=RetrievalStrategy.CONCEPT_EXPANSION,
        context=RetrievalContext(),
        limit=5
    )

    assert result.strategy_used == RetrievalStrategy.CONCEPT_EXPANSION
    assert "concept" in result.explanation.lower()
    assert len(result.results) > 0

    # Should have made multiple search calls (initial + concept searches)
    assert mock_search_service.search.call_count > 1


@pytest.mark.asyncio
async def test_automatic_strategy_selection(advanced_retrieval_service):
    """Test automatic strategy selection based on query analysis."""
    # Test simple query - should select incremental
    simple_result = await advanced_retrieval_service.advanced_retrieve(
        "Python",
        context=RetrievalContext(),
        limit=5
    )
    assert simple_result.strategy_used in [RetrievalStrategy.INCREMENTAL, RetrievalStrategy.ADAPTIVE]

    # Test complex query - should select adaptive or ensemble
    complex_result = await advanced_retrieval_service.advanced_retrieve(
        "Compare and contrast different machine learning algorithms and explain their applications",
        context=RetrievalContext(),
        limit=5
    )
    assert complex_result.strategy_used in [RetrievalStrategy.ADAPTIVE, RetrievalStrategy.ENSEMBLE]

    # Test with conversation history - should select context-aware
    context_with_history = RetrievalContext(
        conversation_history=["What is machine learning?", "How does it work?"]
    )
    context_result = await advanced_retrieval_service.advanced_retrieve(
        "neural networks",
        context=context_with_history,
        limit=5
    )
    assert context_result.strategy_used == RetrievalStrategy.CONTEXT_AWARE


def test_text_similarity():
    """Test text similarity calculation."""
    service = AdvancedRetrievalService(
        search_service=Mock(),
        vector_store=Mock(),
        graph_repository=Mock()
    )

    # Identical texts
    assert service._text_similarity("hello world", "hello world") == 1.0

    # Completely different texts
    assert service._text_similarity("hello world", "goodbye universe") == 0.0

    # Partially similar texts
    similarity = service._text_similarity("machine learning", "machine algorithms")
    assert 0 < similarity < 1
    assert similarity > 0.3  # Should have some similarity due to "machine"


def test_entity_extraction_from_text():
    """Test entity extraction from text."""
    service = AdvancedRetrievalService(
        search_service=Mock(),
        vector_store=Mock(),
        graph_repository=Mock()
    )

    text = "TensorFlow and PyTorch are popular Machine Learning frameworks used by Google and Facebook."
    entities = service._extract_entities_from_text(text)

    assert "TensorFlow" in entities
    assert "PyTorch" in entities
    assert "Machine" in entities  # Individual words from compound entities
    assert "Learning" in entities
    assert "Google" in entities
    # Common words should be filtered out
    assert "The" not in entities
    assert "are" not in entities


def test_keyword_extraction():
    """Test keyword extraction from text."""
    service = AdvancedRetrievalService(
        search_service=Mock(),
        vector_store=Mock(),
        graph_repository=Mock()
    )

    text = "Machine learning algorithms are powerful tools for data analysis and prediction."
    keywords = service._extract_keywords_from_text(text)

    assert "machine" in keywords
    assert "learning" in keywords
    assert "algorithms" in keywords
    assert "analysis" in keywords
    # Common words should be filtered out
    assert "the" not in keywords
    assert "and" not in keywords
    assert "for" not in keywords


def test_query_expansion_with_context():
    """Test query expansion using context."""
    service = AdvancedRetrievalService(
        search_service=Mock(),
        vector_store=Mock(),
        graph_repository=Mock()
    )

    context = RetrievalContext(
        conversation_history=["What is machine learning?", "How does neural networks work?"],
        domain_context="artificial_intelligence",
        preferences={"topics": ["deep_learning", "programming"]}
    )

    expanded_query = service._expand_query_with_context("Python", context)

    # Should contain original query
    assert "Python" in expanded_query
    # Should be longer than original
    assert len(expanded_query) > len("Python")
    # Should contain some context terms
    expanded_lower = expanded_query.lower()
    context_found = any(term in expanded_lower for term in [
        "machine", "learning", "neural", "networks", "artificial_intelligence",
        "deep_learning", "programming"
    ])
    assert context_found


def test_result_deduplication():
    """Test result deduplication functionality."""
    service = AdvancedRetrievalService(
        search_service=Mock(),
        vector_store=Mock(),
        graph_repository=Mock()
    )

    # Create duplicate results
    results = [
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="text1"),
            score=0.9
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk2", document_id="doc2", text="text2"),
            score=0.8
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="text1"),  # Duplicate
            score=0.7
        ),
    ]

    unique_results = service._deduplicate_results(results)

    assert len(unique_results) == 2
    assert unique_results[0].chunk.id == "chunk1"
    assert unique_results[1].chunk.id == "chunk2"
    # Should keep the first occurrence
    assert unique_results[0].score == 0.9


def test_confidence_calculation():
    """Test confidence score calculation."""
    service = AdvancedRetrievalService(
        search_service=Mock(),
        vector_store=Mock(),
        graph_repository=Mock()
    )

    # High-quality results
    high_quality_results = [
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="text1"),
            score=0.9
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk2", document_id="doc2", text="text2"),
            score=0.8
        )
    ]

    analysis = {
        "complexity": QueryComplexity.SIMPLE,
        "recommended_strategies": [RetrievalStrategy.ADAPTIVE]
    }

    confidence = service._calculate_confidence(
        high_quality_results, analysis, RetrievalStrategy.ADAPTIVE
    )

    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.5  # Should be reasonably confident

    # Empty results should have zero confidence
    empty_confidence = service._calculate_confidence([], analysis, RetrievalStrategy.ADAPTIVE)
    assert empty_confidence == 0.0


def test_context_relevance_calculation():
    """Test context relevance calculation."""
    service = AdvancedRetrievalService(
        search_service=Mock(),
        vector_store=Mock(),
        graph_repository=Mock()
    )

    result = SearchResultData(
        chunk=ChunkData(
            id="chunk1",
            document_id="doc1",
            text="machine learning algorithms for data analysis",
            metadata={"topics": ["machine_learning", "data_science"]}
        ),
        score=0.8
    )

    context = RetrievalContext(
        conversation_history=["What is machine learning?"],
        preferences={"topics": ["machine_learning", "programming"]},
        domain_context="computer science"
    )

    relevance = service._calculate_context_relevance(result, context)

    assert 0.0 <= relevance <= 1.0
    assert relevance > 0.0  # Should have some relevance


@pytest.mark.asyncio
async def test_retrieval_result_properties():
    """Test RetrievalResult properties."""
    results = [
        SearchResultData(
            chunk=ChunkData(id="chunk1", document_id="doc1", text="text1"),
            score=0.9
        ),
        SearchResultData(
            chunk=ChunkData(id="chunk2", document_id="doc2", text="text2"),
            score=0.7
        )
    ]

    retrieval_result = RetrievalResult(
        results=results,
        strategy_used=RetrievalStrategy.ENSEMBLE,
        query="test query",
        execution_time_ms=150.0,
        confidence_score=0.85,
        explanation="Test retrieval"
    )

    assert retrieval_result.result_count == 2
    assert retrieval_result.avg_score == 0.8  # (0.9 + 0.7) / 2

    # Test with empty results
    empty_result = RetrievalResult(
        results=[],
        strategy_used=RetrievalStrategy.ADAPTIVE,
        query="test query",
        execution_time_ms=50.0,
        confidence_score=0.0,
        explanation="No results"
    )

    assert empty_result.result_count == 0
    assert empty_result.avg_score == 0.0


def test_retrieval_context_initialization():
    """Test RetrievalContext initialization."""
    # Test with defaults
    context = RetrievalContext()
    assert context.conversation_history == []
    assert context.preferences == {}
    assert context.previous_results == []

    # Test with values
    context_with_values = RetrievalContext(
        user_id="user123",
        conversation_history=["query1", "query2"],
        preferences={"topic": "AI"}
    )
    assert context_with_values.user_id == "user123"
    assert len(context_with_values.conversation_history) == 2
    assert context_with_values.preferences["topic"] == "AI"
