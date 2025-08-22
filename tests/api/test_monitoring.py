"""
Tests for the monitoring and alerting system.

This module tests the comprehensive monitoring capabilities:
- Health and performance metrics endpoints
- Alert management and notification system
- Prometheus metrics export
- System diagnostics and maintenance
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from graph_rag.api.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    """Test the health monitoring endpoint."""
    response = client.get("/api/v1/monitoring/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert "dependencies" in data
    assert isinstance(data["dependencies"], list)


def test_performance_endpoint(client):
    """Test the performance metrics endpoint."""
    response = client.get("/api/v1/monitoring/performance")
    assert response.status_code == 200

    data = response.json()
    assert "request_latency" in data
    assert "vector_search" in data
    assert "graph_queries" in data
    assert "ingestion" in data
    assert "timestamp" in data

    # Check metric structure
    for metric_group in ["request_latency", "vector_search", "graph_queries"]:
        assert "avg_ms" in data[metric_group]
        assert "samples" in data[metric_group]


def test_system_metrics_endpoint(client):
    """Test the system metrics endpoint."""
    response = client.get("/api/v1/monitoring/system")
    assert response.status_code == 200

    data = response.json()
    assert "uptime_seconds" in data
    assert "total_requests" in data
    assert "error_count" in data
    assert "error_rate_percent" in data
    assert "timestamp" in data


def test_prometheus_metrics_endpoint(client):
    """Test the Prometheus metrics export."""
    response = client.get("/api/v1/monitoring/metrics")

    # Either successful metrics or graceful degradation
    if response.status_code == 200:
        # Check content type
        assert "text/plain" in response.headers["content-type"]

        # Check for expected metric names
        content = response.text
        assert "synapse_system_uptime_seconds" in content
        assert "synapse_http_requests_total" in content
        assert "synapse_http_request_duration_seconds" in content
        assert "synapse_vector_search_duration_seconds" in content
    else:
        # Metrics collector not available in test environment
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "Metrics collector not available" in data["detail"]


def test_alerts_summary_endpoint(client):
    """Test the alerts summary endpoint."""
    response = client.get("/api/v1/monitoring/alerts/summary")
    assert response.status_code == 200

    data = response.json()
    assert "total_rules" in data
    assert "active_alerts" in data
    assert "recent_events_24h" in data
    assert "severity_distribution" in data
    assert "timestamp" in data


def test_alerts_history_endpoint(client):
    """Test the alerts history endpoint."""
    response = client.get("/api/v1/monitoring/alerts/history")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_alerts_history_with_limit(client):
    """Test the alerts history endpoint with limit parameter."""
    response = client.get("/api/v1/monitoring/alerts/history?limit=50")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 50


def test_diagnostics_endpoint(client):
    """Test the system diagnostics endpoint."""
    response = client.get("/api/v1/monitoring/diagnostics")
    assert response.status_code == 200

    data = response.json()
    assert "services_status" in data
    assert "configuration" in data
    assert "resource_usage" in data
    assert "performance_summary" in data
    assert "timestamp" in data

    # Check services status structure
    services = data["services_status"]
    expected_services = ["graph_repository", "vector_store", "ingestion_service", "graph_rag_engine"]
    for service in expected_services:
        assert service in services
        assert services[service] in ["operational", "mock", "unavailable"]


def test_maintenance_trigger_endpoint(client):
    """Test the maintenance trigger endpoint."""
    # Test vector store optimization
    response = client.post("/api/v1/monitoring/maintenance/trigger?task_type=vector_store_optimization")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "message" in data


def test_maintenance_unknown_task(client):
    """Test maintenance trigger with unknown task type."""
    response = client.post("/api/v1/monitoring/maintenance/trigger?task_type=unknown_task")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "error"
    assert "Unknown maintenance task" in data["message"]


@pytest.mark.asyncio
async def test_metrics_collector():
    """Test the metrics collector functionality."""
    from graph_rag.observability.metrics import MetricDefinition, MetricsCollector, MetricType

    collector = MetricsCollector(enable_prometheus=False, enable_alerts=False)

    # Test metric registration
    test_metric = MetricDefinition(
        name="test_counter",
        description="Test counter metric",
        metric_type=MetricType.COUNTER
    )
    collector.register_metric(test_metric)

    # Test metric recording
    collector.record_metric("test_counter", 1.0)
    collector.record_metric("test_counter", 2.0)

    # Check metric history
    assert "test_counter" in collector._metric_history
    assert len(collector._metric_history["test_counter"]) == 2


@pytest.mark.asyncio
async def test_alert_manager():
    """Test the alert manager functionality."""
    from graph_rag.observability.alerts import (
        AlertCondition,
        AlertManager,
        AlertRule,
        AlertState,
        NotificationChannel,
        NotificationConfig,
    )

    manager = AlertManager(evaluation_interval=0.1)

    # Create test alert rule
    condition = AlertCondition(
        name="test_condition",
        description="Test condition",
        condition_func=lambda metrics: metrics.get("test_value", 0) > 5,
        threshold=5.0,
        duration_seconds=0.1
    )

    notification = NotificationConfig(
        channel=NotificationChannel.LOG,
        enabled=True
    )

    alert_rule = AlertRule(
        name="test_alert",
        description="Test alert rule",
        condition=condition,
        notifications=[notification]
    )

    manager.register_alert_rule(alert_rule)

    # Verify rule registration
    rules = manager.get_alert_rules()
    assert "test_alert" in rules
    assert rules["test_alert"].state == AlertState.PENDING


@pytest.mark.asyncio
async def test_performance_timing():
    """Test performance timing context manager."""
    from graph_rag.observability.metrics import MetricDefinition, MetricsCollector, MetricType

    collector = MetricsCollector(enable_prometheus=False, enable_alerts=False)

    # Register timing metric
    timing_metric = MetricDefinition(
        name="test_operation_duration",
        description="Test operation duration",
        metric_type=MetricType.HISTOGRAM
    )
    collector.register_metric(timing_metric)

    # Test timing context manager
    async with collector.time_operation("test_operation_duration"):
        await asyncio.sleep(0.01)  # Small delay

    # Check that timing was recorded
    assert "test_operation_duration" in collector._metric_history
    assert len(collector._metric_history["test_operation_duration"]) == 1

    # Verify timing value is reasonable (should be around 10ms)
    recorded_time = collector._metric_history["test_operation_duration"][0].value
    assert 0.005 < recorded_time < 0.05  # Between 5ms and 50ms


def test_monitoring_integration_in_app():
    """Test that monitoring is properly integrated in the main app."""
    app = create_app()

    # Check that monitoring router is included
    routes = [route.path for route in app.routes]
    monitoring_routes = [route for route in routes if "/monitoring" in route]
    assert len(monitoring_routes) > 0

    # Test with client
    client = TestClient(app)

    # Verify monitoring endpoints are accessible
    endpoints_200 = [
        "/api/v1/monitoring/health",
        "/api/v1/monitoring/performance",
        "/api/v1/monitoring/system",
        "/api/v1/monitoring/alerts/summary",
        "/api/v1/monitoring/diagnostics"
    ]

    for endpoint in endpoints_200:
        response = client.get(endpoint)
        assert response.status_code == 200, f"Endpoint {endpoint} failed with {response.status_code}"

    # Metrics endpoint may return 503 if collector not available in test
    response = client.get("/api/v1/monitoring/metrics")
    assert response.status_code in [200, 503], f"Metrics endpoint failed with {response.status_code}"


@pytest.mark.asyncio
async def test_notification_providers():
    """Test notification providers."""
    from graph_rag.observability.alerts import (
        AlertEvent,
        AlertState,
        LogNotificationProvider,
        NotificationChannel,
        NotificationConfig,
        SlackNotificationProvider,
        WebhookNotificationProvider,
    )

    # Test webhook provider validation
    webhook_provider = WebhookNotificationProvider()

    valid_config = {"url": "https://example.com/webhook"}
    invalid_config = {"url": "not-a-url"}

    assert webhook_provider.validate_config(valid_config) is True
    assert webhook_provider.validate_config(invalid_config) is False

    # Test Slack provider validation
    slack_provider = SlackNotificationProvider()

    valid_slack_config = {"webhook_url": "https://hooks.slack.com/services/test"}
    invalid_slack_config = {"webhook_url": "https://example.com/webhook"}

    assert slack_provider.validate_config(valid_slack_config) is True
    assert slack_provider.validate_config(invalid_slack_config) is False

    # Test log provider
    log_provider = LogNotificationProvider()

    valid_log_config = {"level": "WARNING"}
    invalid_log_config = {"level": "INVALID"}

    assert log_provider.validate_config(valid_log_config) is True
    assert log_provider.validate_config(invalid_log_config) is False

    # Test log notification
    alert_event = AlertEvent(
        alert_name="test_alert",
        timestamp=1234567890.0,
        state=AlertState.ACTIVE,
        severity="high",
        description="Test alert description",
        metric_values={"test_metric": 100}
    )

    log_config = NotificationConfig(
        channel=NotificationChannel.LOG,
        config={"level": "WARNING"}
    )

    # This should not raise an exception
    result = await log_provider.send_notification(alert_event, log_config)
    assert result is True
