import asyncio
import logging
from typing import Any, Optional

from .protocols import CacheService  # Import the protocol

logger = logging.getLogger(__name__)


# Basic in-memory cache implementation
class MemoryCache(CacheService):
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._ttl: dict[str, Optional[asyncio.TimerHandle]] = {}
        logger.info("MemoryCache initialized.")

    async def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            logger.debug(f"Cache HIT for key: {key}")
            return self._cache[key]
        else:
            logger.debug(f"Cache MISS for key: {key}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        logger.debug(f"Cache SET for key: {key} with ttl={ttl}")
        self._cache[key] = value
        # Cancel existing timer if any
        if self._ttl.get(key):
            self._ttl[key].cancel()
            self._ttl[key] = None

        if ttl is not None and ttl > 0:
            loop = asyncio.get_running_loop()
            timer = loop.call_later(ttl, self._expire_key, key)
            self._ttl[key] = timer
        else:
            self._ttl[key] = None  # No TTL or indefinite

    def _expire_key(self, key: str) -> None:
        """Internal callback to remove an expired key."""
        if key in self._cache:
            logger.info(f"Cache key expired and removed: {key}")
            del self._cache[key]
            if key in self._ttl:
                del self._ttl[key]

    async def delete(self, key: str) -> None:
        logger.debug(f"Cache DELETE for key: {key}")
        if key in self._cache:
            del self._cache[key]
        if self._ttl.get(key):
            self._ttl[key].cancel()
            del self._ttl[key]

    async def clear(self) -> None:
        logger.info("Clearing entire MemoryCache.")
        for key in list(self._ttl.keys()):  # Iterate over copy
            if self._ttl[key]:
                self._ttl[key].cancel()
        self._cache.clear()
        self._ttl.clear()

    # Optional: Add methods for size, keys, etc. if needed


# </rewritten_file>
