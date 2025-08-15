"""FastAPI middleware for correlation tracking and structured logging."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import CorrelationManager, LogContext, api_logger


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID tracking and request logging."""

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation tracking."""
        start_time = time.time()

        # Get or generate correlation ID
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Set correlation context
        CorrelationManager.set_correlation_id(correlation_id)
        CorrelationManager.set_request_id(request_id)

        # Extract user info if available (can be enhanced with auth)
        user_id = request.headers.get("X-User-ID")
        if user_id:
            CorrelationManager.set_user_id(user_id)

        # Create log context
        context = LogContext(
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=user_id,
            operation=f"{request.method} {request.url.path}",
            start_time=start_time,
            metadata={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None,
            }
        )

        # Log request start
        api_logger.info(
            f"Request started: {request.method} {request.url.path}",
            context,
            method=request.method,
            path=str(request.url.path),
            query_params=dict(request.query_params)
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            context.duration_ms = duration_ms

            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            response.headers["X-Request-ID"] = request_id

            # Log successful completion
            api_logger.info(
                f"Request completed: {request.method} {request.url.path}",
                context,
                status_code=response.status_code,
                duration_ms=duration_ms
            )

            return response

        except Exception as error:
            # Calculate duration for error case
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            context.duration_ms = duration_ms

            # Log error
            api_logger.error(
                f"Request failed: {request.method} {request.url.path}",
                context,
                error=error,
                duration_ms=duration_ms
            )

            # Re-raise the exception
            raise


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to track request and response sizes."""

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with size tracking."""

        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            api_logger.warning(
                "Request size exceeds limit",
                LogContext(
                    operation="size_check",
                    metadata={
                        "content_length": int(content_length),
                        "max_size": self.max_request_size,
                        "path": request.url.path
                    }
                )
            )

        # Process request
        response = await call_next(request)

        # Log response size if significant
        response_size = int(response.headers.get("content-length", 0))
        if response_size > 1024 * 1024:  # Log if > 1MB
            api_logger.info(
                "Large response generated",
                LogContext(
                    operation="response_size",
                    metadata={
                        "response_size": response_size,
                        "path": request.url.path,
                        "status_code": response.status_code
                    }
                )
            )

        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track performance metrics."""

    def __init__(self, app, slow_request_threshold: float = 5000.0):  # 5 seconds
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance tracking."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # Log slow requests
        if duration_ms > self.slow_request_threshold:
            api_logger.warning(
                "Slow request detected",
                LogContext(
                    operation="performance_check",
                    duration_ms=duration_ms,
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                        "threshold_ms": self.slow_request_threshold,
                        "status_code": response.status_code
                    }
                )
            )

        return response
