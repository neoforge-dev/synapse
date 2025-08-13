"""Query result caching to improve performance of repeated operations."""

import asyncio
import hashlib
import json
import logging
from typing import Any, Callable, Optional

from .protocols import CacheService
from .memory_cache import MemoryCache

logger = logging.getLogger(__name__)


class QueryCache:
    """High-level cache for query results with automatic key generation."""
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        self._cache = cache_service or MemoryCache()
        logger.info(f"QueryCache initialized with {type(self._cache).__name__}")
    
    async def get_or_compute(
        self, 
        cache_key: str, 
        compute_func: Callable, 
        *args, 
        ttl: int = 300,
        **kwargs
    ) -> Any:
        """Get result from cache or compute and store it."""
        # Try to get from cache first
        cached_result = await self._cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache HIT for key: {cache_key}")
            return cached_result
        
        # Cache miss - compute the result
        logger.debug(f"Cache MISS for key: {cache_key}, computing...")
        if asyncio.iscoroutinefunction(compute_func):
            result = await compute_func(*args, **kwargs)
        else:
            result = compute_func(*args, **kwargs)
        
        # Store in cache
        await self._cache.set(cache_key, result, ttl=ttl)
        logger.debug(f"Cached result for key: {cache_key}")
        
        return result
    
    async def invalidate(self, cache_key: str) -> None:
        """Remove a specific key from cache."""
        await self._cache.delete(cache_key)
        logger.debug(f"Invalidated cache key: {cache_key}")
    
    async def clear(self) -> None:
        """Clear entire cache."""
        await self._cache.clear()
        logger.info("Cleared entire query cache")
    
    @staticmethod
    def generate_key(*components) -> str:
        """Generate a consistent cache key from components."""
        # Convert components to strings and join
        key_parts = []
        for component in components:
            if isinstance(component, (dict, list)):
                # For complex objects, use JSON representation
                key_parts.append(json.dumps(component, sort_keys=True))
            else:
                key_parts.append(str(component))
        
        combined = "|".join(key_parts)
        
        # For very long keys, use hash to keep them manageable
        if len(combined) > 200:
            return hashlib.md5(combined.encode()).hexdigest()
        
        return combined