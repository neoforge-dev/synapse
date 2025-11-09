"""Security monitoring dashboard with real-time encryption health metrics."""

import asyncio
import logging
import os

# Import our security infrastructure
import sys
from datetime import datetime
from typing import Any
from uuid import UUID

import prometheus_client
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from prometheus_client import Counter, Gauge, Histogram

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from security.encryption import DataEncryptionManager
from security.key_management import VaultKeyManager
from security.zero_trust import IdentityVerificationEngine, ZeroTrustAccessControl

logger = logging.getLogger(__name__)


# Prometheus metrics
encryption_operations_total = Counter(
    'synapse_encryption_operations_total',
    'Total number of encryption operations',
    ['tenant_id', 'operation_type']
)

encryption_duration_seconds = Histogram(
    'synapse_encryption_duration_seconds',
    'Time spent on encryption operations',
    ['tenant_id', 'operation_type'],
    buckets=[0.001, 0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.0, 2.5, 5.0]
)

vault_operations_total = Counter(
    'synapse_vault_operations_total',
    'Total number of Vault operations',
    ['operation_type', 'status']
)

vault_response_time_seconds = Histogram(
    'synapse_vault_response_time_seconds',
    'Vault operation response time',
    ['operation_type'],
    buckets=[0.001, 0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.0, 2.5, 5.0]
)

security_events_total = Counter(
    'synapse_security_events_total',
    'Total number of security events',
    ['event_type', 'severity']
)

active_sessions_gauge = Gauge(
    'synapse_active_sessions',
    'Number of active user sessions'
)

access_control_decisions_total = Counter(
    'synapse_access_control_decisions_total',
    'Total number of access control decisions',
    ['decision', 'resource_type']
)

certificate_expiry_days_gauge = Gauge(
    'synapse_certificate_expiry_days',
    'Days until certificate expiry',
    ['certificate_name', 'namespace']
)

compliance_score_gauge = Gauge(
    'synapse_compliance_score',
    'Overall compliance score (0-100)',
    ['framework']
)


