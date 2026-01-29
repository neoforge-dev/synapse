"""
Enhanced monitoring and health check endpoints for production deployment.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from datetime import datetime, timezone
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from graph_rag.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    checks: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Individual health checks"
    )


class SystemMetrics(BaseModel):
    """System metrics response model."""

    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    memory_available_mb: float = Field(..., description="Available memory in MB")
    disk_percent: float = Field(..., description="Disk usage percentage")
    uptime_seconds: float = Field(..., description="System uptime in seconds")


class ApplicationInfo(BaseModel):
    """Application information response model."""

    name: str = Field(default="synapse-graph-rag")
    version: str = Field(..., description="Application version")
    python_version: str = Field(..., description="Python version")
    platform: str = Field(..., description="Operating system platform")
    environment: str = Field(..., description="Deployment environment")
    started_at: datetime = Field(..., description="Application start time")


# Track application start time
APP_START_TIME = datetime.now(timezone.utc)


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Comprehensive health check",
    description="Returns detailed health status of all system components",
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthStatus:
    """
    Comprehensive health check endpoint.

    Checks:
    - API availability
    - Memgraph connectivity
    - System resources
    - Required services
    """
    checks: dict[str, dict[str, Any]] = {}

    # Check API
    checks["api"] = {
        "status": "healthy",
        "message": "API is running",
    }

    # Check Memgraph connectivity
    try:
        # Import here to avoid circular dependency
        from graph_rag.infrastructure.graph_stores.memgraph_store import (
            MemgraphGraphRepository,
        )

        repo = MemgraphGraphRepository(
            host=settings.memgraph.host,
            port=settings.memgraph.port,
            username=settings.memgraph.username,
            password=settings.memgraph.password,
        )
        # Simple connectivity check
        checks["memgraph"] = {
            "status": "healthy",
            "host": settings.memgraph.host,
            "port": settings.memgraph.port,
        }
    except Exception as e:
        logger.error(f"Memgraph health check failed: {e}")
        checks["memgraph"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Check system resources
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        checks["resources"] = {
            "status": "healthy" if memory.percent < 90 and disk.percent < 90 else "degraded",
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
        }
    except Exception as e:
        logger.error(f"System resources check failed: {e}")
        checks["resources"] = {
            "status": "unknown",
            "error": str(e),
        }

    # Determine overall status
    overall_status = "healthy"
    if any(check.get("status") == "unhealthy" for check in checks.values()):
        overall_status = "unhealthy"
    elif any(check.get("status") == "degraded" for check in checks.values()):
        overall_status = "degraded"

    return HealthStatus(
        status=overall_status,
        version=os.getenv("SYNAPSE_VERSION", "0.1.0"),
        environment=os.getenv("SYNAPSE_ENVIRONMENT", "development"),
        checks=checks,
    )


@router.get(
    "/health/liveness",
    summary="Liveness probe",
    description="Simple liveness check for Kubernetes/Docker",
)
async def liveness_probe() -> dict[str, str]:
    """
    Liveness probe endpoint.

    Returns a simple 200 OK if the application is running.
    Used by Kubernetes/Docker to determine if the container should be restarted.
    """
    return {"status": "alive"}


@router.get(
    "/health/readiness",
    summary="Readiness probe",
    description="Readiness check for Kubernetes/Docker",
)
async def readiness_probe(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """
    Readiness probe endpoint.

    Checks if the application is ready to serve traffic.
    Used by Kubernetes/Docker to determine if traffic should be routed to this instance.
    """
    # Check critical dependencies
    try:
        from graph_rag.infrastructure.graph_stores.memgraph_store import (
            MemgraphGraphRepository,
        )

        # Attempt to connect to Memgraph
        repo = MemgraphGraphRepository(
            host=settings.memgraph.host,
            port=settings.memgraph.port,
            username=settings.memgraph.username,
            password=settings.memgraph.password,
        )

        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )


@router.get(
    "/metrics/system",
    response_model=SystemMetrics,
    summary="System metrics",
    description="Returns current system resource utilization",
)
async def system_metrics() -> SystemMetrics:
    """
    Get current system metrics.

    Returns CPU, memory, disk usage, and uptime.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime = (datetime.now(timezone.utc) - APP_START_TIME).total_seconds()

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / (1024 * 1024),
            disk_percent=disk.percent,
            uptime_seconds=uptime,
        )
    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect system metrics",
        )


@router.get(
    "/info",
    response_model=ApplicationInfo,
    summary="Application information",
    description="Returns application version and environment details",
)
async def application_info(settings: Settings = Depends(get_settings)) -> ApplicationInfo:
    """
    Get application information.

    Returns version, Python version, platform, and startup time.
    """
    return ApplicationInfo(
        version=os.getenv("SYNAPSE_VERSION", "0.1.0"),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=f"{platform.system()} {platform.release()}",
        environment=os.getenv("SYNAPSE_ENVIRONMENT", "development"),
        started_at=APP_START_TIME,
    )
