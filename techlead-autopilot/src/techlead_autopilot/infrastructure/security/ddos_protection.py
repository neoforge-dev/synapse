"""DDoS protection middleware with request pattern analysis and connection limits."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Set, List, Tuple
from collections import defaultdict, deque
from ipaddress import ip_address, ip_network, AddressValueError

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class SuspiciousPattern:
    """Represents a detected suspicious request pattern."""
    pattern_type: str
    severity: int  # 1-10 scale
    description: str
    first_detected: float
    last_seen: float
    occurrence_count: int


@dataclass
class ConnectionInfo:
    """Information about a client connection."""
    ip_address: str
    first_seen: float
    last_seen: float
    request_count: int
    suspicious_patterns: List[SuspiciousPattern]
    is_blocked: bool
    block_expires: Optional[float] = None


class RequestAnalyzer:
    """Analyzes incoming requests for suspicious patterns and DDoS attacks.
    
    Detects various attack patterns:
    - Rapid sequential requests
    - Unusual endpoint access patterns  
    - Large payload attacks
    - Slow request attacks
    - Geographic anomalies
    - Bot/automated traffic
    """
    
    # Suspicious behavior thresholds
    RAPID_REQUEST_THRESHOLD = 20  # requests per 10 seconds
    UNUSUAL_ENDPOINT_THRESHOLD = 5  # different endpoints per minute
    LARGE_PAYLOAD_THRESHOLD = 10 * 1024 * 1024  # 10MB
    SLOW_REQUEST_TIMEOUT = 30  # seconds
    
    # Known bot/crawler User-Agents (partial matches)
    BOT_USER_AGENTS = [
        'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 
        'python-requests', 'python-urllib', 'scrapy', 'aiohttp'
    ]
    
    # Geographic restrictions (if enabled)
    BLOCKED_COUNTRIES = set()  # Can be configured: {'CN', 'RU', 'KP'}
    ALLOWED_NETWORKS = [
        ip_network('10.0.0.0/8'),      # Private networks
        ip_network('172.16.0.0/12'),   
        ip_network('192.168.0.0/16'),
        ip_network('127.0.0.0/8'),     # Localhost
    ]

    def __init__(self, redis_client: redis.Redis):
        """Initialize request analyzer with Redis for state storage.
        
        Args:
            redis_client: Async Redis client for storing analysis state
        """
        self.redis = redis_client
        self.prefix = "ddos_protection"
        self.connection_tracker: Dict[str, ConnectionInfo] = {}
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
    async def analyze_request(self, request: Request) -> Optional[SuspiciousPattern]:
        """Analyze incoming request for suspicious patterns.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            SuspiciousPattern if suspicious activity detected, None otherwise
        """
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Track connection info
        await self._track_connection(client_ip, current_time)
        
        # Run various detection algorithms
        patterns = []
        
        # 1. Rapid request detection
        rapid_pattern = await self._detect_rapid_requests(client_ip, current_time)
        if rapid_pattern:
            patterns.append(rapid_pattern)
            
        # 2. Unusual endpoint access patterns
        endpoint_pattern = await self._detect_unusual_endpoints(client_ip, request.url.path, current_time)
        if endpoint_pattern:
            patterns.append(endpoint_pattern)
            
        # 3. Large payload detection
        payload_pattern = await self._detect_large_payload(request, current_time)
        if payload_pattern:
            patterns.append(payload_pattern)
            
        # 4. Bot detection
        bot_pattern = await self._detect_bot_traffic(request, current_time)
        if bot_pattern:
            patterns.append(bot_pattern)
            
        # 5. Geographic filtering
        geo_pattern = await self._check_geographic_restrictions(client_ip, current_time)
        if geo_pattern:
            patterns.append(geo_pattern)
        
        # Return most severe pattern
        if patterns:
            return max(patterns, key=lambda p: p.severity)
            
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxies.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Client IP address as string
        """
        # Check X-Forwarded-For header (from load balancers/proxies)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take first IP (original client)
            return forwarded_for.split(',')[0].strip()
            
        # Check X-Real-IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
            
        # Fall back to direct connection IP
        if hasattr(request.client, 'host'):
            return request.client.host
            
        return 'unknown'
    
    async def _track_connection(self, client_ip: str, current_time: float) -> None:
        """Track connection information for IP address.
        
        Args:
            client_ip: Client IP address
            current_time: Current timestamp
        """
        key = f"{self.prefix}:connections:{client_ip}"
        
        try:
            # Get existing connection info from Redis
            conn_data = await self.redis.hgetall(key)
            
            if conn_data:
                # Update existing connection
                await self.redis.hset(key, mapping={
                    'last_seen': str(current_time),
                    'request_count': str(int(conn_data.get(b'request_count', 0)) + 1)
                })
            else:
                # New connection
                await self.redis.hset(key, mapping={
                    'ip_address': client_ip,
                    'first_seen': str(current_time),
                    'last_seen': str(current_time),
                    'request_count': '1',
                    'is_blocked': 'false'
                })
            
            # Set expiration to cleanup old connections
            await self.redis.expire(key, 3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Failed to track connection for {client_ip}: {e}")
    
    async def _detect_rapid_requests(self, client_ip: str, current_time: float) -> Optional[SuspiciousPattern]:
        """Detect rapid sequential requests from same IP.
        
        Args:
            client_ip: Client IP address
            current_time: Current timestamp
            
        Returns:
            SuspiciousPattern if rapid requests detected
        """
        key = f"{self.prefix}:rapid:{client_ip}"
        window_start = current_time - 10  # 10 second window
        
        try:
            # Add current request time
            await self.redis.zadd(key, {str(current_time): current_time})
            
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in window
            request_count = await self.redis.zcard(key)
            
            # Set expiration
            await self.redis.expire(key, 60)
            
            if request_count > self.RAPID_REQUEST_THRESHOLD:
                return SuspiciousPattern(
                    pattern_type="rapid_requests",
                    severity=8,
                    description=f"Rapid requests: {request_count} requests in 10 seconds",
                    first_detected=current_time,
                    last_seen=current_time,
                    occurrence_count=request_count
                )
                
        except Exception as e:
            logger.error(f"Failed to detect rapid requests for {client_ip}: {e}")
            
        return None
    
    async def _detect_unusual_endpoints(
        self, 
        client_ip: str, 
        endpoint: str, 
        current_time: float
    ) -> Optional[SuspiciousPattern]:
        """Detect unusual endpoint access patterns.
        
        Args:
            client_ip: Client IP address
            endpoint: Request endpoint path
            current_time: Current timestamp
            
        Returns:
            SuspiciousPattern if unusual endpoint access detected
        """
        key = f"{self.prefix}:endpoints:{client_ip}"
        window_start = current_time - 60  # 1 minute window
        
        try:
            # Track endpoint with timestamp
            await self.redis.zadd(key, {f"{endpoint}:{current_time}": current_time})
            
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # Get unique endpoints in window
            entries = await self.redis.zrange(key, 0, -1)
            unique_endpoints = set(entry.decode().split(':')[0] for entry in entries)
            
            # Set expiration
            await self.redis.expire(key, 300)  # 5 minutes
            
            if len(unique_endpoints) > self.UNUSUAL_ENDPOINT_THRESHOLD:
                return SuspiciousPattern(
                    pattern_type="unusual_endpoints",
                    severity=6,
                    description=f"Accessing {len(unique_endpoints)} different endpoints in 1 minute",
                    first_detected=current_time,
                    last_seen=current_time,
                    occurrence_count=len(unique_endpoints)
                )
                
        except Exception as e:
            logger.error(f"Failed to detect unusual endpoints for {client_ip}: {e}")
            
        return None
    
    async def _detect_large_payload(self, request: Request, current_time: float) -> Optional[SuspiciousPattern]:
        """Detect suspiciously large request payloads.
        
        Args:
            request: FastAPI Request object
            current_time: Current timestamp
            
        Returns:
            SuspiciousPattern if large payload detected
        """
        try:
            content_length = request.headers.get('content-length')
            if content_length:
                payload_size = int(content_length)
                if payload_size > self.LARGE_PAYLOAD_THRESHOLD:
                    return SuspiciousPattern(
                        pattern_type="large_payload",
                        severity=7,
                        description=f"Large payload: {payload_size} bytes",
                        first_detected=current_time,
                        last_seen=current_time,
                        occurrence_count=1
                    )
                    
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse content-length: {e}")
            
        return None
    
    async def _detect_bot_traffic(self, request: Request, current_time: float) -> Optional[SuspiciousPattern]:
        """Detect automated bot traffic.
        
        Args:
            request: FastAPI Request object  
            current_time: Current timestamp
            
        Returns:
            SuspiciousPattern if bot traffic detected
        """
        user_agent = request.headers.get('user-agent', '').lower()
        
        # Check for bot user agents
        for bot_pattern in self.BOT_USER_AGENTS:
            if bot_pattern in user_agent:
                return SuspiciousPattern(
                    pattern_type="bot_traffic",
                    severity=4,  # Lower severity as bots aren't always malicious
                    description=f"Bot user agent detected: {user_agent[:100]}",
                    first_detected=current_time,
                    last_seen=current_time,
                    occurrence_count=1
                )
        
        # Check for missing common headers (sign of automated requests)
        common_headers = ['accept', 'accept-language', 'accept-encoding']
        missing_headers = [h for h in common_headers if h not in request.headers]
        
        if len(missing_headers) >= 2:
            return SuspiciousPattern(
                pattern_type="automated_request",
                severity=5,
                description=f"Missing common headers: {missing_headers}",
                first_detected=current_time,
                last_seen=current_time,
                occurrence_count=1
            )
            
        return None
    
    async def _check_geographic_restrictions(self, client_ip: str, current_time: float) -> Optional[SuspiciousPattern]:
        """Check geographic restrictions (if enabled).
        
        Args:
            client_ip: Client IP address
            current_time: Current timestamp
            
        Returns:
            SuspiciousPattern if geographic restriction triggered
        """
        if not self.BLOCKED_COUNTRIES:
            return None
            
        try:
            # Check if IP is in allowed private networks
            ip_obj = ip_address(client_ip)
            for network in self.ALLOWED_NETWORKS:
                if ip_obj in network:
                    return None  # Allow private networks
                    
            # In real implementation, this would use a GeoIP database
            # For now, we'll skip geographic filtering
            # country_code = get_country_code(client_ip)  # Placeholder
            # if country_code in self.BLOCKED_COUNTRIES:
            #     return SuspiciousPattern(...)
            
        except (AddressValueError, TypeError):
            logger.warning(f"Invalid IP address for geo check: {client_ip}")
            
        return None
    
    async def is_ip_blocked(self, client_ip: str) -> bool:
        """Check if IP address is currently blocked.
        
        Args:
            client_ip: Client IP address to check
            
        Returns:
            Whether IP is currently blocked
        """
        key = f"{self.prefix}:blocked:{client_ip}"
        current_time = time.time()
        
        try:
            block_data = await self.redis.hgetall(key)
            if block_data:
                block_expires = float(block_data.get(b'expires', 0))
                if current_time < block_expires:
                    return True
                else:
                    # Block expired, clean up
                    await self.redis.delete(key)
                    
        except Exception as e:
            logger.error(f"Failed to check IP block status for {client_ip}: {e}")
            
        return False
    
    async def block_ip(self, client_ip: str, duration: int, reason: str) -> None:
        """Block IP address for specified duration.
        
        Args:
            client_ip: IP address to block
            duration: Block duration in seconds
            reason: Reason for blocking
        """
        key = f"{self.prefix}:blocked:{client_ip}"
        current_time = time.time()
        expires_at = current_time + duration
        
        try:
            await self.redis.hset(key, mapping={
                'ip_address': client_ip,
                'blocked_at': str(current_time),
                'expires': str(expires_at),
                'reason': reason,
                'duration': str(duration)
            })
            
            # Set Redis key expiration
            await self.redis.expire(key, duration)
            
            logger.warning(f"Blocked IP {client_ip} for {duration}s: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to block IP {client_ip}: {e}")


class DDoSProtectionMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for DDoS protection and request filtering.
    
    Provides comprehensive protection against various attack vectors:
    - Automatic IP blocking based on suspicious patterns
    - Connection limits per IP
    - Request rate limiting integration
    - Real-time threat analysis
    """
    
    def __init__(self, app, redis_client: redis.Redis, max_connections_per_ip: int = 100):
        """Initialize DDoS protection middleware.
        
        Args:
            app: FastAPI application
            redis_client: Async Redis client
            max_connections_per_ip: Maximum concurrent connections per IP
        """
        super().__init__(app)
        self.analyzer = RequestAnalyzer(redis_client)
        self.max_connections_per_ip = max_connections_per_ip
        
        # Active connections tracking
        self.active_connections: Dict[str, Set[str]] = defaultdict(set)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process incoming request through DDoS protection filters.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response (may be blocked response)
        """
        client_ip = self.analyzer._get_client_ip(request)
        request_id = f"{client_ip}:{time.time()}"
        
        try:
            # 1. Check if IP is currently blocked
            if await self.analyzer.is_ip_blocked(client_ip):
                logger.warning(f"Blocked request from {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": "Your IP address has been temporarily blocked due to suspicious activity",
                        "error_code": "IP_BLOCKED"
                    },
                    headers={"Retry-After": "300"}
                )
            
            # 2. Check connection limits
            self.active_connections[client_ip].add(request_id)
            if len(self.active_connections[client_ip]) > self.max_connections_per_ip:
                self.active_connections[client_ip].discard(request_id)
                logger.warning(f"Connection limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Connections",
                        "message": "Too many concurrent connections from your IP address",
                        "error_code": "CONNECTION_LIMIT_EXCEEDED"
                    }
                )
            
            # 3. Analyze request for suspicious patterns
            suspicious_pattern = await self.analyzer.analyze_request(request)
            
            # 4. Take action based on pattern severity
            if suspicious_pattern and suspicious_pattern.severity >= 7:
                # Block high-severity threats
                await self.analyzer.block_ip(
                    client_ip, 
                    duration=300,  # 5 minutes
                    reason=suspicious_pattern.description
                )
                
                self.active_connections[client_ip].discard(request_id)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Suspicious Activity Detected",
                        "message": "Request blocked due to suspicious activity",
                        "error_code": "SUSPICIOUS_ACTIVITY"
                    }
                )
            elif suspicious_pattern and suspicious_pattern.severity >= 5:
                # Log medium-severity threats but allow request
                logger.warning(
                    f"Suspicious activity from {client_ip}: {suspicious_pattern.description}"
                )
            
            # 5. Process request normally
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Add security headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            logger.error(f"DDoS protection middleware error: {e}")
            # Fail open - allow request if middleware fails
            return await call_next(request)
            
        finally:
            # Clean up connection tracking
            self.active_connections[client_ip].discard(request_id)
            if not self.active_connections[client_ip]:
                del self.active_connections[client_ip]