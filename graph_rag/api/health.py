"""Comprehensive health check system for monitoring service health."""

import logging
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: str | None = None
    response_time_ms: float | None = None
    details: dict[str, Any] = {}
    last_checked: float | None = None


class SystemHealth(BaseModel):
    """Overall system health aggregation."""
    status: HealthStatus
    timestamp: float
    version: str = "1.0.0"
    components: list[ComponentHealth] = []
    summary: dict[str, Any] = {}


class HealthChecker:
    """Comprehensive health checking system."""

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds
        self.checkers: dict[str, Any] = {}

    def register_checker(self, name: str, checker_func):
        """Register a health check function."""
        self.checkers[name] = checker_func

    async def check_component(self, name: str, checker_func) -> ComponentHealth:
        """Check health of a single component."""
        start_time = time.time()

        try:
            # Run health check with timeout
            import asyncio
            result = await asyncio.wait_for(
                checker_func(),
                timeout=self.timeout_seconds
            )

            response_time = (time.time() - start_time) * 1000

            if isinstance(result, dict):
                status = HealthStatus(result.get("status", HealthStatus.HEALTHY))
                message = result.get("message")
                details = result.get("details", {})
            else:
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                message = None
                details = {}

            return ComponentHealth(
                name=name,
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details,
                last_checked=time.time()
            )

        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout_seconds}s",
                response_time_ms=response_time,
                last_checked=time.time()
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
                details={"error_type": e.__class__.__name__},
                last_checked=time.time()
            )

    async def check_all(self, checkers: dict[str, Any] | None = None) -> SystemHealth:
        """Check health of all registered components."""
        checkers = checkers or self.checkers
        components = []

        # Run all health checks
        for name, checker_func in checkers.items():
            component_health = await self.check_component(name, checker_func)
            components.append(component_health)

        # Determine overall status
        overall_status = self._aggregate_status([c.status for c in components])

        # Calculate summary stats
        healthy_count = len([c for c in components if c.status == HealthStatus.HEALTHY])
        degraded_count = len([c for c in components if c.status == HealthStatus.DEGRADED])
        unhealthy_count = len([c for c in components if c.status == HealthStatus.UNHEALTHY])

        avg_response_time = None
        if components:
            response_times = [c.response_time_ms for c in components if c.response_time_ms]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

        summary = {
            "total_components": len(components),
            "healthy_components": healthy_count,
            "degraded_components": degraded_count,
            "unhealthy_components": unhealthy_count,
            "avg_response_time_ms": avg_response_time
        }

        return SystemHealth(
            status=overall_status,
            timestamp=time.time(),
            components=components,
            summary=summary
        )

    def _aggregate_status(self, statuses: list[HealthStatus]) -> HealthStatus:
        """Aggregate component statuses into overall system status."""
        if not statuses:
            return HealthStatus.UNKNOWN

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY

        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED

        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN


# Pre-built health check functions
async def check_graph_repository(graph_repo) -> dict[str, Any]:
    """Health check for graph repository."""
    try:
        if hasattr(graph_repo, 'health_check'):
            result = await graph_repo.health_check()
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Graph repository accessible",
                "details": result
            }
        else:
            # Try a simple operation
            await graph_repo.get_document("__health_check__")
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Graph repository accessible"
            }
    except Exception as e:
        # Check if it's a mock repository
        if "Mock" in graph_repo.__class__.__name__:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Using mock graph repository - limited functionality",
                "details": {"repository_type": "mock"}
            }
        else:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Graph repository error: {str(e)}"
            }


async def check_vector_store(vector_store) -> dict[str, Any]:
    """Health check for vector store."""
    try:
        if hasattr(vector_store, 'health_check'):
            result = await vector_store.health_check()
            return {
                "status": HealthStatus.HEALTHY,
                "details": result
            }
        elif hasattr(vector_store, 'get_vector_store_size'):
            size = await vector_store.get_vector_store_size()
            return {
                "status": HealthStatus.HEALTHY,
                "message": f"Vector store accessible ({size} vectors)",
                "details": {"vector_count": size}
            }
        else:
            # Try a simple search
            await vector_store.search("", 0)
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Vector store accessible"
            }
    except Exception as e:
        if "Mock" in vector_store.__class__.__name__:
            return {
                "status": HealthStatus.DEGRADED,
                "message": "Using mock vector store - limited functionality",
                "details": {"store_type": "mock"}
            }
        else:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Vector store error: {str(e)}"
            }


async def check_llm_service(llm_service) -> dict[str, Any]:
    """Health check for LLM service."""
    try:
        if hasattr(llm_service, 'health_check'):
            result = await llm_service.health_check()
            return {
                "status": HealthStatus.HEALTHY,
                "details": result
            }
        else:
            # Try a simple generation
            response = await llm_service.generate_response("health check", context="test")
            if response:
                service_type = "mock" if "Mock" in llm_service.__class__.__name__ else "production"
                status = HealthStatus.DEGRADED if service_type == "mock" else HealthStatus.HEALTHY
                return {
                    "status": status,
                    "message": f"LLM service accessible ({service_type})",
                    "details": {"service_type": service_type}
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "LLM service returned empty response"
                }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"LLM service error: {str(e)}"
        }


async def check_embedding_service(embedding_service) -> dict[str, Any]:
    """Health check for embedding service."""
    try:
        if hasattr(embedding_service, 'health_check'):
            result = await embedding_service.health_check()
            return {
                "status": HealthStatus.HEALTHY,
                "details": result
            }
        else:
            # Try encoding a simple text
            embeddings = await embedding_service.encode(["health check"])
            if embeddings and len(embeddings) > 0 and len(embeddings[0]) > 0:
                service_type = "mock" if "Mock" in embedding_service.__class__.__name__ else "production"
                status = HealthStatus.DEGRADED if service_type == "mock" else HealthStatus.HEALTHY
                return {
                    "status": status,
                    "message": f"Embedding service accessible ({service_type})",
                    "details": {
                        "service_type": service_type,
                        "embedding_dimension": len(embeddings[0])
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Embedding service returned invalid embeddings"
                }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Embedding service error: {str(e)}"
        }
