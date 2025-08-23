"""Logging middleware for FastAPI applications."""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...infrastructure.logging import get_logger, log_api_request


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""
    
    def __init__(self, app, log_requests: bool = True, log_responses: bool = True):
        """Initialize logging middleware."""
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.logger = get_logger('api.middleware.logging')
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', '')
        
        # Start timing
        start_time = time.time()
        
        # Log incoming request
        if self.log_requests:
            self.logger.info(
                "Incoming request",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                client_ip=client_ip,
                user_agent=user_agent,
                headers=dict(request.headers) if request.headers else {}
            )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Get user ID if available (from JWT or session)
            user_id = getattr(request.state, 'user_id', None)
            
            # Log request completion
            log_api_request(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_id=request_id,
                user_agent=user_agent,
                ip_address=client_ip
            )
            
            # Log response details
            if self.log_responses and response.status_code >= 400:
                self.logger.warning(
                    "Request completed with error",
                    request_id=request_id,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    user_id=user_id
                )
            elif self.log_responses:
                self.logger.info(
                    "Request completed successfully",
                    request_id=request_id,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    user_id=user_id
                )
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            
            return response
            
        except Exception as exc:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            self.logger.error(
                "Request failed with exception",
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True
            )
            
            # Re-raise exception
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP in case of multiple proxies
            return forwarded_for.split(',')[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        if request.client:
            return request.client.host
        
        return 'unknown'


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context to logs."""
    
    def __init__(self, app):
        """Initialize request context middleware."""
        super().__init__(app)
        self.logger = get_logger('api.middleware.context')
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request context to state."""
        # Ensure request ID exists
        if not hasattr(request.state, 'request_id'):
            request.state.request_id = str(uuid.uuid4())
        
        # Add other context information
        request.state.start_time = time.time()
        request.state.client_ip = self._get_client_ip(request)
        request.state.user_agent = request.headers.get('user-agent', '')
        
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            self.logger.error(
                "Unhandled exception in request",
                request_id=request.state.request_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Same logic as LoggingMiddleware
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return 'unknown'


class HealthCheckLoggingFilter:
    """Filter to reduce noise from health check requests."""
    
    def __init__(self, health_check_paths: Optional[list] = None):
        """Initialize health check filter."""
        self.health_check_paths = health_check_paths or ['/health', '/health/', '/ping', '/ping/']
    
    def should_log_request(self, request: Request) -> bool:
        """Determine if request should be logged."""
        path = request.url.path.lower()
        
        # Skip health check paths
        if path in self.health_check_paths:
            return False
        
        # Skip static files (if serving through FastAPI)
        if path.startswith('/static/') or path.startswith('/assets/'):
            return False
        
        return True


class ConditionalLoggingMiddleware(LoggingMiddleware):
    """Logging middleware with conditional filtering."""
    
    def __init__(self, app, health_check_filter: Optional[HealthCheckLoggingFilter] = None, **kwargs):
        """Initialize conditional logging middleware."""
        super().__init__(app, **kwargs)
        self.filter = health_check_filter or HealthCheckLoggingFilter()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with conditional logging."""
        # Check if we should log this request
        should_log = self.filter.should_log_request(request)
        
        if not should_log:
            # Just process the request without detailed logging
            try:
                return await call_next(request)
            except Exception:
                # Still log errors even for filtered requests
                self.logger.error(
                    "Error in filtered request",
                    method=request.method,
                    path=str(request.url.path),
                    exc_info=True
                )
                raise
        
        # Full logging for non-filtered requests
        return await super().dispatch(request, call_next)