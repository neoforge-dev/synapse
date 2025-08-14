"""Standardized error handling for the Graph RAG API.

Implements RFC 7807 Problem Details for HTTP APIs for consistent error responses.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details model."""
    
    model_config = {"extra": "allow"}  # Allow additional fields
    
    type: str = "about:blank"
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None
    
    # Additional custom fields
    error_code: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class GraphRAGError(Exception):
    """Base exception for Graph RAG specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ValidationError(GraphRAGError):
    """Validation errors (400)."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs)
        if field:
            self.details["field"] = field


class NotFoundError(GraphRAGError):
    """Resource not found errors (404)."""
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        message = f"{resource_type} '{resource_id}' not found"
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, **kwargs)
        self.details.update({"resource_type": resource_type, "resource_id": resource_id})


class ConflictError(GraphRAGError):
    """Resource conflict errors (409)."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, **kwargs)


class ServiceUnavailableError(GraphRAGError):
    """Service unavailable errors (503)."""
    
    def __init__(self, service_name: str, reason: Optional[str] = None, **kwargs):
        message = f"{service_name} is currently unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, **kwargs)
        self.details["service_name"] = service_name
        if reason:
            self.details["reason"] = reason


class InternalServerError(GraphRAGError):
    """Internal server errors (500)."""
    
    def __init__(self, message: str = "An internal server error occurred", **kwargs):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, **kwargs)


def create_problem_detail(
    error: Union[GraphRAGError, HTTPException, Exception],
    request: Optional[Request] = None,
    include_traceback: bool = False
) -> ProblemDetail:
    """Create a standardized problem detail from an exception."""
    from datetime import datetime
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    request_id = getattr(request.state, "request_id", None) if request else None
    instance = str(request.url) if request else None
    
    if isinstance(error, GraphRAGError):
        problem = ProblemDetail(
            title=error.__class__.__name__.replace("Error", ""),
            status=error.status_code,
            detail=error.message,
            error_code=error.error_code,
            timestamp=timestamp,
            request_id=request_id,
            instance=instance
        )
        
        # Add custom details
        for key, value in error.details.items():
            setattr(problem, key, value)
            
    elif isinstance(error, HTTPException):
        problem = ProblemDetail(
            title="HTTP Error",
            status=error.status_code,
            detail=str(error.detail),
            timestamp=timestamp,
            request_id=request_id,
            instance=instance
        )
        
    else:
        # Unexpected exception
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        problem = ProblemDetail(
            title="Internal Server Error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
            timestamp=timestamp,
            request_id=request_id,
            instance=instance
        )
        
        if include_traceback:
            problem.traceback = traceback.format_exc()  # type: ignore
    
    return problem


async def graph_rag_exception_handler(request: Request, exc: GraphRAGError) -> JSONResponse:
    """Exception handler for GraphRAGError exceptions."""
    problem = create_problem_detail(exc, request)
    
    logger.warning(
        f"GraphRAG error: {exc.__class__.__name__}: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None),
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"}
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Exception handler for HTTPException."""
    problem = create_problem_detail(exc, request)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Exception handler for unexpected exceptions."""
    problem = create_problem_detail(exc, request, include_traceback=False)  # Never include traceback in production
    
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "url": str(request.url),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"}
    )


# Convenience functions for common error patterns
def raise_not_found(resource_type: str, resource_id: str, error_code: Optional[str] = None) -> None:
    """Raise a standardized not found error."""
    raise NotFoundError(resource_type, resource_id, error_code=error_code)


def raise_validation_error(message: str, field: Optional[str] = None, error_code: Optional[str] = None) -> None:
    """Raise a standardized validation error."""
    raise ValidationError(message, field=field, error_code=error_code)


def raise_service_unavailable(service_name: str, reason: Optional[str] = None, error_code: Optional[str] = None) -> None:
    """Raise a standardized service unavailable error."""
    raise ServiceUnavailableError(service_name, reason=reason, error_code=error_code)


def raise_internal_error(message: str = "An internal server error occurred", error_code: Optional[str] = None) -> None:
    """Raise a standardized internal server error."""
    raise InternalServerError(message, error_code=error_code)