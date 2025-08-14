from typing import Any, Protocol


class CacheService(Protocol):
    """Interface for a key-value cache service."""

    async def get(self, key: str) -> Any | None:
        """Retrieve an item from the cache."""
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store an item in the cache with an optional time-to-live (seconds)."""
        ...

    async def delete(self, key: str) -> None:
        """Delete an item from the cache."""
        ...

    async def clear(self) -> None:
        """Clear the entire cache."""
        ...