class SecurityDashboard:
    """Real-time security monitoring dashboard."""

    def __init__(self, vault_manager: VaultKeyManager,
                 identity_engine: IdentityVerificationEngine,
                 access_control: ZeroTrustAccessControl,
                 encryption_managers: dict[UUID, DataEncryptionManager]):
        """Initialize security dashboard."""
        self.vault_manager = vault_manager
        self.identity_engine = identity_engine
        self.access_control = access_control
        self.encryption_managers = encryption_managers

        # Dashboard state
        self.dashboard_metrics = {
            "encryption_health": {},
            "key_management_status": {},
            "access_control_metrics": {},
            "security_events": [],
            "compliance_status": {}
        }

        # Alert thresholds
        self.alert_thresholds = {
            "encryption_time_ms": 5.0,  # 5ms threshold
            "vault_response_time_ms": 100.0,  # 100ms threshold
            "failed_auth_rate": 10.0,  # 10% failure rate
            "certificate_expiry_days": 30,  # 30 days warning
            "compliance_score_min": 85  # Minimum 85% compliance
        }

        # Background tasks
        self.monitoring_active = False

        logger.info("Initialized SecurityDashboard")

    async def start_monitoring(self):
        """Start background monitoring tasks."""
        self.monitoring_active = True

        # Start monitoring coroutines
        await asyncio.gather(
            self._monitor_encryption_health(),
            self._monitor_vault_health(),
            self._monitor_security_events(),
            self._monitor_certificate_expiry(),
            self._update_compliance_scores()
        )

    async def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitoring_active = False
        logger.info("Stopped security monitoring")

    async def _monitor_encryption_health(self):
        """Monitor encryption operation health."""
        while self.monitoring_active:
            try:
                encryption_health = {}

                for tenant_id, manager in self.encryption_managers.items():
                    health_status = manager.get_encryption_health_status()

                    # Update Prometheus metrics
                    tenant_str = str(tenant_id)

                    # Check encryption performance
                    avg_time_ms = health_status.get("average_encryption_overhead_ms", 0)
                    if avg_time_ms > self.alert_thresholds["encryption_time_ms"]:
                        await self._generate_alert(
                            "encryption_performance",
                            f"Encryption overhead {avg_time_ms}ms exceeds threshold for tenant {tenant_id}",
                            "warning"
                        )

                    # Update gauge metrics
                    encryption_duration_seconds.labels(
                        tenant_id=tenant_str,
                        operation_type="encrypt"
                    ).observe(avg_time_ms / 1000)

                    encryption_health[tenant_str] = health_status

                self.dashboard_metrics["encryption_health"] = encryption_health

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error monitoring encryption health: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_vault_health(self):
        """Monitor Vault key management health."""
        while self.monitoring_active:
            try:
                # Perform Vault health check
                health_result = self.vault_manager.health_check()

                # Update metrics
                vault_operations_total.labels(
                    operation_type="health_check",
                    status="success" if health_result["status"] == "healthy" else "failed"
                ).inc()

                vault_response_time_seconds.labels(
                    operation_type="health_check"
                ).observe(health_result.get("response_time_ms", 0) / 1000)

                # Check for alerts
                if health_result["status"] != "healthy":
                    await self._generate_alert(
                        "vault_unhealthy",
                        f"Vault health check failed: {health_result.get('error', 'Unknown error')}",
                        "critical"
                    )

                # Get key management metrics
                key_metrics = self.vault_manager.get_key_management_metrics()

                # Check response times
                avg_operation_time = key_metrics.get("avg_vault_operation_time", 0) * 1000
                if avg_operation_time > self.alert_thresholds["vault_response_time_ms"]:
                    await self._generate_alert(
                        "vault_performance",
                        f"Vault response time {avg_operation_time}ms exceeds threshold",
                        "warning"
                    )

                self.dashboard_metrics["key_management_status"] = {
                    "health": health_result,
                    "metrics": key_metrics
                }

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error monitoring Vault health: {str(e)}")
                await asyncio.sleep(120)

    async def _monitor_security_events(self):
        """Monitor security events and access control."""
        while self.monitoring_active:
            try:
                # Get identity verification metrics
                identity_metrics = self.identity_engine.get_security_metrics()

                # Calculate failure rate
                total_verifications = identity_metrics.get("total_verifications", 1)
                failed_verifications = identity_metrics.get("failed_verifications", 0)
                failure_rate = (failed_verifications / total_verifications) * 100

                if failure_rate > self.alert_thresholds["failed_auth_rate"]:
                    await self._generate_alert(
                        "high_auth_failure_rate",
                        f"Authentication failure rate {failure_rate:.1f}% exceeds threshold",
                        "warning"
                    )

                # Update Prometheus metrics
                active_sessions_gauge.set(identity_metrics.get("active_sessions", 0))

                # Get access control metrics
                access_metrics = self.access_control.get_access_metrics()

                # Update access control metrics
                for decision in ["granted", "denied"]:
                    for resource_type in ["document", "api_endpoint", "encryption_key"]:
                        access_control_decisions_total.labels(
                            decision=decision,
                            resource_type=resource_type
                        ).inc(0)  # Initialize if not exists

                # Get recent security events
                recent_events = self.identity_engine.get_recent_security_events(limit=50)

                # Process security events for alerts
                for event_type, events in recent_events.items():
                    for _event in events[-10:]:  # Check last 10 events
                        security_events_total.labels(
                            event_type=event_type,
                            severity=self._determine_event_severity(event_type)
                        ).inc()

                self.dashboard_metrics["access_control_metrics"] = access_metrics
                self.dashboard_metrics["security_events"] = recent_events

                await asyncio.sleep(45)  # Check every 45 seconds

            except Exception as e:
                logger.error(f"Error monitoring security events: {str(e)}")
                await asyncio.sleep(90)

    async def _monitor_certificate_expiry(self):
        """Monitor TLS certificate expiry dates."""
        while self.monitoring_active:
            try:
                # This would typically query cert-manager or check certificate files
                certificates = [
                    {"name": "synapse-api-tls", "namespace": "synapse-prod", "expires_in_days": 45},
                    {"name": "synapse-internal-tls", "namespace": "synapse-prod", "expires_in_days": 120},
                    {"name": "synapse-vault-client-tls", "namespace": "synapse-prod", "expires_in_days": 15}
                ]

                for cert in certificates:
                    days_until_expiry = cert["expires_in_days"]

                    # Update metric
                    certificate_expiry_days_gauge.labels(
                        certificate_name=cert["name"],
                        namespace=cert["namespace"]
                    ).set(days_until_expiry)

                    # Check for alerts
                    if days_until_expiry <= self.alert_thresholds["certificate_expiry_days"]:
                        severity = "critical" if days_until_expiry <= 7 else "warning"
                        await self._generate_alert(
                            "certificate_expiry",
                            f"Certificate {cert['name']} expires in {days_until_expiry} days",
                            severity
                        )

                await asyncio.sleep(3600)  # Check every hour

            except Exception as e:
                logger.error(f"Error monitoring certificate expiry: {str(e)}")
                await asyncio.sleep(3600)

    async def _update_compliance_scores(self):
        """Update compliance framework scores."""
        while self.monitoring_active:
            try:
                compliance_frameworks = {
                    "HIPAA": await self._calculate_hipaa_score(),
                    "PCI_DSS": await self._calculate_pci_score(),
                    "GDPR": await self._calculate_gdpr_score(),
                    "SOC2": await self._calculate_soc2_score(),
                    "NIST_Zero_Trust": await self._calculate_nist_zt_score()
                }

                for framework, score in compliance_frameworks.items():
                    compliance_score_gauge.labels(framework=framework).set(score)

                    if score < self.alert_thresholds["compliance_score_min"]:
                        await self._generate_alert(
                            "compliance_score_low",
                            f"{framework} compliance score {score}% below minimum",
                            "warning"
                        )

                self.dashboard_metrics["compliance_status"] = compliance_frameworks

                await asyncio.sleep(3600)  # Update every hour

            except Exception as e:
                logger.error(f"Error updating compliance scores: {str(e)}")
                await asyncio.sleep(3600)

    async def _calculate_hipaa_score(self) -> int:
        """Calculate HIPAA compliance score."""
        score = 100

        # Check encryption coverage
        encryption_health = self.dashboard_metrics.get("encryption_health", {})
        if not all(h.get("health_status") == "healthy" for h in encryption_health.values()):
            score -= 20

        # Check access controls
        access_metrics = self.dashboard_metrics.get("access_control_metrics", {})
        if access_metrics.get("grant_rate", 0) > 90:  # Too permissive
            score -= 10

        # Check audit logging
        # (Implementation would check actual audit log coverage)

        return max(score, 0)

    async def _calculate_pci_score(self) -> int:
        """Calculate PCI-DSS compliance score."""
        score = 100

        # Check for strong encryption
        vault_health = self.dashboard_metrics.get("key_management_status", {})
        if vault_health.get("health", {}).get("status") != "healthy":
            score -= 25

        # Check network security
        # (Implementation would check network policies)

        return max(score, 0)

    async def _calculate_gdpr_score(self) -> int:
        """Calculate GDPR compliance score."""
        score = 100

        # Check data protection measures
        encryption_coverage = len(self.dashboard_metrics.get("encryption_health", {}))
        if encryption_coverage == 0:
            score -= 30

        # Check right to erasure capabilities
        # (Implementation would check deletion capabilities)

        return max(score, 0)

    async def _calculate_soc2_score(self) -> int:
        """Calculate SOC2 compliance score."""
        score = 100

        # Check security monitoring
        security_events = self.dashboard_metrics.get("security_events", {})
        if not security_events:
            score -= 15

        # Check availability metrics
        # (Implementation would check uptime metrics)

        return max(score, 0)

    async def _calculate_nist_zt_score(self) -> int:
        """Calculate NIST Zero Trust compliance score."""
        score = 100

        # Check identity verification
        identity_metrics = self.dashboard_metrics.get("access_control_metrics", {})
        if identity_metrics.get("grant_rate", 0) > 95:  # Should not be too permissive
            score -= 10

        # Check continuous verification
        # (Implementation would check continuous monitoring)

        return max(score, 0)

    async def _generate_alert(self, alert_type: str, message: str, severity: str):
        """Generate security alert."""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": alert_type,
            "message": message,
            "severity": severity
        }

        # Log alert
        logger.warning(f"Security Alert [{severity.upper()}]: {message}")

        # In production, send to alerting system (PagerDuty, Slack, etc.)

        # Store in dashboard
        if "alerts" not in self.dashboard_metrics:
            self.dashboard_metrics["alerts"] = []

        self.dashboard_metrics["alerts"].append(alert)

        # Keep only last 100 alerts
        if len(self.dashboard_metrics["alerts"]) > 100:
            self.dashboard_metrics["alerts"] = self.dashboard_metrics["alerts"][-50:]

    def _determine_event_severity(self, event_type: str) -> str:
        """Determine severity level for security event."""
        high_severity_events = [
            "failed_verifications", "suspicious_activities",
            "cross_tenant_attempts", "privilege_escalations"
        ]

        if event_type in high_severity_events:
            return "high"
        else:
            return "medium"

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get current dashboard data."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active" if self.monitoring_active else "inactive",
            "metrics": self.dashboard_metrics,
            "alert_thresholds": self.alert_thresholds
        }

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall security health summary."""
        encryption_healthy = all(
            h.get("health_status") == "healthy"
            for h in self.dashboard_metrics.get("encryption_health", {}).values()
        )

        vault_healthy = (
            self.dashboard_metrics.get("key_management_status", {})
            .get("health", {}).get("status") == "healthy"
        )

        compliance_scores = self.dashboard_metrics.get("compliance_status", {})
        avg_compliance = sum(compliance_scores.values()) / len(compliance_scores) if compliance_scores else 0

        recent_alerts = self.dashboard_metrics.get("alerts", [])
        critical_alerts = [a for a in recent_alerts[-10:] if a.get("severity") == "critical"]

        overall_health = "healthy"
        if critical_alerts or not vault_healthy:
            overall_health = "critical"
        elif not encryption_healthy or avg_compliance < 90:
            overall_health = "warning"

        return {
            "overall_health": overall_health,
            "encryption_health": "healthy" if encryption_healthy else "degraded",
            "vault_health": "healthy" if vault_healthy else "unhealthy",
            "compliance_average": round(avg_compliance, 1),
            "active_alerts": len(recent_alerts),
            "critical_alerts": len(critical_alerts)
        }


# FastAPI application for dashboard
def create_dashboard_app(security_dashboard: SecurityDashboard) -> FastAPI:
    """Create FastAPI application for security dashboard."""

    app = FastAPI(
        title="Synapse Security Dashboard",
        description="Real-time security monitoring and encryption health dashboard",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def dashboard_home():
        """Security dashboard home page."""
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Synapse Security Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .metric { margin: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
                .healthy { background-color: #d4edda; }
                .warning { background-color: #fff3cd; }
                .critical { background-color: #f8d7da; }
                .header { text-align: center; margin-bottom: 30px; }
            </style>
            <script>
                async function refreshDashboard() {
                    try {
                        const response = await fetch('/api/dashboard');
                        const data = await response.json();
                        document.getElementById('dashboard-data').innerHTML =
                            '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    } catch (error) {
                        console.error('Error refreshing dashboard:', error);
                    }
                }

                setInterval(refreshDashboard, 10000); // Refresh every 10 seconds
                window.onload = refreshDashboard;
            </script>
        </head>
        <body>
            <div class="header">
                <h1>🔒 Synapse Security Dashboard</h1>
                <p>Real-time Zero-Trust Security Monitoring</p>
            </div>

            <div id="dashboard-data">
                Loading security metrics...
            </div>
        </body>
        </html>
        """)

    @app.get("/api/dashboard")
    async def get_dashboard():
        """Get dashboard data API."""
        return security_dashboard.get_dashboard_data()

    @app.get("/api/health")
    async def get_health():
        """Get health summary API."""
        return security_dashboard.get_health_summary()

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return prometheus_client.generate_latest()

    return app


if __name__ == "__main__":
    # Example usage
    from security.key_management import VaultConfig

    # Initialize components (would be injected in production)
    vault_config = VaultConfig(
        url="https://vault.synapse.internal:8200",
        mount_point="synapse-kv"
    )

    vault_manager = VaultKeyManager(vault_config)
    identity_engine = IdentityVerificationEngine()
    access_control = ZeroTrustAccessControl()
    encryption_managers = {}  # Would be populated with tenant managers

    # Create dashboard
    dashboard = SecurityDashboard(
        vault_manager, identity_engine, access_control, encryption_managers
    )

    # Create FastAPI app
    app = create_dashboard_app(dashboard)

    # Start monitoring in background
    async def startup():
        await dashboard.start_monitoring()

    async def shutdown():
        await dashboard.stop_monitoring()

    app.add_event_handler("startup", startup)
    app.add_event_handler("shutdown", shutdown)

    # Run dashboard server
    uvicorn.run(app, host="0.0.0.0", port=8080)
