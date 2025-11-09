"""Unit tests for SearchCache functionality."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graph_rag.core.interfaces import ChunkData, SearchResultData
from graph_rag.services.search import AdvancedSearchService, SearchCache, SearchStrategy


class TestSearchCache:
    """Test SearchCache utility class."""

    def test_cache_initialization(self):
        """Test cache is initialized with correct parameters."""
        cache = SearchCache(maxsize=50, ttl=120)
        stats = cache.stats()

        assert stats["maxsize"] == 50
        assert stats["ttl_seconds"] == 120
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_cache_key_generation(self):
        """Test cache key generation is consistent and unique."""
        cache = SearchCache()

        key1 = cache.get_cache_key("test query", "vector", 10)
        key2 = cache.get_cache_key("test query", "vector", 10)
        key3 = cache.get_cache_key("test query", "keyword", 10)
        key4 = cache.get_cache_key("different query", "vector", 10)

        # Same parameters should produce same key
        assert key1 == key2

        # Different search_type should produce different key
        assert key1 != key3

        # Different query should produce different key
        assert key1 != key4

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = SearchCache()
        key = cache.get_cache_key("test", "vector", 5)

        # Initially cache miss
        result = cache.get(key)
        assert result is None

        # Set value
        cache.set(key, {"results": ["item1", "item2"]})

        # Now cache hit
        result = cache.get(key)
        assert result is not None
        assert result["results"] == ["item1", "item2"]

    def test_cache_stats_tracking(self):
        """Test cache statistics are tracked correctly."""
        cache = SearchCache()
        key1 = cache.get_cache_key("query1", "vector", 5)
        key2 = cache.get_cache_key("query2", "vector", 5)

        # 2 misses
        cache.get(key1)
        cache.get(key2)

        # Set values
        cache.set(key1, "result1")
        cache.set(key2, "result2")

        # 2 hits
        cache.get(key1)
        cache.get(key2)

        # 1 more miss
        cache.get("nonexistent")

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 3
        assert stats["total_requests"] == 5
        assert stats["hit_rate"] == "40.0%"
        assert stats["size"] == 2

    def test_cache_invalidation(self):
        """Test cache invalidation clears all entries."""
        cache = SearchCache()

        # Add multiple entries
        for i in range(5):
            key = cache.get_cache_key(f"query{i}", "vector", 10)
            cache.set(key, f"result{i}")

        stats = cache.stats()
        assert stats["size"] == 5

        # Invalidate cache
        cache.invalidate()

        stats = cache.stats()
        assert stats["size"] == 0

        # Previous keys should miss
        key = cache.get_cache_key("query0", "vector", 10)
        assert cache.get(key) is None

    def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL."""
        # Use very short TTL for testing
        cache = SearchCache(maxsize=10, ttl=1)  # 1 second TTL
        key = cache.get_cache_key("test", "vector", 5)

        # Set value
        cache.set(key, "result")
        assert cache.get(key) is not None

        # Wait for TTL expiration
        time.sleep(1.5)

        # Entry should be expired
        assert cache.get(key) is None

    def test_cache_max_size_limit(self):
        """Test cache respects max size limit."""
        cache = SearchCache(maxsize=3, ttl=300)

        # Add 4 entries (exceeds maxsize of 3)
        for i in range(4):
            key = cache.get_cache_key(f"query{i}", "vector", 10)
            cache.set(key, f"result{i}")

        stats = cache.stats()
        # Should only have 3 entries due to LRU eviction
        assert stats["size"] <= 3
        assert stats["maxsize"] == 3


class TestAdvancedSearchServiceCaching:
    """Test caching integration in AdvancedSearchService."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        store = MagicMock()
        store.search = AsyncMock(return_value=[
            SearchResultData(
                chunk=ChunkData(
                    id="chunk1",
                    text="test content",
                    document_id="doc1"
                ),
                score=0.9
            )
        ])
        return store

    @pytest.fixture
    def mock_graph_repository(self):
        """Create mock graph repository."""
        repo = MagicMock()
        repo.keyword_search = AsyncMock(return_value=[])
        return repo

    @pytest.mark.asyncio
    async def test_search_caching_enabled(self, mock_vector_store, mock_graph_repository):
        """Test that search results are cached when caching is enabled."""
        with patch.dict('os.environ', {'SYNAPSE_ENABLE_SEARCH_CACHE': 'true'}):
            service = AdvancedSearchService(
                vector_store=mock_vector_store,
                graph_repository=mock_graph_repository,
                enable_cache=True
            )

            # First search should call vector_store
            result1 = await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 1

            # Second identical search should use cache (no additional vector_store call)
            result2 = await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 1  # Still 1, not 2

            # Results should be identical
            assert result1.total_results == result2.total_results
            assert len(result1.results) == len(result2.results)

    @pytest.mark.asyncio
    async def test_search_caching_disabled(self, mock_vector_store, mock_graph_repository):
        """Test that caching can be disabled."""
        with patch.dict('os.environ', {'SYNAPSE_ENABLE_SEARCH_CACHE': 'false'}):
            service = AdvancedSearchService(
                vector_store=mock_vector_store,
                graph_repository=mock_graph_repository,
                enable_cache=False
            )

            # Both searches should call vector_store
            await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 1

            await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, mock_vector_store, mock_graph_repository):
        """Test cache invalidation clears cached results."""
        with patch.dict('os.environ', {'SYNAPSE_ENABLE_SEARCH_CACHE': 'true'}):
            service = AdvancedSearchService(
                vector_store=mock_vector_store,
                graph_repository=mock_graph_repository,
                enable_cache=True
            )

            # First search
            await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 1

            # Cached search
            await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 1

            # Invalidate cache
            service.invalidate_cache()

            # Should call vector_store again after invalidation
            await service.search("test query", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 2

    def test_cache_stats_retrieval(self, mock_vector_store, mock_graph_repository):
        """Test cache statistics can be retrieved."""
        with patch.dict('os.environ', {'SYNAPSE_ENABLE_SEARCH_CACHE': 'true'}):
            service = AdvancedSearchService(
                vector_store=mock_vector_store,
                graph_repository=mock_graph_repository,
                enable_cache=True
            )

            stats = service.get_cache_stats()
            assert "hits" in stats
            assert "misses" in stats
            assert "size" in stats
            assert "maxsize" in stats
            assert "ttl_seconds" in stats

    def test_cache_stats_when_disabled(self, mock_vector_store, mock_graph_repository):
        """Test cache stats when caching is disabled."""
        service = AdvancedSearchService(
            vector_store=mock_vector_store,
            graph_repository=mock_graph_repository,
            enable_cache=False
        )

        stats = service.get_cache_stats()
        assert stats["enabled"] is False
        assert "message" in stats

    @pytest.mark.asyncio
    async def test_cache_different_parameters(self, mock_vector_store, mock_graph_repository):
        """Test that different search parameters create different cache entries."""
        with patch.dict('os.environ', {'SYNAPSE_ENABLE_SEARCH_CACHE': 'true'}):
            service = AdvancedSearchService(
                vector_store=mock_vector_store,
                graph_repository=mock_graph_repository,
                enable_cache=True
            )

            # Different queries
            await service.search("query1", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            await service.search("query2", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 2

            # Different limits
            await service.search("query1", strategy=SearchStrategy.VECTOR_ONLY, limit=10)
            assert mock_vector_store.search.call_count == 3

            # Same query and limit should use cache
            await service.search("query1", strategy=SearchStrategy.VECTOR_ONLY, limit=5)
            assert mock_vector_store.search.call_count == 3  # No additional call
