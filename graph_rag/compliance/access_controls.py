"""Compliance-focused access controls for SOC2, GDPR, and HIPAA requirements."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .audit_logging import AuditEvent, AuditEventType, AuditSeverity, ComplianceAuditLogger

logger = logging.getLogger(__name__)


class AccessControlFramework(str, Enum):
    """Compliance frameworks that require access controls."""

    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    NIST = "nist"


class SessionSecurityLevel(str, Enum):
    """Session security levels based on compliance requirements."""

    STANDARD = "standard"         # Basic session management
    ENHANCED = "enhanced"         # MFA required, enhanced monitoring
    HIGH_SECURITY = "high_security"  # Short timeouts, continuous validation
    CRITICAL = "critical"         # Maximum security for sensitive data


@dataclass
class AccessControlPolicy:
    """Access control policy for compliance frameworks."""

    policy_id: str
    name: str
    framework: AccessControlFramework

    # Session management
    session_timeout_minutes: int = 480  # 8 hours default
    idle_timeout_minutes: int = 60      # 1 hour idle timeout
    max_concurrent_sessions: int = 5
    require_mfa: bool = False

    # Password policies
    min_password_length: int = 12
    require_password_complexity: bool = True
    password_expiry_days: int = 90
    password_history_count: int = 12

    # Account lockout
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    progressive_lockout: bool = True

    # Access monitoring
    monitor_failed_logins: bool = True
    monitor_privileged_access: bool = True
    monitor_data_access: bool = True
    alert_on_suspicious_activity: bool = True

    # IP and location restrictions
    allowed_ip_ranges: list[str] = None
    geo_restrictions: list[str] = None
    require_vpn: bool = False

    # Time-based access
    allowed_hours: dict[str, str] | None = None  # {"monday": "09:00-17:00"}
    timezone: str = "UTC"

    # Data access controls
    data_classification_required: bool = True
    audit_all_access: bool = True
    require_justification: bool = False

    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    """Enhanced session state tracking for compliance."""

    session_id: str
    user_id: UUID
    tenant_id: str

    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

    # Security context
    security_level: SessionSecurityLevel = SessionSecurityLevel.STANDARD
    mfa_verified: bool = False
    mfa_method: str | None = None
    source_ip: str
    user_agent: str
    location: str | None = None

    # Risk assessment
    risk_score: float = 0.0  # 0-100 risk score
    suspicious_activity: bool = False
    anomaly_flags: list[str] = Field(default_factory=list)

    # Compliance tracking
    compliance_frameworks: list[AccessControlFramework] = Field(default_factory=list)
    data_accessed: set[str] = Field(default_factory=set)
    privileged_actions: list[str] = Field(default_factory=list)

    # Session limits
    max_idle_minutes: int = 60
    max_session_minutes: int = 480
    concurrent_session_count: int = 1

    is_active: bool = True

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
            set: list
        }

    def is_expired(self) -> bool:
        """Check if session is expired."""
        now = datetime.utcnow()
        return now > self.expires_at or (now - self.last_activity).total_seconds() > (self.max_idle_minutes * 60)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def add_anomaly(self, anomaly_type: str) -> None:
        """Add anomaly flag to session."""
        if anomaly_type not in self.anomaly_flags:
            self.anomaly_flags.append(anomaly_type)
            self.suspicious_activity = True
            # Increase risk score
            self.risk_score = min(100.0, self.risk_score + 20.0)


class ComplianceAccessController:
    """Access controller with comprehensive compliance features."""

    def __init__(self, audit_logger: ComplianceAuditLogger):
        self.audit_logger = audit_logger

        # Policy storage
        self.policies: dict[str, AccessControlPolicy] = {}

        # Session tracking
        self.active_sessions: dict[str, SessionState] = {}
        self.user_sessions: dict[UUID, list[str]] = {}

        # Lockout tracking
        self.failed_attempts: dict[str, list[datetime]] = {}
        self.locked_accounts: dict[str, datetime] = {}

        # Anomaly detection state
        self.login_patterns: dict[UUID, dict[str, Any]] = {}

        # Initialize default policies
        self._create_default_policies()

    def _create_default_policies(self) -> None:
        """Create default access control policies for compliance frameworks."""

        # SOC2 Policy
        soc2_policy = AccessControlPolicy(
            policy_id="soc2_standard",
            name="SOC2 Access Control Policy",
            framework=AccessControlFramework.SOC2,
            session_timeout_minutes=480,  # 8 hours
            idle_timeout_minutes=60,      # 1 hour
            max_concurrent_sessions=3,
            min_password_length=12,
            require_password_complexity=True,
            password_expiry_days=90,
            max_failed_attempts=5,
            lockout_duration_minutes=30,
            monitor_privileged_access=True,
            audit_all_access=True
        )

        # GDPR Policy
        gdpr_policy = AccessControlPolicy(
            policy_id="gdpr_privacy",
            name="GDPR Privacy Access Control",
            framework=AccessControlFramework.GDPR,
            session_timeout_minutes=240,  # 4 hours for privacy-sensitive data
            idle_timeout_minutes=30,      # 30 min idle
            require_mfa=True,
            min_password_length=14,
            password_expiry_days=60,
            max_failed_attempts=3,
            monitor_data_access=True,
            require_justification=True,
            data_classification_required=True
        )

        # HIPAA Policy
        hipaa_policy = AccessControlPolicy(
            policy_id="hipaa_healthcare",
            name="HIPAA Healthcare Access Control",
            framework=AccessControlFramework.HIPAA,
            session_timeout_minutes=120,  # 2 hours for PHI
            idle_timeout_minutes=15,      # 15 min idle for PHI
            max_concurrent_sessions=1,    # Single session for PHI access
            require_mfa=True,
            min_password_length=16,
            require_password_complexity=True,
            password_expiry_days=45,
            max_failed_attempts=3,
            lockout_duration_minutes=60,
            monitor_data_access=True,
            audit_all_access=True,
            require_justification=True,
            allowed_hours={"monday": "06:00-22:00", "tuesday": "06:00-22:00",
                          "wednesday": "06:00-22:00", "thursday": "06:00-22:00",
                          "friday": "06:00-22:00", "saturday": "08:00-18:00",
                          "sunday": "08:00-18:00"}
        )

        self.policies = {
            soc2_policy.policy_id: soc2_policy,
            gdpr_policy.policy_id: gdpr_policy,
            hipaa_policy.policy_id: hipaa_policy
        }

    def get_policy_for_framework(self, framework: AccessControlFramework) -> AccessControlPolicy | None:
        """Get access control policy for compliance framework."""
        for policy in self.policies.values():
            if policy.framework == framework and policy.is_active:
                return policy
        return None

    async def create_session(self, user_id: UUID, tenant_id: str, source_ip: str,
                           user_agent: str, security_level: SessionSecurityLevel = SessionSecurityLevel.STANDARD,
                           compliance_frameworks: list[AccessControlFramework] = None) -> SessionState:
        """Create new session with compliance controls."""

        # Determine applicable policies
        if not compliance_frameworks:
            compliance_frameworks = [AccessControlFramework.SOC2]  # Default

        # Get most restrictive policy
        applicable_policies = [self.get_policy_for_framework(fw) for fw in compliance_frameworks]
        applicable_policies = [p for p in applicable_policies if p is not None]

        if not applicable_policies:
            raise ValueError("No applicable access control policy found")

        # Use most restrictive settings
        min_session_timeout = min(p.session_timeout_minutes for p in applicable_policies)
        min_idle_timeout = min(p.idle_timeout_minutes for p in applicable_policies)
        max_concurrent = min(p.max_concurrent_sessions for p in applicable_policies)
        require_mfa = any(p.require_mfa for p in applicable_policies)

        # Check concurrent session limits
        user_session_count = len(self.user_sessions.get(user_id, []))
        if user_session_count >= max_concurrent:
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.ACCESS_DENIED,
                user_id=user_id,
                tenant_id=tenant_id,
                source_ip=source_ip,
                action="Session creation denied - concurrent session limit exceeded",
                outcome="failure",
                severity=AuditSeverity.HIGH,
                details={"concurrent_sessions": user_session_count, "limit": max_concurrent}
            ))
            raise ValueError(f"Concurrent session limit exceeded: {user_session_count}/{max_concurrent}")

        # Create session
        import secrets
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=min_session_timeout)

        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            expires_at=expires_at,
            security_level=security_level,
            source_ip=source_ip,
            user_agent=user_agent,
            compliance_frameworks=compliance_frameworks,
            max_idle_minutes=min_idle_timeout,
            max_session_minutes=min_session_timeout,
            concurrent_session_count=user_session_count + 1
        )

        # Check for anomalies in login pattern
        await self._detect_login_anomalies(user_id, source_ip, user_agent, session)

        # Store session
        self.active_sessions[session_id] = session
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.USER_LOGIN,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            source_ip=source_ip,
            user_agent=user_agent,
            action="Session created with compliance controls",
            details={
                "security_level": security_level.value,
                "compliance_frameworks": [fw.value for fw in compliance_frameworks],
                "session_timeout": min_session_timeout,
                "require_mfa": require_mfa,
                "risk_score": session.risk_score
            },
            compliance_frameworks=[fw.value for fw in compliance_frameworks]
        ))

        logger.info(f"Created session {session_id} for user {user_id} with {security_level.value} security")

        return session

    async def validate_session(self, session_id: str) -> SessionState | None:
        """Validate session and check compliance controls."""
        session = self.active_sessions.get(session_id)
        if not session:
            return None

        # Check if session is expired
        if session.is_expired():
            await self.terminate_session(session_id, reason="expired")
            return None

        # Update activity
        session.update_activity()

        # Check risk score - terminate if too high
        if session.risk_score > 80.0:
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.SECURITY_INCIDENT,
                user_id=session.user_id,
                tenant_id=session.tenant_id,
                session_id=session_id,
                action="Session terminated due to high risk score",
                severity=AuditSeverity.CRITICAL,
                details={"risk_score": session.risk_score, "anomalies": session.anomaly_flags}
            ))
            await self.terminate_session(session_id, reason="high_risk")
            return None

        return session

    async def record_data_access(self, session_id: str, resource_type: str,
                               resource_id: str, data_classification: str,
                               justification: str | None = None) -> None:
        """Record data access for compliance monitoring."""
        session = await self.validate_session(session_id)
        if not session:
            raise ValueError("Invalid session")

        # Check if justification is required
        applicable_policies = [self.get_policy_for_framework(fw) for fw in session.compliance_frameworks]
        require_justification = any(p and p.require_justification for p in applicable_policies)

        if require_justification and not justification:
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.ACCESS_DENIED,
                user_id=session.user_id,
                tenant_id=session.tenant_id,
                session_id=session_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action="Data access denied - justification required",
                outcome="failure",
                data_classification=data_classification
            ))
            raise ValueError("Justification required for data access")

        # Record access
        access_key = f"{resource_type}:{resource_id}"
        session.data_accessed.add(access_key)

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.DATA_ACCESSED,
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=f"Accessed {resource_type} data",
            data_classification=data_classification,
            personal_data_involved=data_classification in ["pii", "phi"],
            details={"justification": justification} if justification else {},
            compliance_frameworks=[fw.value for fw in session.compliance_frameworks]
        ))

    async def record_privileged_action(self, session_id: str, action: str,
                                     target_resource: str | None = None) -> None:
        """Record privileged action for SOC2 compliance."""
        session = await self.validate_session(session_id)
        if not session:
            raise ValueError("Invalid session")

        session.privileged_actions.append(action)

        # Audit log with high severity
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.ACCESS_GRANTED,
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            session_id=session_id,
            action=f"Privileged action: {action}",
            resource_id=target_resource,
            severity=AuditSeverity.HIGH,
            details={"privileged_action": action, "target": target_resource},
            compliance_frameworks=[fw.value for fw in session.compliance_frameworks]
        ))

        logger.warning(f"Privileged action by user {session.user_id}: {action}")

    async def record_failed_login(self, username: str, source_ip: str,
                                reason: str = "invalid_credentials") -> bool:
        """Record failed login and check lockout policies."""
        now = datetime.utcnow()
        key = f"{username}:{source_ip}"

        # Initialize failed attempts list
        if key not in self.failed_attempts:
            self.failed_attempts[key] = []

        # Add failed attempt
        self.failed_attempts[key].append(now)

        # Clean old attempts (last hour)
        cutoff = now - timedelta(hours=1)
        self.failed_attempts[key] = [attempt for attempt in self.failed_attempts[key] if attempt > cutoff]

        # Check if account should be locked
        attempts_count = len(self.failed_attempts[key])

        # Get lockout policy (use most restrictive)
        max_attempts = 5
        lockout_minutes = 30

        for policy in self.policies.values():
            if policy.is_active:
                max_attempts = min(max_attempts, policy.max_failed_attempts)
                lockout_minutes = max(lockout_minutes, policy.lockout_duration_minutes)

        should_lock = attempts_count >= max_attempts

        if should_lock:
            lockout_until = now + timedelta(minutes=lockout_minutes)
            self.locked_accounts[username] = lockout_until

            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.LOGIN_FAILED,
                username=username,
                source_ip=source_ip,
                action=f"Account locked due to {attempts_count} failed login attempts",
                outcome="failure",
                severity=AuditSeverity.HIGH,
                details={
                    "failed_attempts": attempts_count,
                    "lockout_until": lockout_until.isoformat(),
                    "reason": reason
                }
            ))

            logger.warning(f"Account locked: {username} from {source_ip} - {attempts_count} failed attempts")
        else:
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.LOGIN_FAILED,
                username=username,
                source_ip=source_ip,
                action="Login failed",
                outcome="failure",
                details={"failed_attempts": attempts_count, "reason": reason}
            ))

        return should_lock

    def is_account_locked(self, username: str) -> bool:
        """Check if account is currently locked."""
        if username not in self.locked_accounts:
            return False

        lockout_until = self.locked_accounts[username]
        if datetime.utcnow() > lockout_until:
            # Lock expired
            del self.locked_accounts[username]
            return False

        return True

    async def terminate_session(self, session_id: str, reason: str = "logout") -> None:
        """Terminate session with audit logging."""
        session = self.active_sessions.get(session_id)
        if not session:
            return

        # Remove from tracking
        del self.active_sessions[session_id]

        user_sessions = self.user_sessions.get(session.user_id, [])
        if session_id in user_sessions:
            user_sessions.remove(session_id)
            if not user_sessions:
                del self.user_sessions[session.user_id]

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.USER_LOGOUT,
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            session_id=session_id,
            action=f"Session terminated: {reason}",
            details={
                "reason": reason,
                "session_duration_minutes": (datetime.utcnow() - session.created_at).total_seconds() / 60,
                "data_accessed_count": len(session.data_accessed),
                "privileged_actions_count": len(session.privileged_actions),
                "final_risk_score": session.risk_score
            },
            compliance_frameworks=[fw.value for fw in session.compliance_frameworks]
        ))

        logger.info(f"Terminated session {session_id}: {reason}")

    async def _detect_login_anomalies(self, user_id: UUID, source_ip: str,
                                    user_agent: str, session: SessionState) -> None:
        """Detect anomalies in login patterns."""

        # Initialize user pattern tracking
        if user_id not in self.login_patterns:
            self.login_patterns[user_id] = {
                'known_ips': set(),
                'known_user_agents': set(),
                'login_times': [],
                'geographic_locations': set()
            }

        patterns = self.login_patterns[user_id]

        # Check for new IP
        if source_ip not in patterns['known_ips']:
            if len(patterns['known_ips']) > 0:  # Not first login
                session.add_anomaly("new_ip_address")
                logger.warning(f"New IP address for user {user_id}: {source_ip}")
        patterns['known_ips'].add(source_ip)

        # Check for new user agent
        if user_agent not in patterns['known_user_agents']:
            if len(patterns['known_user_agents']) > 0:  # Not first login
                session.add_anomaly("new_user_agent")
        patterns['known_user_agents'].add(user_agent)

        # Check for unusual login times (simple heuristic)
        now = datetime.utcnow()
        hour = now.hour

        # Track login times
        patterns['login_times'].append(hour)
        if len(patterns['login_times']) > 50:  # Keep last 50 logins
            patterns['login_times'] = patterns['login_times'][-50:]

        # Check if login time is unusual (outside normal hours if we have enough data)
        if len(patterns['login_times']) > 10:
            common_hours = set(patterns['login_times'][-10:])  # Last 10 login hours
            if hour not in common_hours and (hour < 6 or hour > 22):  # Outside business hours
                session.add_anomaly("unusual_login_time")

        # Multiple rapid logins from different IPs (potential attack)
        recent_logins = [s for s in self.active_sessions.values()
                        if s.user_id == user_id and
                        (datetime.utcnow() - s.created_at).total_seconds() < 300]  # Last 5 minutes

        if len(recent_logins) > 1:
            unique_ips = {s.source_ip for s in recent_logins}
            if len(unique_ips) > 1:
                session.add_anomaly("multiple_concurrent_ips")
                logger.warning(f"Multiple concurrent IPs for user {user_id}: {unique_ips}")

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and tracking data."""
        now = datetime.utcnow()
        expired_sessions = []

        for session_id, session in list(self.active_sessions.items()):
            if session.is_expired():
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.terminate_session(session_id, reason="expired")

        # Clean up old failed attempts
        cutoff = now - timedelta(hours=24)
        for key in list(self.failed_attempts.keys()):
            self.failed_attempts[key] = [attempt for attempt in self.failed_attempts[key] if attempt > cutoff]
            if not self.failed_attempts[key]:
                del self.failed_attempts[key]

        # Clean up expired lockouts
        for username in list(self.locked_accounts.keys()):
            if now > self.locked_accounts[username]:
                del self.locked_accounts[username]

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    async def get_compliance_status(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get access control compliance status."""
        now = datetime.utcnow()

        # Filter sessions by tenant if specified
        relevant_sessions = [
            s for s in self.active_sessions.values()
            if not tenant_id or s.tenant_id == tenant_id
        ]

        # Calculate metrics
        total_sessions = len(relevant_sessions)
        high_risk_sessions = len([s for s in relevant_sessions if s.risk_score > 50])
        mfa_sessions = len([s for s in relevant_sessions if s.mfa_verified])
        suspicious_sessions = len([s for s in relevant_sessions if s.suspicious_activity])

        # Lockout statistics
        active_lockouts = len([u for u, until in self.locked_accounts.items() if now < until])

        return {
            'active_sessions': total_sessions,
            'high_risk_sessions': high_risk_sessions,
            'mfa_protected_sessions': mfa_sessions,
            'suspicious_sessions': suspicious_sessions,
            'active_lockouts': active_lockouts,
            'compliance_health': 'healthy' if high_risk_sessions == 0 and suspicious_sessions == 0 else 'warning',
            'average_risk_score': sum(s.risk_score for s in relevant_sessions) / max(1, total_sessions),
            'generated_at': now.isoformat()
        }
