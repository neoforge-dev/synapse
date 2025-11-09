"""
Advanced Performance Monitoring and Alerting System

This module provides comprehensive monitoring capabilities for the GraphRAG system:
- Real-time performance metrics collection
- Health status monitoring and alerting
- Resource utilization tracking
- Business intelligence metrics
- Custom alerts and thresholds
- Dashboard-ready metric endpoints

Supports both Prometheus export and structured logging for enterprise monitoring.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Optional Prometheus support
try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Summary,
        generate_latest,
    )
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    CollectorRegistry = None


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MetricType(Enum):
    """Types of metrics supported."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """Definition of a metric with metadata."""
    name: str
    description: str
    metric_type: MetricType
    labels: list[str] = field(default_factory=list)
    buckets: list[float] | None = None  # For histograms
    unit: str = ""
    namespace: str = "synapse"


@dataclass
class Alert:
    """Alert definition with conditions and actions."""
    name: str
    description: str
    condition: Callable[[dict[str, Any]], bool]
    severity: AlertSeverity
    threshold: float | None = None
    duration_seconds: float = 60.0  # Alert if condition true for this duration
    cooldown_seconds: float = 300.0  # Minimum time between alerts
    last_triggered: float | None = None
    active: bool = True


@dataclass
class MetricData:
    """Data point for a metric."""
    name: str
    value: int | float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    unit: str = ""


class MetricsCollector:
    """
    Comprehensive metrics collection and monitoring system.

    Features:
    - Real-time metric collection
    - Alerting based on thresholds
    - Prometheus export
    - Health monitoring
    - Performance tracking
    """

    def __init__(
        self,
        enable_prometheus: bool = True,
        enable_alerts: bool = True,
        alert_check_interval: float = 30.0,
        max_history_size: int = 1000,
    ):
        """
        Initialize the metrics collector.

        Args:
            enable_prometheus: Whether to enable Prometheus metrics export
            enable_alerts: Whether to enable alerting system
            alert_check_interval: How often to check alert conditions (seconds)
            max_history_size: Maximum number of historical data points to keep
        """
        self.enable_prometheus = enable_prometheus and HAS_PROMETHEUS
        self.enable_alerts = enable_alerts
        self.alert_check_interval = alert_check_interval
        self.max_history_size = max_history_size

        # Metric storage
        self._metrics: dict[str, Any] = {}
        self._metric_definitions: dict[str, MetricDefinition] = {}
        self._metric_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))

        # Alerting
        self._alerts: dict[str, Alert] = {}
        self._alert_history: list[dict[str, Any]] = []
        self._alert_task: asyncio.Task | None = None

        # Prometheus registry
        self._prometheus_registry: CollectorRegistry | None = None
        if self.enable_prometheus:
            self._prometheus_registry = CollectorRegistry()

        # System metrics
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._last_health_check = time.time()

        # Performance tracking
        self._performance_metrics = {
            "request_latency": deque(maxlen=1000),
            "vector_search_time": deque(maxlen=1000),
            "graph_query_time": deque(maxlen=1000),
            "ingestion_rate": deque(maxlen=100),
        }

        self._initialize_core_metrics()
        self._initialize_core_alerts()

        logger.info(f"MetricsCollector initialized (prometheus={self.enable_prometheus}, alerts={self.enable_alerts})")

    def _initialize_core_metrics(self):
        """Initialize core system metrics."""
        core_metrics = [
            MetricDefinition(
                name="system_uptime_seconds",
                description="System uptime in seconds",
                metric_type=MetricType.GAUGE,
                unit="seconds"
            ),
            MetricDefinition(
                name="http_requests_total",
                description="Total HTTP requests",
                metric_type=MetricType.COUNTER,
                labels=["method", "endpoint", "status_code"]
            ),
            MetricDefinition(
                name="http_request_duration_seconds",
                description="HTTP request duration",
                metric_type=MetricType.HISTOGRAM,
                labels=["method", "endpoint"],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
                unit="seconds"
            ),
            MetricDefinition(
                name="vector_search_duration_seconds",
                description="Vector search operation duration",
                metric_type=MetricType.HISTOGRAM,
                labels=["store_type"],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
                unit="seconds"
            ),
            MetricDefinition(
                name="graph_query_duration_seconds",
                description="Graph query operation duration",
                metric_type=MetricType.HISTOGRAM,
                labels=["query_type"],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
                unit="seconds"
            ),
            MetricDefinition(
                name="ingestion_documents_total",
                description="Total documents processed for ingestion",
                metric_type=MetricType.COUNTER,
                labels=["status"]
            ),
            MetricDefinition(
                name="vector_store_size",
                description="Number of vectors in the vector store",
                metric_type=MetricType.GAUGE,
                unit="vectors"
            ),
            MetricDefinition(
                name="graph_nodes_total",
                description="Total nodes in the knowledge graph",
                metric_type=MetricType.GAUGE,
                unit="nodes"
            ),
            MetricDefinition(
                name="memory_usage_bytes",
                description="Memory usage in bytes",
                metric_type=MetricType.GAUGE,
                labels=["component"],
                unit="bytes"
            ),
            MetricDefinition(
                name="error_rate",
                description="Error rate percentage",
                metric_type=MetricType.GAUGE,
                unit="percentage"
            ),
        ]

        for metric_def in core_metrics:
            self.register_metric(metric_def)

    def _initialize_core_alerts(self):
        """Initialize core system alerts."""
        if not self.enable_alerts:
            return

        core_alerts = [
            Alert(
                name="high_error_rate",
                description="Error rate exceeds threshold",
                condition=lambda metrics: metrics.get("error_rate", 0) > 5.0,
                severity=AlertSeverity.HIGH,
                threshold=5.0,
                duration_seconds=60.0
            ),
            Alert(
                name="slow_vector_search",
                description="Vector search latency too high",
                condition=lambda metrics: self._get_average_latency("vector_search_time") > 1.0,
                severity=AlertSeverity.MEDIUM,
                threshold=1.0,
                duration_seconds=120.0
            ),
            Alert(
                name="slow_graph_queries",
                description="Graph query latency too high",
                condition=lambda metrics: self._get_average_latency("graph_query_time") > 5.0,
                severity=AlertSeverity.MEDIUM,
                threshold=5.0,
                duration_seconds=120.0
            ),
            Alert(
                name="high_request_latency",
                description="HTTP request latency too high",
                condition=lambda metrics: self._get_average_latency("request_latency") > 10.0,
                severity=AlertSeverity.HIGH,
                threshold=10.0,
                duration_seconds=180.0
            ),
        ]

        for alert in core_alerts:
            self.register_alert(alert)

    def register_metric(self, metric_def: MetricDefinition):
        """Register a metric definition."""
        self._metric_definitions[metric_def.name] = metric_def

        if self.enable_prometheus and self._prometheus_registry:
            self._create_prometheus_metric(metric_def)

        logger.debug(f"Registered metric: {metric_def.name} ({metric_def.metric_type.value})")

    def register_alert(self, alert: Alert):
        """Register an alert definition."""
        self._alerts[alert.name] = alert
        logger.debug(f"Registered alert: {alert.name} ({alert.severity.value})")

    def _create_prometheus_metric(self, metric_def: MetricDefinition):
        """Create a Prometheus metric from definition."""
        if not (self.enable_prometheus and self._prometheus_registry):
            return

        kwargs = {
            "name": f"{metric_def.namespace}_{metric_def.name}",
            "documentation": metric_def.description,
            "labelnames": metric_def.labels,
            "registry": self._prometheus_registry,
        }

        if metric_def.metric_type == MetricType.COUNTER:
            self._metrics[metric_def.name] = Counter(**kwargs)
        elif metric_def.metric_type == MetricType.GAUGE:
            self._metrics[metric_def.name] = Gauge(**kwargs)
        elif metric_def.metric_type == MetricType.HISTOGRAM:
            if metric_def.buckets:
                kwargs["buckets"] = metric_def.buckets
            self._metrics[metric_def.name] = Histogram(**kwargs)
        elif metric_def.metric_type == MetricType.SUMMARY:
            self._metrics[metric_def.name] = Summary(**kwargs)

    def record_metric(
        self,
        name: str,
        value: int | float,
        labels: dict[str, str] | None = None,
        timestamp: float | None = None
    ):
        """Record a metric value."""
        if name not in self._metric_definitions:
            logger.warning(f"Recording metric for undefined metric: {name}")
            return

        labels = labels or {}
        timestamp = timestamp or time.time()

        # Store in history
        metric_data = MetricData(
            name=name,
            value=value,
            labels=labels,
            timestamp=timestamp
        )
        self._metric_history[name].append(metric_data)

        # Update Prometheus metric if available
        if self.enable_prometheus and name in self._metrics:
            prometheus_metric = self._metrics[name]
            metric_def = self._metric_definitions[name]

            try:
                if metric_def.metric_type in [MetricType.COUNTER]:
                    if labels:
                        prometheus_metric.labels(**labels).inc(value)
                    else:
                        prometheus_metric.inc(value)
                elif metric_def.metric_type == MetricType.GAUGE:
                    if labels:
                        prometheus_metric.labels(**labels).set(value)
                    else:
                        prometheus_metric.set(value)
                elif metric_def.metric_type in [MetricType.HISTOGRAM, MetricType.SUMMARY]:
                    if labels:
                        prometheus_metric.labels(**labels).observe(value)
                    else:
                        prometheus_metric.observe(value)
            except Exception as e:
                logger.error(f"Error recording Prometheus metric {name}: {e}")

    def increment_counter(self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0):
        """Increment a counter metric."""
        self.record_metric(name, amount, labels)

    def set_gauge(self, name: str, value: int | float, labels: dict[str, str] | None = None):
        """Set a gauge metric value."""
        self.record_metric(name, value, labels)

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None):
        """Observe a value for a histogram metric."""
        self.record_metric(name, value, labels)

    @asynccontextmanager
    async def time_operation(self, metric_name: str, labels: dict[str, str] | None = None):
        """Context manager to time an operation and record the duration."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe_histogram(metric_name, duration, labels)

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        self.increment_counter(
            "http_requests_total",
            labels={"method": method, "endpoint": endpoint, "status_code": str(status_code)}
        )
        self.observe_histogram(
            "http_request_duration_seconds",
            duration,
            labels={"method": method, "endpoint": endpoint}
        )

        # Track performance metrics
        self._performance_metrics["request_latency"].append(duration)
        self._request_count += 1

        if status_code >= 400:
            self._error_count += 1

    def record_vector_search(self, duration: float, store_type: str = "unknown"):
        """Record vector search performance."""
        self.observe_histogram(
            "vector_search_duration_seconds",
            duration,
            labels={"store_type": store_type}
        )
        self._performance_metrics["vector_search_time"].append(duration)

    def record_graph_query(self, duration: float, query_type: str = "unknown"):
        """Record graph query performance."""
        self.observe_histogram(
            "graph_query_duration_seconds",
            duration,
            labels={"query_type": query_type}
        )
        self._performance_metrics["graph_query_time"].append(duration)

    def record_ingestion(self, document_count: int, success: bool, duration: float):
        """Record document ingestion metrics."""
        status = "success" if success else "error"
        self.increment_counter(
            "ingestion_documents_total",
            labels={"status": status},
            amount=document_count
        )

        if success and duration > 0:
            rate = document_count / duration
            self._performance_metrics["ingestion_rate"].append(rate)

    def update_system_metrics(self):
        """Update system-level metrics."""
        current_time = time.time()

        # System uptime
        uptime = current_time - self._start_time
        self.set_gauge("system_uptime_seconds", uptime)

        # Error rate
        if self._request_count > 0:
            error_rate = (self._error_count / self._request_count) * 100
            self.set_gauge("error_rate", error_rate)

    def _get_average_latency(self, metric_name: str, window_seconds: float = 300.0) -> float:
        """Get average latency for a metric over a time window."""
        if metric_name not in self._performance_metrics:
            return 0.0

        data = self._performance_metrics[metric_name]
        if not data:
            return 0.0

        # Simple average for now; could implement time-windowed average
        return sum(data) / len(data)

    async def start_monitoring(self):
        """Start the monitoring and alerting system."""
        if self.enable_alerts and not self._alert_task:
            self._alert_task = asyncio.create_task(self._alert_loop())
            logger.info("Started monitoring and alerting system")

    async def stop_monitoring(self):
        """Stop the monitoring system."""
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
            self._alert_task = None
            logger.info("Stopped monitoring system")

    async def _alert_loop(self):
        """Main alerting loop."""
        while True:
            try:
                await asyncio.sleep(self.alert_check_interval)
                await self._check_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert loop: {e}", exc_info=True)

    async def _check_alerts(self):
        """Check all alert conditions."""
        current_time = time.time()
        current_metrics = self._get_current_metrics()

        for alert_name, alert in self._alerts.items():
            if not alert.active:
                continue

            try:
                # Check cooldown
                if (alert.last_triggered and
                    current_time - alert.last_triggered < alert.cooldown_seconds):
                    continue

                # Evaluate condition
                if alert.condition(current_metrics):
                    await self._trigger_alert(alert, current_metrics)

            except Exception as e:
                logger.error(f"Error checking alert {alert_name}: {e}", exc_info=True)

    def _get_current_metrics(self) -> dict[str, Any]:
        """Get current metric values for alert evaluation."""
        metrics = {}

        # Add computed metrics
        metrics["error_rate"] = (self._error_count / max(self._request_count, 1)) * 100
        metrics["uptime"] = time.time() - self._start_time

        # Add latest values from history
        for metric_name, history in self._metric_history.items():
            if history:
                metrics[metric_name] = history[-1].value

        return metrics

    async def _trigger_alert(self, alert: Alert, current_metrics: dict[str, Any]):
        """Trigger an alert."""
        current_time = time.time()
        alert.last_triggered = current_time

        alert_event = {
            "alert_name": alert.name,
            "description": alert.description,
            "severity": alert.severity.value,
            "timestamp": current_time,
            "metrics": current_metrics.copy(),
            "threshold": alert.threshold,
        }

        self._alert_history.append(alert_event)

        # Log the alert
        log_level = logging.CRITICAL if alert.severity == AlertSeverity.CRITICAL else logging.WARNING
        logger.log(
            log_level,
            f"ALERT TRIGGERED: {alert.name} ({alert.severity.value}) - {alert.description}"
        )

        # Could add webhook notifications, email alerts, etc. here
        await self._send_alert_notification(alert_event)

    async def _send_alert_notification(self, alert_event: dict[str, Any]):
        """Send alert notification (placeholder for actual notification system)."""
        # Implement actual notification logic here:
        # - Webhook calls
        # - Email notifications
        # - Slack/Teams integration
        # - PagerDuty integration

        # For now, just structured logging
        logger.warning(
            "Alert notification",
            extra={
                "alert": alert_event,
                "type": "alert_notification"
            }
        )

    def get_metrics_export(self) -> str | None:
        """Export metrics in Prometheus format."""
        if not (self.enable_prometheus and self._prometheus_registry):
            return None

        try:
            return generate_latest(self._prometheus_registry).decode('utf-8')
        except Exception as e:
            logger.error(f"Error generating metrics export: {e}")
            return None

    def get_health_summary(self) -> dict[str, Any]:
        """Get comprehensive health summary."""
        current_time = time.time()
        uptime = current_time - self._start_time

        # Calculate performance metrics
        avg_request_latency = self._get_average_latency("request_latency")
        avg_vector_search = self._get_average_latency("vector_search_time")
        avg_graph_query = self._get_average_latency("graph_query_time")

        error_rate = (self._error_count / max(self._request_count, 1)) * 100

        # Recent alerts
        recent_alerts = [
            alert for alert in self._alert_history
            if current_time - alert["timestamp"] < 3600  # Last hour
        ]

        return {
            "status": "healthy" if error_rate < 5 and avg_request_latency < 5 else "degraded",
            "uptime_seconds": uptime,
            "total_requests": self._request_count,
            "error_count": self._error_count,
            "error_rate_percent": error_rate,
            "performance": {
                "avg_request_latency_ms": avg_request_latency * 1000,
                "avg_vector_search_ms": avg_vector_search * 1000,
                "avg_graph_query_ms": avg_graph_query * 1000,
            },
            "alerts": {
                "total_alerts": len(self._alert_history),
                "recent_alerts": len(recent_alerts),
                "active_alerts": len([a for a in self._alerts.values() if a.active]),
            },
            "monitoring": {
                "prometheus_enabled": self.enable_prometheus,
                "alerts_enabled": self.enable_alerts,
                "metrics_collected": len(self._metric_definitions),
            },
            "timestamp": current_time,
        }

    def get_performance_report(self) -> dict[str, Any]:
        """Get detailed performance report."""
        return {
            "request_latency": {
                "avg_ms": self._get_average_latency("request_latency") * 1000,
                "samples": len(self._performance_metrics["request_latency"]),
            },
            "vector_search": {
                "avg_ms": self._get_average_latency("vector_search_time") * 1000,
                "samples": len(self._performance_metrics["vector_search_time"]),
            },
            "graph_queries": {
                "avg_ms": self._get_average_latency("graph_query_time") * 1000,
                "samples": len(self._performance_metrics["graph_query_time"]),
            },
            "ingestion": {
                "avg_rate": (
                    sum(self._performance_metrics["ingestion_rate"]) /
                    max(len(self._performance_metrics["ingestion_rate"]), 1)
                ),
                "samples": len(self._performance_metrics["ingestion_rate"]),
            },
        }


