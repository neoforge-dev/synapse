"""Integrated security middleware combining rate limiting and DDoS protection."""

import logging
import time
from typing import Dict, Any, Optional, Callable
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .rate_limiter import AdvancedRateLimiter, LimitType, SubscriptionTier
from .ddos_protection import DDoSProtectionMiddleware, RequestAnalyzer

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware integrating rate limiting and DDoS protection.
    
    Provides layered security with:
    - Multi-tier rate limiting (IP, User, Endpoint)
    - DDoS protection and request analysis
    - Graceful error responses with proper headers
    - Health check bypass for monitoring
    - Admin bypass for emergency access
    """
    
    # Endpoints that bypass security checks
    BYPASS_ENDPOINTS = {
        '/health',
        '/ready', 
        '/live',
        '/metrics',
        '/api/v1/health',
    }
    
    # Admin endpoints with special handling
    ADMIN_ENDPOINTS = {
        '/api/v1/admin',
        '/api/v1/debug',
    }

    def __init__(
        self, 
        app, 
        redis_client: redis.Redis,
        enable_rate_limiting: bool = True,
        enable_ddos_protection: bool = True,
        bypass_admin_ips: Optional[list] = None
    ):
        """Initialize comprehensive security middleware.
        
        Args:
            app: FastAPI application
            redis_client: Async Redis client
            enable_rate_limiting: Whether to enable rate limiting
            enable_ddos_protection: Whether to enable DDoS protection
            bypass_admin_ips: List of admin IP addresses to bypass restrictions
        """
        super().__init__(app)
        
        self.rate_limiter = AdvancedRateLimiter(redis_client) if enable_rate_limiting else None
        self.request_analyzer = RequestAnalyzer(redis_client) if enable_ddos_protection else None
        self.bypass_admin_ips = set(bypass_admin_ips or [])
        
        # Statistics tracking
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'rate_limited_requests': 0,
            'ddos_blocked_requests': 0,
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through comprehensive security checks.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response (potentially blocked)
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        try:
            # Extract client information
            client_ip = self._get_client_ip(request)
            endpoint = request.url.path
            method = request.method
            
            # 1. Check bypass conditions
            if self._should_bypass_security(endpoint, client_ip):
                return await call_next(request)
            
            # 2. DDoS Protection Check (if enabled)
            if self.request_analyzer:
                ddos_response = await self._check_ddos_protection(request, client_ip)
                if ddos_response:
                    self.stats['ddos_blocked_requests'] += 1
                    self.stats['blocked_requests'] += 1
                    return ddos_response
            
            # 3. Rate Limiting Check (if enabled) 
            if self.rate_limiter:
                rate_limit_response = await self._check_rate_limits(
                    request, client_ip, endpoint, method
                )
                if rate_limit_response:
                    self.stats['rate_limited_requests'] += 1
                    self.stats['blocked_requests'] += 1
                    return rate_limit_response
            
            # 4. Process request normally
            response = await call_next(request)
            
            # 5. Add security headers
            self._add_security_headers(response, client_ip, start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            # Fail open - process request normally if security checks fail
            return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxies and load balancers.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Client IP address
        """
        # Priority order for IP detection
        headers_to_check = [
            'X-Forwarded-For',
            'X-Real-IP', 
            'X-Client-IP',
            'CF-Connecting-IP',  # Cloudflare
            'X-Forwarded',
            'Forwarded-For',
            'Forwarded'
        ]
        
        for header in headers_to_check:
            value = request.headers.get(header)
            if value:
                # Handle comma-separated IPs (take first one)
                ip = value.split(',')[0].strip()
                if ip and ip != 'unknown':
                    return ip
        
        # Fall back to direct connection
        return getattr(request.client, 'host', 'unknown')
    
    def _should_bypass_security(self, endpoint: str, client_ip: str) -> bool:
        """Check if request should bypass security checks.
        
        Args:
            endpoint: Request endpoint path
            client_ip: Client IP address
            
        Returns:
            Whether to bypass security checks
        """
        # Health checks and monitoring endpoints
        if endpoint in self.BYPASS_ENDPOINTS:
            return True
            
        # Admin IP allowlist
        if client_ip in self.bypass_admin_ips:
            logger.info(f"Admin IP bypassing security: {client_ip}")
            return True
            
        return False
    
    async def _check_ddos_protection(self, request: Request, client_ip: str) -> Optional[Response]:
        """Check DDoS protection and request analysis.
        
        Args:
            request: HTTP request
            client_ip: Client IP address
            
        Returns:
            Block response if request should be blocked, None otherwise
        """
        try:
            # Check if IP is already blocked
            if await self.request_analyzer.is_ip_blocked(client_ip):
                return self._create_blocked_response(
                    "IP_BLOCKED",
                    "Your IP address has been temporarily blocked due to suspicious activity",
                    retry_after=300
                )
            
            # Analyze request for suspicious patterns
            suspicious_pattern = await self.request_analyzer.analyze_request(request)
            
            if suspicious_pattern:
                if suspicious_pattern.severity >= 8:
                    # Block high-severity threats immediately
                    await self.request_analyzer.block_ip(
                        client_ip,
                        duration=900,  # 15 minutes
                        reason=suspicious_pattern.description
                    )
                    
                    return self._create_blocked_response(
                        "SUSPICIOUS_ACTIVITY",
                        f"Request blocked: {suspicious_pattern.description}",
                        retry_after=900
                    )
                elif suspicious_pattern.severity >= 6:
                    # Log medium-severity patterns
                    logger.warning(
                        f"Suspicious activity detected from {client_ip}: "
                        f"{suspicious_pattern.description} (severity: {suspicious_pattern.severity})"
                    )
                    
        except Exception as e:
            logger.error(f"DDoS protection check failed: {e}")
            
        return None
    
    async def _check_rate_limits(
        self, 
        request: Request, 
        client_ip: str, 
        endpoint: str, 
        method: str
    ) -> Optional[Response]:
        """Check various rate limiting tiers.
        
        Args:
            request: HTTP request
            client_ip: Client IP address
            endpoint: Request endpoint
            method: HTTP method
            
        Returns:
            Rate limit response if blocked, None otherwise
        """
        try:
            # 1. IP-based rate limiting (most restrictive for anonymous users)
            ip_limit = self.rate_limiter.ANONYMOUS_LIMITS.get('requests_per_minute', 60)
            ip_result = await self.rate_limiter.is_allowed(
                identifier=client_ip,
                limit_type=LimitType.IP,
                max_requests=ip_limit,
                window_size=60,
                endpoint=endpoint
            )
            
            if not ip_result.is_allowed:
                return self._create_rate_limit_response(ip_result, "IP_RATE_LIMIT")
            
            # 2. User-based rate limiting (if authenticated)
            user = await self._get_authenticated_user(request)
            if user:
                user_tier = self._get_user_tier(user)
                user_limits = self.rate_limiter.USER_LIMITS.get(user_tier, {})
                user_limit = user_limits.get('api_requests', 1000)
                
                user_result = await self.rate_limiter.is_allowed(
                    identifier=str(user.get('id', user.get('email'))),
                    limit_type=LimitType.USER,
                    max_requests=user_limit,
                    window_size=3600,  # 1 hour
                    endpoint=endpoint,
                    user_tier=user_tier
                )
                
                if not user_result.is_allowed:
                    return self._create_rate_limit_response(user_result, "USER_RATE_LIMIT")
            
            # 3. Endpoint-specific rate limiting
            if endpoint in self.rate_limiter.ENDPOINT_LIMITS:
                endpoint_config = self.rate_limiter.ENDPOINT_LIMITS[endpoint]
                endpoint_identifier = f"{client_ip}:{endpoint}"
                
                endpoint_result = await self.rate_limiter.is_allowed(
                    identifier=endpoint_identifier,
                    limit_type=LimitType.ENDPOINT,
                    max_requests=endpoint_config['rate'],
                    window_size=endpoint_config['period'],
                    endpoint=endpoint
                )
                
                if not endpoint_result.is_allowed:
                    return self._create_rate_limit_response(endpoint_result, "ENDPOINT_RATE_LIMIT")
                    
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            
        return None
    
    async def _get_authenticated_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract authenticated user from request (if available).
        
        Args:
            request: HTTP request
            
        Returns:
            User dictionary if authenticated, None otherwise
        """
        try:
            # Try to get user from request state (set by auth middleware)
            return getattr(request.state, 'user', None)
            
        except Exception as e:
            logger.debug(f"Could not extract user from request: {e}")
            return None
    
    def _get_user_tier(self, user: Dict[str, Any]) -> SubscriptionTier:
        """Determine user's subscription tier.
        
        Args:
            user: User dictionary
            
        Returns:
            User's subscription tier
        """
        tier = user.get('subscription_tier', 'free')
        
        tier_mapping = {
            'free': SubscriptionTier.FREE,
            'pro': SubscriptionTier.PRO,
            'enterprise': SubscriptionTier.ENTERPRISE
        }
        
        return tier_mapping.get(tier, SubscriptionTier.FREE)
    
    def _create_rate_limit_response(self, rate_result, error_code: str) -> JSONResponse:
        """Create standardized rate limit response.
        
        Args:
            rate_result: Rate limit check result
            error_code: Specific error code
            
        Returns:
            JSON response with rate limit information
        """
        headers = {
            'X-RateLimit-Remaining': str(rate_result.remaining),
            'X-RateLimit-Reset': str(rate_result.reset_time),
        }
        
        if rate_result.retry_after:
            headers['Retry-After'] = str(rate_result.retry_after)
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate Limit Exceeded",
                "message": f"Too many requests. Limit type: {rate_result.limit_type}",
                "error_code": error_code,
                "details": {
                    "remaining": rate_result.remaining,
                    "reset_time": rate_result.reset_time,
                    "limit_type": rate_result.limit_type,
                },
                "retry_after": rate_result.retry_after
            },
            headers=headers
        )
    
    def _create_blocked_response(
        self, 
        error_code: str, 
        message: str, 
        retry_after: int = 300
    ) -> JSONResponse:
        """Create standardized blocked response.
        
        Args:
            error_code: Specific error code
            message: Human-readable message
            retry_after: Seconds to wait before retrying
            
        Returns:
            JSON response indicating blocked request
        """
        return JSONResponse(
            status_code=429,
            content={
                "error": "Request Blocked",
                "message": message,
                "error_code": error_code,
                "retry_after": retry_after
            },
            headers={
                'Retry-After': str(retry_after),
                'X-Security-Block': 'true'
            }
        )
    
    def _add_security_headers(self, response: Response, client_ip: str, start_time: float) -> None:
        """Add security and performance headers to response.
        
        Args:
            response: HTTP response
            client_ip: Client IP address  
            start_time: Request start timestamp
        """
        # Security headers
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        })
        
        # Performance and debugging headers
        process_time = time.time() - start_time
        response.headers.update({
            'X-Process-Time': f"{process_time:.3f}",
            'X-Client-IP': client_ip,
        })
    
    async def get_security_stats(self) -> Dict[str, Any]:
        """Get comprehensive security statistics.
        
        Returns:
            Dictionary with security metrics and statistics
        """
        stats = dict(self.stats)
        
        try:
            # Add rate limiter stats
            if self.rate_limiter:
                rate_limit_stats = await self.rate_limiter.get_global_stats()
                stats.update({f"rate_limiter_{k}": v for k, v in rate_limit_stats.items()})
            
            # Calculate percentages
            total = stats['total_requests']
            if total > 0:
                stats['block_rate_percentage'] = (stats['blocked_requests'] / total) * 100
                stats['rate_limit_percentage'] = (stats['rate_limited_requests'] / total) * 100
                stats['ddos_block_percentage'] = (stats['ddos_blocked_requests'] / total) * 100
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get security stats: {e}")
            return stats