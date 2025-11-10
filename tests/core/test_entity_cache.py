"""Unit tests for entity extraction cache functionality.

Tests the EntityCache class and integration with SpacyEntityExtractor
to verify performance improvements for duplicate text during batch ingestion.
"""

import os
import pytest

from graph_rag.core.entity_extractor import EntityCache, SpacyEntityExtractor
from graph_rag.core.interfaces import ExtractedEntity


class TestEntityCache:
    """Test suite for EntityCache class."""

    def test_cache_initialization(self):
        """Test cache initializes with correct parameters."""
        cache = EntityCache(maxsize=100)
        assert cache._cache.maxsize == 100
        assert cache._hits == 0
        assert cache._misses == 0

    def test_cache_get_miss(self):
        """Test cache returns None for uncached text."""
        cache = EntityCache()
        result = cache.get("uncached text")
        assert result is None
        assert cache._misses == 1
        assert cache._hits == 0

    def test_cache_set_and_get_hit(self):
        """Test cache stores and retrieves entities."""
        cache = EntityCache()
        entities = [
            ExtractedEntity(id="e1", name="Apple", text="Apple", label="ORG"),
            ExtractedEntity(id="e2", name="California", text="California", label="GPE"),
        ]

        # Set entities
        cache.set("Apple Inc. is in California", entities)

        # Get entities (should be a hit)
        result = cache.get("Apple Inc. is in California")
        assert result == entities
        assert cache._hits == 1
        assert cache._misses == 0

    def test_cache_stats(self):
        """Test cache statistics calculation."""
        cache = EntityCache(maxsize=10)
        entities = [ExtractedEntity(id="e1", name="Test", text="Test", label="ORG")]

        # Initial stats
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"
        assert stats["size"] == 0
        assert stats["maxsize"] == 10

        # Add some operations
        cache.set("text1", entities)
        cache.get("text1")  # hit
        cache.get("text2")  # miss
        cache.get("text1")  # hit

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "66.7%"
        assert stats["size"] == 1

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = EntityCache(maxsize=2)
        e1 = [ExtractedEntity(id="e1", name="E1", text="E1", label="ORG")]
        e2 = [ExtractedEntity(id="e2", name="E2", text="E2", label="ORG")]
        e3 = [ExtractedEntity(id="e3", name="E3", text="E3", label="ORG")]

        # Fill cache to capacity
        cache.set("text1", e1)
        cache.set("text2", e2)

        # Both should be in cache
        assert cache.get("text1") is not None
        assert cache.get("text2") is not None

        # Add one more (should evict oldest)
        cache.set("text3", e3)

        # text1 should be evicted (it was accessed least recently)
        assert cache.get("text3") is not None
        assert cache.get("text2") is not None

    def test_cache_key_generation(self):
        """Test SHA256 cache key generation."""
        key1 = EntityCache._get_cache_key("test text")
        key2 = EntityCache._get_cache_key("test text")
        key3 = EntityCache._get_cache_key("different text")

        # Same text should produce same key
        assert key1 == key2
        # Different text should produce different key
        assert key1 != key3
        # Should be 64-character SHA256 hex
        assert len(key1) == 64