# Global metrics collector instance
_global_metrics: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector | None:
    """Get the global metrics collector instance."""
    return _global_metrics


def initialize_metrics(
    enable_prometheus: bool = True,
    enable_alerts: bool = True,
    alert_check_interval: float = 30.0,
) -> MetricsCollector:
    """Initialize the global metrics collector."""
    global _global_metrics

    if _global_metrics is None:
        _global_metrics = MetricsCollector(
            enable_prometheus=enable_prometheus,
            enable_alerts=enable_alerts,
            alert_check_interval=alert_check_interval,
        )
        logger.info("Initialized global metrics collector")

    return _global_metrics


async def start_monitoring():
    """Start the global monitoring system."""
    if _global_metrics:
        await _global_metrics.start_monitoring()


async def stop_monitoring():
    """Stop the global monitoring system."""
    if _global_metrics:
        await _global_metrics.stop_monitoring()


# Convenience functions for common operations
def record_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    if _global_metrics:
        _global_metrics.record_request(method, endpoint, status_code, duration)


def record_vector_search(duration: float, store_type: str = "unknown"):
    """Record vector search performance."""
    if _global_metrics:
        _global_metrics.record_vector_search(duration, store_type)


def record_graph_query(duration: float, query_type: str = "unknown"):
    """Record graph query performance."""
    if _global_metrics:
        _global_metrics.record_graph_query(duration, query_type)


def record_ingestion(document_count: int, success: bool, duration: float):
    """Record document ingestion metrics."""
    if _global_metrics:
        _global_metrics.record_ingestion(document_count, success, duration)
