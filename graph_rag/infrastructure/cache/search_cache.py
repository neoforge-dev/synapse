"""Search result caching for vector and graph searches."""

import logging
from collections.abc import Callable

from .query_cache import QueryCache

logger = logging.getLogger(__name__)


class SearchCache:
    """Specialized cache for search results."""

    def __init__(self, cache_service=None):
        self._query_cache = QueryCache(cache_service)
        logger.info("SearchCache initialized")

    async def get_or_compute(
        self,
        cache_key: str,
        search_func: Callable,
        *args,
        ttl: int = 600,  # Search results cached for 10 minutes
        **kwargs
    ) -> list[dict]:
        """Get search results from cache or compute them."""
        return await self._query_cache.get_or_compute(
            cache_key, search_func, *args, ttl=ttl, **kwargs
        )

    def generate_vector_search_key(self, query_vector: list[float], top_k: int, filters: dict = None) -> str:
        """Generate cache key for vector search."""
        vector_hash = hash(tuple(query_vector))
        filter_hash = hash(tuple(sorted(filters.items()))) if filters else ""
        return f"vector_search:{vector_hash}:{top_k}:{filter_hash}"

    def generate_graph_search_key(self, node_id: str, depth: int, rel_types: list[str] = None) -> str:
        """Generate cache key for graph traversal."""
        rel_types_str = ",".join(sorted(rel_types)) if rel_types else ""
        return f"graph_search:{node_id}:{depth}:{rel_types_str}"