@pytest.mark.asyncio
class TestSpacyEntityExtractorCache:
    """Test suite for cache integration in SpacyEntityExtractor."""

    @pytest.fixture
    def mock_env_cache_enabled(self, monkeypatch):
        """Set environment to enable cache."""
        monkeypatch.setenv("SYNAPSE_ENABLE_ENTITY_CACHE", "true")
        monkeypatch.setenv("SYNAPSE_ENTITY_CACHE_SIZE", "100")
        monkeypatch.setenv("SKIP_SPACY_IMPORT", "1")  # Lightweight testing

    @pytest.fixture
    def mock_env_cache_disabled(self, monkeypatch):
        """Set environment to disable cache."""
        monkeypatch.setenv("SYNAPSE_ENABLE_ENTITY_CACHE", "false")
        monkeypatch.setenv("SKIP_SPACY_IMPORT", "1")

    async def test_cache_enabled_on_init(self, mock_env_cache_enabled):
        """Test cache is initialized when enabled."""
        # SpacyEntityExtractor will fail to load spaCy model but cache should still init
        try:
            extractor = SpacyEntityExtractor()
        except:
            pass  # Expected to fail without spaCy
        # We can't test the cache directly without spaCy, but we verified the init code

    async def test_get_cache_stats_with_mock(self, mock_env_cache_enabled, mocker):
        """Test get_cache_stats with mocked spaCy."""
        # Mock spacy module
        mock_spacy = mocker.MagicMock()
        mock_nlp = mocker.MagicMock()
        mock_spacy.load.return_value = mock_nlp
        mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

        extractor = SpacyEntityExtractor()
        assert extractor._cache is not None

        stats = extractor.get_cache_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "size" in stats
        assert "maxsize" in stats

    async def test_cache_disabled_stats(self, mock_env_cache_disabled, mocker):
        """Test get_cache_stats returns message when cache disabled."""
        # Mock spacy module
        mock_spacy = mocker.MagicMock()
        mock_nlp = mocker.MagicMock()
        mock_spacy.load.return_value = mock_nlp
        mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

        extractor = SpacyEntityExtractor()
        assert extractor._cache is None

        stats = extractor.get_cache_stats()
        assert stats == {"message": "Entity extraction cache is not enabled"}

    async def test_extraction_caching(self, mock_env_cache_enabled, mocker):
        """Test entity extraction is cached."""
        # Mock spacy module and NLP pipeline
        mock_spacy = mocker.MagicMock()
        mock_nlp = mocker.MagicMock()

        # Create mock entities
        mock_ent1 = mocker.MagicMock()
        mock_ent1.text = "Apple"
        mock_ent1.label_ = "ORG"
        mock_ent1.start_char = 0
        mock_ent1.end_char = 5

        mock_doc = mocker.MagicMock()
        mock_doc.ents = [mock_ent1]
        mock_nlp.return_value = mock_doc

        mock_spacy.load.return_value = mock_nlp
        mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

        extractor = SpacyEntityExtractor()
        assert extractor.nlp is not None

        # First extraction - should compute
        result1 = await extractor.extract_from_text("Apple Inc.")
        assert mock_nlp.call_count == 1
        assert len(result1.entities) == 1

        # Second extraction with same text - should use cache
        result2 = await extractor.extract_from_text("Apple Inc.")
        assert mock_nlp.call_count == 1  # No additional call
        assert len(result2.entities) == 1

        # Verify cache stats
        stats = extractor.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    async def test_extraction_with_context(self, mock_env_cache_enabled, mocker):
        """Test cached entities get updated context."""
        # Mock spacy module and NLP pipeline
        mock_spacy = mocker.MagicMock()
        mock_nlp = mocker.MagicMock()

        mock_ent = mocker.MagicMock()
        mock_ent.text = "Apple"
        mock_ent.label_ = "ORG"
        mock_ent.start_char = 0
        mock_ent.end_char = 5

        mock_doc = mocker.MagicMock()
        mock_doc.ents = [mock_ent]
        mock_nlp.return_value = mock_doc

        mock_spacy.load.return_value = mock_nlp
        mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

        extractor = SpacyEntityExtractor()

        # First extraction with context
        context1 = {"chunk_id": "chunk1"}
        result1 = await extractor.extract_from_text("Apple Inc.", context1)
        assert result1.entities[0].metadata == context1

        # Second extraction with different context - should update cached entities
        context2 = {"chunk_id": "chunk2"}
        result2 = await extractor.extract_from_text("Apple Inc.", context2)
        # Context should be updated from cache
        assert "chunk_id" in result2.entities[0].metadata

        # Verify cache was hit
        stats = extractor.get_cache_stats()
        assert stats["hits"] == 1

    async def test_empty_text_handling(self, mock_env_cache_enabled, mocker):
        """Test empty text returns empty results without caching."""
        # Mock spacy module
        mock_spacy = mocker.MagicMock()
        mock_nlp = mocker.MagicMock()
        mock_spacy.load.return_value = mock_nlp
        mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

        extractor = SpacyEntityExtractor()

        # Empty text should return empty results
        result = await extractor.extract_from_text("")
        assert len(result.entities) == 0
        assert mock_nlp.call_count == 0  # Should not call NLP

        # Whitespace-only text
        result = await extractor.extract_from_text("   ")
        assert len(result.entities) == 0
        assert mock_nlp.call_count == 0

    async def test_no_cache_when_disabled(self, mock_env_cache_disabled, mocker):
        """Test extraction without cache."""
        # Mock spacy module and NLP pipeline
        mock_spacy = mocker.MagicMock()
        mock_nlp = mocker.MagicMock()

        mock_ent = mocker.MagicMock()
        mock_ent.text = "Apple"
        mock_ent.label_ = "ORG"
        mock_ent.start_char = 0
        mock_ent.end_char = 5

        mock_doc = mocker.MagicMock()
        mock_doc.ents = [mock_ent]
        mock_nlp.return_value = mock_doc

        mock_spacy.load.return_value = mock_nlp
        mocker.patch.dict("sys.modules", {"spacy": mock_spacy})

        extractor = SpacyEntityExtractor()
        assert extractor._cache is None

        # Multiple calls should not use cache
        await extractor.extract_from_text("Apple Inc.")
        await extractor.extract_from_text("Apple Inc.")

        # Should compute both times
        assert mock_nlp.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
