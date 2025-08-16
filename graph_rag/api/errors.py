"""Standardized error handling for the Graph RAG API.

Implements RFC 7807 Problem Details for HTTP APIs for consistent error responses.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional

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
    detail: str | None = None
    instance: str | None = None

    # Additional custom fields
    error_code: str | None = None
    timestamp: str | None = None
    request_id: str | None = None


class GraphRAGError(Exception):
    """Base exception for Graph RAG specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ValidationError(GraphRAGError):
    """Validation errors (400)."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
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

    def __init__(self, service_name: str, reason: str | None = None, recovery_suggestions: list[str] | None = None, **kwargs):
        message = f"{service_name} is currently unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, **kwargs)
        self.details["service_name"] = service_name
        if reason:
            self.details["reason"] = reason
        if recovery_suggestions:
            self.details["recovery_suggestions"] = recovery_suggestions


class InternalServerError(GraphRAGError):
    """Internal server errors (500)."""

    def __init__(self, message: str = "An internal server error occurred", **kwargs):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, **kwargs)


def create_problem_detail(
    error: GraphRAGError | HTTPException | Exception,
    request: Request | None = None,
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
        media_type="application/problem+json",
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Exception handler for HTTPException."""
    problem = create_problem_detail(exc, request)

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
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
        media_type="application/problem+json",
    )


# Convenience functions for common error patterns
def raise_not_found(resource_type: str, resource_id: str, error_code: str | None = None) -> None:
    """Raise a standardized not found error."""
    raise NotFoundError(resource_type, resource_id, error_code=error_code)


def raise_validation_error(message: str, field: str | None = None, error_code: str | None = None) -> None:
    """Raise a standardized validation error."""
    raise ValidationError(message, field=field, error_code=error_code)


def raise_service_unavailable(service_name: str, reason: str | None = None, error_code: str | None = None) -> None:
    """Raise a standardized service unavailable error."""
    raise ServiceUnavailableError(service_name, reason=reason, error_code=error_code)


def raise_internal_error(message: str = "An internal server error occurred", error_code: str | None = None) -> None:
    """Raise a standardized internal server error."""
    raise InternalServerError(message, error_code=error_code)


# Extended error classes for specific Graph-RAG scenarios
class MemgraphConnectionError(ServiceUnavailableError):
    """Memgraph database connection errors."""
    
    def __init__(self, reason: str | None = None, **kwargs):
        recovery_suggestions = [
            "Check if Memgraph is running: 'docker ps' or 'make run-memgraph'",
            "Verify connection settings: SYNAPSE_MEMGRAPH_HOST and SYNAPSE_MEMGRAPH_PORT",
            "Try using fallback search: 'synapse search --vector-only <query>'",
            "Check system health: 'synapse admin health'"
        ]
        super().__init__(
            "Knowledge graph database", 
            reason=reason or "Connection failed",
            recovery_suggestions=recovery_suggestions,
            error_code="MEMGRAPH_CONNECTION_FAILED",
            **kwargs
        )


class VectorStoreError(ServiceUnavailableError):
    """Vector store operation errors."""
    
    def __init__(self, operation: str, reason: str | None = None, **kwargs):
        recovery_suggestions = [
            "Try rebuilding vector index: 'synapse admin rebuild-vectors'",
            "Use graph-only search: 'synapse search --graph-only <query>'",
            "Check available disk space and memory",
            "Verify vector store configuration: SYNAPSE_VECTOR_STORE_TYPE"
        ]
        super().__init__(
            "Vector store",
            reason=f"Failed to {operation}: {reason}" if reason else f"Failed to {operation}",
            recovery_suggestions=recovery_suggestions,
            error_code="VECTOR_STORE_ERROR",
            **kwargs
        )


class EmbeddingServiceError(ServiceUnavailableError):
    """Embedding generation service errors."""
    
    def __init__(self, reason: str | None = None, **kwargs):
        recovery_suggestions = [
            "Retry with mock embeddings: add '--no-embeddings' flag",
            "Check sentence-transformers model availability",
            "Verify sufficient memory for embedding model",
            "Consider switching to alternative provider: SYNAPSE_EMBEDDING_PROVIDER"
        ]
        super().__init__(
            "Embedding service",
            reason=reason or "Failed to generate embeddings",
            recovery_suggestions=recovery_suggestions,
            error_code="EMBEDDING_GENERATION_FAILED",
            **kwargs
        )


class IngestionError(GraphRAGError):
    """Document ingestion pipeline errors."""
    
    def __init__(self, document_id: str | None = None, stage: str | None = None, 
                 reason: str | None = None, recoverable: bool = True, **kwargs):
        message = "Document ingestion failed"
        if document_id:
            message += f" for document '{document_id}'"
        if stage:
            message += f" at stage '{stage}'"
        if reason:
            message += f": {reason}"
            
        recovery_suggestions = []
        if recoverable:
            recovery_suggestions.extend([
                "Retry ingestion with: 'synapse ingest <path> --replace'",
                "Check document format and encoding",
                "Try ingesting without embeddings: '--no-embeddings'",
                "Verify sufficient disk space and memory"
            ])
        else:
            recovery_suggestions.extend([
                "Check document is not corrupted or encrypted",
                "Verify file permissions and accessibility",
                "Try a different document format if possible"
            ])
            
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, **kwargs)
        self.details.update({
            "document_id": document_id,
            "stage": stage,
            "recoverable": recoverable,
            "recovery_suggestions": recovery_suggestions
        })


