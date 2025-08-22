"""
Rate limiting middleware for API protection.

Implements sliding window rate limiting to prevent abuse and ensure fair usage.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Callable, Dict, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ...config import get_settings

logger = logging.getLogger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.
    
    Limits requests per user/IP to prevent abuse and ensure fair usage.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        
        # Rate limiting configuration
        self.rate_limits = {
            # General API limits (per minute)
            "general": {"requests": 100, "window": 60},
            # Authentication endpoints (stricter)
            "auth": {"requests": 10, "window": 60},
            # Content generation (resource intensive)
            "content": {"requests": 20, "window": 60},
            # Lead detection
            "leads": {"requests": 50, "window": 60},
        }
        
        # In-memory storage for rate limiting
        # In production, use Redis for distributed systems
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        
        # Cleanup old entries periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests."""
        try:
            # Get client identifier
            client_id = self._get_client_identifier(request)
            
            # Determine rate limit category
            category = self._get_rate_limit_category(request)
            
            # Check if request is allowed
            is_allowed, remaining, reset_time = await self._check_rate_limit(
                client_id, category
            )
            
            if not is_allowed:
                logger.warning(f"Rate limit exceeded for {client_id} on {category}")
                return self._rate_limit_response(remaining, reset_time)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers.update({
                "X-RateLimit-Limit": str(self.rate_limits[category]["requests"]),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_time)),
                "X-RateLimit-Window": str(self.rate_limits[category]["window"])
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Continue with request on middleware error
            return await call_next(request)
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for client (user or IP).
        
        Priority: User ID > API Key > IP Address
        """
        # Try to get user ID from authorization
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from ..auth.jwt import verify_token
            token = auth_header.split(" ")[1]
            token_data = verify_token(token)
            if token_data:
                return f"user:{token_data.user_id}"
        
        # Try API key
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"api:{api_key[:8]}..."  # Only log first 8 chars for security
        
        # Fallback to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_rate_limit_category(self, request: Request) -> str:
        """Determine rate limit category based on request path."""
        path = request.url.path.lower()
        
        if "/auth/" in path:
            return "auth"
        elif "/content/" in path:
            return "content"
        elif "/leads/" in path:
            return "leads"
        else:
            return "general"
    
    async def _check_rate_limit(
        self, client_id: str, category: str
    ) -> Tuple[bool, int, float]:
        """
        Check if request is within rate limit.
        
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time)
        """
        now = time.time()
        config = self.rate_limits[category]
        window_start = now - config["window"]
        
        # Clean up old entries
        if now - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_old_entries()
        
        # Get request history for this client+category
        key = f"{client_id}:{category}"
        request_times = self.request_counts[key]
        
        # Remove requests outside the time window
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # Check if within limit
        current_count = len(request_times)
        is_allowed = current_count < config["requests"]
        
        if is_allowed:
            # Add current request time
            request_times.append(now)
        
        # Calculate remaining and reset time
        remaining = max(0, config["requests"] - current_count - (1 if is_allowed else 0))
        reset_time = now + config["window"]
        
        return is_allowed, remaining, reset_time
    
    async def _cleanup_old_entries(self):
        """Clean up old rate limiting entries to prevent memory leaks."""
        now = time.time()
        cutoff_time = now - max(config["window"] for config in self.rate_limits.values())
        
        keys_to_remove = []
        
        for key, request_times in self.request_counts.items():
            # Remove old requests
            while request_times and request_times[0] < cutoff_time:
                request_times.popleft()
            
            # Remove empty deques
            if not request_times:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.request_counts[key]
        
        self.last_cleanup = now
        logger.debug(f"Cleaned up {len(keys_to_remove)} empty rate limit entries")
    
    def _rate_limit_response(self, remaining: int, reset_time: float) -> Response:
        """Generate rate limit exceeded response."""
        return Response(
            content="Rate limit exceeded. Too many requests.",
            status_code=429,
            headers={
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_time)),
                "Retry-After": str(int(reset_time - time.time())),
                "Content-Type": "application/json"
            }
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


class AdaptiveRateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Adaptive rate limiting that adjusts based on system load.
    
    Reduces rate limits when system is under high load to maintain stability.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.base_middleware = RateLimitingMiddleware(app)
        
        # System load tracking
        self.response_times = deque(maxlen=100)  # Last 100 response times
        self.error_count = 0
        self.total_requests = 0
        self.load_check_interval = 60  # Check load every minute
        self.last_load_check = time.time()
        
        # Load-based multipliers
        self.load_multipliers = {
            "low": 1.0,      # Normal rate limits
            "medium": 0.7,   # Reduce by 30%
            "high": 0.5,     # Reduce by 50%
            "critical": 0.2  # Reduce by 80%
        }
        
        self.current_load = "low"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply adaptive rate limiting based on system load."""
        start_time = time.time()
        
        try:
            # Update load assessment
            await self._update_system_load()
            
            # Adjust rate limits based on load
            await self._adjust_rate_limits()
            
            # Use base rate limiting middleware
            response = await self.base_middleware.dispatch(request, call_next)
            
            # Track response time
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            self.total_requests += 1
            
            # Track errors
            if response.status_code >= 500:
                self.error_count += 1
            
            # Add adaptive rate limiting header
            response.headers["X-RateLimit-Load"] = self.current_load
            
            return response
            
        except Exception as e:
            logger.error(f"Adaptive rate limiting error: {e}")
            return await call_next(request)
    
    async def _update_system_load(self):
        """Update system load assessment."""
        now = time.time()
        
        if now - self.last_load_check < self.load_check_interval:
            return
        
        # Calculate metrics
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        error_rate = self.error_count / max(self.total_requests, 1)
        
        # Determine load level
        if avg_response_time > 2.0 or error_rate > 0.1:
            self.current_load = "critical"
        elif avg_response_time > 1.0 or error_rate > 0.05:
            self.current_load = "high"
        elif avg_response_time > 0.5 or error_rate > 0.02:
            self.current_load = "medium"
        else:
            self.current_load = "low"
        
        # Reset counters
        self.error_count = 0
        self.total_requests = 0
        self.last_load_check = now
        
        logger.info(f"System load updated: {self.current_load} (avg response: {avg_response_time:.2f}s)")
    
    async def _adjust_rate_limits(self):
        """Adjust rate limits based on current load."""
        multiplier = self.load_multipliers[self.current_load]
        
        # Apply multiplier to base rate limits
        for category, config in self.base_middleware.rate_limits.items():
            adjusted_requests = int(config["requests"] * multiplier)
            config["requests"] = max(1, adjusted_requests)  # Minimum 1 request