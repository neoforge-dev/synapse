"""Resource isolation and management for multi-tenant architecture.

This module provides:
- CPU and memory limits per tenant
- Dynamic resource scaling based on usage patterns
- Quality of Service (QoS) guarantees per tenant
- Resource monitoring and alerting
- Tenant-specific performance optimization
"""

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil

from .tenant_manager import TenantContext, get_current_tenant

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of resources that can be managed."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_CONNECTIONS = "database_connections"
    API_CALLS = "api_calls"
    CONCURRENT_REQUESTS = "concurrent_requests"


class QoSLevel(str, Enum):
    """Quality of Service levels for tenants."""
    PREMIUM = "premium"     # Guaranteed resources, highest priority
    STANDARD = "standard"   # Best effort with reasonable limits
    BASIC = "basic"        # Basic service with strict limits
    TRIAL = "trial"        # Highly restricted for trial users


@dataclass
class ResourceLimits:
    """Resource limits configuration for a tenant."""
    tenant_id: str
    qos_level: QoSLevel

    # CPU limits (percentage of system CPU)
    cpu_limit_percent: float = 10.0
    cpu_burst_limit_percent: float = 20.0

    # Memory limits (MB)
    memory_limit_mb: int = 512
    memory_burst_limit_mb: int = 1024

    # I/O limits
    disk_read_mb_per_sec: float = 50.0
    disk_write_mb_per_sec: float = 25.0
    network_mb_per_sec: float = 100.0

    # Database connection limits
    max_db_connections: int = 5
    max_db_query_time_sec: int = 30

    # API and concurrency limits
    max_api_calls_per_hour: int = 1000
    max_concurrent_requests: int = 10

    # Monitoring thresholds
    warning_threshold_percent: float = 80.0
    alert_threshold_percent: float = 95.0


@dataclass
class ResourceUsage:
    """Current resource usage for a tenant."""
    tenant_id: str
    timestamp: datetime

    # CPU usage
    cpu_percent: float = 0.0
    cpu_time_seconds: float = 0.0

    # Memory usage
    memory_mb: float = 0.0
    memory_percent: float = 0.0

    # I/O usage
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0

    # Database usage
    active_db_connections: int = 0
    db_queries_per_hour: int = 0

    # API usage
    api_calls_per_hour: int = 0
    concurrent_requests: int = 0


@dataclass
class ResourceAlert:
    """Resource alert for tenant."""
    tenant_id: str
    resource_type: ResourceType
    severity: str  # warning, critical
    current_usage: float
    limit: float
    timestamp: datetime
    message: str


