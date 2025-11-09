"""Comprehensive audit logging for enterprise compliance (SOC2, GDPR, HIPAA)."""

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of auditable events for compliance frameworks."""

    # Authentication events (SOC2, GDPR, HIPAA)
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"

    # Authorization events (SOC2, HIPAA)
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGED = "permission_changed"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # Data access events (GDPR, HIPAA)
    DATA_ACCESSED = "data_accessed"
    DATA_EXPORTED = "data_exported"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"

    # System events (SOC2)
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    SYSTEM_MAINTENANCE = "system_maintenance"

    # Privacy events (GDPR)
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    DATA_SUBJECT_REQUEST = "data_subject_request"
    DATA_BREACH_DETECTED = "data_breach_detected"
    RIGHT_TO_ERASURE = "right_to_erasure"
    DATA_PORTABILITY = "data_portability"

    # Security events (SOC2, HIPAA)
    SECURITY_INCIDENT = "security_incident"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ENCRYPTION_KEY_ROTATED = "encryption_key_rotated"

    # API events (SOC2)
    API_CALL = "api_call"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Administrative events (SOC2, HIPAA)
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_DEACTIVATED = "user_deactivated"
    TENANT_CREATED = "tenant_created"
    SSO_CONFIGURED = "sso_configured"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Comprehensive audit event model for compliance logging."""

    # Event identification
    event_id: UUID = Field(default_factory=uuid4)
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: AuditSeverity = Field(default=AuditSeverity.MEDIUM)

    # Actor (who performed the action)
    user_id: UUID | None = None
    username: str | None = None
    user_role: str | None = None
    session_id: str | None = None

    # Context (where and how)
    tenant_id: str | None = None
    client_id: str | None = None
    source_ip: str | None = None
    user_agent: str | None = None
    api_endpoint: str | None = None
    http_method: str | None = None

    # Target (what was affected)
    resource_type: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None

    # Event details
    action: str  # Human-readable action description
    outcome: str = "success"  # success, failure, partial
    details: dict[str, Any] = Field(default_factory=dict)

    # Data fields (for GDPR/HIPAA)
    data_classification: str | None = None  # public, internal, confidential, restricted
    personal_data_involved: bool = False
    sensitive_data_types: list[str] = Field(default_factory=list)  # pii, phi, financial

    # Compliance metadata
    retention_period: int | None = None  # Days to retain this audit record
    compliance_frameworks: list[str] = Field(default_factory=list)  # soc2, gdpr, hipaa
    legal_basis: str | None = None  # GDPR legal basis

    # System metadata
    system_version: str | None = None
    correlation_id: str | None = None
    parent_event_id: UUID | None = None

    @validator('compliance_frameworks')
    def validate_compliance_frameworks(cls, v):
        """Ensure compliance frameworks are valid."""
        valid_frameworks = {'soc2', 'gdpr', 'hipaa', 'pci', 'sox', 'iso27001'}
        for framework in v:
            if framework.lower() not in valid_frameworks:
                raise ValueError(f"Invalid compliance framework: {framework}")
        return [f.lower() for f in v]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class ComplianceAuditLogger:
    """Enterprise-grade audit logger with encryption and compliance features."""

    def __init__(self, audit_db_path: Path, encryption_key: str | None = None,
                 retention_days: int = 2555):  # 7 years default
        self.audit_db_path = Path(audit_db_path)
        self.audit_db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        if encryption_key:
            self.encryption = Fernet(encryption_key.encode())
        else:
            self.encryption = Fernet(Fernet.generate_key())

        self.default_retention_days = retention_days

        # Initialize audit database
        self._init_audit_database()

        # Event counters for reporting
        self._event_counters: dict[AuditEventType, int] = {}
        self._last_cleanup = datetime.utcnow()

    def _init_audit_database(self) -> None:
        """Initialize audit database with compliance-optimized schema."""
        with self._get_audit_connection() as conn:
            # Main audit events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    severity TEXT NOT NULL,

                    -- Actor information
                    user_id TEXT,
                    username TEXT,
                    user_role TEXT,
                    session_id TEXT,

                    -- Context information
                    tenant_id TEXT,
                    client_id TEXT,
                    source_ip TEXT,
                    user_agent TEXT,
                    api_endpoint TEXT,
                    http_method TEXT,

                    -- Target information
                    resource_type TEXT,
                    resource_id TEXT,
                    resource_name TEXT,

                    -- Event details (encrypted)
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    details_encrypted TEXT,

                    -- Data classification
                    data_classification TEXT,
                    personal_data_involved BOOLEAN DEFAULT FALSE,
                    sensitive_data_types TEXT,  -- JSON array

                    -- Compliance metadata
                    retention_period INTEGER,
                    compliance_frameworks TEXT,  -- JSON array
                    legal_basis TEXT,

                    -- System metadata
                    system_version TEXT,
                    correlation_id TEXT,
                    parent_event_id TEXT,

                    -- Integrity check
                    event_hash TEXT NOT NULL
                )
            """)

            # Compliance-specific indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_events (timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user
                ON audit_events (user_id, tenant_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_type_tenant
                ON audit_events (event_type, tenant_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_compliance
                ON audit_events (compliance_frameworks, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_personal_data
                ON audit_events (personal_data_involved, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_resource
                ON audit_events (resource_type, resource_id, timestamp)
            """)

            # Event statistics table for reporting
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_statistics (
                    date DATE PRIMARY KEY,
                    tenant_id TEXT,
                    event_type TEXT,
                    event_count INTEGER DEFAULT 0,
                    unique_users INTEGER DEFAULT 0,
                    failed_events INTEGER DEFAULT 0,
                    compliance_events INTEGER DEFAULT 0
                )
            """)

            # Data retention tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS retention_tracking (
                    event_id TEXT PRIMARY KEY,
                    retention_until DATE NOT NULL,
                    legal_hold BOOLEAN DEFAULT FALSE,
                    retention_reason TEXT,
                    FOREIGN KEY (event_id) REFERENCES audit_events (event_id)
                )
            """)

    @contextmanager
    def _get_audit_connection(self):
        """Get audit database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.audit_db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
        finally:
            conn.close()

    def _calculate_event_hash(self, event: AuditEvent) -> str:
        """Calculate integrity hash for audit event."""
        # Create deterministic string representation
        hash_data = f"{event.event_id}:{event.timestamp.isoformat()}:{event.event_type}:{event.action}:{event.user_id}:{event.resource_id}"
        return hashlib.sha256(hash_data.encode()).hexdigest()

    def _encrypt_sensitive_data(self, data: dict[str, Any]) -> str:
        """Encrypt sensitive audit data."""
        json_data = json.dumps(data, default=str)
        return self.encryption.encrypt(json_data.encode()).decode()

    def _decrypt_sensitive_data(self, encrypted_data: str) -> dict[str, Any]:
        """Decrypt sensitive audit data."""
        decrypted = self.encryption.decrypt(encrypted_data.encode()).decode()
        return json.loads(decrypted)

    async def log_event(self, event: AuditEvent) -> None:
        """Log audit event with compliance features."""
        try:
            # Set default retention if not specified
            if not event.retention_period:
                event.retention_period = self.default_retention_days

            # Calculate event hash for integrity
            event_hash = self._calculate_event_hash(event)

            # Encrypt sensitive details
            encrypted_details = self._encrypt_sensitive_data(event.details)

            # Store in database
            with self._get_audit_connection() as conn:
                conn.execute("""
                    INSERT INTO audit_events (
                        event_id, event_type, timestamp, severity,
                        user_id, username, user_role, session_id,
                        tenant_id, client_id, source_ip, user_agent,
                        api_endpoint, http_method,
                        resource_type, resource_id, resource_name,
                        action, outcome, details_encrypted,
                        data_classification, personal_data_involved,
                        sensitive_data_types, retention_period,
                        compliance_frameworks, legal_basis,
                        system_version, correlation_id, parent_event_id,
                        event_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(event.event_id), event.event_type.value, event.timestamp, event.severity.value,
                    str(event.user_id) if event.user_id else None, event.username, event.user_role, event.session_id,
                    event.tenant_id, event.client_id, event.source_ip, event.user_agent,
                    event.api_endpoint, event.http_method,
                    event.resource_type, event.resource_id, event.resource_name,
                    event.action, event.outcome, encrypted_details,
                    event.data_classification, event.personal_data_involved,
                    json.dumps(event.sensitive_data_types), event.retention_period,
                    json.dumps(event.compliance_frameworks), event.legal_basis,
                    event.system_version, event.correlation_id,
                    str(event.parent_event_id) if event.parent_event_id else None,
                    event_hash
                ))

                # Add retention tracking
                retention_until = event.timestamp + timedelta(days=event.retention_period)
                conn.execute("""
                    INSERT INTO retention_tracking (event_id, retention_until, retention_reason)
                    VALUES (?, ?, ?)
                """, (str(event.event_id), retention_until.date(), "standard_retention"))

                conn.commit()

            # Update statistics
            self._event_counters[event.event_type] = self._event_counters.get(event.event_type, 0) + 1

            # Log to system logger based on severity
            if event.severity == AuditSeverity.CRITICAL:
                logger.critical(f"AUDIT: {event.action} - {event.event_type}")
            elif event.severity == AuditSeverity.HIGH:
                logger.warning(f"AUDIT: {event.action} - {event.event_type}")
            else:
                logger.info(f"AUDIT: {event.action} - {event.event_type}")

        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            # In production, this should trigger alerts
            raise

    async def get_audit_trail(self, tenant_id: str | None = None,
                            user_id: UUID | None = None,
                            start_time: datetime | None = None,
                            end_time: datetime | None = None,
                            event_types: list[AuditEventType] | None = None,
                            resource_type: str | None = None,
                            limit: int = 100) -> list[dict[str, Any]]:
        """Get audit trail for compliance reporting."""
        query_parts = ["SELECT * FROM audit_events WHERE 1=1"]
        params = []

        if tenant_id:
            query_parts.append("AND tenant_id = ?")
            params.append(tenant_id)

        if user_id:
            query_parts.append("AND user_id = ?")
            params.append(str(user_id))

        if start_time:
            query_parts.append("AND timestamp >= ?")
            params.append(start_time)

        if end_time:
            query_parts.append("AND timestamp <= ?")
            params.append(end_time)

        if event_types:
            placeholders = ",".join("?" * len(event_types))
            query_parts.append(f"AND event_type IN ({placeholders})")
            params.extend([et.value for et in event_types])

        if resource_type:
            query_parts.append("AND resource_type = ?")
            params.append(resource_type)

        query_parts.append("ORDER BY timestamp DESC LIMIT ?")
        params.append(limit)

        query = " ".join(query_parts)

        with self._get_audit_connection() as conn:
            rows = conn.execute(query, params).fetchall()

            events = []
            for row in rows:
                event_dict = dict(row)

                # Decrypt sensitive details
                if event_dict['details_encrypted']:
                    try:
                        event_dict['details'] = self._decrypt_sensitive_data(event_dict['details_encrypted'])
                    except Exception:
                        event_dict['details'] = {}  # Fallback if decryption fails

                # Parse JSON fields
                if event_dict['sensitive_data_types']:
                    event_dict['sensitive_data_types'] = json.loads(event_dict['sensitive_data_types'])
                if event_dict['compliance_frameworks']:
                    event_dict['compliance_frameworks'] = json.loads(event_dict['compliance_frameworks'])

                # Remove encrypted field from response
                del event_dict['details_encrypted']

                events.append(event_dict)

            return events

    async def get_gdpr_data_subject_audit(self, user_id: UUID,
                                         include_personal_data: bool = False) -> list[dict[str, Any]]:
        """Get audit trail for GDPR data subject request."""
        return await self.get_audit_trail(
            user_id=user_id,
            start_time=datetime.utcnow() - timedelta(days=365),  # Last year
            limit=1000
        )

    async def get_hipaa_access_audit(self, resource_id: str,
                                   days_back: int = 30) -> list[dict[str, Any]]:
        """Get HIPAA-specific access audit for protected health information."""
        start_time = datetime.utcnow() - timedelta(days=days_back)

        hipaa_event_types = [
            AuditEventType.DATA_ACCESSED,
            AuditEventType.DATA_EXPORTED,
            AuditEventType.DATA_MODIFIED,
            AuditEventType.DATA_DELETED
        ]

        return await self.get_audit_trail(
            start_time=start_time,
            event_types=hipaa_event_types,
            resource_type="patient_data",
            limit=500
        )

    async def cleanup_expired_records(self) -> int:
        """Clean up audit records that have exceeded retention period."""
        cutoff_date = datetime.utcnow().date()

        with self._get_audit_connection() as conn:
            # Find expired records not under legal hold
            expired_events = conn.execute("""
                SELECT event_id FROM retention_tracking
                WHERE retention_until < ? AND legal_hold = FALSE
            """, (cutoff_date,)).fetchall()

            if expired_events:
                event_ids = [row[0] for row in expired_events]
                placeholders = ",".join("?" * len(event_ids))

                # Delete from audit_events
                conn.execute(f"DELETE FROM audit_events WHERE event_id IN ({placeholders})", event_ids)

                # Delete from retention_tracking
                conn.execute(f"DELETE FROM retention_tracking WHERE event_id IN ({placeholders})", event_ids)

                conn.commit()

                logger.info(f"Cleaned up {len(event_ids)} expired audit records")
                return len(event_ids)

        return 0

    async def place_legal_hold(self, event_ids: list[str], reason: str) -> int:
        """Place legal hold on audit records to prevent deletion."""
        with self._get_audit_connection() as conn:
            placeholders = ",".join("?" * len(event_ids))
            cursor = conn.execute(f"""
                UPDATE retention_tracking
                SET legal_hold = TRUE, retention_reason = ?
                WHERE event_id IN ({placeholders})
            """, [reason] + event_ids)

            conn.commit()

            logger.warning(f"Placed legal hold on {cursor.rowcount} audit records: {reason}")
            return cursor.rowcount

    async def get_compliance_statistics(self, tenant_id: str | None = None,
                                      days_back: int = 30) -> dict[str, Any]:
        """Get compliance-related statistics for reporting."""
        start_time = datetime.utcnow() - timedelta(days=days_back)

        with self._get_audit_connection() as conn:
            # Base query conditions
            where_clause = "WHERE timestamp >= ?"
            params = [start_time]

            if tenant_id:
                where_clause += " AND tenant_id = ?"
                params.append(tenant_id)

            # Total events
            total_events = conn.execute(f"SELECT COUNT(*) FROM audit_events {where_clause}", params).fetchone()[0]

            # Events by type
            events_by_type = dict(conn.execute(f"""
                SELECT event_type, COUNT(*) FROM audit_events
                {where_clause} GROUP BY event_type
            """, params).fetchall())

            # Failed events
            failed_params = params + ["failure"]
            failed_events = conn.execute(f"""
                SELECT COUNT(*) FROM audit_events
                {where_clause} AND outcome = ?
            """, failed_params).fetchone()[0]

            # Personal data events
            personal_data_params = params + [True]
            personal_data_events = conn.execute(f"""
                SELECT COUNT(*) FROM audit_events
                {where_clause} AND personal_data_involved = ?
            """, personal_data_params).fetchone()[0]

            # Unique users
            unique_users = conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) FROM audit_events
                {where_clause} AND user_id IS NOT NULL
            """, params).fetchone()[0]

            return {
                'period_days': days_back,
                'total_events': total_events,
                'events_by_type': events_by_type,
                'failed_events': failed_events,
                'failure_rate': (failed_events / total_events * 100) if total_events > 0 else 0,
                'personal_data_events': personal_data_events,
                'unique_users': unique_users,
                'compliance_health': 'healthy' if failed_events / total_events < 0.01 else 'warning',
                'generated_at': datetime.utcnow().isoformat()
            }
