"""Enterprise-grade rate limiting system with multi-tier support."""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass

from pydantic import BaseModel, Field

from ...compliance.audit_logging import ComplianceAuditLogger, AuditEvent, AuditEventType, AuditSeverity


logger = logging.getLogger(__name__)


class RateLimitTier(str, Enum):
    """Enterprise rate limiting tiers based on contract value."""
    
    BASIC = "basic"              # $0-50K contracts
    PROFESSIONAL = "professional"  # $50K-150K contracts  
    ENTERPRISE = "enterprise"    # $150K-500K contracts
    PREMIUM = "premium"          # $500K+ contracts


class RateLimitType(str, Enum):
    """Types of rate limits."""
    
    REQUESTS_PER_SECOND = "requests_per_second"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    CONCURRENT_REQUESTS = "concurrent_requests"
    DATA_TRANSFER_MB = "data_transfer_mb"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    
    limit_type: RateLimitType
    limit: int
    window_seconds: int
    burst_allowance: float = 1.5  # Allow 50% burst above limit


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, limit_type: RateLimitType, limit: int, 
                 current: int, retry_after: Optional[int] = None):
        self.limit_type = limit_type
        self.limit = limit
        self.current = current
        self.retry_after = retry_after
        
        message = f"Rate limit exceeded: {current}/{limit} {limit_type.value}"
        if retry_after:
            message += f". Retry after {retry_after} seconds."
        
        super().__init__(message)


class ClientRateLimitState(BaseModel):
    """Rate limit state for a client."""
    
    client_id: str
    tenant_id: str
    tier: RateLimitTier
    
    # Request tracking
    request_counts: Dict[RateLimitType, deque] = Field(default_factory=lambda: defaultdict(deque))
    concurrent_requests: int = 0
    data_transfer_mb: float = 0.0
    
    # State tracking
    first_request: Optional[datetime] = None
    last_request: Optional[datetime] = None
    total_requests: int = 0
    blocked_requests: int = 0
    
    # Burst handling
    burst_tokens: Dict[RateLimitType, float] = Field(default_factory=lambda: defaultdict(float))
    last_token_refresh: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            deque: list
        }


