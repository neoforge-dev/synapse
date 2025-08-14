"""Test standardized error handling and middleware."""


import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from graph_rag.api.errors import (
    GraphRAGError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
    create_problem_detail,
)
from graph_rag.api.main import create_app


@pytest.fixture
def test_client():
    """Create a test client with all middleware and error handlers."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(test_client):
    """Test that health endpoint works with new error handling."""
    response = test_client.get("/health")

    # Should either succeed or fail gracefully with structured error
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
    else:
        # Should return problem detail format
        assert response.headers.get("content-type") == "application/problem+json"
        data = response.json()
        assert "title" in data
        assert "status" in data
        assert "timestamp" in data


def test_request_id_header(test_client):
    """Test that request ID is added to response headers."""
    response = test_client.get("/health")
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers

    # Request ID should be a valid UUID format
    request_id = response.headers["X-Request-ID"]
    import uuid
    try:
        uuid.UUID(request_id)
    except ValueError:
        pytest.fail(f"Invalid UUID format for request ID: {request_id}")


def test_security_headers(test_client):
    """Test that security headers are added."""
    response = test_client.get("/health")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("X-API-Version") == "1.0.0"
    assert response.headers.get("X-Powered-By") == "Synapse GraphRAG"


def test_not_found_error_format(test_client):
    """Test that 404 errors follow problem detail format."""
    response = test_client.get("/api/v1/nonexistent")

    assert response.status_code == 404
    assert response.headers.get("content-type") == "application/problem+json"

    data = response.json()
    assert "title" in data
    assert "status" in data
    assert data["status"] == 404
    assert "timestamp" in data
    assert "request_id" in data


def test_create_problem_detail():
    """Test problem detail creation from exceptions."""
    # Test GraphRAGError
    error = ValidationError("Invalid field", field="username")
    problem = create_problem_detail(error)

    assert problem.title == "Validation"
    assert problem.status == 400
    assert problem.detail == "Invalid field"
    assert problem.error_code is None
    assert hasattr(problem, "field")
    assert problem.field == "username"  # type: ignore

    # Test NotFoundError
    error = NotFoundError("Document", "doc-123")
    problem = create_problem_detail(error)

    assert problem.title == "NotFound"
    assert problem.status == 404
    assert "doc-123" in problem.detail
    assert hasattr(problem, "resource_type")
    assert problem.resource_type == "Document"  # type: ignore

    # Test HTTPException
    error = HTTPException(status_code=401, detail="Unauthorized")
    problem = create_problem_detail(error)

    assert problem.title == "HTTP Error"
    assert problem.status == 401
    assert problem.detail == "Unauthorized"


def test_service_unavailable_error():
    """Test service unavailable error handling."""
    error = ServiceUnavailableError("Memgraph", reason="Connection timeout")
    problem = create_problem_detail(error)

    assert problem.title == "ServiceUnavailable"
    assert problem.status == 503
    assert "Memgraph" in problem.detail
    assert "Connection timeout" in problem.detail
    assert hasattr(problem, "service_name")
    assert problem.service_name == "Memgraph"  # type: ignore


def test_error_with_custom_code():
    """Test error with custom error code."""
    error = GraphRAGError(
        "Custom error",
        error_code="CUSTOM_001",
        status_code=422
    )
    problem = create_problem_detail(error)

    assert problem.error_code == "CUSTOM_001"
    assert problem.status == 422


@pytest.mark.parametrize("endpoint", [
    "/health",
    "/ready",
    "/",
    "/docs",
])
def test_common_endpoints_work(test_client, endpoint):
    """Test that common endpoints don't break with new error handling."""
    response = test_client.get(endpoint)

    # Should not return 500 errors
    assert response.status_code < 500

    # Should have request ID
    assert "X-Request-ID" in response.headers


def test_rate_limiting_headers(test_client):
    """Test rate limiting headers are present."""
    response = test_client.get("/health")

    # Rate limiting headers should be present
    assert "X-RateLimit-Limit-Minute" in response.headers
    assert "X-RateLimit-Limit-Hour" in response.headers
    assert "X-RateLimit-Remaining-Minute" in response.headers
    assert "X-RateLimit-Remaining-Hour" in response.headers

    # Verify header values are numeric
    assert int(response.headers["X-RateLimit-Limit-Minute"]) > 0
    assert int(response.headers["X-RateLimit-Limit-Hour"]) > 0
