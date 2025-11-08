"""Service Level Agreement (SLA) management and monitoring system."""

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ...compliance.audit_logging import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    ComplianceAuditLogger,
)

logger = logging.getLogger(__name__)


class SLAMetric(str, Enum):
    """SLA metrics that can be tracked and enforced."""

    AVAILABILITY = "availability"           # Uptime percentage
    RESPONSE_TIME = "response_time"        # Average response time
    ERROR_RATE = "error_rate"              # Error rate percentage
    THROUGHPUT = "throughput"              # Requests per second
    DATA_DURABILITY = "data_durability"    # Data loss protection


class SLAViolationType(str, Enum):
    """Types of SLA violations."""

    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class SLATarget(BaseModel):
    """SLA target definition."""

    metric: SLAMetric
    target_value: float
    measurement_period: str = "monthly"  # daily, weekly, monthly, quarterly

    # Thresholds
    warning_threshold: float | None = None  # Warn before violation
    critical_threshold: float | None = None  # Critical violation level

    # Units and description
    unit: str = "percentage"  # percentage, milliseconds, count, etc.
    description: str = ""


class ServiceLevelAgreement(BaseModel):
    """Complete SLA definition for a tenant."""

    sla_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    client_id: str

    # SLA metadata
    name: str
    description: str
    tier: str  # basic, professional, enterprise, premium

    # SLA targets
    targets: list[SLATarget]

    # Contract details
    contract_start: datetime
    contract_end: datetime

    # Credits and penalties
    credit_percentage_per_violation: float = 5.0
    max_monthly_credit: float = 100.0

    # Status
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SLAViolation(BaseModel):
    """Record of an SLA violation."""

    violation_id: str = Field(default_factory=lambda: str(uuid4()))
    sla_id: str
    tenant_id: str

    # Violation details
    violation_type: SLAViolationType
    metric: SLAMetric
    target_value: float
    actual_value: float

    # Timing
    violation_start: datetime
    violation_end: datetime | None = None
    duration_minutes: int | None = None

    # Impact
    severity: str = "low"  # low, medium, high, critical
    affected_users: int = 0
    estimated_impact: str = ""

    # Resolution
    is_resolved: bool = False
    resolution_notes: str | None = None
    credit_applied: bool = False
    credit_amount: float = 0.0

    # Root cause analysis
    root_cause: str | None = None
    preventive_actions: list[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SLAMetrics(BaseModel):
    """Current SLA metrics for a tenant."""

    tenant_id: str
    measurement_period: datetime

    # Availability metrics
    uptime_percentage: float = 100.0
    downtime_minutes: int = 0

    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Error rate metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    error_rate_percentage: float = 0.0

    # Throughput metrics
    requests_per_second: float = 0.0
    peak_requests_per_second: float = 0.0

    # Violation tracking
    sla_violations: int = 0
    active_violations: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SLAStatus(BaseModel):
    """Current SLA status and compliance."""

    tenant_id: str
    sla_id: str
    status: str = "compliant"  # compliant, at_risk, violation

    # Compliance summary
    overall_compliance_percentage: float = 100.0
    targets_met: int = 0
    targets_at_risk: int = 0
    targets_violated: int = 0

    # Target details
    target_status: dict[SLAMetric, dict[str, Any]] = Field(default_factory=dict)

    # Credits and financials
    total_credits_earned: float = 0.0
    credits_applied_this_month: float = 0.0

    # Next review
    next_review_date: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            SLAMetric: lambda v: v.value
        }


