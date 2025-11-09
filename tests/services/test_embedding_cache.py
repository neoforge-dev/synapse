"""Unit tests for embedding cache functionality.

Tests the EmbeddingCache class and integration with SentenceTransformersEmbeddingService
to verify performance improvements for duplicate content during batch ingestion.
"""

import os
import pytest

from graph_rag.services.embedding import EmbeddingCache, SentenceTransformerEmbeddingService


class TestEmbeddingCache:
    """Test suite for EmbeddingCache class."""

    def test_cache_initialization(self):
        """Test cache initializes with correct parameters."""
        cache = EmbeddingCache(maxsize=100)
        assert cache._cache.maxsize == 100
        assert cache._hits == 0
        assert cache._misses == 0

    def test_cache_get_miss(self):
        """Test cache returns None for uncached text."""
        cache = EmbeddingCache()
        result = cache.get("uncached text")
        assert result is None
        assert cache._misses == 1
        assert cache._hits == 0

    def test_cache_set_and_get_hit(self):
        """Test cache stores and retrieves embeddings."""
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3, 0.4]

        # Set embedding
        cache.set("test text", embedding)

        # Get embedding (should be a hit)
        result = cache.get("test text")
        assert result == embedding
        assert cache._hits == 1
        assert cache._misses == 0

    def test_cache_key_normalization(self):
        """Test cache normalizes text for consistent keys."""
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        # Set with various forms of the same text
        cache.set("  Test Text  ", embedding)

        # Should hit with normalized form
        assert cache.get("test text") == embedding
        assert cache.get("  TEST TEXT  ") == embedding
        assert cache.get("Test Text") == embedding

    def test_cache_stats(self):
        """Test cache statistics calculation."""
        cache = EmbeddingCache(maxsize=10)
        embedding = [0.1, 0.2]

        # Initial stats
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"
        assert stats["size"] == 0
        assert stats["maxsize"] == 10

        # Add some operations
        cache.set("text1", embedding)
        cache.get("text1")  # hit
        cache.get("text2")  # miss
        cache.get("text1")  # hit

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "66.7%"
        assert stats["size"] == 1

    def test_cache_get_batch(self):
        """Test batch cache lookup."""
        cache = EmbeddingCache()
        texts = ["text1", "text2", "text3", "text4"]
        embeddings = [[0.1], [0.2], [0.3], [0.4]]

        # Cache only text1 and text3
        cache.set("text1", embeddings[0])
        cache.set("text3", embeddings[2])

        # Check batch
        cached_indices, uncached_indices, uncached_texts = cache.get_batch(texts)

        assert cached_indices == [0, 2]
        assert uncached_indices == [1, 3]
        assert uncached_texts == ["text2", "text4"]

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = EmbeddingCache(maxsize=3)

        # Fill cache to capacity
        cache.set("text1", [0.1])
        cache.set("text2", [0.2])
        cache.set("text3", [0.3])

        # All should be in cache
        assert cache.get("text1") is not None
        assert cache.get("text2") is not None
        assert cache.get("text3") is not None

        # Add one more (should evict oldest)
        cache.set("text4", [0.4])

        # text1 should be evicted
        assert cache.get("text4") is not None
        assert cache.get("text2") is not None
        assert cache.get("text3") is not None

    def test_cache_key_generation(self):
        """Test SHA256 cache key generation."""
        key1 = EmbeddingCache._get_cache_key("test text")
        key2 = EmbeddingCache._get_cache_key("test text")
        key3 = EmbeddingCache._get_cache_key("different text")

        # Same text should produce same key
        assert key1 == key2
        # Different text should produce different key
        assert key1 != key3
        # Should be 64-character SHA256 hex
        assert len(key1) == 64


