"""Advanced Redis-backed rate limiting with sliding windows and multi-tier protection."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LimitType(str, Enum):
    """Rate limit types for different protection layers."""
    IP = "ip"
    USER = "user" 
    ENDPOINT = "endpoint"
    SUBSCRIPTION = "subscription"


class SubscriptionTier(str, Enum):
    """User subscription tiers with different limits."""
    FREE = "free_tier"
    PRO = "pro_tier"
    ENTERPRISE = "enterprise"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting rules."""
    requests_per_minute: int
    burst_allowance: int = 0
    window_size: int = 60  # seconds
    max_requests: Optional[int] = None  # for longer windows


@dataclass 
class RateLimitResult:
    """Result of rate limit check."""
    is_allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    limit_type: Optional[str] = None
    

class AdvancedRateLimiter:
    """Redis-backed sliding window rate limiter with multi-tier protection.
    
    Implements sophisticated rate limiting with:
    - Sliding window algorithm for accurate rate limiting
    - Multi-tier protection (IP, User, Endpoint)
    - Subscription-based limits
    - Burst allowances for traffic spikes
    - Connection-level protection
    """
    
    # IP-based limits (per minute)
    ANONYMOUS_LIMITS = {
        'requests_per_minute': 60,
        'auth_attempts': 5,
        'registration_attempts': 3,
        'password_reset': 2
    }
    
    # Burst allowances for legitimate traffic spikes  
    BURST_ALLOWANCES = {
        'short_burst': 120,  # 2x normal rate for 30 seconds
        'medium_burst': 180, # 3x normal rate for 10 seconds
    }
    
    # Subscription tier-based limits (per hour)
    USER_LIMITS = {
        SubscriptionTier.FREE: {
            'api_requests': 1000,
            'content_generations': 50, 
            'lead_queries': 100
        },
        SubscriptionTier.PRO: {
            'api_requests': 10000,
            'content_generations': 500,
            'lead_queries': 1000
        },
        SubscriptionTier.ENTERPRISE: {
            'api_requests': 100000,
            'content_generations': 5000,
            'lead_queries': 10000
        }
    }
    
    # Resource-intensive endpoints get special treatment
    ENDPOINT_LIMITS = {
        '/api/v1/content/generate': {'rate': 10, 'period': 60},
        '/api/v1/leads/analyze': {'rate': 20, 'period': 60},
        '/api/v1/analytics/report': {'rate': 5, 'period': 60},
        '/api/v1/scheduler/bulk': {'rate': 3, 'period': 300}
    }

    def __init__(self, redis_client: redis.Redis, window_size: int = 60):
        """Initialize rate limiter with Redis client.
        
        Args:
            redis_client: Async Redis client
            window_size: Default sliding window size in seconds
        """
        self.redis = redis_client
        self.window_size = window_size
        self.prefix = "rate_limit"
        
    async def is_allowed(
        self, 
        identifier: str, 
        limit_type: LimitType,
        max_requests: int,
        window_size: Optional[int] = None,
        endpoint: Optional[str] = None,
        user_tier: Optional[SubscriptionTier] = None
    ) -> RateLimitResult:
        """Check if request is allowed under rate limits.
        
        Uses sliding window algorithm with Redis for accurate rate limiting.
        
        Args:
            identifier: Unique identifier (IP, user_id, etc.)
            limit_type: Type of limit being checked
            max_requests: Maximum requests allowed in window
            window_size: Window size in seconds (defaults to instance window_size)
            endpoint: Specific endpoint being accessed
            user_tier: User's subscription tier for tier-based limits
            
        Returns:
            RateLimitResult with allowance status and metadata
        """
        window = window_size or self.window_size
        current_time = int(time.time())
        window_start = current_time - window
        
        # Create Redis key with type prefix
        key = f"{self.prefix}:{limit_type.value}:{identifier}"
        
        # Apply endpoint-specific limits if applicable
        if endpoint and endpoint in self.ENDPOINT_LIMITS:
            endpoint_config = self.ENDPOINT_LIMITS[endpoint]
            max_requests = min(max_requests, endpoint_config['rate'])
            window = endpoint_config['period']
            key = f"{key}:endpoint:{endpoint.replace('/', '_')}"
        
        # Apply subscription tier limits for user-based limiting
        if limit_type == LimitType.USER and user_tier:
            tier_limits = self.USER_LIMITS.get(user_tier, {})
            if endpoint and 'content' in endpoint:
                max_requests = min(max_requests, tier_limits.get('content_generations', max_requests))
            elif endpoint and 'leads' in endpoint:
                max_requests = min(max_requests, tier_limits.get('lead_queries', max_requests))
            else:
                max_requests = min(max_requests, tier_limits.get('api_requests', max_requests))
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove expired entries from sliding window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]
            
            # Check if under limit
            if current_count < max_requests:
                # Add current request to window
                await self.redis.zadd(key, {str(current_time): current_time})
                
                # Set expiration to cleanup old keys
                await self.redis.expire(key, window * 2)
                
                return RateLimitResult(
                    is_allowed=True,
                    remaining=max_requests - current_count - 1,
                    reset_time=current_time + window,
                    limit_type=limit_type.value
                )
            else:
                # Check for burst allowance
                burst_allowed = await self._check_burst_allowance(
                    identifier, limit_type, current_count, max_requests
                )
                
                if burst_allowed:
                    await self.redis.zadd(key, {str(current_time): current_time})
                    await self.redis.expire(key, window * 2)
                    
                    return RateLimitResult(
                        is_allowed=True,
                        remaining=0,
                        reset_time=current_time + window,
                        limit_type=f"{limit_type.value}_burst"
                    )
                
                # Rate limit exceeded
                oldest_request_time = await self.redis.zrange(key, 0, 0, withscores=True)
                if oldest_request_time:
                    oldest_time = int(oldest_request_time[0][1])
                    retry_after = max(1, oldest_time + window - current_time)
                else:
                    retry_after = window
                    
                return RateLimitResult(
                    is_allowed=False,
                    remaining=0,
                    reset_time=current_time + window,
                    retry_after=retry_after,
                    limit_type=limit_type.value
                )
                
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            # Fail open - allow request if Redis is unavailable
            return RateLimitResult(
                is_allowed=True,
                remaining=-1,
                reset_time=current_time + window,
                limit_type=f"{limit_type.value}_fallback"
            )
    
    async def _check_burst_allowance(
        self, 
        identifier: str, 
        limit_type: LimitType, 
        current_count: int, 
        base_limit: int
    ) -> bool:
        """Check if burst allowance can be applied.
        
        Allows legitimate traffic spikes while preventing abuse.
        
        Args:
            identifier: Request identifier
            limit_type: Type of limit being checked
            current_count: Current request count in window
            base_limit: Base rate limit
            
        Returns:
            Whether burst allowance can be applied
        """
        burst_key = f"{self.prefix}:burst:{limit_type.value}:{identifier}"
        current_time = int(time.time())
        
        try:
            # Check recent burst usage
            recent_bursts = await self.redis.zcount(
                burst_key, current_time - 300, current_time  # Last 5 minutes
            )
            
            # Allow short burst if under medium burst limit and hasn't used many bursts recently
            if (current_count <= self.BURST_ALLOWANCES['medium_burst'] and 
                recent_bursts < 3):
                
                # Record burst usage
                await self.redis.zadd(burst_key, {str(current_time): current_time})
                await self.redis.expire(burst_key, 3600)  # Cleanup after 1 hour
                
                logger.info(
                    f"Burst allowance granted for {identifier} "
                    f"({limit_type.value}): {current_count}/{base_limit}"
                )
                return True
                
        except Exception as e:
            logger.error(f"Burst allowance check failed: {e}")
            
        return False
    
    async def get_rate_limit_status(
        self, 
        identifier: str, 
        limit_type: LimitType,
        window_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get current rate limit status without incrementing counters.
        
        Args:
            identifier: Request identifier
            limit_type: Type of limit to check
            window_size: Window size in seconds
            
        Returns:
            Dictionary with current rate limit status
        """
        window = window_size or self.window_size
        current_time = int(time.time())
        window_start = current_time - window
        
        key = f"{self.prefix}:{limit_type.value}:{identifier}"
        
        try:
            # Clean up expired entries and count current
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zrange(key, 0, 0, withscores=True)  # Oldest entry
            results = await pipe.execute()
            
            current_count = results[1]
            oldest_entries = results[2]
            
            oldest_time = None
            if oldest_entries:
                oldest_time = int(oldest_entries[0][1])
                
            return {
                "identifier": identifier,
                "limit_type": limit_type.value,
                "current_count": current_count,
                "window_size": window,
                "oldest_request_time": oldest_time,
                "window_start": window_start,
                "window_end": current_time + window
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {
                "identifier": identifier, 
                "limit_type": limit_type.value,
                "error": str(e)
            }
    
    async def reset_rate_limit(
        self, 
        identifier: str, 
        limit_type: LimitType
    ) -> bool:
        """Reset rate limit for identifier (admin function).
        
        Args:
            identifier: Request identifier to reset
            limit_type: Type of limit to reset
            
        Returns:
            Whether reset was successful
        """
        key = f"{self.prefix}:{limit_type.value}:{identifier}"
        burst_key = f"{self.prefix}:burst:{limit_type.value}:{identifier}"
        
        try:
            pipe = self.redis.pipeline()
            pipe.delete(key)
            pipe.delete(burst_key)
            results = await pipe.execute()
            
            logger.info(f"Rate limit reset for {identifier} ({limit_type.value})")
            return all(results)
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics.
        
        Returns:
            Dictionary with global rate limiting metrics
        """
        try:
            # Count keys by type
            stats = {}
            for limit_type in LimitType:
                pattern = f"{self.prefix}:{limit_type.value}:*"
                keys = await self.redis.keys(pattern)
                stats[f"{limit_type.value}_active_limiters"] = len(keys)
                
            # Get burst statistics
            burst_pattern = f"{self.prefix}:burst:*"
            burst_keys = await self.redis.keys(burst_pattern)
            stats["active_burst_allowances"] = len(burst_keys)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get global stats: {e}")
            return {"error": str(e)}