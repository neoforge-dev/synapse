"""Automatic key rotation system for enterprise security compliance."""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

import schedule

from .vault_key_manager import VaultKeyManager

logger = logging.getLogger(__name__)


class RotationStatus(Enum):
    """Key rotation status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class KeyRotationPolicy:
    """Policy defining key rotation requirements."""
    key_type: str
    rotation_interval_days: int
    compliance_framework: str  # HIPAA, PCI-DSS, GDPR, etc.
    max_key_age_days: int
    rotation_window_hours: list[int] = field(default_factory=lambda: [2, 3, 4])  # 2-4 AM UTC
    notification_days_before: int = 7
    automatic_rotation: bool = True
    require_approval: bool = False
    backup_retention_days: int = 365

    def __post_init__(self):
        """Validate policy configuration."""
        if self.rotation_interval_days <= 0:
            raise ValueError("Rotation interval must be positive")
        if self.max_key_age_days < self.rotation_interval_days:
            raise ValueError("Max key age must be >= rotation interval")


@dataclass
class RotationSchedule:
    """Scheduled key rotation entry."""
    tenant_id: UUID
    key_type: str
    policy: KeyRotationPolicy
    next_rotation: datetime
    status: RotationStatus = RotationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_rotation_attempt: datetime | None = None
    rotation_history: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


class AutomaticKeyRotation:
    """Automatic key rotation service for enterprise security compliance."""

    def __init__(self, vault_manager: VaultKeyManager):
        """Initialize automatic key rotation service."""
        self.vault_manager = vault_manager
        self.rotation_schedules: dict[str, RotationSchedule] = {}
        self.rotation_policies: dict[str, KeyRotationPolicy] = {}

        # Initialize default policies
        self._setup_default_policies()

        # Rotation callbacks
        self.pre_rotation_callbacks: list[Callable] = []
        self.post_rotation_callbacks: list[Callable] = []

        # Metrics
        self.rotation_metrics = {
            "total_rotations": 0,
            "successful_rotations": 0,
            "failed_rotations": 0,
            "average_rotation_time": 0.0,
            "last_rotation_time": None,
            "tenants_with_active_schedules": 0
        }

        # Start scheduler
        self.scheduler_running = False
        self._setup_scheduler()

        logger.info("Initialized AutomaticKeyRotation service")

    def _setup_default_policies(self):
        """Setup default rotation policies for compliance frameworks."""

        # HIPAA compliance policy - 30 days
        self.rotation_policies["hipaa"] = KeyRotationPolicy(
            key_type="encryption",
            rotation_interval_days=30,
            compliance_framework="HIPAA",
            max_key_age_days=35,
            notification_days_before=7,
            automatic_rotation=True,
            require_approval=False
        )

        # PCI-DSS compliance policy - 90 days
        self.rotation_policies["pci_dss"] = KeyRotationPolicy(
            key_type="encryption",
            rotation_interval_days=90,
            compliance_framework="PCI-DSS",
            max_key_age_days=95,
            notification_days_before=14,
            automatic_rotation=True,
            require_approval=True
        )

        # GDPR compliance policy - 365 days
        self.rotation_policies["gdpr"] = KeyRotationPolicy(
            key_type="encryption",
            rotation_interval_days=365,
            compliance_framework="GDPR",
            max_key_age_days=370,
            notification_days_before=30,
            automatic_rotation=True,
            require_approval=False
        )

        # High-security enterprise policy - 7 days
        self.rotation_policies["high_security"] = KeyRotationPolicy(
            key_type="encryption",
            rotation_interval_days=7,
            compliance_framework="Enterprise-HighSec",
            max_key_age_days=10,
            notification_days_before=1,
            automatic_rotation=True,
            require_approval=False,
            rotation_window_hours=[1, 2, 3, 4, 5]  # Extended window for frequent rotation
        )

        logger.info(f"Setup {len(self.rotation_policies)} default rotation policies")

    def register_tenant(self, tenant_id: UUID, policy_name: str) -> bool:
        """Register tenant for automatic key rotation."""
        if policy_name not in self.rotation_policies:
            logger.error(f"Unknown rotation policy: {policy_name}")
            return False

        policy = self.rotation_policies[policy_name]
        schedule_key = f"{tenant_id}:{policy.key_type}"

        # Calculate next rotation time
        next_rotation = datetime.utcnow() + timedelta(days=policy.rotation_interval_days)
        # Adjust to rotation window (default 2-4 AM UTC)
        next_rotation = next_rotation.replace(
            hour=policy.rotation_window_hours[0],
            minute=0,
            second=0,
            microsecond=0
        )

        # Create rotation schedule
        schedule = RotationSchedule(
            tenant_id=tenant_id,
            key_type=policy.key_type,
            policy=policy,
            next_rotation=next_rotation
        )

        self.rotation_schedules[schedule_key] = schedule
        self.rotation_metrics["tenants_with_active_schedules"] = len(
            {s.tenant_id for s in self.rotation_schedules.values()}
        )

        logger.info(f"Registered tenant {tenant_id} for {policy_name} key rotation")
        return True

    def unregister_tenant(self, tenant_id: UUID, key_type: str = "encryption") -> bool:
        """Unregister tenant from automatic key rotation."""
        schedule_key = f"{tenant_id}:{key_type}"

        if schedule_key in self.rotation_schedules:
            del self.rotation_schedules[schedule_key]
            self.rotation_metrics["tenants_with_active_schedules"] = len(
                {s.tenant_id for s in self.rotation_schedules.values()}
            )
            logger.info(f"Unregistered tenant {tenant_id} from key rotation")
            return True

        return False

    def force_rotation(self, tenant_id: UUID, key_type: str = "encryption") -> dict[str, Any]:
        """Force immediate key rotation for tenant."""
        start_time = time.time()

        try:
            # Execute rotation
            result = self._execute_key_rotation(tenant_id, key_type, force=True)

            rotation_time = time.time() - start_time

            if result["success"]:
                self.rotation_metrics["successful_rotations"] += 1
                logger.info(f"Force rotation successful for tenant {tenant_id}")
            else:
                self.rotation_metrics["failed_rotations"] += 1
                logger.error(f"Force rotation failed for tenant {tenant_id}: {result['error']}")

            self.rotation_metrics["total_rotations"] += 1
            self._update_average_rotation_time(rotation_time)

            return result

        except Exception as e:
            logger.error(f"Force rotation exception for tenant {tenant_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def run_scheduler(self):
        """Run the key rotation scheduler."""
        self.scheduler_running = True
        logger.info("Started key rotation scheduler")

        while self.scheduler_running:
            try:
                await self._check_pending_rotations()
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                await asyncio.sleep(60)

    def stop_scheduler(self):
        """Stop the key rotation scheduler."""
        self.scheduler_running = False
        logger.info("Stopped key rotation scheduler")

    async def _check_pending_rotations(self):
        """Check for and execute pending rotations."""
        current_time = datetime.utcnow()

        for _schedule_key, schedule in self.rotation_schedules.items():
            if (schedule.status == RotationStatus.PENDING and
                current_time >= schedule.next_rotation):

                # Check if we're in the rotation window
                current_hour = current_time.hour
                if current_hour in schedule.policy.rotation_window_hours:
                    await self._execute_scheduled_rotation(schedule)

    async def _execute_scheduled_rotation(self, schedule: RotationSchedule):
        """Execute a scheduled rotation."""
        schedule.status = RotationStatus.IN_PROGRESS
        schedule.last_rotation_attempt = datetime.utcnow()

        try:
            # Execute pre-rotation callbacks
            await self._execute_callbacks(self.pre_rotation_callbacks, schedule)

            # Perform rotation
            result = self._execute_key_rotation(
                schedule.tenant_id,
                schedule.key_type,
                force=False
            )

            if result["success"]:
                # Update schedule for next rotation
                schedule.status = RotationStatus.COMPLETED
                schedule.next_rotation = datetime.utcnow() + timedelta(
                    days=schedule.policy.rotation_interval_days
                )
                schedule.retry_count = 0

                # Add to history
                schedule.rotation_history.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "completed",
                    "old_version": result.get("old_version"),
                    "new_version": result.get("new_version"),
                    "rotation_time": result.get("rotation_time")
                })

                self.rotation_metrics["successful_rotations"] += 1
                logger.info(f"Scheduled rotation completed for tenant {schedule.tenant_id}")

                # Execute post-rotation callbacks
                await self._execute_callbacks(self.post_rotation_callbacks, schedule)

            else:
                self._handle_rotation_failure(schedule, result["error"])

            self.rotation_metrics["total_rotations"] += 1

        except Exception as e:
            self._handle_rotation_failure(schedule, str(e))

        finally:
            if schedule.status == RotationStatus.IN_PROGRESS:
                schedule.status = RotationStatus.PENDING  # Reset if still in progress

    def _execute_key_rotation(self, tenant_id: UUID, key_type: str, force: bool = False) -> dict[str, Any]:
        """Execute actual key rotation using Vault manager."""
        start_time = time.time()

        try:
            # Rotate master key in Vault
            rotation_result = self.vault_manager.rotate_master_key(tenant_id, key_type)

            rotation_time = time.time() - start_time

            result = {
                "success": True,
                "tenant_id": str(tenant_id),
                "key_type": key_type,
                "old_version": rotation_result["old_version"],
                "new_version": rotation_result["new_version"],
                "rotated_at": rotation_result["rotated_at"],
                "rotation_time": rotation_time,
                "forced": force
            }

            self._update_average_rotation_time(rotation_time)
            self.rotation_metrics["last_rotation_time"] = datetime.utcnow().isoformat()

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tenant_id": str(tenant_id),
                "key_type": key_type,
                "forced": force
            }

    def _handle_rotation_failure(self, schedule: RotationSchedule, error: str):
        """Handle rotation failure with retry logic."""
        schedule.retry_count += 1

        if schedule.retry_count >= schedule.max_retries:
            schedule.status = RotationStatus.FAILED
            logger.error(f"Rotation failed permanently for tenant {schedule.tenant_id}: {error}")

            # Add failure to history
            schedule.rotation_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": error,
                "retry_count": schedule.retry_count
            })

        else:
            # Schedule retry
            schedule.status = RotationStatus.PENDING
            retry_delay = min(2 ** schedule.retry_count, 24)  # Exponential backoff, max 24h
            schedule.next_rotation = datetime.utcnow() + timedelta(hours=retry_delay)

            logger.warning(f"Rotation failed for tenant {schedule.tenant_id}, retry {schedule.retry_count}/{schedule.max_retries} in {retry_delay}h: {error}")

        self.rotation_metrics["failed_rotations"] += 1

    async def _execute_callbacks(self, callbacks: list[Callable], schedule: RotationSchedule):
        """Execute rotation callbacks."""
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(schedule)
                else:
                    callback(schedule)
            except Exception as e:
                logger.error(f"Callback error during rotation: {str(e)}")

    def add_pre_rotation_callback(self, callback: Callable):
        """Add callback to execute before rotation."""
        self.pre_rotation_callbacks.append(callback)

    def add_post_rotation_callback(self, callback: Callable):
        """Add callback to execute after rotation."""
        self.post_rotation_callbacks.append(callback)

    def _update_average_rotation_time(self, rotation_time: float):
        """Update average rotation time metric."""
        current_avg = self.rotation_metrics["average_rotation_time"]
        total_rotations = self.rotation_metrics["total_rotations"]

        if total_rotations > 0:
            self.rotation_metrics["average_rotation_time"] = (
                (current_avg * (total_rotations - 1) + rotation_time) / total_rotations
            )
        else:
            self.rotation_metrics["average_rotation_time"] = rotation_time

    def _setup_scheduler(self):
        """Setup scheduled tasks using schedule library."""
        # Daily check for overdue rotations
        schedule.every().day.at("01:00").do(self._check_overdue_rotations)

        # Weekly compliance report
        schedule.every().monday.at("09:00").do(self._generate_compliance_report)

        # Hourly metrics update
        schedule.every().hour.do(self._update_metrics)

    def _check_overdue_rotations(self):
        """Check for overdue key rotations."""
        current_time = datetime.utcnow()
        overdue_schedules = []

        for schedule_key, schedule in self.rotation_schedules.items():
            if schedule.status in [RotationStatus.PENDING, RotationStatus.FAILED]:
                days_overdue = (current_time - schedule.next_rotation).days
                if days_overdue > 0:
                    overdue_schedules.append({
                        "schedule_key": schedule_key,
                        "tenant_id": schedule.tenant_id,
                        "days_overdue": days_overdue,
                        "policy": schedule.policy.compliance_framework
                    })

        if overdue_schedules:
            logger.warning(f"Found {len(overdue_schedules)} overdue key rotations")

            # Force rotation for critically overdue keys
            for overdue in overdue_schedules:
                if overdue["days_overdue"] > 7:  # More than a week overdue
                    self.force_rotation(overdue["tenant_id"])

    def _generate_compliance_report(self) -> dict[str, Any]:
        """Generate compliance report for key rotation status."""
        report = {
            "report_date": datetime.utcnow().isoformat(),
            "total_tenants": len({s.tenant_id for s in self.rotation_schedules.values()}),
            "total_schedules": len(self.rotation_schedules),
            "metrics": self.rotation_metrics.copy(),
            "compliance_status": {},
            "overdue_rotations": [],
            "upcoming_rotations": []
        }

        current_time = datetime.utcnow()

        # Analyze compliance by framework
        for _policy_name, policy in self.rotation_policies.items():
            matching_schedules = [
                s for s in self.rotation_schedules.values()
                if s.policy.compliance_framework == policy.compliance_framework
            ]

            compliant = sum(1 for s in matching_schedules if s.status == RotationStatus.COMPLETED)
            overdue = sum(1 for s in matching_schedules if current_time > s.next_rotation)

            report["compliance_status"][policy.compliance_framework] = {
                "total_schedules": len(matching_schedules),
                "compliant": compliant,
                "overdue": overdue,
                "compliance_rate": (compliant / max(len(matching_schedules), 1)) * 100
            }

        # Find overdue and upcoming rotations
        for schedule in self.rotation_schedules.values():
            days_until_rotation = (schedule.next_rotation - current_time).days

            if days_until_rotation < 0:
                report["overdue_rotations"].append({
                    "tenant_id": str(schedule.tenant_id),
                    "days_overdue": abs(days_until_rotation),
                    "compliance_framework": schedule.policy.compliance_framework
                })
            elif days_until_rotation <= 7:
                report["upcoming_rotations"].append({
                    "tenant_id": str(schedule.tenant_id),
                    "days_until_rotation": days_until_rotation,
                    "compliance_framework": schedule.policy.compliance_framework
                })

        logger.info(f"Generated compliance report: {report['compliance_status']}")
        return report

    def _update_metrics(self):
        """Update rotation metrics."""
        self.rotation_metrics["tenants_with_active_schedules"] = len(
            {s.tenant_id for s in self.rotation_schedules.values()}
        )

    def get_tenant_rotation_status(self, tenant_id: UUID) -> dict[str, Any]:
        """Get rotation status for specific tenant."""
        tenant_schedules = [
            s for s in self.rotation_schedules.values()
            if s.tenant_id == tenant_id
        ]

        if not tenant_schedules:
            return {"tenant_id": str(tenant_id), "status": "not_registered"}

        status = {
            "tenant_id": str(tenant_id),
            "schedules": [],
            "overall_status": "compliant"
        }

        current_time = datetime.utcnow()

        for schedule in tenant_schedules:
            schedule_info = {
                "key_type": schedule.key_type,
                "policy": schedule.policy.compliance_framework,
                "status": schedule.status.value,
                "next_rotation": schedule.next_rotation.isoformat(),
                "days_until_rotation": (schedule.next_rotation - current_time).days,
                "rotation_history": schedule.rotation_history[-5:]  # Last 5 rotations
            }

            if schedule.status == RotationStatus.FAILED or current_time > schedule.next_rotation:
                status["overall_status"] = "non_compliant"

            status["schedules"].append(schedule_info)

        return status

    def get_rotation_metrics(self) -> dict[str, Any]:
        """Get comprehensive rotation metrics."""
        return {
            **self.rotation_metrics,
            "active_policies": list(self.rotation_policies.keys()),
            "scheduler_running": self.scheduler_running,
            "total_active_schedules": len(self.rotation_schedules)
        }
