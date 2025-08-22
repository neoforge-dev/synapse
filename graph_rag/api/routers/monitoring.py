"""
Monitoring and Alerting API Router

This module provides REST API endpoints for comprehensive system monitoring:
- Real-time metrics endpoints
- Health and readiness checks
- Performance analytics
- Alert management
- System diagnostics
- Dashboard data feeds

Supports both human-readable and machine-readable formats for integration
with monitoring tools and dashboards.
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from graph_rag.api.dependencies import get_settings
from graph_rag.config import Settings

logger = logging.getLogger(__name__)


# Pydantic models for API responses
class HealthStatus(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Unix timestamp")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    dependencies: list[str] = Field(default_factory=list, description="Checked dependencies")
    degraded_services: list[str] | None = Field(None, description="Services running in degraded mode")
    message: str | None = Field(None, description="Additional status message")


class PerformanceMetrics(BaseModel):
    """Performance metrics response model."""
    request_latency: dict[str, float] = Field(..., description="HTTP request latency metrics")
    vector_search: dict[str, float] = Field(..., description="Vector search performance metrics")
    graph_queries: dict[str, float] = Field(..., description="Graph query performance metrics")
    ingestion: dict[str, float] = Field(..., description="Document ingestion performance metrics")
    timestamp: float = Field(..., description="Metrics timestamp")


class SystemMetrics(BaseModel):
    """System-level metrics response model."""
    uptime_seconds: float = Field(..., description="System uptime")
    total_requests: int = Field(..., description="Total HTTP requests processed")
    error_count: int = Field(..., description="Total error count")
    error_rate_percent: float = Field(..., description="Error rate percentage")
    vector_store_size: int | None = Field(None, description="Number of vectors in store")
    graph_node_count: int | None = Field(None, description="Number of nodes in graph")
    memory_usage_mb: float | None = Field(None, description="Memory usage in MB")
    timestamp: float = Field(..., description="Metrics timestamp")


class AlertSummary(BaseModel):
    """Alert summary response model."""
    total_rules: int = Field(..., description="Total number of alert rules")
    active_alerts: int = Field(..., description="Number of currently active alerts")
    recent_events_24h: int = Field(..., description="Alert events in last 24 hours")
    severity_distribution: dict[str, int] = Field(..., description="Alert distribution by severity")
    timestamp: float = Field(..., description="Summary timestamp")


class AlertEvent(BaseModel):
    """Alert event response model."""
    alert_name: str = Field(..., description="Name of the alert")
    timestamp: float = Field(..., description="Event timestamp")
    state: str = Field(..., description="Alert state")
    severity: str = Field(..., description="Alert severity")
    description: str = Field(..., description="Alert description")
    metric_values: dict[str, Any] = Field(..., description="Metric values at time of alert")
    tags: list[str] = Field(default_factory=list, description="Alert tags")


class SystemDiagnostics(BaseModel):
    """System diagnostics response model."""
    services_status: dict[str, str] = Field(..., description="Status of system services")
    configuration: dict[str, Any] = Field(..., description="Current system configuration")
    resource_usage: dict[str, Any] = Field(..., description="Resource utilization")
    performance_summary: dict[str, Any] = Field(..., description="Performance summary")
    timestamp: float = Field(..., description="Diagnostics timestamp")


def create_monitoring_router() -> APIRouter:
    """Create and configure the monitoring router."""
    router = APIRouter()

    @router.get(
        "/health",
        response_model=HealthStatus,
        summary="Comprehensive health check",
        description="Get detailed health status including dependency checks and performance indicators"
    )
    async def get_health_status(request: Request) -> HealthStatus:
        """Get comprehensive system health status."""
        try:
            from graph_rag.observability.metrics import get_metrics_collector

            # Get metrics collector
            metrics_collector = get_metrics_collector()

            if metrics_collector:
                health_data = metrics_collector.get_health_summary()

                return HealthStatus(
                    status=health_data.get("status", "unknown"),
                    timestamp=health_data.get("timestamp", time.time()),
                    uptime_seconds=health_data.get("uptime_seconds", 0),
                    dependencies=["metrics_collector", "vector_store", "graph_repository"],
                    degraded_services=health_data.get("degraded_services"),
                    message=health_data.get("message")
                )
            else:
                # Fallback health check
                return HealthStatus(
                    status="degraded",
                    timestamp=time.time(),
                    uptime_seconds=0,
                    dependencies=[],
                    message="Metrics collector not available"
                )

        except Exception as e:
            logger.error(f"Error getting health status: {e}", exc_info=True)
            return HealthStatus(
                status="unhealthy",
                timestamp=time.time(),
                uptime_seconds=0,
                dependencies=[],
                message=f"Health check failed: {str(e)}"
            )

    @router.get(
        "/metrics",
        summary="Prometheus metrics export",
        description="Export metrics in Prometheus format for monitoring tools",
        response_class=None
    )
    async def get_prometheus_metrics():
        """Export metrics in Prometheus format."""
        try:
            from graph_rag.observability.metrics import get_metrics_collector

            metrics_collector = get_metrics_collector()
            if not metrics_collector:
                raise HTTPException(status_code=503, detail="Metrics collector not available")

            metrics_data = metrics_collector.get_metrics_export()
            if metrics_data is None:
                raise HTTPException(status_code=503, detail="Prometheus metrics not enabled")

            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                content=metrics_data,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )

        except HTTPException:
            # Re-raise HTTP exceptions as-is (503 for unavailable services)
            raise
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to export metrics")

    @router.get(
        "/performance",
        response_model=PerformanceMetrics,
        summary="Performance metrics",
        description="Get detailed performance metrics for system components"
    )
    async def get_performance_metrics() -> PerformanceMetrics:
        """Get performance metrics."""
        try:
            from graph_rag.observability.metrics import get_metrics_collector

            metrics_collector = get_metrics_collector()
            if not metrics_collector:
                # Return empty metrics if collector not available
                return PerformanceMetrics(
                    request_latency={"avg_ms": 0.0, "samples": 0},
                    vector_search={"avg_ms": 0.0, "samples": 0},
                    graph_queries={"avg_ms": 0.0, "samples": 0},
                    ingestion={"avg_rate": 0.0, "samples": 0},
                    timestamp=time.time()
                )

            performance_data = metrics_collector.get_performance_report()

            return PerformanceMetrics(
                request_latency=performance_data.get("request_latency", {"avg_ms": 0.0, "samples": 0}),
                vector_search=performance_data.get("vector_search", {"avg_ms": 0.0, "samples": 0}),
                graph_queries=performance_data.get("graph_queries", {"avg_ms": 0.0, "samples": 0}),
                ingestion=performance_data.get("ingestion", {"avg_rate": 0.0, "samples": 0}),
                timestamp=time.time()
            )

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}", exc_info=True)
            # Return empty metrics on error instead of raising HTTP exception
            return PerformanceMetrics(
                request_latency={"avg_ms": 0.0, "samples": 0},
                vector_search={"avg_ms": 0.0, "samples": 0},
                graph_queries={"avg_ms": 0.0, "samples": 0},
                ingestion={"avg_rate": 0.0, "samples": 0},
                timestamp=time.time()
            )

    @router.get(
        "/system",
        response_model=SystemMetrics,
        summary="System metrics",
        description="Get system-level metrics including resource usage and operational statistics"
    )
    async def get_system_metrics(request: Request) -> SystemMetrics:
        """Get system-level metrics."""
        try:
            from graph_rag.observability.metrics import get_metrics_collector

            metrics_collector = get_metrics_collector()
            if not metrics_collector:
                # Return basic metrics without collector
                return SystemMetrics(
                    uptime_seconds=0,
                    total_requests=0,
                    error_count=0,
                    error_rate_percent=0,
                    timestamp=time.time()
                )

            health_data = metrics_collector.get_health_summary()

            # Get vector store size if available
            vector_store_size = None
            if hasattr(request.app.state, "vector_store") and request.app.state.vector_store:
                try:
                    if hasattr(request.app.state.vector_store, "get_vector_store_size"):
                        vector_store_size = await request.app.state.vector_store.get_vector_store_size()
                    elif hasattr(request.app.state.vector_store, "stats"):
                        stats = await request.app.state.vector_store.stats()
                        vector_store_size = stats.get("vectors", stats.get("vector_count"))
                except Exception:
                    pass

            # Get graph node count if available
            graph_node_count = None
            if hasattr(request.app.state, "graph_repository") and request.app.state.graph_repository:
                try:
                    # This would need to be implemented in the graph repository
                    # graph_node_count = await request.app.state.graph_repository.get_node_count()
                    pass
                except Exception:
                    pass

            return SystemMetrics(
                uptime_seconds=health_data.get("uptime_seconds", 0),
                total_requests=health_data.get("total_requests", 0),
                error_count=health_data.get("error_count", 0),
                error_rate_percent=health_data.get("error_rate_percent", 0),
                vector_store_size=vector_store_size,
                graph_node_count=graph_node_count,
                timestamp=time.time()
            )

        except Exception as e:
            logger.error(f"Error getting system metrics: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get system metrics")

    @router.get(
        "/alerts/summary",
        response_model=AlertSummary,
        summary="Alert summary",
        description="Get summary of alert rules and recent activity"
    )
    async def get_alert_summary() -> AlertSummary:
        """Get alert summary."""
        try:
            from graph_rag.observability.alerts import get_alert_manager

            alert_manager = get_alert_manager()
            if not alert_manager:
                return AlertSummary(
                    total_rules=0,
                    active_alerts=0,
                    recent_events_24h=0,
                    severity_distribution={},
                    timestamp=time.time()
                )

            stats = alert_manager.get_alert_statistics()

            return AlertSummary(
                total_rules=stats.get("total_rules", 0),
                active_alerts=stats.get("active_alerts", 0),
                recent_events_24h=stats.get("recent_events_24h", 0),
                severity_distribution=stats.get("severity_distribution", {}),
                timestamp=time.time()
            )

        except Exception as e:
            logger.error(f"Error getting alert summary: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get alert summary")

    @router.get(
        "/alerts/history",
        response_model=list[AlertEvent],
        summary="Alert history",
        description="Get recent alert events"
    )
    async def get_alert_history(
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return")
    ) -> list[AlertEvent]:
        """Get alert history."""
        try:
            from graph_rag.observability.alerts import get_alert_manager

            alert_manager = get_alert_manager()
            if not alert_manager:
                return []

            history = alert_manager.get_alert_history(limit=limit)

            return [
                AlertEvent(
                    alert_name=event.alert_name,
                    timestamp=event.timestamp,
                    state=event.state.value,
                    severity=event.severity,
                    description=event.description,
                    metric_values=event.metric_values,
                    tags=list(event.tags)
                )
                for event in history
            ]

        except Exception as e:
            logger.error(f"Error getting alert history: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get alert history")

    @router.get(
        "/diagnostics",
        response_model=SystemDiagnostics,
        summary="System diagnostics",
        description="Get comprehensive system diagnostics including configuration and resource usage"
    )
    async def get_system_diagnostics(
        request: Request,
        settings: Settings = Depends(get_settings)
    ) -> SystemDiagnostics:
        """Get system diagnostics."""
        try:
            # Check service status
            services_status = {}

            # Check graph repository
            if hasattr(request.app.state, "graph_repository") and request.app.state.graph_repository:
                repo_type = request.app.state.graph_repository.__class__.__name__
                services_status["graph_repository"] = "mock" if "Mock" in repo_type else "operational"
            else:
                services_status["graph_repository"] = "unavailable"

            # Check vector store
            if hasattr(request.app.state, "vector_store") and request.app.state.vector_store:
                store_type = request.app.state.vector_store.__class__.__name__
                services_status["vector_store"] = "mock" if "Mock" in store_type else "operational"
            else:
                services_status["vector_store"] = "unavailable"

            # Check other services
            services_status["ingestion_service"] = (
                "operational" if hasattr(request.app.state, "ingestion_service")
                and request.app.state.ingestion_service else "unavailable"
            )
            services_status["graph_rag_engine"] = (
                "operational" if hasattr(request.app.state, "graph_rag_engine")
                and request.app.state.graph_rag_engine else "unavailable"
            )

            # Get configuration (safe subset)
            configuration = {
                "vector_store_type": settings.vector_store_type,
                "embedding_provider": settings.embedding_provider,
                "entity_extractor_type": settings.entity_extractor_type,
                "llm_type": settings.llm_type,
                "enable_metrics": settings.enable_metrics,
                "api_log_level": settings.api_log_level,
            }

            # Resource usage (basic implementation)
            resource_usage = {
                "vector_store_persistent": getattr(settings, "simple_vector_store_persistent", False),
                "faiss_optimized": getattr(settings, "use_optimized_faiss", False),
                "gpu_enabled": getattr(settings, "faiss_use_gpu", False),
            }

            # Performance summary
            performance_summary = {}
            try:
                from graph_rag.observability.metrics import get_metrics_collector

                metrics_collector = get_metrics_collector()
                if metrics_collector:
                    performance_data = metrics_collector.get_performance_report()
                    performance_summary = {
                        "avg_request_latency_ms": performance_data.get("request_latency", {}).get("avg_ms", 0),
                        "avg_vector_search_ms": performance_data.get("vector_search", {}).get("avg_ms", 0),
                        "avg_graph_query_ms": performance_data.get("graph_queries", {}).get("avg_ms", 0),
                    }
            except Exception:
                pass

            return SystemDiagnostics(
                services_status=services_status,
                configuration=configuration,
                resource_usage=resource_usage,
                performance_summary=performance_summary,
                timestamp=time.time()
            )

        except Exception as e:
            logger.error(f"Error getting system diagnostics: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get system diagnostics")

    @router.post(
        "/maintenance/trigger",
        summary="Trigger maintenance",
        description="Manually trigger system maintenance tasks"
    )
    async def trigger_maintenance(
        request: Request,
        task_type: str = Query(..., description="Type of maintenance task to run")
    ) -> dict[str, Any]:
        """Trigger maintenance tasks."""
        try:
            if task_type == "vector_store_optimization":
                # Trigger vector store optimization
                if hasattr(request.app.state, "vector_store") and request.app.state.vector_store:
                    vector_store = request.app.state.vector_store
                    if hasattr(vector_store, "optimize_index"):
                        await vector_store.optimize_index()
                        return {"status": "success", "message": "Vector store optimization triggered"}
                    elif hasattr(vector_store, "rebuild_index"):
                        await vector_store.rebuild_index()
                        return {"status": "success", "message": "Vector store rebuild triggered"}

                return {"status": "error", "message": "Vector store optimization not available"}

            elif task_type == "metrics_reset":
                # Reset metrics collector
                from graph_rag.observability.metrics import get_metrics_collector

                metrics_collector = get_metrics_collector()
                if metrics_collector:
                    # Clear performance metrics history
                    for key in metrics_collector._performance_metrics:
                        metrics_collector._performance_metrics[key].clear()

                    return {"status": "success", "message": "Metrics reset completed"}

                return {"status": "error", "message": "Metrics collector not available"}

            else:
                return {"status": "error", "message": f"Unknown maintenance task: {task_type}"}

        except Exception as e:
            logger.error(f"Error triggering maintenance: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to trigger maintenance")

    return router


# Export for use in main application
__all__ = ["create_monitoring_router"]
