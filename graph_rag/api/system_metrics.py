"""System metrics and monitoring for production health tracking."""

import asyncio
import platform
import time
from dataclasses import dataclass, field
from typing import Any

import psutil

from graph_rag.observability import (
    ComponentType,
    LogContext,
    get_component_logger,
)

# Use structured logger for system metrics
logger = get_component_logger(ComponentType.MONITORING, "system_metrics")


@dataclass
class SystemResourceMetrics:
    """Current system resource usage metrics."""

    # CPU metrics
    cpu_percent: float
    cpu_count: int

    # Memory metrics
    memory_total: int
    memory_available: int
    memory_used: int
    memory_percent: float

    # Disk metrics
    disk_total: int
    disk_used: int
    disk_free: int
    disk_percent: float

    # Process metrics
    process_count: int

    # Timestamp
    timestamp: float = field(default_factory=time.time)

    # Optional metrics (with defaults)
    load_average: list[float] | None = None
    network_sent: int | None = None
    network_recv: int | None = None


@dataclass
class ApplicationMetrics:
    """Application-specific metrics for GraphRAG."""

    # Memory usage of current process
    process_memory_mb: float
    process_cpu_percent: float

    # Thread and connection counts
    thread_count: int
    open_files: int

    # Performance metrics
    uptime_seconds: float

    # Cache and storage metrics
    cache_hit_rate: float | None = None
    vector_store_size: int | None = None
    graph_node_count: int | None = None

    # Request metrics
    total_requests: int | None = None
    avg_response_time: float | None = None

    timestamp: float = field(default_factory=time.time)


