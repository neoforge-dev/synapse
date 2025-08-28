"""Time service abstraction for consistent datetime handling in authentication."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional


class TimeService(ABC):
    """Abstract time service for consistent datetime operations."""
    
    @abstractmethod
    def utcnow(self) -> datetime:
        """Get current UTC datetime."""
        pass
    
    @abstractmethod
    def add_days(self, base_time: Optional[datetime] = None, days: int = 0) -> datetime:
        """Add days to a datetime, using utcnow if base_time is None."""
        pass


class SystemTimeService(TimeService):
    """Production time service using system time."""
    
    def utcnow(self) -> datetime:
        """Get current UTC datetime from system."""
        return datetime.utcnow()
    
    def add_days(self, base_time: Optional[datetime] = None, days: int = 0) -> datetime:
        """Add days to a datetime, using utcnow if base_time is None."""
        if base_time is None:
            base_time = self.utcnow()
        return base_time + timedelta(days=days)


class FixedTimeService(TimeService):
    """Test time service with fixed time for deterministic testing."""
    
    def __init__(self, fixed_time: datetime):
        self._fixed_time = fixed_time
    
    def utcnow(self) -> datetime:
        """Get fixed UTC datetime for testing."""
        return self._fixed_time
    
    def set_time(self, new_time: datetime) -> None:
        """Set the fixed time (for test manipulation)."""
        self._fixed_time = new_time
    
    def advance_days(self, days: int) -> None:
        """Advance the fixed time by specified days."""
        self._fixed_time += timedelta(days=days)
    
    def add_days(self, base_time: Optional[datetime] = None, days: int = 0) -> datetime:
        """Add days to a datetime, using fixed time if base_time is None."""
        if base_time is None:
            base_time = self.utcnow()
        return base_time + timedelta(days=days)


# Default time service instance for production use
default_time_service = SystemTimeService()