class SLAManager:
    """Comprehensive SLA management and monitoring system."""

    def __init__(self, audit_logger: ComplianceAuditLogger):
        self.audit_logger = audit_logger

        # SLA storage
        self.slas: dict[str, ServiceLevelAgreement] = {}
        self.tenant_slas: dict[str, str] = {}  # tenant_id -> sla_id

        # Metrics tracking
        self.tenant_metrics: dict[str, SLAMetrics] = {}
        self.request_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.response_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))

        # Violation tracking
        self.violations: list[SLAViolation] = []
        self.active_violations: dict[str, SLAViolation] = {}

        # Monitoring
        self._monitoring_task: asyncio.Task | None = None

        # Default SLA templates
        self._create_default_sla_templates()

        logger.info("SLA Manager initialized")

    def _create_default_sla_templates(self) -> None:
        """Create default SLA templates for different tiers."""

        # Enterprise tier SLA template
        self.enterprise_sla_template = [
            SLATarget(
                metric=SLAMetric.AVAILABILITY,
                target_value=99.9,  # 99.9% uptime
                measurement_period="monthly",
                warning_threshold=99.5,
                critical_threshold=99.0,
                unit="percentage",
                description="System availability and uptime"
            ),
            SLATarget(
                metric=SLAMetric.RESPONSE_TIME,
                target_value=500.0,  # 500ms average response time
                measurement_period="monthly",
                warning_threshold=750.0,
                critical_threshold=1000.0,
                unit="milliseconds",
                description="Average API response time"
            ),
            SLATarget(
                metric=SLAMetric.ERROR_RATE,
                target_value=0.5,  # 0.5% error rate
                measurement_period="monthly",
                warning_threshold=1.0,
                critical_threshold=2.0,
                unit="percentage",
                description="Error rate for API requests"
            ),
            SLATarget(
                metric=SLAMetric.THROUGHPUT,
                target_value=100.0,  # 100 RPS minimum
                measurement_period="daily",
                warning_threshold=75.0,
                critical_threshold=50.0,
                unit="requests_per_second",
                description="Minimum supported throughput"
            )
        ]

        # Premium tier SLA template
        self.premium_sla_template = [
            SLATarget(
                metric=SLAMetric.AVAILABILITY,
                target_value=99.95,  # 99.95% uptime
                measurement_period="monthly",
                warning_threshold=99.9,
                critical_threshold=99.5,
                unit="percentage",
                description="System availability and uptime"
            ),
            SLATarget(
                metric=SLAMetric.RESPONSE_TIME,
                target_value=250.0,  # 250ms average response time
                measurement_period="monthly",
                warning_threshold=400.0,
                critical_threshold=500.0,
                unit="milliseconds",
                description="Average API response time"
            ),
            SLATarget(
                metric=SLAMetric.ERROR_RATE,
                target_value=0.1,  # 0.1% error rate
                measurement_period="monthly",
                warning_threshold=0.25,
                critical_threshold=0.5,
                unit="percentage",
                description="Error rate for API requests"
            ),
            SLATarget(
                metric=SLAMetric.THROUGHPUT,
                target_value=500.0,  # 500 RPS minimum
                measurement_period="daily",
                warning_threshold=400.0,
                critical_threshold=250.0,
                unit="requests_per_second",
                description="Minimum supported throughput"
            )
        ]

    async def create_sla(self, tenant_id: str, client_id: str, tier: str,
                        contract_start: datetime, contract_end: datetime,
                        custom_targets: list[SLATarget] | None = None) -> ServiceLevelAgreement:
        """Create SLA for a tenant."""

        # Select appropriate template
        if tier == "premium":
            targets = custom_targets or self.premium_sla_template.copy()
        else:  # enterprise or others
            targets = custom_targets or self.enterprise_sla_template.copy()

        sla = ServiceLevelAgreement(
            tenant_id=tenant_id,
            client_id=client_id,
            name=f"{tier.title()} SLA for {tenant_id}",
            description=f"Service Level Agreement for {tier} tier client",
            tier=tier,
            targets=targets,
            contract_start=contract_start,
            contract_end=contract_end
        )

        # Store SLA
        self.slas[sla.sla_id] = sla
        self.tenant_slas[tenant_id] = sla.sla_id

        # Initialize metrics
        self.tenant_metrics[tenant_id] = SLAMetrics(
            tenant_id=tenant_id,
            measurement_period=datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            tenant_id=tenant_id,
            action=f"Created SLA for tenant: {tier} tier",
            details={
                "sla_id": sla.sla_id,
                "tier": tier,
                "targets_count": len(targets),
                "contract_start": contract_start.isoformat(),
                "contract_end": contract_end.isoformat()
            }
        ))

        logger.info(f"Created SLA {sla.sla_id} for tenant {tenant_id} ({tier} tier)")

        return sla

    async def get_sla(self, tenant_id: str) -> ServiceLevelAgreement | None:
        """Get SLA for a tenant."""

        sla_id = self.tenant_slas.get(tenant_id)
        if sla_id:
            return self.slas.get(sla_id)
        return None

    async def record_request(self, tenant_id: str, response_time_ms: float,
                           success: bool, timestamp: datetime | None = None) -> None:
        """Record a request for SLA tracking."""

        if timestamp is None:
            timestamp = datetime.utcnow()

        # Update tenant metrics
        if tenant_id in self.tenant_metrics:
            metrics = self.tenant_metrics[tenant_id]
            metrics.total_requests += 1

            if success:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1

            # Update error rate
            metrics.error_rate_percentage = (metrics.failed_requests / metrics.total_requests) * 100

            # Store request details for analysis
            self.request_history[tenant_id].append((timestamp, success, response_time_ms))
            self.response_times[tenant_id].append(response_time_ms)

            # Update response time metrics
            recent_times = list(self.response_times[tenant_id])
            if recent_times:
                metrics.avg_response_time_ms = sum(recent_times) / len(recent_times)
                sorted_times = sorted(recent_times)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                metrics.p95_response_time_ms = sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0
                metrics.p99_response_time_ms = sorted_times[p99_idx] if p99_idx < len(sorted_times) else 0

        # Check for SLA violations
        await self._check_sla_violations(tenant_id)

    async def record_downtime(self, tenant_id: str, start_time: datetime,
                            end_time: datetime, reason: str) -> None:
        """Record downtime for SLA tracking."""

        duration_minutes = int((end_time - start_time).total_seconds() / 60)

        if tenant_id in self.tenant_metrics:
            metrics = self.tenant_metrics[tenant_id]
            metrics.downtime_minutes += duration_minutes

            # Recalculate uptime percentage
            # This is simplified - in practice you'd track uptime over the measurement period
            total_minutes_in_month = 30 * 24 * 60  # Approximate
            uptime_minutes = total_minutes_in_month - metrics.downtime_minutes
            metrics.uptime_percentage = (uptime_minutes / total_minutes_in_month) * 100

        # Check for availability violations
        await self._check_availability_violation(tenant_id, duration_minutes, reason)

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.SECURITY_INCIDENT,
            tenant_id=tenant_id,
            action=f"System downtime recorded: {duration_minutes} minutes",
            severity=AuditSeverity.HIGH if duration_minutes > 60 else AuditSeverity.MEDIUM,
            details={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": duration_minutes,
                "reason": reason
            }
        ))

    async def _check_sla_violations(self, tenant_id: str) -> None:
        """Check for SLA violations and create violation records."""

        sla = await self.get_sla(tenant_id)
        if not sla:
            return

        metrics = self.tenant_metrics.get(tenant_id)
        if not metrics:
            return

        for target in sla.targets:
            violation_key = f"{tenant_id}_{target.metric.value}"
            current_violation = self.active_violations.get(violation_key)

            # Check each target
            is_violated = False
            actual_value = 0.0

            if target.metric == SLAMetric.RESPONSE_TIME:
                actual_value = metrics.avg_response_time_ms
                is_violated = actual_value > target.target_value

            elif target.metric == SLAMetric.ERROR_RATE:
                actual_value = metrics.error_rate_percentage
                is_violated = actual_value > target.target_value

            elif target.metric == SLAMetric.AVAILABILITY:
                actual_value = metrics.uptime_percentage
                is_violated = actual_value < target.target_value

            elif target.metric == SLAMetric.THROUGHPUT:
                # Calculate recent throughput
                recent_requests = self._calculate_recent_throughput(tenant_id)
                actual_value = recent_requests
                is_violated = actual_value < target.target_value

            # Handle violation state changes
            if is_violated and not current_violation:
                # Start new violation
                await self._start_violation(sla, target, actual_value)

            elif not is_violated and current_violation:
                # End existing violation
                await self._end_violation(current_violation)

            elif current_violation:
                # Update existing violation
                current_violation.actual_value = actual_value

    async def _start_violation(self, sla: ServiceLevelAgreement, target: SLATarget,
                             actual_value: float) -> None:
        """Start a new SLA violation."""

        violation = SLAViolation(
            sla_id=sla.sla_id,
            tenant_id=sla.tenant_id,
            violation_type=self._get_violation_type(target.metric),
            metric=target.metric,
            target_value=target.target_value,
            actual_value=actual_value,
            violation_start=datetime.utcnow()
        )

        # Determine severity
        if target.critical_threshold and actual_value >= target.critical_threshold:
            violation.severity = "critical"
        elif target.warning_threshold and actual_value >= target.warning_threshold:
            violation.severity = "high"
        else:
            violation.severity = "medium"

        # Store violation
        violation_key = f"{sla.tenant_id}_{target.metric.value}"
        self.active_violations[violation_key] = violation
        self.violations.append(violation)

        # Update metrics
        if sla.tenant_id in self.tenant_metrics:
            self.tenant_metrics[sla.tenant_id].active_violations += 1
            self.tenant_metrics[sla.tenant_id].sla_violations += 1

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.SECURITY_INCIDENT,
            tenant_id=sla.tenant_id,
            action=f"SLA violation started: {target.metric.value}",
            severity=AuditSeverity.CRITICAL if violation.severity == "critical" else AuditSeverity.HIGH,
            details={
                "violation_id": violation.violation_id,
                "metric": target.metric.value,
                "target_value": target.target_value,
                "actual_value": actual_value,
                "severity": violation.severity
            }
        ))

        logger.warning(f"SLA violation started for {sla.tenant_id}: {target.metric.value} "
                      f"(target: {target.target_value}, actual: {actual_value})")

    async def _end_violation(self, violation: SLAViolation) -> None:
        """End an active SLA violation."""

        violation.violation_end = datetime.utcnow()
        violation.duration_minutes = int(
            (violation.violation_end - violation.violation_start).total_seconds() / 60
        )
        violation.is_resolved = True

        # Remove from active violations
        violation_key = f"{violation.tenant_id}_{violation.metric.value}"
        if violation_key in self.active_violations:
            del self.active_violations[violation_key]

        # Update metrics
        if violation.tenant_id in self.tenant_metrics:
            self.tenant_metrics[violation.tenant_id].active_violations -= 1

        # Calculate and apply credit
        await self._calculate_sla_credit(violation)

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.SECURITY_INCIDENT,
            tenant_id=violation.tenant_id,
            action=f"SLA violation resolved: {violation.metric.value}",
            severity=AuditSeverity.MEDIUM,
            details={
                "violation_id": violation.violation_id,
                "duration_minutes": violation.duration_minutes,
                "credit_applied": violation.credit_applied,
                "credit_amount": violation.credit_amount
            }
        ))

        logger.info(f"SLA violation resolved for {violation.tenant_id}: {violation.metric.value} "
                   f"(duration: {violation.duration_minutes} minutes)")

    async def _calculate_sla_credit(self, violation: SLAViolation) -> None:
        """Calculate and apply SLA credit for violation."""

        sla = self.slas.get(violation.sla_id)
        if not sla:
            return

        # Calculate credit based on violation duration and severity
        base_credit = sla.credit_percentage_per_violation

        # Severity multiplier
        severity_multiplier = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5,
            "critical": 2.0
        }.get(violation.severity, 1.0)

        # Duration bonus for longer violations
        duration_hours = violation.duration_minutes / 60
        duration_multiplier = 1.0 + (duration_hours / 24)  # +100% for 24-hour violation

        credit_percentage = min(
            base_credit * severity_multiplier * duration_multiplier,
            sla.max_monthly_credit
        )

        violation.credit_applied = True
        violation.credit_amount = credit_percentage

        logger.info(f"SLA credit calculated for {violation.tenant_id}: {credit_percentage}%")

    def _get_violation_type(self, metric: SLAMetric) -> SLAViolationType:
        """Map SLA metric to violation type."""

        mapping = {
            SLAMetric.AVAILABILITY: SLAViolationType.AVAILABILITY,
            SLAMetric.RESPONSE_TIME: SLAViolationType.PERFORMANCE,
            SLAMetric.ERROR_RATE: SLAViolationType.ERROR_RATE,
            SLAMetric.THROUGHPUT: SLAViolationType.THROUGHPUT,
        }
        return mapping.get(metric, SLAViolationType.PERFORMANCE)

    def _calculate_recent_throughput(self, tenant_id: str, minutes: int = 10) -> float:
        """Calculate recent throughput for a tenant."""

        if tenant_id not in self.request_history:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent_requests = [
            req for req in self.request_history[tenant_id]
            if req[0] > cutoff  # req[0] is timestamp
        ]

        if not recent_requests:
            return 0.0

        return len(recent_requests) / (minutes * 60)  # requests per second

    async def _check_availability_violation(self, tenant_id: str,
                                          downtime_minutes: int, reason: str) -> None:
        """Check if downtime causes availability violation."""

        sla = await self.get_sla(tenant_id)
        if not sla:
            return

        # Find availability target
        availability_target = None
        for target in sla.targets:
            if target.metric == SLAMetric.AVAILABILITY:
                availability_target = target
                break

        if not availability_target:
            return

        # Check if downtime causes violation
        metrics = self.tenant_metrics.get(tenant_id)
        if metrics and metrics.uptime_percentage < availability_target.target_value:
            # This will be caught by the regular violation checking
            pass

    async def get_sla_status(self, tenant_id: str) -> SLAStatus | None:
        """Get current SLA status for a tenant."""

        sla = await self.get_sla(tenant_id)
        if not sla:
            return None

        metrics = self.tenant_metrics.get(tenant_id)
        if not metrics:
            return None

        # Calculate target status
        target_status = {}
        targets_met = 0
        targets_at_risk = 0
        targets_violated = 0

        for target in sla.targets:
            status = {"target": target.target_value, "actual": 0.0, "status": "met"}

            if target.metric == SLAMetric.AVAILABILITY:
                status["actual"] = metrics.uptime_percentage
                if metrics.uptime_percentage < target.target_value:
                    status["status"] = "violated"
                    targets_violated += 1
                elif target.warning_threshold and metrics.uptime_percentage < target.warning_threshold:
                    status["status"] = "at_risk"
                    targets_at_risk += 1
                else:
                    targets_met += 1

            elif target.metric == SLAMetric.RESPONSE_TIME:
                status["actual"] = metrics.avg_response_time_ms
                if metrics.avg_response_time_ms > target.target_value:
                    status["status"] = "violated"
                    targets_violated += 1
                elif target.warning_threshold and metrics.avg_response_time_ms > target.warning_threshold:
                    status["status"] = "at_risk"
                    targets_at_risk += 1
                else:
                    targets_met += 1

            elif target.metric == SLAMetric.ERROR_RATE:
                status["actual"] = metrics.error_rate_percentage
                if metrics.error_rate_percentage > target.target_value:
                    status["status"] = "violated"
                    targets_violated += 1
                elif target.warning_threshold and metrics.error_rate_percentage > target.warning_threshold:
                    status["status"] = "at_risk"
                    targets_at_risk += 1
                else:
                    targets_met += 1

            target_status[target.metric] = status

        # Overall status
        overall_status = "compliant"
        if targets_violated > 0:
            overall_status = "violation"
        elif targets_at_risk > 0:
            overall_status = "at_risk"

        # Calculate compliance percentage
        total_targets = len(sla.targets)
        compliance_percentage = (targets_met / total_targets) * 100 if total_targets > 0 else 100

        # Calculate credits
        total_credits = sum(v.credit_amount for v in self.violations
                          if v.tenant_id == tenant_id and v.credit_applied)
        monthly_credits = sum(v.credit_amount for v in self.violations
                            if v.tenant_id == tenant_id and v.credit_applied and
                            v.violation_start.month == datetime.utcnow().month)

        return SLAStatus(
            tenant_id=tenant_id,
            sla_id=sla.sla_id,
            status=overall_status,
            overall_compliance_percentage=compliance_percentage,
            targets_met=targets_met,
            targets_at_risk=targets_at_risk,
            targets_violated=targets_violated,
            target_status=target_status,
            total_credits_earned=total_credits,
            credits_applied_this_month=monthly_credits
        )

    async def get_violations(self, tenant_id: str | None = None,
                           active_only: bool = False) -> list[SLAViolation]:
        """Get SLA violations, optionally filtered by tenant."""

        violations = self.violations

        if tenant_id:
            violations = [v for v in violations if v.tenant_id == tenant_id]

        if active_only:
            violations = [v for v in violations if not v.is_resolved]

        return violations

    async def start_monitoring(self) -> None:
        """Start background SLA monitoring."""

        async def monitoring_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Check every 5 minutes

                    # Check all tenants for violations
                    for tenant_id in self.tenant_metrics.keys():
                        await self._check_sla_violations(tenant_id)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"SLA monitoring error: {e}")

        self._monitoring_task = asyncio.create_task(monitoring_loop())
        logger.info("Started SLA monitoring")

    async def stop_monitoring(self) -> None:
        """Stop background SLA monitoring."""

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            logger.info("Stopped SLA monitoring")

    async def generate_sla_report(self, tenant_id: str, start_date: datetime,
                                end_date: datetime) -> dict[str, Any]:
        """Generate comprehensive SLA report for a tenant."""

        sla = await self.get_sla(tenant_id)
        if not sla:
            return {"error": "No SLA found for tenant"}

        status = await self.get_sla_status(tenant_id)
        violations = await self.get_violations(tenant_id)
        metrics = self.tenant_metrics.get(tenant_id)

        # Filter violations to date range
        period_violations = [
            v for v in violations
            if start_date <= v.violation_start <= end_date
        ]

        return {
            "tenant_id": tenant_id,
            "sla_id": sla.sla_id,
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "sla_status": status.dict() if status else None,
            "metrics": metrics.dict() if metrics else None,
            "violations": [v.dict() for v in period_violations],
            "violation_summary": {
                "total_violations": len(period_violations),
                "by_type": {
                    "availability": len([v for v in period_violations if v.violation_type == SLAViolationType.AVAILABILITY]),
                    "performance": len([v for v in period_violations if v.violation_type == SLAViolationType.PERFORMANCE]),
                    "error_rate": len([v for v in period_violations if v.violation_type == SLAViolationType.ERROR_RATE]),
                    "throughput": len([v for v in period_violations if v.violation_type == SLAViolationType.THROUGHPUT])
                },
                "total_downtime_minutes": sum(v.duration_minutes or 0 for v in period_violations),
                "total_credits": sum(v.credit_amount for v in period_violations if v.credit_applied)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
