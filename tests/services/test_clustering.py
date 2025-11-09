"""Tests for semantic clustering functionality."""


import pytest

from graph_rag.core.interfaces import ChunkData, SearchResultData
from graph_rag.services.clustering import (
    ClusterInfo,
    ClusteringStrategy,
    ClusterResult,
    SemanticClusteringService,
)


@pytest.fixture
def clustering_service():
    """Create clustering service for testing."""
    return SemanticClusteringService(min_cluster_size=2, max_clusters=5)


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing."""
    return [
        SearchResultData(
            chunk=ChunkData(
                id="chunk1",
                document_id="doc1",
                text="Machine learning algorithms are powerful tools for data analysis",
                embedding=[0.1, 0.2, 0.3, 0.4],
                metadata={"topics": ["machine_learning", "data_science"]}
            ),
            score=0.9
        ),
        SearchResultData(
            chunk=ChunkData(
                id="chunk2",
                document_id="doc1",
                text="Artificial intelligence and machine learning are related fields",
                embedding=[0.2, 0.1, 0.4, 0.3],
                metadata={"topics": ["artificial_intelligence", "machine_learning"]}
            ),
            score=0.85
        ),
        SearchResultData(
            chunk=ChunkData(
                id="chunk3",
                document_id="doc2",
                text="Python programming language is great for web development",
                embedding=[0.8, 0.1, 0.2, 0.1],
                metadata={"topics": ["programming", "python"]}
            ),
            score=0.8
        ),
        SearchResultData(
            chunk=ChunkData(
                id="chunk4",
                document_id="doc2",
                text="Web development using Python frameworks like Django and Flask",
                embedding=[0.7, 0.2, 0.1, 0.3],
                metadata={"topics": ["programming", "web_development"]}
            ),
            score=0.75
        ),
        SearchResultData(
            chunk=ChunkData(
                id="chunk5",
                document_id="doc3",
                text="Database design principles for modern applications",
                embedding=[0.3, 0.8, 0.1, 0.2],
                metadata={"topics": ["database", "software_design"]}
            ),
            score=0.7
        ),
    ]


def test_threshold_clustering(clustering_service, sample_search_results):
    """Test similarity threshold clustering."""
    result = clustering_service.cluster_results(
        sample_search_results,
        strategy=ClusteringStrategy.SIMILARITY_THRESHOLD,
        similarity_threshold=0.3
    )

    assert isinstance(result, ClusterResult)
    assert result.strategy == ClusteringStrategy.SIMILARITY_THRESHOLD
    assert result.total_clusters >= 1
    assert len(result.clusters) == result.total_clusters
    assert len(result.cluster_info) == result.total_clusters

    # Check that all results are assigned to clusters
    total_clustered = sum(len(cluster) for cluster in result.clusters)
    assert total_clustered == len(sample_search_results)

    # Check cluster info
    for info in result.cluster_info:
        assert isinstance(info, ClusterInfo)
        assert info.size > 0
        assert info.avg_score > 0
        assert 0 <= info.diversity_score <= 1


def test_kmeans_clustering(clustering_service, sample_search_results):
    """Test k-means clustering."""
    result = clustering_service.cluster_results(
        sample_search_results,
        strategy=ClusteringStrategy.KMEANS,
        target_clusters=3
    )

    assert isinstance(result, ClusterResult)
    assert result.strategy == ClusteringStrategy.KMEANS
    assert result.total_clusters >= 1

    # Check that clusters contain minimum required items
    for cluster in result.clusters:
        assert len(cluster) >= clustering_service.min_cluster_size

    # Check that centroids are calculated when possible
    for info in result.cluster_info:
        if info.centroid:
            assert isinstance(info.centroid, list)
            assert len(info.centroid) > 0


def test_topic_based_clustering(clustering_service, sample_search_results):
    """Test topic-based clustering."""
    result = clustering_service.cluster_results(
        sample_search_results,
        strategy=ClusteringStrategy.TOPIC_BASED
    )

    assert isinstance(result, ClusterResult)
    assert result.strategy == ClusteringStrategy.TOPIC_BASED
    assert result.total_clusters >= 1

    # Should create clusters based on similar topics
    ml_cluster = None
    programming_cluster = None

    for cluster in result.clusters:
        topics = set()
        for item in cluster:
            item_topics = item.chunk.metadata.get("topics", [])
            topics.update(item_topics)

        if "machine_learning" in topics:
            ml_cluster = cluster
        elif "programming" in topics:
            programming_cluster = cluster

    # Should have separated ML and programming topics
    assert ml_cluster is not None or programming_cluster is not None


def test_small_dataset_handling(clustering_service):
    """Test handling of datasets smaller than minimum cluster size."""
    small_results = [
        SearchResultData(
            chunk=ChunkData(
                id="chunk1",
                document_id="doc1",
                text="Single item",
                embedding=[0.1, 0.2]
            ),
            score=0.9
        )
    ]

    result = clustering_service.cluster_results(small_results)

    assert result.total_clusters == 1
    assert len(result.clusters[0]) == 1
    assert result.clusters[0][0] == small_results[0]


def test_cluster_diversification(clustering_service, sample_search_results):
    """Test cluster diversification functionality."""
    # First cluster the results
    cluster_result = clustering_service.cluster_results(
        sample_search_results,
        strategy=ClusteringStrategy.SIMILARITY_THRESHOLD
    )

    # Then diversify
    diversified = clustering_service.diversify_clusters(
        cluster_result,
        max_per_cluster=2
    )

    assert isinstance(diversified, ClusterResult)
    assert diversified.total_clusters == cluster_result.total_clusters

    # Each cluster should have at most max_per_cluster items
    for cluster in diversified.clusters:
        assert len(cluster) <= 2


def test_similarity_calculation(clustering_service):
    """Test similarity calculation methods."""
    result1 = SearchResultData(
        chunk=ChunkData(
            id="chunk1",
            document_id="doc1",
            text="machine learning algorithms",
            embedding=[0.1, 0.2, 0.3]
        ),
        score=0.9
    )

    result2 = SearchResultData(
        chunk=ChunkData(
            id="chunk2",
            document_id="doc2",
            text="machine learning models",
            embedding=[0.1, 0.2, 0.3]
        ),
        score=0.8
    )

    result3 = SearchResultData(
        chunk=ChunkData(
            id="chunk3",
            document_id="doc3",
            text="completely different topic",
            embedding=[0.9, 0.8, 0.1]
        ),
        score=0.7
    )

    # Test cosine similarity with identical embeddings
    sim1 = clustering_service._calculate_similarity(result1, result2)
    assert sim1 == 1.0  # Identical embeddings should have similarity 1.0

    # Test similarity with different embeddings
    sim2 = clustering_service._calculate_similarity(result1, result3)
    assert 0 <= sim2 < 1.0  # Different embeddings should have lower similarity

    # Test text-based similarity fallback
    result_no_embedding = SearchResultData(
        chunk=ChunkData(
            id="chunk4",
            document_id="doc4",
            text="machine learning algorithms",
            embedding=None
        ),
        score=0.6
    )

    text_sim = clustering_service._calculate_similarity(result1, result_no_embedding)
    assert 0 <= text_sim <= 1.0


def test_cosine_similarity(clustering_service):
    """Test cosine similarity calculation."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]
    vec4 = [0.0, 0.0, 0.0]  # Zero vector

    # Identical vectors
    assert clustering_service._cosine_similarity(vec1, vec2) == 1.0

    # Orthogonal vectors
    assert clustering_service._cosine_similarity(vec1, vec3) == 0.0

    # Zero vector
    assert clustering_service._cosine_similarity(vec1, vec4) == 0.0

    # Different length vectors
    assert clustering_service._cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


