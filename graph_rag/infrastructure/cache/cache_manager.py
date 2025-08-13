"""Cache manager for coordinated cache operations and invalidation."""

import logging
import re
from typing import Any, Optional

from .protocols import CacheService
from .memory_cache import MemoryCache

logger = logging.getLogger(__name__)


class CacheManager:
    """High-level cache manager with pattern-based invalidation."""
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        self._cache = cache_service or MemoryCache()
        logger.info(f"CacheManager initialized with {type(self._cache).__name__}")
    
    async def get(self, key: str) -> Any:
        """Get value from cache."""
        return await self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        await self._cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> None:
        """Delete specific key from cache."""
        await self._cache.delete(key)
    
    async def clear(self) -> None:
        """Clear entire cache."""
        await self._cache.clear()
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern.
        
        Args:
            pattern: Pattern with * wildcards (e.g., "graph:node123*")
            
        Returns:
            Number of keys invalidated
        """
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(f"^{regex_pattern}$")
        
        # Get all keys and filter by pattern
        # Note: This is a simplified implementation for MemoryCache
        # For Redis, you'd use SCAN with MATCH pattern
        invalidated_count = 0
        
        if hasattr(self._cache, '_cache'):  # MemoryCache implementation
            keys_to_delete = []
            for key in self._cache._cache.keys():
                if regex.match(key):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                await self._cache.delete(key)
                invalidated_count += 1
        
        logger.info(f"Invalidated {invalidated_count} keys matching pattern: {pattern}")
        return invalidated_count
    
    async def invalidate_for_document(self, document_id: str) -> None:
        """Invalidate all cache entries related to a document."""
        patterns = [
            f"graph:*{document_id}*",
            f"search:*{document_id}*", 
            f"embedding:*{document_id}*",
            f"vector_search:*{document_id}*"
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            count = await self.invalidate_pattern(pattern)
            total_invalidated += count
        
        logger.info(f"Invalidated {total_invalidated} cache entries for document: {document_id}")
    
    async def invalidate_for_node(self, node_id: str) -> None:
        """Invalidate all cache entries related to a graph node."""
        patterns = [
            f"graph:*{node_id}*",
            f"graph_search:{node_id}:*",
            f"graph_neighbors:{node_id}:*"
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            count = await self.invalidate_pattern(pattern)
            total_invalidated += count
        
        logger.info(f"Invalidated {total_invalidated} cache entries for node: {node_id}")