class SearchError(GraphRAGError):
    """Search operation errors with fallback suggestions."""
    
    def __init__(self, query: str | None = None, search_type: str | None = None, 
                 reason: str | None = None, **kwargs):
        message = "Search operation failed"
        if query:
            message += f" for query '{query[:50]}...' " if len(query) > 50 else f" for query '{query}'"
        if reason:
            message += f": {reason}"
            
        recovery_suggestions = [
            "Try simplified search: 'synapse search <simple keywords>'",
            "Use different search modes: '--vector-only' or '--graph-only'",
            "Check if documents are ingested: 'synapse admin stats'",
            "Verify system health: 'synapse admin health'"
        ]
        
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, **kwargs)
        self.details.update({
            "query": query,
            "search_type": search_type,
            "recovery_suggestions": recovery_suggestions
        })


class ConfigurationError(ValidationError):
    """Configuration and setup errors."""
    
    def __init__(self, config_key: str | None = None, reason: str | None = None, **kwargs):
        message = "Configuration error"
        if config_key:
            message += f" for '{config_key}'"
        if reason:
            message += f": {reason}"
            
        recovery_suggestions = [
            "Check configuration: 'synapse config show'",
            "Set required environment variables (SYNAPSE_*)",
            "Initialize configuration: 'synapse init'",
            "View configuration help: 'synapse config --help'"
        ]
        
        super().__init__(message, **kwargs)
        self.details.update({
            "config_key": config_key,
            "recovery_suggestions": recovery_suggestions
        })


# Error detection and classification utilities
class ErrorClassifier:
    """Classify and transform common errors into user-friendly GraphRAG errors."""
    
    @staticmethod
    def classify_error(error: Exception, context: Dict[str, Any] | None = None) -> GraphRAGError:
        """Transform common exceptions into appropriate GraphRAG errors with user guidance."""
        context = context or {}
        error_msg = str(error).lower()
        
        # Memgraph/Database connection errors
        if any(keyword in error_msg for keyword in [
            "connection refused", "connection failed", "connection timed out",
            "host unreachable", "mgclient", "memgraph", "cypher"
        ]):
            return MemgraphConnectionError(reason=str(error))
            
        # Vector store errors
        if any(keyword in error_msg for keyword in [
            "faiss", "vector", "embedding dimension", "index error", "dimension mismatch"
        ]):
            operation = context.get("operation", "unknown operation")
            return VectorStoreError(operation=operation, reason=str(error))
            
        # Embedding service errors
        if any(keyword in error_msg for keyword in [
            "sentence-transformers", "embedding model", "tokenizer", "transformers", "torch"
        ]):
            return EmbeddingServiceError(reason=str(error))
            
        # File and permission errors
        if any(keyword in error_msg for keyword in [
            "permission denied", "file not found", "no such file", "access denied"
        ]):
            return ValidationError(
                f"File access error: {error}",
                error_code="FILE_ACCESS_ERROR"
            )
            
        # Network and timeout errors
        if any(keyword in error_msg for keyword in [
            "timeout", "network", "dns", "resolve", "unreachable"
        ]):
            return ServiceUnavailableError(
                "Network service",
                reason=str(error),
                recovery_suggestions=[
                    "Check internet connection",
                    "Verify service URLs and endpoints",
                    "Try again in a few moments",
                    "Check firewall and proxy settings"
                ]
            )
            
        # Out of memory errors
        if any(keyword in error_msg for keyword in [
            "out of memory", "memory error", "allocation failed"
        ]):
            return ServiceUnavailableError(
                "System resources",
                reason="Insufficient memory",
                recovery_suggestions=[
                    "Close other applications to free memory",
                    "Process smaller documents or batches",
                    "Use lightweight embedding models",
                    "Increase system memory if possible"
                ]
            )
            
        # Generic fallback
        return InternalServerError(
            f"Unexpected error: {error}",
            error_code="UNCLASSIFIED_ERROR"
        )


# Enhanced convenience functions with automatic error classification
def handle_service_error(error: Exception, service_name: str, context: Dict[str, Any] | None = None) -> None:
    """Handle service errors with automatic classification and user guidance."""
    context = context or {}
    context["service_name"] = service_name
    
    classified_error = ErrorClassifier.classify_error(error, context)
    raise classified_error


def handle_ingestion_error(error: Exception, document_id: str | None = None, 
                          stage: str | None = None) -> None:
    """Handle ingestion errors with specific context."""
    # Check if this is a recoverable error
    error_msg = str(error).lower()
    recoverable = not any(keyword in error_msg for keyword in [
        "corrupted", "encrypted", "invalid format", "unsupported"
    ])
    
    raise IngestionError(
        document_id=document_id,
        stage=stage,
        reason=str(error),
        recoverable=recoverable
    )


def handle_search_error(error: Exception, query: str | None = None, 
                       search_type: str | None = None) -> None:
    """Handle search errors with query context."""
    raise SearchError(
        query=query,
        search_type=search_type,
        reason=str(error)
    )