def test_text_similarity(clustering_service):
    """Test text-based similarity calculation."""
    text1 = "machine learning algorithms"
    text2 = "machine learning models"
    text3 = "completely different topic"

    # Similar texts
    sim1 = clustering_service._text_similarity(text1, text2)
    assert sim1 >= 0.5  # Should have high similarity due to shared words

    # Different texts
    sim2 = clustering_service._text_similarity(text1, text3)
    assert sim2 < 0.5  # Should have low similarity

    # Empty text
    sim3 = clustering_service._text_similarity(text1, "")
    assert sim3 == 0.0


def test_keyword_extraction(clustering_service):
    """Test keyword extraction from text."""
    text = "Machine learning and artificial intelligence with Python programming"
    keywords = clustering_service._extract_keywords_from_text(text)

    assert isinstance(keywords, list)
    assert len(keywords) <= 3  # Should return top 3 keywords

    # Should extract technical terms
    expected_terms = ["machine_learning", "artificial_intelligence", "python"]
    found_terms = [term for term in expected_terms if term in keywords]
    assert len(found_terms) > 0


def test_empty_results_handling(clustering_service):
    """Test handling of empty result sets."""
    result = clustering_service.cluster_results([])

    assert result.total_clusters == 0
    assert len(result.clusters) == 0
    assert len(result.cluster_info) == 0