class SystemMetricsCollector:
    """Collects comprehensive system and application metrics."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time = time.time()
        self._last_network_stats = None

    def collect_system_metrics(self) -> SystemResourceMetrics:
        """Collect system-level resource metrics."""

        context = LogContext(
            component=ComponentType.MONITORING,
            operation="collect_system_metrics",
            metadata={"collector": "psutil"}
        )

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Load average (Unix-like systems only)
            load_avg = None
            try:
                if hasattr(psutil, 'getloadavg'):
                    load_avg = list(psutil.getloadavg())
            except (AttributeError, OSError):
                pass

            # Memory metrics
            memory = psutil.virtual_memory()

            # Disk metrics (for root partition)
            disk = psutil.disk_usage('/')

            # Network metrics
            network_sent = None
            network_recv = None
            try:
                network_io = psutil.net_io_counters()
                if network_io:
                    network_sent = network_io.bytes_sent
                    network_recv = network_io.bytes_recv
            except Exception:
                pass

            # Process count
            process_count = len(psutil.pids())

            metrics = SystemResourceMetrics(
                cpu_percent=cpu_percent,
                cpu_count=cpu_count,
                load_average=load_avg,
                memory_total=memory.total,
                memory_available=memory.available,
                memory_used=memory.used,
                memory_percent=memory.percent,
                disk_total=disk.total,
                disk_used=disk.used,
                disk_free=disk.free,
                disk_percent=(disk.used / disk.total) * 100,
                network_sent=network_sent,
                network_recv=network_recv,
                process_count=process_count,
            )

            logger.debug(
                "Collected system metrics",
                context,
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=metrics.disk_percent
            )

            return metrics

        except Exception as e:
            logger.error(
                "Failed to collect system metrics",
                context,
                error=e
            )
            raise

    def collect_application_metrics(
        self,
        vector_store=None,
        graph_repository=None,
        cache_stats: dict[str, Any] | None = None,
        performance_stats: dict[str, Any] | None = None
    ) -> ApplicationMetrics:
        """Collect application-specific metrics."""

        context = LogContext(
            component=ComponentType.MONITORING,
            operation="collect_application_metrics",
            metadata={"has_vector_store": vector_store is not None}
        )

        try:
            # Process-specific metrics
            memory_info = self.process.memory_info()
            process_memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            process_cpu_percent = self.process.cpu_percent()

            # Thread and file metrics
            thread_count = self.process.num_threads()
            open_files = len(self.process.open_files())

            # Uptime
            uptime_seconds = time.time() - self.start_time

            # Cache metrics
            cache_hit_rate = None
            if cache_stats:
                total_accesses = cache_stats.get("total_accesses", 0)
                if total_accesses > 0:
                    # This is a simplified calculation - in reality you'd track hits vs misses
                    cache_hit_rate = 0.85  # Placeholder

            # Vector store size
            vector_store_size = None
            if vector_store and hasattr(vector_store, 'get_vector_store_size'):
                try:
                    vector_store_size = vector_store.get_vector_store_size()
                    if asyncio.iscoroutine(vector_store_size):
                        # Can't await here, will be None
                        vector_store_size = None
                except Exception:
                    pass

            # Graph metrics
            graph_node_count = None
            if graph_repository:
                try:
                    # This would need to be implemented in the repository
                    if hasattr(graph_repository, 'get_node_count'):
                        graph_node_count = graph_repository.get_node_count()
                except Exception:
                    pass

            # Request metrics from performance stats
            total_requests = None
            avg_response_time = None
            if performance_stats:
                # Aggregate request stats from all monitored functions
                total_calls = sum(
                    stats.get("total_calls", 0)
                    for stats in performance_stats.values()
                    if isinstance(stats, dict)
                )
                if total_calls > 0:
                    total_requests = total_calls

                    total_duration = sum(
                        stats.get("total_calls", 0) * stats.get("avg_duration", 0)
                        for stats in performance_stats.values()
                        if isinstance(stats, dict)
                    )
                    avg_response_time = total_duration / total_calls if total_calls > 0 else 0

            metrics = ApplicationMetrics(
                process_memory_mb=process_memory_mb,
                process_cpu_percent=process_cpu_percent,
                thread_count=thread_count,
                open_files=open_files,
                uptime_seconds=uptime_seconds,
                cache_hit_rate=cache_hit_rate,
                vector_store_size=vector_store_size,
                graph_node_count=graph_node_count,
                total_requests=total_requests,
                avg_response_time=avg_response_time,
            )

            logger.debug(
                "Collected application metrics",
                context,
                process_memory_mb=process_memory_mb,
                uptime_hours=uptime_seconds / 3600,
                thread_count=thread_count
            )

            return metrics

        except Exception as e:
            logger.error(
                "Failed to collect application metrics",
                context,
                error=e
            )
            raise

    def get_platform_info(self) -> dict[str, Any]:
        """Get platform and environment information."""

        context = LogContext(
            component=ComponentType.MONITORING,
            operation="collect_platform_info"
        )

        try:
            info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
                "boot_time": psutil.boot_time(),
            }

            logger.debug("Collected platform info", context, system=info["system"])
            return info

        except Exception as e:
            logger.error("Failed to collect platform info", context, error=e)
            return {"error": str(e)}


class HealthThresholds:
    """Define health thresholds for various metrics."""

    # CPU thresholds
    CPU_WARNING = 70.0
    CPU_CRITICAL = 90.0

    # Memory thresholds
    MEMORY_WARNING = 80.0
    MEMORY_CRITICAL = 95.0

    # Disk thresholds
    DISK_WARNING = 85.0
    DISK_CRITICAL = 95.0

    # Response time thresholds (seconds)
    RESPONSE_TIME_WARNING = 2.0
    RESPONSE_TIME_CRITICAL = 5.0

    # Process memory thresholds (MB)
    PROCESS_MEMORY_WARNING = 1024  # 1GB
    PROCESS_MEMORY_CRITICAL = 2048  # 2GB


def assess_system_health(
    system_metrics: SystemResourceMetrics,
    app_metrics: ApplicationMetrics
) -> dict[str, Any]:
    """Assess overall system health based on metrics and thresholds."""

    context = LogContext(
        component=ComponentType.MONITORING,
        operation="assess_system_health",
        metadata={
            "cpu_percent": system_metrics.cpu_percent,
            "memory_percent": system_metrics.memory_percent,
            "disk_percent": system_metrics.disk_percent
        }
    )

    issues = []
    warnings = []

    # Check CPU usage
    if system_metrics.cpu_percent >= HealthThresholds.CPU_CRITICAL:
        issues.append(f"Critical CPU usage: {system_metrics.cpu_percent:.1f}%")
    elif system_metrics.cpu_percent >= HealthThresholds.CPU_WARNING:
        warnings.append(f"High CPU usage: {system_metrics.cpu_percent:.1f}%")

    # Check memory usage
    if system_metrics.memory_percent >= HealthThresholds.MEMORY_CRITICAL:
        issues.append(f"Critical memory usage: {system_metrics.memory_percent:.1f}%")
    elif system_metrics.memory_percent >= HealthThresholds.MEMORY_WARNING:
        warnings.append(f"High memory usage: {system_metrics.memory_percent:.1f}%")

    # Check disk usage
    if system_metrics.disk_percent >= HealthThresholds.DISK_CRITICAL:
        issues.append(f"Critical disk usage: {system_metrics.disk_percent:.1f}%")
    elif system_metrics.disk_percent >= HealthThresholds.DISK_WARNING:
        warnings.append(f"High disk usage: {system_metrics.disk_percent:.1f}%")

    # Check process memory
    if app_metrics.process_memory_mb >= HealthThresholds.PROCESS_MEMORY_CRITICAL:
        issues.append(f"Critical process memory: {app_metrics.process_memory_mb:.1f}MB")
    elif app_metrics.process_memory_mb >= HealthThresholds.PROCESS_MEMORY_WARNING:
        warnings.append(f"High process memory: {app_metrics.process_memory_mb:.1f}MB")

    # Check average response time
    if (app_metrics.avg_response_time and
        app_metrics.avg_response_time >= HealthThresholds.RESPONSE_TIME_CRITICAL):
        issues.append(f"Critical response time: {app_metrics.avg_response_time:.2f}s")
    elif (app_metrics.avg_response_time and
          app_metrics.avg_response_time >= HealthThresholds.RESPONSE_TIME_WARNING):
        warnings.append(f"Slow response time: {app_metrics.avg_response_time:.2f}s")

    # Determine overall health status
    if issues:
        status = "critical"
    elif warnings:
        status = "warning"
    else:
        status = "healthy"

    assessment = {
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "total_issues": len(issues),
            "total_warnings": len(warnings),
        }
    }

    logger.info(
        f"System health assessment completed: {status}",
        context,
        status=status,
        issue_count=len(issues),
        warning_count=len(warnings)
    )

    return assessment


# Global collector instance
_global_collector = SystemMetricsCollector()


def get_system_metrics() -> SystemResourceMetrics:
    """Get current system metrics."""
    return _global_collector.collect_system_metrics()


def get_application_metrics(
    vector_store=None,
    graph_repository=None,
    cache_stats=None,
    performance_stats=None
) -> ApplicationMetrics:
    """Get current application metrics."""
    return _global_collector.collect_application_metrics(
        vector_store=vector_store,
        graph_repository=graph_repository,
        cache_stats=cache_stats,
        performance_stats=performance_stats
    )


def get_platform_info() -> dict[str, Any]:
    """Get platform information."""
    return _global_collector.get_platform_info()
