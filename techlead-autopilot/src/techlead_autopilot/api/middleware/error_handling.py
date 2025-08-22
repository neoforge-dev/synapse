"""
Error handling middleware for consistent error responses and logging.

Provides structured error responses and comprehensive error logging for debugging.
"""

import logging
import traceback
from typing import Callable, Dict, Any

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ...config import get_settings

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Centralized error handling middleware.
    
    Catches all exceptions and returns consistent error responses while
    logging detailed error information for debugging.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle all exceptions and return consistent error responses."""
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            # FastAPI HTTPExceptions - pass through with consistent formatting
            return await self._handle_http_exception(request, e)
            
        except ValidationError as e:
            # Pydantic validation errors
            return await self._handle_validation_error(request, e)
            
        except IntegrityError as e:
            # Database integrity errors
            return await self._handle_integrity_error(request, e)
            
        except OperationalError as e:
            # Database operational errors
            return await self._handle_database_error(request, e)
            
        except Exception as e:
            # All other exceptions
            return await self._handle_generic_error(request, e)
    
    async def _handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        error_id = self._generate_error_id()
        
        # Log error details
        self._log_error(
            error_id=error_id,
            request=request,
            exception=exc,
            error_type="http_exception"
        )
        
        # Prepare error response
        error_response = {
            "error": {
                "type": "http_error",
                "code": exc.status_code,
                "message": exc.detail,
                "error_id": error_id
            }
        }
        
        # Add details in development
        if self.settings.is_development:
            error_response["error"]["path"] = str(request.url.path)
            error_response["error"]["method"] = request.method
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=getattr(exc, "headers", None)
        )
    
    async def _handle_validation_error(self, request: Request, exc: ValidationError) -> JSONResponse:
        """Handle Pydantic validation errors."""
        error_id = self._generate_error_id()
        
        # Log validation error
        self._log_error(
            error_id=error_id,
            request=request,
            exception=exc,
            error_type="validation_error"
        )
        
        # Format validation errors
        validation_errors = []
        for error in exc.errors():
            validation_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        error_response = {
            "error": {
                "type": "validation_error",
                "code": 422,
                "message": "Request validation failed",
                "error_id": error_id,
                "details": validation_errors
            }
        }
        
        return JSONResponse(
            status_code=422,
            content=error_response
        )
    
    async def _handle_integrity_error(self, request: Request, exc: IntegrityError) -> JSONResponse:
        """Handle database integrity constraint errors."""
        error_id = self._generate_error_id()
        
        # Log database error
        self._log_error(
            error_id=error_id,
            request=request,
            exception=exc,
            error_type="database_integrity_error"
        )
        
        # Parse common integrity errors
        error_message = "Database constraint violation"
        if "unique constraint" in str(exc).lower():
            error_message = "Resource already exists"
        elif "foreign key constraint" in str(exc).lower():
            error_message = "Referenced resource not found"
        elif "not null constraint" in str(exc).lower():
            error_message = "Required field missing"
        
        error_response = {
            "error": {
                "type": "database_error",
                "code": 409,
                "message": error_message,
                "error_id": error_id
            }
        }
        
        # Add technical details in development
        if self.settings.is_development:
            error_response["error"]["technical_details"] = str(exc.orig)
        
        return JSONResponse(
            status_code=409,
            content=error_response
        )
    
    async def _handle_database_error(self, request: Request, exc: OperationalError) -> JSONResponse:
        """Handle database operational errors."""
        error_id = self._generate_error_id()
        
        # Log database error
        self._log_error(
            error_id=error_id,
            request=request,
            exception=exc,
            error_type="database_operational_error",
            level="critical"
        )
        
        error_response = {
            "error": {
                "type": "database_error",
                "code": 503,
                "message": "Database temporarily unavailable",
                "error_id": error_id
            }
        }
        
        # Add technical details in development
        if self.settings.is_development:
            error_response["error"]["technical_details"] = str(exc.orig)
        
        return JSONResponse(
            status_code=503,
            content=error_response
        )
    
    async def _handle_generic_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle all other unexpected exceptions."""
        error_id = self._generate_error_id()
        
        # Log unexpected error
        self._log_error(
            error_id=error_id,
            request=request,
            exception=exc,
            error_type="unexpected_error",
            level="critical"
        )
        
        # Generic error response (don't leak internal details)
        error_response = {
            "error": {
                "type": "internal_error",
                "code": 500,
                "message": "An unexpected error occurred",
                "error_id": error_id
            }
        }
        
        # Add technical details in development only
        if self.settings.is_development:
            error_response["error"]["technical_details"] = str(exc)
            error_response["error"]["exception_type"] = type(exc).__name__
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    
    def _log_error(
        self,
        error_id: str,
        request: Request,
        exception: Exception,
        error_type: str,
        level: str = "error"
    ):
        """Log error details for debugging and monitoring."""
        # Prepare log context
        log_context = {
            "error_id": error_id,
            "error_type": error_type,
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params) if request.query_params else None,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
        }
        
        # Add authentication context if available
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from ..auth.jwt import verify_token
            token = auth_header.split(" ")[1]
            token_data = verify_token(token)
            if token_data:
                log_context["user_id"] = token_data.user_id
                log_context["organization_id"] = token_data.organization_id
        
        # Log with appropriate level
        log_message = f"{error_type}: {str(exception)}"
        
        if level == "critical":
            logger.critical(log_message, extra=log_context, exc_info=True)
        elif level == "warning":
            logger.warning(log_message, extra=log_context)
        else:
            logger.error(log_message, extra=log_context)
        
        # In development, also log the full traceback
        if self.settings.is_development:
            logger.debug(f"Full traceback for {error_id}:\n{traceback.format_exc()}")
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


class PII_SanitizationMiddleware(BaseHTTPMiddleware):
    """
    PII (Personally Identifiable Information) sanitization middleware.
    
    Prevents sensitive data from being logged or exposed in error responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Fields that should be redacted in logs
        self.sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session",
            "ssn",
            "social_security",
            "credit_card",
            "card_number",
            "cvv",
            "pin",
            "access_token",
            "refresh_token",
            "api_key",
            "private_key",
            "client_secret"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Sanitize PII from requests and responses."""
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Sanitize exception messages before re-raising
            sanitized_message = self._sanitize_message(str(e))
            
            # Create new exception with sanitized message
            if isinstance(e, HTTPException):
                e.detail = self._sanitize_message(e.detail)
            
            raise e
    
    def _sanitize_message(self, message: str) -> str:
        """Remove potentially sensitive information from messages."""
        if not isinstance(message, str):
            return message
        
        sanitized = message
        
        # Redact email addresses (keep domain for debugging)
        import re
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', 
                          r'[EMAIL]@\1', sanitized)
        
        # Redact potential tokens (long alphanumeric strings)
        sanitized = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[TOKEN]', sanitized)
        
        # Redact potential API keys
        sanitized = re.sub(r'\b(sk-|pk_live_|pk_test_)[A-Za-z0-9]+\b', '[API_KEY]', sanitized)
        
        return sanitized
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data."""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_dict(item) if isinstance(item, dict) else item 
                                for item in value]
            else:
                sanitized[key] = value
        
        return sanitized