def test_cluster_info_creation(clustering_service, sample_search_results):
    """Test cluster info creation."""
    # Take first 3 results as a cluster
    cluster = sample_search_results[:3]

    info = clustering_service._create_cluster_info("test_cluster", cluster)

    assert info.id == "test_cluster"
    assert info.size == 3
    assert info.avg_score > 0
    assert 0 <= info.diversity_score <= 1
    assert len(info.representative_text) > 0

    # Should have centroid if all items have embeddings
    assert info.centroid is not None
    assert len(info.centroid) == 4  # Same dimension as input embeddings


def test_diverse_representative_selection(clustering_service, sample_search_results):
    """Test selection of diverse representatives from a cluster."""
    # Use all sample results as one large cluster
    representatives = clustering_service._select_diverse_representatives(
        sample_search_results, max_items=3
    )

    assert len(representatives) == 3
    assert len({rep.chunk.id for rep in representatives}) == 3  # All different

    # Should include the highest scoring item
    highest_score = max(sample_search_results, key=lambda x: x.score)
    assert highest_score in representatives

    # Test with max_items larger than cluster size
    all_representatives = clustering_service._select_diverse_representatives(
        sample_search_results, max_items=10
    )
    assert len(all_representatives) == len(sample_search_results)


@pytest.mark.asyncio
async def test_clustering_integration_with_search():
    """Test clustering integration with advanced search service."""
    from unittest.mock import AsyncMock

    from graph_rag.services.search import AdvancedSearchService, SearchStrategy

    # Create mocks
    vector_store = AsyncMock()
    graph_repo = AsyncMock()
    clustering_service = SemanticClusteringService()

    # Mock search results
    search_results = [
        SearchResultData(
            chunk=ChunkData(
                id=f"chunk{i}",
                document_id="doc1",
                text=f"Sample text {i}",
                embedding=[0.1 * i, 0.2 * i, 0.3 * i]
            ),
            score=0.9 - (i * 0.1)
        )
        for i in range(6)  # 6 results to enable clustering
    ]

    vector_store.search.return_value = search_results[:4]
    graph_repo.keyword_search.return_value = search_results[4:]

    # Create service with clustering
    service = AdvancedSearchService(
        vector_store=vector_store,
        graph_repository=graph_repo,
        clustering_service=clustering_service
    )

    # Test search with clustering
    result = await service.search(
        "test query",
        strategy=SearchStrategy.HYBRID,
        cluster=True,
        cluster_strategy="similarity_threshold"
    )

    assert result.clustered is True
    assert result.cluster_count is not None
    assert result.cluster_count >= 1
    assert len(result.results) > 0