class ResourceMonitor:
    """Resource monitoring system for tenants."""

    def __init__(self, monitoring_interval: float = 30.0):
        """Initialize resource monitor."""
        self.monitoring_interval = monitoring_interval
        self._tenant_usage: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._tenant_limits: dict[str, ResourceLimits] = {}
        self._active_alerts: dict[str, list[ResourceAlert]] = defaultdict(list)
        self._monitoring_task: asyncio.Task | None = None
        self._is_monitoring = False

        logger.info(f"ResourceMonitor initialized with {monitoring_interval}s interval")

    def start_monitoring(self) -> None:
        """Start resource monitoring task."""
        if not self._is_monitoring:
            self._is_monitoring = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Resource monitoring started")

    def stop_monitoring(self) -> None:
        """Stop resource monitoring task."""
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            logger.info("Resource monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                await self._collect_system_metrics()
                await self._check_resource_limits()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _collect_system_metrics(self) -> None:
        """Collect system-wide resource metrics."""
        system_cpu = psutil.cpu_percent(interval=1)
        system_memory = psutil.virtual_memory()
        system_disk = psutil.disk_io_counters()
        system_network = psutil.net_io_counters()

        # In a real implementation, we would need to track per-tenant resource usage
        # This would require process tracking, cgroup integration, or similar mechanisms

        for tenant_id in self._tenant_limits:
            # Placeholder: estimate tenant usage based on activity
            usage = await self._estimate_tenant_usage(tenant_id, {
                'system_cpu': system_cpu,
                'system_memory': system_memory,
                'system_disk': system_disk,
                'system_network': system_network
            })

            self._tenant_usage[tenant_id].append(usage)

    async def _estimate_tenant_usage(self, tenant_id: str, system_metrics: dict) -> ResourceUsage:
        """Estimate resource usage for a specific tenant."""
        # Simplified estimation - in production would use proper process tracking
        return ResourceUsage(
            tenant_id=tenant_id,
            timestamp=datetime.utcnow(),
            cpu_percent=system_metrics['system_cpu'] * 0.1,  # Estimate 10% of system usage
            memory_mb=system_metrics['system_memory'].used / (1024 * 1024) * 0.05,  # 5% estimate
            disk_read_mb=0.0,
            disk_write_mb=0.0,
            network_sent_mb=0.0,
            network_recv_mb=0.0,
            active_db_connections=0,
            db_queries_per_hour=0,
            api_calls_per_hour=0,
            concurrent_requests=0
        )

    async def _check_resource_limits(self) -> None:
        """Check if any tenants are exceeding resource limits."""
        for tenant_id, limits in self._tenant_limits.items():
            recent_usage = self._get_recent_usage(tenant_id)
            if recent_usage:
                await self._check_tenant_limits(limits, recent_usage)

    def _get_recent_usage(self, tenant_id: str) -> ResourceUsage | None:
        """Get most recent usage data for tenant."""
        usage_history = self._tenant_usage.get(tenant_id)
        return usage_history[-1] if usage_history else None

    async def _check_tenant_limits(self, limits: ResourceLimits, usage: ResourceUsage) -> None:
        """Check if tenant is exceeding limits and generate alerts."""
        alerts = []

        # Check CPU limit
        if usage.cpu_percent > limits.cpu_limit_percent * limits.alert_threshold_percent / 100:
            alerts.append(ResourceAlert(
                tenant_id=limits.tenant_id,
                resource_type=ResourceType.CPU,
                severity="critical" if usage.cpu_percent > limits.cpu_limit_percent else "warning",
                current_usage=usage.cpu_percent,
                limit=limits.cpu_limit_percent,
                timestamp=datetime.utcnow(),
                message=f"CPU usage {usage.cpu_percent:.1f}% exceeds limit {limits.cpu_limit_percent:.1f}%"
            ))

        # Check memory limit
        if usage.memory_mb > limits.memory_limit_mb * limits.alert_threshold_percent / 100:
            alerts.append(ResourceAlert(
                tenant_id=limits.tenant_id,
                resource_type=ResourceType.MEMORY,
                severity="critical" if usage.memory_mb > limits.memory_limit_mb else "warning",
                current_usage=usage.memory_mb,
                limit=limits.memory_limit_mb,
                timestamp=datetime.utcnow(),
                message=f"Memory usage {usage.memory_mb:.1f}MB exceeds limit {limits.memory_limit_mb}MB"
            ))

        # Store alerts
        if alerts:
            self._active_alerts[limits.tenant_id].extend(alerts)
            for alert in alerts:
                logger.warning(f"Resource alert for {alert.tenant_id}: {alert.message}")

    def set_tenant_limits(self, tenant_id: str, limits: ResourceLimits) -> None:
        """Set resource limits for a tenant."""
        self._tenant_limits[tenant_id] = limits
        logger.info(f"Set resource limits for tenant {tenant_id}: QoS {limits.qos_level}")

    def get_tenant_usage(self, tenant_id: str, hours: int = 1) -> list[ResourceUsage]:
        """Get usage history for tenant."""
        usage_history = self._tenant_usage.get(tenant_id, [])
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return [usage for usage in usage_history if usage.timestamp > cutoff_time]

    def get_tenant_alerts(self, tenant_id: str, severity: str | None = None) -> list[ResourceAlert]:
        """Get active alerts for tenant."""
        alerts = self._active_alerts.get(tenant_id, [])

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        return alerts

    def clear_tenant_alerts(self, tenant_id: str) -> None:
        """Clear all alerts for tenant."""
        self._active_alerts[tenant_id] = []


class ResourceThrottler:
    """Resource throttling system to enforce limits."""

    def __init__(self):
        """Initialize resource throttler."""
        self._tenant_counters: dict[str, dict[str, Any]] = defaultdict(dict)
        self._rate_limiters: dict[str, dict[str, Any]] = defaultdict(dict)

        logger.info("ResourceThrottler initialized")

    async def check_resource_availability(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        requested_amount: float = 1.0
    ) -> tuple[bool, str | None]:
        """Check if tenant can use requested resources."""
        # Get current tenant context
        tenant_context = get_current_tenant()
        if not tenant_context or tenant_context.tenant_id != tenant_id:
            return False, "Invalid tenant context"

        # Check resource-specific limits
        if resource_type == ResourceType.API_CALLS:
            return await self._check_api_rate_limit(tenant_id, requested_amount)
        elif resource_type == ResourceType.CONCURRENT_REQUESTS:
            return await self._check_concurrent_requests(tenant_id, requested_amount)
        elif resource_type == ResourceType.DATABASE_CONNECTIONS:
            return await self._check_db_connections(tenant_id, requested_amount)

        # Default allow for other resource types
        return True, None

    async def _check_api_rate_limit(self, tenant_id: str, calls: float) -> tuple[bool, str | None]:
        """Check API rate limiting for tenant."""
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        # Initialize or get counter for current hour
        if 'api_calls' not in self._tenant_counters[tenant_id]:
            self._tenant_counters[tenant_id]['api_calls'] = {}

        hourly_calls = self._tenant_counters[tenant_id]['api_calls']
        current_calls = hourly_calls.get(current_hour, 0)

        # Get tenant resource limits (would come from configuration)
        max_calls_per_hour = 1000  # Default limit

        if current_calls + calls > max_calls_per_hour:
            return False, f"API rate limit exceeded: {current_calls + calls}/{max_calls_per_hour} calls per hour"

        # Update counter
        hourly_calls[current_hour] = current_calls + calls

        # Clean old counters
        cutoff_time = current_hour - timedelta(hours=1)
        hourly_calls = {k: v for k, v in hourly_calls.items() if k >= cutoff_time}
        self._tenant_counters[tenant_id]['api_calls'] = hourly_calls

        return True, None

    async def _check_concurrent_requests(self, tenant_id: str, requests: float) -> tuple[bool, str | None]:
        """Check concurrent request limits for tenant."""
        current_requests = self._tenant_counters[tenant_id].get('concurrent_requests', 0)
        max_concurrent = 10  # Default limit

        if current_requests + requests > max_concurrent:
            return False, f"Concurrent request limit exceeded: {current_requests + requests}/{max_concurrent}"

        return True, None

    async def _check_db_connections(self, tenant_id: str, connections: float) -> tuple[bool, str | None]:
        """Check database connection limits for tenant."""
        current_connections = self._tenant_counters[tenant_id].get('db_connections', 0)
        max_connections = 5  # Default limit

        if current_connections + connections > max_connections:
            return False, f"Database connection limit exceeded: {current_connections + connections}/{max_connections}"

        return True, None

    async def acquire_resource(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        amount: float = 1.0
    ) -> bool:
        """Acquire resource allocation for tenant."""
        available, error = await self.check_resource_availability(tenant_id, resource_type, amount)

        if not available:
            logger.warning(f"Resource acquisition failed for {tenant_id}: {error}")
            return False

        # Update resource counters
        if resource_type == ResourceType.CONCURRENT_REQUESTS:
            current = self._tenant_counters[tenant_id].get('concurrent_requests', 0)
            self._tenant_counters[tenant_id]['concurrent_requests'] = current + amount
        elif resource_type == ResourceType.DATABASE_CONNECTIONS:
            current = self._tenant_counters[tenant_id].get('db_connections', 0)
            self._tenant_counters[tenant_id]['db_connections'] = current + amount

        return True

    async def release_resource(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        amount: float = 1.0
    ) -> None:
        """Release resource allocation for tenant."""
        if resource_type == ResourceType.CONCURRENT_REQUESTS:
            current = self._tenant_counters[tenant_id].get('concurrent_requests', 0)
            self._tenant_counters[tenant_id]['concurrent_requests'] = max(0, current - amount)
        elif resource_type == ResourceType.DATABASE_CONNECTIONS:
            current = self._tenant_counters[tenant_id].get('db_connections', 0)
            self._tenant_counters[tenant_id]['db_connections'] = max(0, current - amount)


class TenantResourceManager:
    """High-level tenant resource management."""

    def __init__(self):
        """Initialize tenant resource manager."""
        self.monitor = ResourceMonitor()
        self.throttler = ResourceThrottler()
        self._tenant_configs: dict[str, ResourceLimits] = {}

        # Default resource limits by QoS level
        self._default_limits = {
            QoSLevel.PREMIUM: ResourceLimits(
                tenant_id="", qos_level=QoSLevel.PREMIUM,
                cpu_limit_percent=25.0, cpu_burst_limit_percent=50.0,
                memory_limit_mb=2048, memory_burst_limit_mb=4096,
                max_api_calls_per_hour=5000, max_concurrent_requests=50,
                max_db_connections=20
            ),
            QoSLevel.STANDARD: ResourceLimits(
                tenant_id="", qos_level=QoSLevel.STANDARD,
                cpu_limit_percent=15.0, cpu_burst_limit_percent=30.0,
                memory_limit_mb=1024, memory_burst_limit_mb=2048,
                max_api_calls_per_hour=2000, max_concurrent_requests=20,
                max_db_connections=10
            ),
            QoSLevel.BASIC: ResourceLimits(
                tenant_id="", qos_level=QoSLevel.BASIC,
                cpu_limit_percent=10.0, cpu_burst_limit_percent=20.0,
                memory_limit_mb=512, memory_burst_limit_mb=1024,
                max_api_calls_per_hour=1000, max_concurrent_requests=10,
                max_db_connections=5
            ),
            QoSLevel.TRIAL: ResourceLimits(
                tenant_id="", qos_level=QoSLevel.TRIAL,
                cpu_limit_percent=5.0, cpu_burst_limit_percent=10.0,
                memory_limit_mb=256, memory_burst_limit_mb=512,
                max_api_calls_per_hour=500, max_concurrent_requests=5,
                max_db_connections=2
            )
        }

        logger.info("TenantResourceManager initialized")

    def start(self) -> None:
        """Start resource management."""
        self.monitor.start_monitoring()
        logger.info("TenantResourceManager started")

    def stop(self) -> None:
        """Stop resource management."""
        self.monitor.stop_monitoring()
        logger.info("TenantResourceManager stopped")

    def configure_tenant_resources(
        self,
        tenant_context: TenantContext,
        custom_limits: ResourceLimits | None = None
    ) -> None:
        """Configure resource limits for tenant."""
        if custom_limits:
            limits = custom_limits
        else:
            # Determine QoS level based on tenant type
            if tenant_context.is_enterprise:
                qos_level = QoSLevel.PREMIUM
            elif tenant_context.is_consultation:
                qos_level = QoSLevel.STANDARD  # Protect Epic 7 performance
            else:
                qos_level = QoSLevel.BASIC

            # Create limits from template
            template = self._default_limits[qos_level]
            limits = ResourceLimits(
                tenant_id=tenant_context.tenant_id,
                qos_level=qos_level,
                cpu_limit_percent=template.cpu_limit_percent,
                cpu_burst_limit_percent=template.cpu_burst_limit_percent,
                memory_limit_mb=template.memory_limit_mb,
                memory_burst_limit_mb=template.memory_burst_limit_mb,
                max_api_calls_per_hour=template.max_api_calls_per_hour,
                max_concurrent_requests=template.max_concurrent_requests,
                max_db_connections=template.max_db_connections
            )

        self._tenant_configs[tenant_context.tenant_id] = limits
        self.monitor.set_tenant_limits(tenant_context.tenant_id, limits)

        logger.info(f"Configured resources for tenant {tenant_context.tenant_id} with QoS {limits.qos_level}")

    async def check_resource_availability(
        self,
        resource_type: ResourceType,
        amount: float = 1.0,
        tenant_context: TenantContext | None = None
    ) -> tuple[bool, str | None]:
        """Check if tenant can use requested resources."""
        if not tenant_context:
            tenant_context = get_current_tenant()
            if not tenant_context:
                return False, "No tenant context available"

        return await self.throttler.check_resource_availability(
            tenant_context.tenant_id, resource_type, amount
        )

    async def acquire_resource(
        self,
        resource_type: ResourceType,
        amount: float = 1.0,
        tenant_context: TenantContext | None = None
    ) -> bool:
        """Acquire resource for tenant."""
        if not tenant_context:
            tenant_context = get_current_tenant()
            if not tenant_context:
                return False

        return await self.throttler.acquire_resource(
            tenant_context.tenant_id, resource_type, amount
        )

    async def release_resource(
        self,
        resource_type: ResourceType,
        amount: float = 1.0,
        tenant_context: TenantContext | None = None
    ) -> None:
        """Release resource for tenant."""
        if not tenant_context:
            tenant_context = get_current_tenant()
            if not tenant_context:
                return

        await self.throttler.release_resource(
            tenant_context.tenant_id, resource_type, amount
        )

    def get_tenant_usage(self, tenant_id: str, hours: int = 1) -> list[ResourceUsage]:
        """Get usage history for tenant."""
        return self.monitor.get_tenant_usage(tenant_id, hours)

    def get_tenant_alerts(self, tenant_id: str) -> list[ResourceAlert]:
        """Get active alerts for tenant."""
        return self.monitor.get_tenant_alerts(tenant_id)

    def get_tenant_limits(self, tenant_id: str) -> ResourceLimits | None:
        """Get resource limits for tenant."""
        return self._tenant_configs.get(tenant_id)


# Global resource manager instance
_resource_manager: TenantResourceManager | None = None


def get_resource_manager() -> TenantResourceManager:
    """Get global resource manager instance."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = TenantResourceManager()
    return _resource_manager


# Resource management context manager
class ResourceContext:
    """Context manager for resource acquisition/release."""

    def __init__(self, resource_type: ResourceType, amount: float = 1.0):
        """Initialize resource context."""
        self.resource_type = resource_type
        self.amount = amount
        self.acquired = False

    async def __aenter__(self):
        """Acquire resource on entering context."""
        manager = get_resource_manager()
        self.acquired = await manager.acquire_resource(self.resource_type, self.amount)

        if not self.acquired:
            raise ResourceError(f"Failed to acquire {self.resource_type} resource")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release resource on exiting context."""
        if self.acquired:
            manager = get_resource_manager()
            await manager.release_resource(self.resource_type, self.amount)


class ResourceError(Exception):
    """Exception raised when resource limits are exceeded."""
    pass
