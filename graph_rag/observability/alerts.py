"""
Advanced Alerting System for GraphRAG

This module provides comprehensive alerting capabilities:
- Real-time threshold monitoring
- Custom alert conditions
- Multi-channel notifications (webhook, email, Slack)
- Alert escalation and de-escalation
- Alert suppression and correlation
- Dashboard integration

Supports integration with popular monitoring tools and notification services.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)


class AlertState(Enum):
    """Alert state enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Supported notification channels."""
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    PAGERDUTY = "pagerduty"
    LOG = "log"


@dataclass
class AlertCondition:
    """Defines an alert condition with evaluation logic."""
    name: str
    description: str
    condition_func: Callable[[dict[str, Any]], bool]
    threshold: float | None = None
    comparison: str = ">"  # >, <, >=, <=, ==, !=
    field: str | None = None
    duration_seconds: float = 60.0
    evaluation_interval: float = 30.0


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    channel: NotificationChannel
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

    # Rate limiting
    max_notifications_per_hour: int = 10
    suppress_duplicate_duration: float = 300.0  # 5 minutes


@dataclass
class AlertRule:
    """Complete alert rule definition."""
    name: str
    description: str
    condition: AlertCondition
    severity: str = "medium"
    tags: set[str] = field(default_factory=set)
    notifications: list[NotificationConfig] = field(default_factory=list)

    # Alert behavior
    auto_resolve: bool = True
    auto_resolve_duration: float = 300.0  # Auto-resolve after 5 minutes
    escalation_rules: list[dict[str, Any]] = field(default_factory=list)

    # State tracking
    state: AlertState = AlertState.PENDING
    first_triggered: float | None = None
    last_triggered: float | None = None
    last_resolved: float | None = None
    trigger_count: int = 0
    active: bool = True


@dataclass
class AlertEvent:
    """Represents an alert event."""
    alert_name: str
    timestamp: float
    state: AlertState
    severity: str
    description: str
    metric_values: dict[str, Any]
    tags: set[str] = field(default_factory=set)
    correlation_id: str | None = None
    source: str = "synapse"


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    @abstractmethod
    async def send_notification(
        self,
        alert_event: AlertEvent,
        config: NotificationConfig
    ) -> bool:
        """Send notification for an alert event."""
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate notification configuration."""
        pass


class WebhookNotificationProvider(NotificationProvider):
    """Webhook notification provider."""

    async def send_notification(
        self,
        alert_event: AlertEvent,
        config: NotificationConfig
    ) -> bool:
        """Send webhook notification."""
        url = config.config.get("url")
        if not url:
            logger.error("Webhook URL not configured")
            return False

        headers = config.config.get("headers", {})
        headers.setdefault("Content-Type", "application/json")

        payload = {
            "alert_name": alert_event.alert_name,
            "timestamp": alert_event.timestamp,
            "state": alert_event.state.value,
            "severity": alert_event.severity,
            "description": alert_event.description,
            "metric_values": alert_event.metric_values,
            "tags": list(alert_event.tags),
            "source": alert_event.source,
        }

        # Add custom fields if configured
        if "custom_fields" in config.config:
            payload.update(config.config["custom_fields"])

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status < 400:
                        logger.debug(f"Webhook notification sent successfully to {url}")
                        return True
                    else:
                        logger.error(f"Webhook notification failed: {response.status} {await response.text()}")
                        return False
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate webhook configuration."""
        url = config.get("url")
        if not url:
            return False

        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ["http", "https"] and parsed.netloc)
        except Exception:
            return False


class SlackNotificationProvider(NotificationProvider):
    """Slack notification provider."""

    async def send_notification(
        self,
        alert_event: AlertEvent,
        config: NotificationConfig
    ) -> bool:
        """Send Slack notification."""
        webhook_url = config.config.get("webhook_url")
        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return False

        # Determine emoji and color based on severity and state
        emoji_map = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "⚡",
            "low": "ℹ️",
        }

        color_map = {
            "critical": "#FF0000",
            "high": "#FF8800",
            "medium": "#FFAA00",
            "low": "#00AA00",
        }

        emoji = emoji_map.get(alert_event.severity, "🔔")
        color = color_map.get(alert_event.severity, "#808080")

        if alert_event.state == AlertState.RESOLVED:
            emoji = "✅"
            color = "#00AA00"

        # Format metric values for display
        metrics_text = "\n".join([
            f"• {key}: {value}" for key, value in alert_event.metric_values.items()
        ])

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} {alert_event.alert_name}",
                    "text": alert_event.description,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert_event.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "State",
                            "value": alert_event.state.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Source",
                            "value": alert_event.source,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": f"<!date^{int(alert_event.timestamp)}^{{date_short_pretty}} {{time}}|{alert_event.timestamp}>",
                            "short": True
                        },
                    ],
                    "footer": "Synapse GraphRAG Monitoring",
                    "ts": int(alert_event.timestamp)
                }
            ]
        }

        if metrics_text:
            payload["attachments"][0]["fields"].append({
                "title": "Metrics",
                "value": f"```{metrics_text}```",
                "short": False
            })

        if alert_event.tags:
            payload["attachments"][0]["fields"].append({
                "title": "Tags",
                "value": ", ".join(f"`{tag}`" for tag in alert_event.tags),
                "short": False
            })

        # Add custom channel if specified
        if "channel" in config.config:
            payload["channel"] = config.config["channel"]

        if "username" in config.config:
            payload["username"] = config.config["username"]

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status < 400:
                        logger.debug("Slack notification sent successfully")
                        return True
                    else:
                        logger.error(f"Slack notification failed: {response.status} {await response.text()}")
                        return False
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate Slack configuration."""
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return False

        try:
            parsed = urlparse(webhook_url)
            return bool(parsed.netloc == "hooks.slack.com")
        except Exception:
            return False