class RateLimiter:
    """Enterprise rate limiting system with tiered limits and burst handling."""
    
    def __init__(self, audit_logger: Optional[ComplianceAuditLogger] = None):
        self.audit_logger = audit_logger
        
        # Rate limit configurations by tier
        self.tier_limits = self._initialize_tier_limits()
        
        # Client state tracking
        self.client_states: Dict[str, ClientRateLimitState] = {}
        
        # Global state
        self.total_requests = 0
        self.blocked_requests = 0
        self.start_time = datetime.utcnow()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
    def _initialize_tier_limits(self) -> Dict[RateLimitTier, Dict[RateLimitType, RateLimit]]:
        """Initialize rate limit configurations for each tier."""
        
        return {
            RateLimitTier.BASIC: {
                RateLimitType.REQUESTS_PER_SECOND: RateLimit(RateLimitType.REQUESTS_PER_SECOND, 10, 1),
                RateLimitType.REQUESTS_PER_MINUTE: RateLimit(RateLimitType.REQUESTS_PER_MINUTE, 300, 60),
                RateLimitType.REQUESTS_PER_HOUR: RateLimit(RateLimitType.REQUESTS_PER_HOUR, 5000, 3600),
                RateLimitType.REQUESTS_PER_DAY: RateLimit(RateLimitType.REQUESTS_PER_DAY, 50000, 86400),
                RateLimitType.CONCURRENT_REQUESTS: RateLimit(RateLimitType.CONCURRENT_REQUESTS, 50, 0),
                RateLimitType.DATA_TRANSFER_MB: RateLimit(RateLimitType.DATA_TRANSFER_MB, 1000, 86400)
            },
            RateLimitTier.PROFESSIONAL: {
                RateLimitType.REQUESTS_PER_SECOND: RateLimit(RateLimitType.REQUESTS_PER_SECOND, 25, 1),
                RateLimitType.REQUESTS_PER_MINUTE: RateLimit(RateLimitType.REQUESTS_PER_MINUTE, 750, 60),
                RateLimitType.REQUESTS_PER_HOUR: RateLimit(RateLimitType.REQUESTS_PER_HOUR, 15000, 3600),
                RateLimitType.REQUESTS_PER_DAY: RateLimit(RateLimitType.REQUESTS_PER_DAY, 150000, 86400),
                RateLimitType.CONCURRENT_REQUESTS: RateLimit(RateLimitType.CONCURRENT_REQUESTS, 100, 0),
                RateLimitType.DATA_TRANSFER_MB: RateLimit(RateLimitType.DATA_TRANSFER_MB, 5000, 86400)
            },
            RateLimitTier.ENTERPRISE: {
                RateLimitType.REQUESTS_PER_SECOND: RateLimit(RateLimitType.REQUESTS_PER_SECOND, 50, 1),
                RateLimitType.REQUESTS_PER_MINUTE: RateLimit(RateLimitType.REQUESTS_PER_MINUTE, 1500, 60),
                RateLimitType.REQUESTS_PER_HOUR: RateLimit(RateLimitType.REQUESTS_PER_HOUR, 50000, 3600),
                RateLimitType.REQUESTS_PER_DAY: RateLimit(RateLimitType.REQUESTS_PER_DAY, 500000, 86400),
                RateLimitType.CONCURRENT_REQUESTS: RateLimit(RateLimitType.CONCURRENT_REQUESTS, 200, 0),
                RateLimitType.DATA_TRANSFER_MB: RateLimit(RateLimitType.DATA_TRANSFER_MB, 20000, 86400)
            },
            RateLimitTier.PREMIUM: {
                RateLimitType.REQUESTS_PER_SECOND: RateLimit(RateLimitType.REQUESTS_PER_SECOND, 100, 1),
                RateLimitType.REQUESTS_PER_MINUTE: RateLimit(RateLimitType.REQUESTS_PER_MINUTE, 3000, 60),
                RateLimitType.REQUESTS_PER_HOUR: RateLimit(RateLimitType.REQUESTS_PER_HOUR, 100000, 3600),
                RateLimitType.REQUESTS_PER_DAY: RateLimit(RateLimitType.REQUESTS_PER_DAY, 1000000, 86400),
                RateLimitType.CONCURRENT_REQUESTS: RateLimit(RateLimitType.CONCURRENT_REQUESTS, 500, 0),
                RateLimitType.DATA_TRANSFER_MB: RateLimit(RateLimitType.DATA_TRANSFER_MB, 100000, 86400)
            }
        }
    
    async def check_rate_limits(self, client_id: str, tenant_id: str, 
                              tier: RateLimitTier, request_size_mb: float = 0.0) -> None:
        """Check all rate limits for a client request.
        
        Raises:
            RateLimitExceeded: If any rate limit is exceeded
        """
        # Get or create client state
        state = self._get_client_state(client_id, tenant_id, tier)
        
        # Refresh burst tokens
        self._refresh_burst_tokens(state)
        
        # Get tier limits
        limits = self.tier_limits[tier]
        now = datetime.utcnow()
        
        # Check each rate limit
        for limit_type, rate_limit in limits.items():
            if limit_type == RateLimitType.CONCURRENT_REQUESTS:
                # Check concurrent requests
                if state.concurrent_requests >= rate_limit.limit:
                    await self._log_rate_limit_exceeded(client_id, tenant_id, limit_type, 
                                                       rate_limit.limit, state.concurrent_requests)
                    raise RateLimitExceeded(limit_type, rate_limit.limit, state.concurrent_requests)
                    
            elif limit_type == RateLimitType.DATA_TRANSFER_MB:
                # Check daily data transfer
                if state.data_transfer_mb + request_size_mb > rate_limit.limit:
                    await self._log_rate_limit_exceeded(client_id, tenant_id, limit_type,
                                                       rate_limit.limit, int(state.data_transfer_mb + request_size_mb))
                    raise RateLimitExceeded(limit_type, rate_limit.limit, int(state.data_transfer_mb + request_size_mb))
                    
            else:
                # Check request-based limits
                current_count = self._count_requests_in_window(state, limit_type, rate_limit.window_seconds)
                
                # Check if limit exceeded (with burst allowance)
                effective_limit = int(rate_limit.limit * rate_limit.burst_allowance)
                
                # Use burst tokens if available
                if current_count >= rate_limit.limit:
                    tokens_needed = current_count - rate_limit.limit + 1
                    if state.burst_tokens[limit_type] >= tokens_needed:
                        state.burst_tokens[limit_type] -= tokens_needed
                    elif current_count >= effective_limit:
                        retry_after = self._calculate_retry_after(state, limit_type, rate_limit.window_seconds)
                        await self._log_rate_limit_exceeded(client_id, tenant_id, limit_type,
                                                           rate_limit.limit, current_count, retry_after)
                        raise RateLimitExceeded(limit_type, rate_limit.limit, current_count, retry_after)
        
        # All checks passed - record the request
        await self._record_request(state, request_size_mb)
    
    async def start_request(self, client_id: str) -> None:
        """Mark start of concurrent request."""
        if client_id in self.client_states:
            self.client_states[client_id].concurrent_requests += 1
    
    async def end_request(self, client_id: str) -> None:
        """Mark end of concurrent request."""
        if client_id in self.client_states:
            state = self.client_states[client_id]
            state.concurrent_requests = max(0, state.concurrent_requests - 1)
    
    def _get_client_state(self, client_id: str, tenant_id: str, 
                         tier: RateLimitTier) -> ClientRateLimitState:
        """Get or create client rate limit state."""
        if client_id not in self.client_states:
            self.client_states[client_id] = ClientRateLimitState(
                client_id=client_id,
                tenant_id=tenant_id,
                tier=tier
            )
        
        return self.client_states[client_id]
    
    def _refresh_burst_tokens(self, state: ClientRateLimitState) -> None:
        """Refresh burst tokens for a client based on tier."""
        now = datetime.utcnow()
        time_passed = (now - state.last_token_refresh).total_seconds()
        
        # Refresh tokens (1 token per second, max 10 tokens per tier)
        max_tokens = {
            RateLimitTier.BASIC: 5,
            RateLimitTier.PROFESSIONAL: 10, 
            RateLimitTier.ENTERPRISE: 20,
            RateLimitTier.PREMIUM: 50
        }[state.tier]
        
        for limit_type in RateLimitType:
            if limit_type not in [RateLimitType.CONCURRENT_REQUESTS, RateLimitType.DATA_TRANSFER_MB]:
                tokens_to_add = min(time_passed / 2, max_tokens - state.burst_tokens[limit_type])
                state.burst_tokens[limit_type] = min(max_tokens, 
                                                   state.burst_tokens[limit_type] + tokens_to_add)
        
        state.last_token_refresh = now
    
    def _count_requests_in_window(self, state: ClientRateLimitState, 
                                 limit_type: RateLimitType, window_seconds: int) -> int:
        """Count requests in the specified time window."""
        now = time.time()
        cutoff = now - window_seconds
        
        # Get the deque for this limit type
        request_times = state.request_counts[limit_type]
        
        # Remove old requests
        while request_times and request_times[0] < cutoff:
            request_times.popleft()
        
        return len(request_times)
    
    def _calculate_retry_after(self, state: ClientRateLimitState,
                              limit_type: RateLimitType, window_seconds: int) -> int:
        """Calculate retry-after seconds."""
        request_times = state.request_counts[limit_type]
        if not request_times:
            return 1
        
        # Time until oldest request in window expires
        oldest_request = request_times[0]
        now = time.time()
        retry_after = int(oldest_request + window_seconds - now) + 1
        
        return max(1, retry_after)
    
    async def _record_request(self, state: ClientRateLimitState, request_size_mb: float) -> None:
        """Record a successful request."""
        now = time.time()
        now_dt = datetime.utcnow()
        
        # Update request counts
        for limit_type in [RateLimitType.REQUESTS_PER_SECOND, RateLimitType.REQUESTS_PER_MINUTE,
                          RateLimitType.REQUESTS_PER_HOUR, RateLimitType.REQUESTS_PER_DAY]:
            state.request_counts[limit_type].append(now)
        
        # Update data transfer
        state.data_transfer_mb += request_size_mb
        
        # Update state tracking
        if state.first_request is None:
            state.first_request = now_dt
        state.last_request = now_dt
        state.total_requests += 1
        
        # Update global counters
        self.total_requests += 1
    
    async def _log_rate_limit_exceeded(self, client_id: str, tenant_id: str,
                                     limit_type: RateLimitType, limit: int, current: int,
                                     retry_after: Optional[int] = None) -> None:
        """Log rate limit exceeded event."""
        if self.audit_logger:
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                tenant_id=tenant_id,
                action=f"Rate limit exceeded: {limit_type.value}",
                outcome="failure",
                severity=AuditSeverity.MEDIUM,
                details={
                    "client_id": client_id,
                    "limit_type": limit_type.value,
                    "limit": limit,
                    "current": current,
                    "retry_after": retry_after
                }
            ))
        
        # Update blocked request counter
        if client_id in self.client_states:
            self.client_states[client_id].blocked_requests += 1
        self.blocked_requests += 1
        
        logger.warning(f"Rate limit exceeded for client {client_id}: {current}/{limit} {limit_type.value}")
    
    async def get_client_usage(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get current usage statistics for a client."""
        if client_id not in self.client_states:
            return None
        
        state = self.client_states[client_id]
        limits = self.tier_limits[state.tier]
        now = datetime.utcnow()
        
        usage = {
            "client_id": client_id,
            "tenant_id": state.tenant_id,
            "tier": state.tier.value,
            "current_usage": {},
            "limits": {},
            "utilization_percentage": {},
            "total_requests": state.total_requests,
            "blocked_requests": state.blocked_requests,
            "concurrent_requests": state.concurrent_requests,
            "data_transfer_mb": state.data_transfer_mb,
            "burst_tokens": dict(state.burst_tokens),
            "first_request": state.first_request.isoformat() if state.first_request else None,
            "last_request": state.last_request.isoformat() if state.last_request else None
        }
        
        # Calculate current usage for each limit type
        for limit_type, rate_limit in limits.items():
            if limit_type == RateLimitType.CONCURRENT_REQUESTS:
                current = state.concurrent_requests
            elif limit_type == RateLimitType.DATA_TRANSFER_MB:
                current = int(state.data_transfer_mb)
            else:
                current = self._count_requests_in_window(state, limit_type, rate_limit.window_seconds)
            
            usage["current_usage"][limit_type.value] = current
            usage["limits"][limit_type.value] = rate_limit.limit
            usage["utilization_percentage"][limit_type.value] = (current / rate_limit.limit * 100) if rate_limit.limit > 0 else 0
        
        return usage
    
    async def get_global_statistics(self) -> Dict[str, Any]:
        """Get global rate limiting statistics."""
        now = datetime.utcnow()
        uptime_hours = (now - self.start_time).total_seconds() / 3600
        
        # Client statistics by tier
        clients_by_tier = defaultdict(int)
        total_blocked = 0
        
        for state in self.client_states.values():
            clients_by_tier[state.tier.value] += 1
            total_blocked += state.blocked_requests
        
        return {
            "uptime_hours": round(uptime_hours, 2),
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "success_rate": ((self.total_requests - self.blocked_requests) / max(1, self.total_requests)) * 100,
            "active_clients": len(self.client_states),
            "clients_by_tier": dict(clients_by_tier),
            "requests_per_hour": self.total_requests / max(1, uptime_hours),
            "generated_at": now.isoformat()
        }
    
    async def update_client_tier(self, client_id: str, new_tier: RateLimitTier) -> bool:
        """Update a client's rate limiting tier."""
        if client_id not in self.client_states:
            return False
        
        old_tier = self.client_states[client_id].tier
        self.client_states[client_id].tier = new_tier
        
        if self.audit_logger:
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                action=f"Updated client rate limit tier: {old_tier.value} -> {new_tier.value}",
                details={"client_id": client_id, "old_tier": old_tier.value, "new_tier": new_tier.value}
            ))
        
        logger.info(f"Updated client {client_id} rate limit tier: {old_tier.value} -> {new_tier.value}")
        
        return True
    
    async def reset_client_limits(self, client_id: str) -> bool:
        """Reset rate limits for a client (admin function)."""
        if client_id not in self.client_states:
            return False
        
        state = self.client_states[client_id]
        
        # Clear request history
        for limit_type in state.request_counts:
            state.request_counts[limit_type].clear()
        
        # Reset counters
        state.concurrent_requests = 0
        state.data_transfer_mb = 0.0
        state.blocked_requests = 0
        
        # Restore burst tokens
        max_tokens = {
            RateLimitTier.BASIC: 5,
            RateLimitTier.PROFESSIONAL: 10,
            RateLimitTier.ENTERPRISE: 20,
            RateLimitTier.PREMIUM: 50
        }[state.tier]
        
        for limit_type in RateLimitType:
            if limit_type not in [RateLimitType.CONCURRENT_REQUESTS, RateLimitType.DATA_TRANSFER_MB]:
                state.burst_tokens[limit_type] = max_tokens
        
        if self.audit_logger:
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
                action=f"Reset rate limits for client: {client_id}",
                details={"client_id": client_id, "tier": state.tier.value},
                severity=AuditSeverity.MEDIUM
            ))
        
        logger.info(f"Reset rate limits for client {client_id}")
        
        return True
    
    async def cleanup_inactive_clients(self, inactive_hours: int = 24) -> int:
        """Remove rate limit state for inactive clients."""
        cutoff = datetime.utcnow() - timedelta(hours=inactive_hours)
        inactive_clients = []
        
        for client_id, state in self.client_states.items():
            if state.last_request and state.last_request < cutoff:
                inactive_clients.append(client_id)
        
        for client_id in inactive_clients:
            del self.client_states[client_id]
        
        if inactive_clients:
            logger.info(f"Cleaned up {len(inactive_clients)} inactive client rate limit states")
        
        return len(inactive_clients)
    
    async def start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is not None:
            return
        
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(3600)  # Run every hour
                    await self.cleanup_inactive_clients()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Rate limiter cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Started rate limiter cleanup task")
    
    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped rate limiter cleanup task")