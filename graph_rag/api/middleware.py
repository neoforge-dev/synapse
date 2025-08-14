"""Middleware for request processing, monitoring, and error handling."""

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request ID generation, timing, and structured logging."""

    def __init__(self, app, enable_metrics: bool = False):
        super().__init__(app)
        self.enable_metrics = enable_metrics

        # Import metrics components if enabled
        if enable_metrics:
            try:
                from graph_rag.api.metrics import (
                    inc_ask_total,
                    inc_ingest_total,
                    observe_query_latency,
                )
                self.inc_ask_total = inc_ask_total
                self.inc_ingest_total = inc_ingest_total
                self.observe_query_latency = observe_query_latency
            except ImportError:
                logger.warning("Metrics enabled but metric functions not available")
                self.enable_metrics = False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Log request start
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": request.client.host if request.client else None
            }
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time": process_time,
                }
            )

            # Record metrics if enabled
            if self.enable_metrics:
                self._record_metrics(request, response, process_time)

            return response

        except Exception as exc:
            process_time = time.time() - start_time

            # Log request error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "process_time": process_time,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__
                },
                exc_info=True
            )

            # Re-raise to be handled by exception handlers
            raise

    def _record_metrics(self, request: Request, response: Response, process_time: float):
        """Record business metrics for specific endpoints."""
        try:
            path = request.url.path

            # Query/Ask metrics
            if path.endswith("/api/v1/query/ask") or path.endswith("/api/v1/query/ask/stream"):
                self.inc_ask_total()
                self.observe_query_latency(process_time)

            # Ingestion metrics
            elif path.endswith("/api/v1/ingestion/documents") and response.status_code == 202:
                self.inc_ingest_total()

        except Exception as e:
            logger.debug(f"Failed to record metrics: {e}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add API-specific headers
        response.headers["X-API-Version"] = "1.0.0"
        response.headers["X-Powered-By"] = "Synapse GraphRAG"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware (in-memory, not production-ready for distributed systems)."""

    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_cache = {}  # In production, use Redis or similar

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries (simple cleanup)
        self._cleanup_cache(current_time)

        # Get or create client record
        if client_ip not in self.requests_cache:
            self.requests_cache[client_ip] = {
                "requests": [],
                "blocked_until": 0
            }

        client_record = self.requests_cache[client_ip]

        # Check if client is temporarily blocked
        if current_time < client_record["blocked_until"]:
            from graph_rag.api.errors import GraphRAGError
            raise GraphRAGError(
                "Rate limit exceeded. Please try again later.",
                error_code="RATE_LIMIT_EXCEEDED",
                status_code=429
            )

        # Add current request timestamp
        client_record["requests"].append(current_time)

        # Check rate limits
        minute_ago = current_time - 60
        hour_ago = current_time - 3600

        recent_requests = [ts for ts in client_record["requests"] if ts > minute_ago]
        hourly_requests = [ts for ts in client_record["requests"] if ts > hour_ago]

        if len(recent_requests) > self.requests_per_minute:
            client_record["blocked_until"] = current_time + 60  # Block for 1 minute
            from graph_rag.api.errors import GraphRAGError
            raise GraphRAGError(
                f"Rate limit exceeded: {len(recent_requests)} requests in the last minute (limit: {self.requests_per_minute})",
                error_code="RATE_LIMIT_MINUTE_EXCEEDED",
                status_code=429
            )

        if len(hourly_requests) > self.requests_per_hour:
            client_record["blocked_until"] = current_time + 3600  # Block for 1 hour
            from graph_rag.api.errors import GraphRAGError
            raise GraphRAGError(
                f"Rate limit exceeded: {len(hourly_requests)} requests in the last hour (limit: {self.requests_per_hour})",
                error_code="RATE_LIMIT_HOUR_EXCEEDED",
                status_code=429
            )

        # Update client record with cleaned requests
        client_record["requests"] = hourly_requests

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, self.requests_per_minute - len(recent_requests)))
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, self.requests_per_hour - len(hourly_requests)))

        return response

    def _cleanup_cache(self, current_time: float):
        """Remove old entries from cache to prevent memory leaks."""
        cutoff_time = current_time - 3600  # Keep 1 hour of history

        for client_ip, record in list(self.requests_cache.items()):
            # Clean old requests
            record["requests"] = [ts for ts in record["requests"] if ts > cutoff_time]

            # Remove empty records
            if not record["requests"] and record["blocked_until"] < current_time:
                del self.requests_cache[client_ip]