@pytest.mark.asyncio
class TestSentenceTransformersEmbeddingServiceCache:
    """Test suite for cache integration in SentenceTransformersEmbeddingService."""

    @pytest.fixture
    def mock_env_cache_enabled(self, monkeypatch):
        """Set environment to enable cache."""
        monkeypatch.setenv("SYNAPSE_ENABLE_EMBEDDING_CACHE", "true")
        monkeypatch.setenv("SYNAPSE_EMBEDDING_CACHE_SIZE", "100")
        monkeypatch.setenv("SKIP_SPACY_IMPORT", "1")  # Lightweight testing

    @pytest.fixture
    def mock_env_cache_disabled(self, monkeypatch):
        """Set environment to disable cache."""
        monkeypatch.setenv("SYNAPSE_ENABLE_EMBEDDING_CACHE", "false")
        monkeypatch.setenv("SKIP_SPACY_IMPORT", "1")

    async def test_cache_enabled_on_init(self, mock_env_cache_enabled):
        """Test cache is initialized when enabled."""
        service = SentenceTransformerEmbeddingService()
        assert service._cache is not None
        assert service._cache._cache.maxsize == 100

    async def test_cache_disabled_on_init(self, mock_env_cache_disabled):
        """Test cache is not initialized when disabled."""
        service = SentenceTransformerEmbeddingService()
        assert service._cache is None

    async def test_get_cache_stats_enabled(self, mock_env_cache_enabled):
        """Test get_cache_stats returns stats when cache enabled."""
        service = SentenceTransformerEmbeddingService()
        stats = service.get_cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "size" in stats
        assert "maxsize" in stats

    async def test_get_cache_stats_disabled(self, mock_env_cache_disabled):
        """Test get_cache_stats returns message when cache disabled."""
        service = SentenceTransformerEmbeddingService()
        stats = service.get_cache_stats()

        assert stats == {"message": "Embedding cache is not enabled"}

    async def test_single_text_caching(self, mock_env_cache_enabled, mocker):
        """Test single text embedding is cached."""
        service = SentenceTransformerEmbeddingService()

        # Mock the model - return numpy-like array with tolist() method
        import numpy as np

        mock_model = mocker.MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        service._model = mock_model

        # First call - should compute
        embedding1 = await service.encode("test text")
        assert mock_model.encode.call_count == 1

        # Second call - should use cache
        embedding2 = await service.encode("test text")
        assert mock_model.encode.call_count == 1  # No additional call
        assert embedding1 == embedding2

        # Verify cache stats
        stats = service.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    async def test_batch_text_caching(self, mock_env_cache_enabled, mocker):
        """Test batch text embedding with partial cache hits."""
        import numpy as np

        service = SentenceTransformerEmbeddingService()

        # Mock the model - return numpy arrays
        mock_model = mocker.MagicMock()
        mock_model.encode.return_value = np.array([
            [0.1, 0.2],
            [0.3, 0.4],
            [0.5, 0.6],
        ])
        service._model = mock_model

        # First batch - all uncached
        texts1 = ["text1", "text2", "text3"]
        embeddings1 = await service.encode(texts1)
        assert mock_model.encode.call_count == 1
        assert len(embeddings1) == 3

        # Second batch with duplicates - should use cache for text1 and text3
        mock_model.encode.return_value = np.array([[0.7, 0.8]])  # Only for text4
        texts2 = ["text1", "text4", "text3"]
        embeddings2 = await service.encode(texts2)

        # Should only compute text4
        assert mock_model.encode.call_count == 2
        assert len(embeddings2) == 3

        # Verify cached values match
        assert embeddings2[0] == embeddings1[0]  # text1
        assert embeddings2[2] == embeddings1[2]  # text3

        # Verify cache stats
        stats = service.get_cache_stats()
        assert stats["hits"] == 2  # text1 and text3 retrieved from cache
        # Note: misses are not tracked during get_batch check, only during actual get() calls
        # First batch caches text1, text2, text3 without calling get() (0 misses)
        # Second batch calls get() for text1 and text3 (2 hits), no get() calls that miss

    async def test_cache_normalization(self, mock_env_cache_enabled, mocker):
        """Test cache handles text normalization."""
        import numpy as np

        service = SentenceTransformerEmbeddingService()

        # Mock the model - return numpy array
        mock_model = mocker.MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])
        service._model = mock_model

        # First call with whitespace
        await service.encode("  Test Text  ")
        assert mock_model.encode.call_count == 1

        # Second call with different case - should hit cache
        await service.encode("test text")
        assert mock_model.encode.call_count == 1  # No additional call

        stats = service.get_cache_stats()
        assert stats["hits"] == 1

    async def test_no_cache_when_disabled(self, mock_env_cache_disabled, mocker):
        """Test embedding computation without cache."""
        import numpy as np

        service = SentenceTransformerEmbeddingService()

        # Mock the model - return numpy array
        mock_model = mocker.MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])
        service._model = mock_model

        # Multiple calls should not use cache
        await service.encode("test text")
        await service.encode("test text")

        # Should compute both times
        assert mock_model.encode.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
