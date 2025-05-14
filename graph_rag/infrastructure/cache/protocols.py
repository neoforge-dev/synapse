from typing import Any, Optional, Protocol


class CacheService(Protocol):
    """Interface for a key-value cache service."""

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from the cache."""
        ...

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store an item in the cache with an optional time-to-live (seconds)."""
        ...

    async def delete(self, key: str) -> None:
        """Delete an item from the cache."""
        ...

    async def clear(self) -> None:
        """Clear the entire cache."""
        ...
