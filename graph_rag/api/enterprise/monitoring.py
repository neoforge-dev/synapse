"""Enterprise monitoring system for API health, performance, and alerting."""

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """System health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemHealth(BaseModel):
    """System health metrics."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: HealthStatus = HealthStatus.HEALTHY

    # Performance metrics
    cpu_usage_percentage: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percentage: float = 0.0
    disk_usage_percentage: float = 0.0
    network_connections: int = 0

    # Request metrics
    requests_per_second: float = 0.0
    avg_response_time_ms: float = 0.0
    error_rate_percentage: float = 0.0
    active_connections: int = 0

    # Endpoint health
    healthy_endpoints: int = 0
    degraded_endpoints: int = 0
    failed_endpoints: int = 0

    # Database connectivity (if applicable)
    database_connections_active: int = 0
    database_response_time_ms: float = 0.0

    # Alerts
    active_alerts: int = 0
    critical_alerts: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EndpointMetrics(BaseModel):
    """Metrics for individual API endpoints."""

    endpoint: str
    method: str

    # Request counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Response times
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0

    # Error details
    error_rate_percentage: float = 0.0
    status_code_counts: dict[int, int] = Field(default_factory=dict)

    # Last activity
    last_request: datetime | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Alert(BaseModel):
    """System alert for monitoring."""

    alert_id: str
    level: AlertLevel
    title: str
    description: str

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    is_active: bool = True

    # Context
    component: str  # "api", "database", "auth", etc.
    metrics: dict[str, Any] = Field(default_factory=dict)

    # Escalation
    escalation_level: int = 0
    escalation_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EnterpriseMonitor:
    """Comprehensive monitoring system for enterprise API operations."""

    def __init__(self):
        # Request tracking
        self.endpoint_metrics: dict[str, EndpointMetrics] = {}
        self.request_times: deque = deque(maxlen=10000)  # Last 10k request times
        self.request_counts: deque = deque(maxlen=300)   # 5-minute windows for 25 hours

        # System health
        self.system_metrics_history: list[SystemHealth] = []
        self.max_history_entries = 1440  # 24 hours of minute-by-minute data

        # Alerts
        self.active_alerts: dict[str, Alert] = {}
        self.alert_history: list[Alert] = []

        # Thresholds
        self.thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 85.0,
            "memory_warning": 80.0,
            "memory_critical": 90.0,
            "disk_warning": 85.0,
            "disk_critical": 95.0,
            "response_time_warning": 2000.0,  # 2 seconds
            "response_time_critical": 5000.0,  # 5 seconds
            "error_rate_warning": 5.0,        # 5%
            "error_rate_critical": 10.0,      # 10%
        }

        # Background tasks
        self._monitoring_task: asyncio.Task | None = None

        logger.info("Enterprise monitor initialized")

    async def record_request(self, response_time_ms: float, success: bool,
                           endpoint: str, method: str = "GET") -> None:
        """Record a request for monitoring purposes."""

        # Record global metrics
        self.request_times.append(response_time_ms)

        # Update request counts (per minute)
        now = datetime.utcnow()
        minute_key = now.replace(second=0, microsecond=0)

        # Initialize minute bucket if needed
        if not self.request_counts or self.request_counts[-1][0] != minute_key:
            self.request_counts.append((minute_key, {"total": 0, "success": 0, "failed": 0}))

        # Update current minute
        current_minute = self.request_counts[-1][1]
        current_minute["total"] += 1
        if success:
            current_minute["success"] += 1
        else:
            current_minute["failed"] += 1

        # Update endpoint metrics
        endpoint_key = f"{method} {endpoint}"
        if endpoint_key not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint_key] = EndpointMetrics(
                endpoint=endpoint,
                method=method
            )

        metrics = self.endpoint_metrics[endpoint_key]
        metrics.total_requests += 1
        metrics.last_request = now

        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1

        # Update response time statistics
        if metrics.total_requests == 1:
            metrics.min_response_time_ms = response_time_ms
            metrics.max_response_time_ms = response_time_ms
            metrics.avg_response_time_ms = response_time_ms
        else:
            metrics.min_response_time_ms = min(metrics.min_response_time_ms, response_time_ms)
            metrics.max_response_time_ms = max(metrics.max_response_time_ms, response_time_ms)

            # Update average (simple moving average)
            metrics.avg_response_time_ms = (
                (metrics.avg_response_time_ms * (metrics.total_requests - 1) + response_time_ms)
                / metrics.total_requests
            )

        # Update error rate
        metrics.error_rate_percentage = (metrics.failed_requests / metrics.total_requests) * 100

        # Check for alerts
        await self._check_endpoint_alerts(endpoint_key, metrics)

    async def get_health_status(self) -> SystemHealth:
        """Get current system health status."""

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_connections = len(psutil.net_connections())

        # Calculate request metrics
        requests_per_second = self._calculate_requests_per_second()
        avg_response_time = self._calculate_avg_response_time()
        error_rate = self._calculate_error_rate()

        # Count endpoint health
        healthy_endpoints = 0
        degraded_endpoints = 0
        failed_endpoints = 0

        for metrics in self.endpoint_metrics.values():
            if metrics.error_rate_percentage < 1.0 and metrics.avg_response_time_ms < 1000:
                healthy_endpoints += 1
            elif metrics.error_rate_percentage < 5.0 and metrics.avg_response_time_ms < 3000:
                degraded_endpoints += 1
            else:
                failed_endpoints += 1

        # Determine overall health status
        status = HealthStatus.HEALTHY

        if (cpu_percent > self.thresholds["cpu_critical"] or
            memory.percent > self.thresholds["memory_critical"] or
            disk.percent > self.thresholds["disk_critical"] or
            error_rate > self.thresholds["error_rate_critical"] or
            avg_response_time > self.thresholds["response_time_critical"] or
            failed_endpoints > 0):
            status = HealthStatus.CRITICAL
        elif (cpu_percent > self.thresholds["cpu_warning"] or
              memory.percent > self.thresholds["memory_warning"] or
              disk.percent > self.thresholds["disk_warning"] or
              error_rate > self.thresholds["error_rate_warning"] or
              avg_response_time > self.thresholds["response_time_warning"] or
              degraded_endpoints > 0):
            status = HealthStatus.WARNING

        # Create health status
        health = SystemHealth(
            status=status,
            cpu_usage_percentage=cpu_percent,
            memory_usage_mb=memory.used / (1024 * 1024),
            memory_usage_percentage=memory.percent,
            disk_usage_percentage=disk.percent,
            network_connections=net_connections,
            requests_per_second=requests_per_second,
            avg_response_time_ms=avg_response_time,
            error_rate_percentage=error_rate,
            active_connections=len(self.endpoint_metrics),  # Approximation
            healthy_endpoints=healthy_endpoints,
            degraded_endpoints=degraded_endpoints,
            failed_endpoints=failed_endpoints,
            active_alerts=len([a for a in self.active_alerts.values() if a.is_active]),
            critical_alerts=len([a for a in self.active_alerts.values()
                               if a.is_active and a.level == AlertLevel.CRITICAL])
        )

        # Store in history
        self.system_metrics_history.append(health)
        if len(self.system_metrics_history) > self.max_history_entries:
            self.system_metrics_history.pop(0)

        # Check for system-level alerts
        await self._check_system_alerts(health)

        return health

    def _calculate_requests_per_second(self) -> float:
        """Calculate current requests per second."""
        if not self.request_counts:
            return 0.0

        # Get last 60 seconds of data
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=60)

        total_requests = 0
        minutes_counted = 0

        for timestamp, counts in reversed(self.request_counts):
            if timestamp < cutoff:
                break
            total_requests += counts["total"]
            minutes_counted += 1

        if minutes_counted == 0:
            return 0.0

        # Convert to requests per second
        return total_requests / (minutes_counted * 60)

    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time from recent requests."""
        if not self.request_times:
            return 0.0

        # Use last 1000 requests or all if fewer
        recent_times = list(self.request_times)[-1000:]
        return sum(recent_times) / len(recent_times)

    def _calculate_error_rate(self) -> float:
        """Calculate error rate from recent requests."""
        if not self.request_counts:
            return 0.0

        # Get last 5 minutes of data
        total_requests = 0
        failed_requests = 0

        for _, counts in list(self.request_counts)[-5:]:
            total_requests += counts["total"]
            failed_requests += counts["failed"]

        if total_requests == 0:
            return 0.0

        return (failed_requests / total_requests) * 100

    async def _check_endpoint_alerts(self, endpoint_key: str, metrics: EndpointMetrics) -> None:
        """Check for endpoint-specific alerts."""

        alert_id = f"endpoint_{endpoint_key.replace(' ', '_').replace('/', '_')}"

        # Check for high error rate
        if metrics.error_rate_percentage > self.thresholds["error_rate_critical"]:
            await self._create_or_update_alert(
                alert_id + "_error_rate",
                AlertLevel.CRITICAL,
                f"High error rate on {endpoint_key}",
                f"Error rate is {metrics.error_rate_percentage:.1f}% (threshold: {self.thresholds['error_rate_critical']}%)",
                "api",
                {"endpoint": endpoint_key, "error_rate": metrics.error_rate_percentage}
            )
        elif metrics.error_rate_percentage > self.thresholds["error_rate_warning"]:
            await self._create_or_update_alert(
                alert_id + "_error_rate",
                AlertLevel.WARNING,
                f"Elevated error rate on {endpoint_key}",
                f"Error rate is {metrics.error_rate_percentage:.1f}% (threshold: {self.thresholds['error_rate_warning']}%)",
                "api",
                {"endpoint": endpoint_key, "error_rate": metrics.error_rate_percentage}
            )
        else:
            await self._resolve_alert(alert_id + "_error_rate")

        # Check for high response time
        if metrics.avg_response_time_ms > self.thresholds["response_time_critical"]:
            await self._create_or_update_alert(
                alert_id + "_response_time",
                AlertLevel.CRITICAL,
                f"High response time on {endpoint_key}",
                f"Average response time is {metrics.avg_response_time_ms:.1f}ms (threshold: {self.thresholds['response_time_critical']}ms)",
                "api",
                {"endpoint": endpoint_key, "response_time": metrics.avg_response_time_ms}
            )
        elif metrics.avg_response_time_ms > self.thresholds["response_time_warning"]:
            await self._create_or_update_alert(
                alert_id + "_response_time",
                AlertLevel.WARNING,
                f"Elevated response time on {endpoint_key}",
                f"Average response time is {metrics.avg_response_time_ms:.1f}ms (threshold: {self.thresholds['response_time_warning']}ms)",
                "api",
                {"endpoint": endpoint_key, "response_time": metrics.avg_response_time_ms}
            )
        else:
            await self._resolve_alert(alert_id + "_response_time")

    async def _check_system_alerts(self, health: SystemHealth) -> None:
        """Check for system-level alerts."""

        # CPU alerts
        if health.cpu_usage_percentage > self.thresholds["cpu_critical"]:
            await self._create_or_update_alert(
                "system_cpu",
                AlertLevel.CRITICAL,
                "Critical CPU usage",
                f"CPU usage is {health.cpu_usage_percentage:.1f}% (threshold: {self.thresholds['cpu_critical']}%)",
                "system",
                {"cpu_usage": health.cpu_usage_percentage}
            )
        elif health.cpu_usage_percentage > self.thresholds["cpu_warning"]:
            await self._create_or_update_alert(
                "system_cpu",
                AlertLevel.WARNING,
                "High CPU usage",
                f"CPU usage is {health.cpu_usage_percentage:.1f}% (threshold: {self.thresholds['cpu_warning']}%)",
                "system",
                {"cpu_usage": health.cpu_usage_percentage}
            )
        else:
            await self._resolve_alert("system_cpu")

        # Memory alerts
        if health.memory_usage_percentage > self.thresholds["memory_critical"]:
            await self._create_or_update_alert(
                "system_memory",
                AlertLevel.CRITICAL,
                "Critical memory usage",
                f"Memory usage is {health.memory_usage_percentage:.1f}% (threshold: {self.thresholds['memory_critical']}%)",
                "system",
                {"memory_usage": health.memory_usage_percentage}
            )
        elif health.memory_usage_percentage > self.thresholds["memory_warning"]:
            await self._create_or_update_alert(
                "system_memory",
                AlertLevel.WARNING,
                "High memory usage",
                f"Memory usage is {health.memory_usage_percentage:.1f}% (threshold: {self.thresholds['memory_warning']}%)",
                "system",
                {"memory_usage": health.memory_usage_percentage}
            )
        else:
            await self._resolve_alert("system_memory")

        # Disk alerts
        if health.disk_usage_percentage > self.thresholds["disk_critical"]:
            await self._create_or_update_alert(
                "system_disk",
                AlertLevel.CRITICAL,
                "Critical disk usage",
                f"Disk usage is {health.disk_usage_percentage:.1f}% (threshold: {self.thresholds['disk_critical']}%)",
                "system",
                {"disk_usage": health.disk_usage_percentage}
            )
        elif health.disk_usage_percentage > self.thresholds["disk_warning"]:
            await self._create_or_update_alert(
                "system_disk",
                AlertLevel.WARNING,
                "High disk usage",
                f"Disk usage is {health.disk_usage_percentage:.1f}% (threshold: {self.thresholds['disk_warning']}%)",
                "system",
                {"disk_usage": health.disk_usage_percentage}
            )
        else:
            await self._resolve_alert("system_disk")

    async def _create_or_update_alert(self, alert_id: str, level: AlertLevel,
                                    title: str, description: str, component: str,
                                    metrics: dict[str, Any]) -> None:
        """Create new alert or update existing one."""

        if alert_id in self.active_alerts:
            # Update existing alert
            alert = self.active_alerts[alert_id]
            alert.description = description
            alert.metrics = metrics
            alert.escalation_count += 1

            # Escalate if needed
            if alert.escalation_count > 5 and level == AlertLevel.WARNING:
                alert.level = AlertLevel.ERROR
                alert.escalation_level += 1
            elif alert.escalation_count > 10 and level == AlertLevel.ERROR:
                alert.level = AlertLevel.CRITICAL
                alert.escalation_level += 1
        else:
            # Create new alert
            alert = Alert(
                alert_id=alert_id,
                level=level,
                title=title,
                description=description,
                component=component,
                metrics=metrics
            )
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)

            logger.warning(f"New alert created: {title} - {description}")

    async def _resolve_alert(self, alert_id: str) -> None:
        """Resolve an active alert."""

        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.is_active = False
            alert.resolved_at = datetime.utcnow()

            logger.info(f"Alert resolved: {alert.title}")

            del self.active_alerts[alert_id]

    async def get_endpoint_metrics(self, endpoint: str | None = None) -> dict[str, Any]:
        """Get metrics for endpoints."""

        if endpoint:
            # Return specific endpoint metrics
            matching_endpoints = {k: v for k, v in self.endpoint_metrics.items()
                                if endpoint in k}
            return {"endpoints": matching_endpoints}
        else:
            # Return all endpoint metrics
            return {"endpoints": self.endpoint_metrics}

    async def get_alerts(self, active_only: bool = True) -> list[Alert]:
        """Get current alerts."""

        if active_only:
            return list(self.active_alerts.values())
        else:
            return self.alert_history

    async def get_system_metrics_history(self, hours: int = 24) -> list[SystemHealth]:
        """Get system metrics history."""

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [h for h in self.system_metrics_history if h.timestamp > cutoff]

    async def start_monitoring(self) -> None:
        """Start background monitoring tasks."""

        async def monitoring_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # Monitor every minute
                    await self.get_health_status()  # This triggers alert checking
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Monitoring loop error: {e}")

        self._monitoring_task = asyncio.create_task(monitoring_loop())
        logger.info("Started enterprise monitoring")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Stopped enterprise monitoring")

    async def update_thresholds(self, new_thresholds: dict[str, float]) -> None:
        """Update monitoring thresholds."""

        self.thresholds.copy()
        self.thresholds.update(new_thresholds)

        logger.info(f"Updated monitoring thresholds: {new_thresholds}")

        # Log the change
        # In a real implementation, you might want to audit this change
