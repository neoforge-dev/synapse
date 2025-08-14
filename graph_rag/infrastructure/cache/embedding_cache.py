"""Embedding caching to prevent expensive recomputation."""

import hashlib
import logging
from collections.abc import Callable

from .query_cache import QueryCache

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Specialized cache for embedding vectors."""

    def __init__(self, cache_service=None):
        self._query_cache = QueryCache(cache_service)
        logger.info("EmbeddingCache initialized")

    async def get_or_compute(
        self,
        text: str,
        embed_func: Callable,
        *args,
        ttl: int = 3600,  # Embeddings can be cached longer
        **kwargs
    ) -> list[float]:
        """Get embedding from cache or compute it."""
        # Generate cache key based on text content
        cache_key = f"embedding:{self._text_hash(text)}"

        return await self._query_cache.get_or_compute(
            cache_key, embed_func, *args, ttl=ttl, **kwargs
        )

    async def invalidate_text(self, text: str) -> None:
        """Invalidate cached embedding for specific text."""
        cache_key = f"embedding:{self._text_hash(text)}"
        await self._query_cache.invalidate(cache_key)

    @staticmethod
    def _text_hash(text: str) -> str:
        """Generate consistent hash for text content."""
        # Normalize text (strip whitespace, lowercase for consistency)
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