class LogNotificationProvider(NotificationProvider):
    """Log-based notification provider."""

    async def send_notification(
        self,
        alert_event: AlertEvent,
        config: NotificationConfig
    ) -> bool:
        """Send log notification."""
        log_level = config.config.get("level", "WARNING").upper()

        # Map to logging levels
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        level = level_map.get(log_level, logging.WARNING)

        logger.log(
            level,
            f"ALERT: {alert_event.alert_name} ({alert_event.state.value}) - {alert_event.description}",
            extra={
                "alert_event": {
                    "name": alert_event.alert_name,
                    "timestamp": alert_event.timestamp,
                    "state": alert_event.state.value,
                    "severity": alert_event.severity,
                    "metric_values": alert_event.metric_values,
                    "tags": list(alert_event.tags),
                }
            }
        )

        return True

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate log configuration."""
        level = config.get("level", "WARNING")
        return level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class AlertManager:
    """
    Comprehensive alert management system.

    Features:
    - Real-time alert evaluation
    - Multi-channel notifications
    - Alert state management
    - Rate limiting and deduplication
    - Alert correlation and suppression
    """

    def __init__(
        self,
        evaluation_interval: float = 30.0,
        max_alert_history: int = 1000,
        enable_auto_resolve: bool = True,
    ):
        """
        Initialize the alert manager.

        Args:
            evaluation_interval: How often to evaluate alert conditions (seconds)
            max_alert_history: Maximum number of alert events to keep in history
            enable_auto_resolve: Whether to automatically resolve alerts
        """
        self.evaluation_interval = evaluation_interval
        self.max_alert_history = max_alert_history
        self.enable_auto_resolve = enable_auto_resolve

        # Alert storage
        self._alert_rules: dict[str, AlertRule] = {}
        self._alert_history: list[AlertEvent] = []
        self._notification_providers: dict[NotificationChannel, NotificationProvider] = {}

        # State tracking
        self._evaluation_task: asyncio.Task | None = None
        self._running = False
        self._last_evaluation: dict[str, float] = {}
        self._notification_counts: dict[str, list[float]] = {}

        # Initialize default notification providers
        self._initialize_providers()

        logger.info(f"AlertManager initialized (interval={evaluation_interval}s)")

    def _initialize_providers(self):
        """Initialize notification providers."""
        self._notification_providers[NotificationChannel.WEBHOOK] = WebhookNotificationProvider()
        self._notification_providers[NotificationChannel.SLACK] = SlackNotificationProvider()
        self._notification_providers[NotificationChannel.LOG] = LogNotificationProvider()

    def register_alert_rule(self, alert_rule: AlertRule):
        """Register an alert rule."""
        # Validate the rule
        if not self._validate_alert_rule(alert_rule):
            raise ValueError(f"Invalid alert rule: {alert_rule.name}")

        self._alert_rules[alert_rule.name] = alert_rule
        logger.info(f"Registered alert rule: {alert_rule.name} (severity: {alert_rule.severity})")

    def _validate_alert_rule(self, rule: AlertRule) -> bool:
        """Validate an alert rule."""
        if not rule.name or not rule.condition:
            return False

        # Validate notification configurations
        for notification in rule.notifications:
            provider = self._notification_providers.get(notification.channel)
            if not provider:
                logger.warning(f"Unknown notification channel: {notification.channel}")
                continue

            if not provider.validate_config(notification.config):
                logger.warning(f"Invalid notification config for {notification.channel}")
                return False

        return True

    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self._alert_rules:
            del self._alert_rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")

    def get_alert_rules(self) -> dict[str, AlertRule]:
        """Get all alert rules."""
        return self._alert_rules.copy()

    def get_active_alerts(self) -> list[AlertRule]:
        """Get currently active alerts."""
        return [
            rule for rule in self._alert_rules.values()
            if rule.state == AlertState.ACTIVE
        ]

    async def start(self):
        """Start the alert evaluation loop."""
        if self._running:
            return

        self._running = True
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())
        logger.info("Alert manager started")

    async def stop(self):
        """Stop the alert evaluation loop."""
        self._running = False

        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass
            self._evaluation_task = None

        logger.info("Alert manager stopped")

    async def _evaluation_loop(self):
        """Main alert evaluation loop."""
        while self._running:
            try:
                await asyncio.sleep(self.evaluation_interval)
                await self._evaluate_alerts()

                if self.enable_auto_resolve:
                    await self._auto_resolve_alerts()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}", exc_info=True)

    async def _evaluate_alerts(self):
        """Evaluate all alert conditions."""
        current_time = time.time()

        for rule_name, rule in self._alert_rules.items():
            if not rule.active:
                continue

            try:
                # Check if it's time to evaluate this rule
                last_eval = self._last_evaluation.get(rule_name, 0)
                if current_time - last_eval < rule.condition.evaluation_interval:
                    continue

                self._last_evaluation[rule_name] = current_time

                # Get current metrics for evaluation
                metrics = await self._get_current_metrics()

                # Evaluate condition
                condition_met = rule.condition.condition_func(metrics)

                await self._process_condition_result(rule, condition_met, metrics, current_time)

            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule_name}: {e}", exc_info=True)

    async def _get_current_metrics(self) -> dict[str, Any]:
        """Get current metrics for alert evaluation."""
        # This should integrate with the metrics collector
        # For now, return a placeholder
        from graph_rag.observability.metrics import get_metrics_collector

        collector = get_metrics_collector()
        if collector:
            return collector._get_current_metrics()

        return {}

    async def _process_condition_result(
        self,
        rule: AlertRule,
        condition_met: bool,
        metrics: dict[str, Any],
        current_time: float
    ):
        """Process the result of an alert condition evaluation."""
        if condition_met:
            # Condition is met - trigger or maintain alert
            if rule.state in [AlertState.PENDING, AlertState.RESOLVED]:
                # Check if we should trigger based on duration
                if rule.first_triggered is None:
                    rule.first_triggered = current_time
                elif current_time - rule.first_triggered >= rule.condition.duration_seconds:
                    # Trigger the alert
                    await self._trigger_alert(rule, metrics, current_time)

            rule.last_triggered = current_time

        else:
            # Condition is not met - resolve if active
            if rule.state == AlertState.ACTIVE:
                await self._resolve_alert(rule, current_time)

            # Reset trigger time if condition not met
            rule.first_triggered = None

    async def _trigger_alert(self, rule: AlertRule, metrics: dict[str, Any], timestamp: float):
        """Trigger an alert."""
        rule.state = AlertState.ACTIVE
        rule.trigger_count += 1

        # Create alert event
        alert_event = AlertEvent(
            alert_name=rule.name,
            timestamp=timestamp,
            state=AlertState.ACTIVE,
            severity=rule.severity,
            description=rule.description,
            metric_values=metrics,
            tags=rule.tags,
        )

        # Add to history
        self._add_to_history(alert_event)

        # Send notifications
        await self._send_notifications(rule, alert_event)

        logger.warning(f"Alert triggered: {rule.name} (severity: {rule.severity})")

    async def _resolve_alert(self, rule: AlertRule, timestamp: float):
        """Resolve an alert."""
        if rule.state != AlertState.ACTIVE:
            return

        rule.state = AlertState.RESOLVED
        rule.last_resolved = timestamp

        # Create resolution event
        alert_event = AlertEvent(
            alert_name=rule.name,
            timestamp=timestamp,
            state=AlertState.RESOLVED,
            severity=rule.severity,
            description=f"Alert resolved: {rule.description}",
            metric_values={},
            tags=rule.tags,
        )

        # Add to history
        self._add_to_history(alert_event)

        # Send resolution notifications
        await self._send_notifications(rule, alert_event)

        logger.info(f"Alert resolved: {rule.name}")

    async def _auto_resolve_alerts(self):
        """Auto-resolve alerts that have been active too long."""
        current_time = time.time()

        for rule in self._alert_rules.values():
            if (rule.state == AlertState.ACTIVE and
                rule.auto_resolve and
                rule.last_triggered and
                current_time - rule.last_triggered >= rule.auto_resolve_duration):

                await self._resolve_alert(rule, current_time)

    def _add_to_history(self, alert_event: AlertEvent):
        """Add alert event to history."""
        self._alert_history.append(alert_event)

        # Trim history if needed
        if len(self._alert_history) > self.max_alert_history:
            self._alert_history = self._alert_history[-self.max_alert_history:]

    async def _send_notifications(self, rule: AlertRule, alert_event: AlertEvent):
        """Send notifications for an alert event."""
        for notification in rule.notifications:
            if not notification.enabled:
                continue

            # Check rate limiting
            if not self._check_rate_limit(rule.name, notification):
                logger.debug(f"Rate limit exceeded for {rule.name} on {notification.channel.value}")
                continue

            # Get provider
            provider = self._notification_providers.get(notification.channel)
            if not provider:
                logger.warning(f"No provider for notification channel: {notification.channel}")
                continue

            try:
                success = await provider.send_notification(alert_event, notification)
                if success:
                    self._record_notification(rule.name, notification)
                    logger.debug(f"Notification sent via {notification.channel.value} for {rule.name}")
                else:
                    logger.error(f"Failed to send notification via {notification.channel.value} for {rule.name}")

            except Exception as e:
                logger.error(f"Error sending notification via {notification.channel.value}: {e}")

    def _check_rate_limit(self, rule_name: str, notification: NotificationConfig) -> bool:
        """Check if notification is within rate limits."""
        key = f"{rule_name}:{notification.channel.value}"
        current_time = time.time()

        # Initialize if needed
        if key not in self._notification_counts:
            self._notification_counts[key] = []

        # Remove old entries (outside the hour window)
        hour_ago = current_time - 3600
        self._notification_counts[key] = [
            t for t in self._notification_counts[key] if t > hour_ago
        ]

        # Check rate limit
        return len(self._notification_counts[key]) < notification.max_notifications_per_hour

    def _record_notification(self, rule_name: str, notification: NotificationConfig):
        """Record a sent notification for rate limiting."""
        key = f"{rule_name}:{notification.channel.value}"
        current_time = time.time()

        if key not in self._notification_counts:
            self._notification_counts[key] = []

        self._notification_counts[key].append(current_time)

    def get_alert_history(self, limit: int = 100) -> list[AlertEvent]:
        """Get alert history."""
        return self._alert_history[-limit:]

    def get_alert_statistics(self) -> dict[str, Any]:
        """Get alert statistics."""
        total_rules = len(self._alert_rules)
        active_alerts = len(self.get_active_alerts())

        # Count alerts by severity
        severity_counts = {}
        for rule in self._alert_rules.values():
            severity_counts[rule.severity] = severity_counts.get(rule.severity, 0) + 1

        # Recent activity (last 24 hours)
        day_ago = time.time() - 86400
        recent_events = [e for e in self._alert_history if e.timestamp > day_ago]

        return {
            "total_rules": total_rules,
            "active_alerts": active_alerts,
            "severity_distribution": severity_counts,
            "recent_events_24h": len(recent_events),
            "total_events": len(self._alert_history),
            "notification_channels": len(self._notification_providers),
        }


# Global alert manager instance
_global_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager | None:
    """Get the global alert manager instance."""
    return _global_alert_manager


def initialize_alerts(
    evaluation_interval: float = 30.0,
    enable_auto_resolve: bool = True,
) -> AlertManager:
    """Initialize the global alert manager."""
    global _global_alert_manager

    if _global_alert_manager is None:
        _global_alert_manager = AlertManager(
            evaluation_interval=evaluation_interval,
            enable_auto_resolve=enable_auto_resolve,
        )
        logger.info("Initialized global alert manager")

    return _global_alert_manager


async def start_alerting():
    """Start the global alerting system."""
    if _global_alert_manager:
        await _global_alert_manager.start()


async def stop_alerting():
    """Stop the global alerting system."""
    if _global_alert_manager:
        await _global_alert_manager.stop()
