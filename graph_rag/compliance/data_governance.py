"""Data governance framework for GDPR, HIPAA, and enterprise data protection."""

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
from pydantic import BaseModel, Field

from .audit_logging import AuditEvent, AuditEventType, AuditSeverity, ComplianceAuditLogger

logger = logging.getLogger(__name__)


class DataClassification(str, Enum):
    """Data classification levels for governance and compliance."""

    PUBLIC = "public"              # No restrictions
    INTERNAL = "internal"          # Internal use only
    CONFIDENTIAL = "confidential"  # Restricted access
    RESTRICTED = "restricted"      # Highest security level
    PII = "pii"                   # Personally Identifiable Information (GDPR)
    PHI = "phi"                   # Protected Health Information (HIPAA)
    FINANCIAL = "financial"       # Financial data (PCI DSS)


class ProcessingBasis(str, Enum):
    """GDPR legal basis for data processing."""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataSubjectRights(str, Enum):
    """GDPR data subject rights."""

    ACCESS = "access"                    # Right to access personal data
    RECTIFICATION = "rectification"      # Right to correct inaccurate data
    ERASURE = "erasure"                 # Right to be forgotten
    RESTRICT_PROCESSING = "restrict_processing"  # Right to restrict processing
    DATA_PORTABILITY = "data_portability"        # Right to data portability
    OBJECT = "object"                   # Right to object to processing
    AUTOMATED_DECISION = "automated_decision"    # Rights related to automated decisions


class RetentionPolicy(BaseModel):
    """Data retention policy configuration."""

    policy_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    name: str
    description: str

    # Retention configuration
    retention_days: int = Field(..., ge=1)
    data_classifications: list[DataClassification]
    resource_types: list[str] = Field(default_factory=list)  # document, user_data, analytics

    # Legal basis
    legal_basis: list[ProcessingBasis] = Field(default_factory=list)
    regulatory_requirements: list[str] = Field(default_factory=list)  # gdpr, hipaa, sox

    # Deletion configuration
    auto_delete: bool = Field(default=True)
    require_approval: bool = Field(default=False)
    grace_period_days: int = Field(default=30)  # Grace period before actual deletion

    # Exceptions
    legal_hold_exempt: bool = Field(default=False)
    business_critical: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)


class DataRecord(BaseModel):
    """Tracked data record for governance."""

    record_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    user_id: UUID | None = None

    # Data identification
    resource_type: str  # document, user_profile, search_query, etc.
    resource_id: str
    data_classification: DataClassification

    # Content metadata
    contains_pii: bool = False
    contains_phi: bool = False
    pii_types: list[str] = Field(default_factory=list)  # email, name, ssn, etc.
    data_subjects: list[str] = Field(default_factory=list)  # User IDs affected

    # Processing metadata
    processing_basis: list[ProcessingBasis] = Field(default_factory=list)
    consent_id: str | None = None
    processing_purposes: list[str] = Field(default_factory=list)

    # Retention and lifecycle
    retention_policy_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    retention_until: datetime
    scheduled_deletion: datetime | None = None

    # Status tracking
    is_encrypted: bool = False
    is_backed_up: bool = False
    is_anonymized: bool = False
    legal_hold: bool = False

    # Compliance flags
    gdpr_applicable: bool = False
    hipaa_applicable: bool = False
    pci_applicable: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class DataSubjectRequest(BaseModel):
    """GDPR data subject request tracking."""

    request_id: UUID = Field(default_factory=uuid4)
    tenant_id: str

    # Request details
    request_type: DataSubjectRights
    data_subject_id: str  # Email or user ID
    data_subject_email: str
    description: str

    # Request metadata
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_by: str  # User who submitted (may be different from data subject)
    verification_method: str = "email"  # How identity was verified

    # Processing status
    status: str = "pending"  # pending, in_progress, completed, rejected
    assigned_to: str | None = None
    priority: str = "normal"  # low, normal, high, urgent

    # Response tracking
    due_date: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    completed_at: datetime | None = None
    response_provided: bool = False
    response_format: str | None = None  # json, csv, pdf

    # Processing notes
    processing_notes: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None

    # Impact tracking
    records_identified: int = 0
    records_processed: int = 0
    records_deleted: int = 0
    data_exported: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class ConsentRecord(BaseModel):
    """GDPR consent tracking."""

    consent_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    data_subject_id: str

    # Consent details
    processing_purposes: list[str]
    data_categories: list[str]
    legal_basis: ProcessingBasis = ProcessingBasis.CONSENT

    # Consent metadata
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    granted_method: str = "web_form"  # web_form, api, email, etc.
    consent_text: str
    version: str = "1.0"

    # Status
    is_active: bool = True
    withdrawn_at: datetime | None = None
    withdrawal_reason: str | None = None

    # Renewal and expiry
    expires_at: datetime | None = None
    last_renewed: datetime | None = None
    renewal_required: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class DataGovernanceManager:
    """Comprehensive data governance manager for enterprise compliance."""

    def __init__(self, data_dir: Path, audit_logger: ComplianceAuditLogger,
                 encryption_key: str | None = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "data_governance.db"
        self.audit_logger = audit_logger

        # Initialize encryption
        if encryption_key:
            self.encryption = Fernet(encryption_key.encode())
        else:
            self.encryption = Fernet(Fernet.generate_key())

        # Initialize database
        self._init_database()

        # Default retention policies
        self._create_default_retention_policies()

        # Cache for performance
        self._retention_policies: dict[str, RetentionPolicy] = {}
        self._last_cache_refresh = datetime.utcnow()

    def _init_database(self) -> None:
        """Initialize data governance database."""
        with self._get_connection() as conn:
            # Retention policies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS retention_policies (
                    policy_id TEXT PRIMARY KEY,
                    policy_data TEXT NOT NULL,  -- Encrypted JSON
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)

            # Data records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_records (
                    record_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    user_id TEXT,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    data_classification TEXT NOT NULL,
                    record_data TEXT NOT NULL,  -- Encrypted JSON
                    retention_policy_id TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    retention_until TIMESTAMP NOT NULL,
                    scheduled_deletion TIMESTAMP,
                    legal_hold BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (retention_policy_id) REFERENCES retention_policies (policy_id)
                )
            """)

            # Data subject requests table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_subject_requests (
                    request_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    request_data TEXT NOT NULL,  -- Encrypted JSON
                    status TEXT NOT NULL,
                    submitted_at TIMESTAMP NOT NULL,
                    due_date TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP
                )
            """)

            # Consent records table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consent_records (
                    consent_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    data_subject_id TEXT NOT NULL,
                    consent_data TEXT NOT NULL,  -- Encrypted JSON
                    granted_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    withdrawn_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_tenant_retention ON data_records (tenant_id, retention_until)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_scheduled_deletion ON data_records (scheduled_deletion)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_tenant_status ON data_subject_requests (tenant_id, status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_due_date ON data_subject_requests (due_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_consent_subject ON consent_records (data_subject_id, is_active)")

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.encryption.encrypt(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.encryption.decrypt(encrypted_data.encode()).decode()

    def _create_default_retention_policies(self) -> None:
        """Create default retention policies for common use cases."""
        default_policies = [
            RetentionPolicy(
                policy_id="gdpr_user_data",
                name="GDPR User Data",
                description="Standard retention for user personal data under GDPR",
                retention_days=2555,  # 7 years
                data_classifications=[DataClassification.PII],
                resource_types=["user_profile", "user_preferences"],
                legal_basis=[ProcessingBasis.CONSENT, ProcessingBasis.CONTRACT],
                regulatory_requirements=["gdpr"]
            ),
            RetentionPolicy(
                policy_id="hipaa_phi",
                name="HIPAA Protected Health Information",
                description="HIPAA retention for protected health information",
                retention_days=2190,  # 6 years
                data_classifications=[DataClassification.PHI],
                resource_types=["medical_document", "health_record"],
                regulatory_requirements=["hipaa"],
                require_approval=True
            ),
            RetentionPolicy(
                policy_id="business_documents",
                name="Business Documents",
                description="Standard business document retention",
                retention_days=2555,  # 7 years
                data_classifications=[DataClassification.CONFIDENTIAL, DataClassification.INTERNAL],
                resource_types=["document", "search_query", "analytics"],
                regulatory_requirements=["sox"],
                business_critical=True
            ),
            RetentionPolicy(
                policy_id="audit_logs",
                name="Audit Logs",
                description="Audit log retention for compliance",
                retention_days=2555,  # 7 years
                data_classifications=[DataClassification.CONFIDENTIAL],
                resource_types=["audit_log", "access_log"],
                auto_delete=False,  # Manual review required
                legal_hold_exempt=False
            )
        ]

        for policy in default_policies:
            try:
                self.create_retention_policy(policy)
            except Exception as e:
                # Policy may already exist
                logger.debug(f"Default policy creation skipped: {policy.policy_id} - {e}")

    async def create_retention_policy(self, policy: RetentionPolicy) -> None:
        """Create or update retention policy."""
        policy.updated_at = datetime.utcnow()
        policy_json = policy.json()
        encrypted_policy = self._encrypt_data(policy_json)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO retention_policies 
                (policy_id, policy_data, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (policy.policy_id, encrypted_policy, policy.created_at,
                  policy.updated_at, policy.is_active))
            conn.commit()

        # Update cache
        self._retention_policies[policy.policy_id] = policy

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            action=f"Created/updated retention policy: {policy.name}",
            resource_type="retention_policy",
            resource_id=policy.policy_id,
            details={"policy_id": policy.policy_id, "retention_days": policy.retention_days},
            compliance_frameworks=["gdpr", "hipaa", "sox"]
        ))

        logger.info(f"Created/updated retention policy: {policy.policy_id}")

    async def register_data_record(self, record: DataRecord) -> None:
        """Register data record for governance tracking."""
        # Calculate retention until date
        retention_policy = await self.get_retention_policy(record.retention_policy_id)
        if not retention_policy:
            raise ValueError(f"Retention policy not found: {record.retention_policy_id}")

        record.retention_until = record.created_at + timedelta(days=retention_policy.retention_days)

        # Encrypt record data
        record_json = record.json()
        encrypted_record = self._encrypt_data(record_json)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO data_records (
                    record_id, tenant_id, user_id, resource_type, resource_id,
                    data_classification, record_data, retention_policy_id,
                    created_at, retention_until, legal_hold
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(record.record_id), record.tenant_id,
                str(record.user_id) if record.user_id else None,
                record.resource_type, record.resource_id,
                record.data_classification.value, encrypted_record,
                record.retention_policy_id, record.created_at,
                record.retention_until, record.legal_hold
            ))
            conn.commit()

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.DATA_ACCESSED,
            tenant_id=record.tenant_id,
            user_id=record.user_id,
            action=f"Registered data record for governance: {record.resource_type}",
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            data_classification=record.data_classification.value,
            personal_data_involved=record.contains_pii or record.contains_phi,
            sensitive_data_types=record.pii_types,
            compliance_frameworks=["gdpr"] if record.gdpr_applicable else []
        ))

        logger.info(f"Registered data record: {record.record_id} ({record.resource_type})")

    async def submit_data_subject_request(self, request: DataSubjectRequest) -> None:
        """Submit GDPR data subject request."""
        # Encrypt request data
        request_json = request.json()
        encrypted_request = self._encrypt_data(request_json)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO data_subject_requests (
                    request_id, tenant_id, request_data, status,
                    submitted_at, due_date
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(request.request_id), request.tenant_id, encrypted_request,
                request.status, request.submitted_at, request.due_date
            ))
            conn.commit()

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.DATA_SUBJECT_REQUEST,
            tenant_id=request.tenant_id,
            action=f"Data subject request submitted: {request.request_type.value}",
            resource_type="data_subject_request",
            resource_id=str(request.request_id),
            details={
                "request_type": request.request_type.value,
                "data_subject": request.data_subject_email,
                "due_date": request.due_date.isoformat()
            },
            severity=AuditSeverity.HIGH,
            personal_data_involved=True,
            compliance_frameworks=["gdpr"]
        ))

        logger.warning(f"Data subject request submitted: {request.request_id} ({request.request_type})")

    async def process_data_subject_request(self, request_id: UUID,
                                         user_id: str) -> dict[str, Any]:
        """Process GDPR data subject request."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM data_subject_requests WHERE request_id = ?
            """, (str(request_id),)).fetchone()

            if not row:
                raise ValueError(f"Request not found: {request_id}")

            # Decrypt request data
            decrypted_data = self._decrypt_data(row['request_data'])
            request = DataSubjectRequest.parse_raw(decrypted_data)

            result = {"request_id": str(request_id), "processed": False}

            if request.request_type == DataSubjectRights.ACCESS:
                # Find all data records for this subject
                records = await self.get_data_records_for_subject(
                    request.tenant_id, request.data_subject_id
                )
                result.update({
                    "data_records": len(records),
                    "personal_data": [r for r in records if r['contains_pii'] or r['contains_phi']]
                })

            elif request.request_type == DataSubjectRights.ERASURE:
                # Schedule deletion of all personal data
                deleted_count = await self.schedule_data_deletion(
                    request.tenant_id, request.data_subject_id,
                    reason=f"GDPR right to erasure - request {request_id}"
                )
                result.update({"records_scheduled_for_deletion": deleted_count})

            elif request.request_type == DataSubjectRights.DATA_PORTABILITY:
                # Export data in portable format
                export_data = await self.export_subject_data(
                    request.tenant_id, request.data_subject_id
                )
                result.update({"export_data": export_data})

            # Update request status
            request.status = "completed"
            request.completed_at = datetime.utcnow()
            request.assigned_to = user_id

            updated_request = self._encrypt_data(request.json())
            conn.execute("""
                UPDATE data_subject_requests 
                SET request_data = ?, status = ?, completed_at = ?
                WHERE request_id = ?
            """, (updated_request, "completed", request.completed_at, str(request_id)))
            conn.commit()

            result["processed"] = True

            # Audit log
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.DATA_SUBJECT_REQUEST,
                tenant_id=request.tenant_id,
                user_id=UUID(user_id) if user_id else None,
                action=f"Processed data subject request: {request.request_type.value}",
                resource_type="data_subject_request",
                resource_id=str(request_id),
                details=result,
                severity=AuditSeverity.HIGH,
                personal_data_involved=True,
                compliance_frameworks=["gdpr"]
            ))

            return result

    async def get_retention_policy(self, policy_id: str) -> RetentionPolicy | None:
        """Get retention policy by ID."""
        if policy_id in self._retention_policies:
            return self._retention_policies[policy_id]

        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT policy_data FROM retention_policies 
                WHERE policy_id = ? AND is_active = TRUE
            """, (policy_id,)).fetchone()

            if row:
                decrypted_data = self._decrypt_data(row['policy_data'])
                policy = RetentionPolicy.parse_raw(decrypted_data)
                self._retention_policies[policy_id] = policy
                return policy

        return None

    async def get_data_records_for_subject(self, tenant_id: str,
                                         data_subject_id: str) -> list[dict[str, Any]]:
        """Get all data records for a data subject (GDPR compliance)."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM data_records 
                WHERE tenant_id = ? AND (user_id = ? OR JSON_EXTRACT(record_data, '$.data_subjects') LIKE ?)
            """, (tenant_id, data_subject_id, f'%"{data_subject_id}"%')).fetchall()

            records = []
            for row in rows:
                try:
                    decrypted_data = self._decrypt_data(row['record_data'])
                    record_data = json.loads(decrypted_data)
                    record_data['record_id'] = row['record_id']
                    records.append(record_data)
                except Exception as e:
                    logger.error(f"Failed to decrypt record {row['record_id']}: {e}")

            return records

    async def schedule_data_deletion(self, tenant_id: str, data_subject_id: str | None = None,
                                   resource_type: str | None = None,
                                   reason: str = "retention_policy") -> int:
        """Schedule data for deletion based on retention policies."""
        with self._get_connection() as conn:
            query = """
                UPDATE data_records 
                SET scheduled_deletion = ? 
                WHERE tenant_id = ? AND legal_hold = FALSE AND scheduled_deletion IS NULL
            """
            params = [datetime.utcnow() + timedelta(days=30), tenant_id]  # 30-day grace period

            if data_subject_id:
                query += " AND user_id = ?"
                params.append(data_subject_id)

            if resource_type:
                query += " AND resource_type = ?"
                params.append(resource_type)

            cursor = conn.execute(query, params)
            conn.commit()

            count = cursor.rowcount

            # Audit log
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.DATA_DELETED,
                tenant_id=tenant_id,
                action=f"Scheduled {count} records for deletion",
                details={"reason": reason, "records_count": count},
                compliance_frameworks=["gdpr", "hipaa"]
            ))

            logger.info(f"Scheduled {count} records for deletion: {reason}")
            return count

    async def execute_scheduled_deletions(self) -> int:
        """Execute scheduled data deletions."""
        with self._get_connection() as conn:
            # Find records ready for deletion
            rows = conn.execute("""
                SELECT record_id, tenant_id, resource_type, resource_id 
                FROM data_records 
                WHERE scheduled_deletion <= ? AND legal_hold = FALSE
            """, (datetime.utcnow(),)).fetchall()

            if not rows:
                return 0

            deleted_records = []
            for row in rows:
                # Delete the actual data (this would integrate with your storage systems)
                # For now, just track the deletion
                deleted_records.append({
                    'record_id': row['record_id'],
                    'tenant_id': row['tenant_id'],
                    'resource_type': row['resource_type'],
                    'resource_id': row['resource_id']
                })

            # Remove records from governance tracking
            record_ids = [row['record_id'] for row in rows]
            placeholders = ','.join('?' * len(record_ids))
            conn.execute(f"DELETE FROM data_records WHERE record_id IN ({placeholders})", record_ids)
            conn.commit()

            # Audit log
            await self.audit_logger.log_event(AuditEvent(
                event_type=AuditEventType.DATA_DELETED,
                action=f"Executed scheduled deletion of {len(deleted_records)} records",
                details={"deleted_records": deleted_records},
                compliance_frameworks=["gdpr", "hipaa"]
            ))

            logger.info(f"Executed deletion of {len(deleted_records)} records")
            return len(deleted_records)

    async def export_subject_data(self, tenant_id: str, data_subject_id: str) -> dict[str, Any]:
        """Export all data for a data subject (GDPR data portability)."""
        records = await self.get_data_records_for_subject(tenant_id, data_subject_id)

        export_data = {
            'data_subject_id': data_subject_id,
            'tenant_id': tenant_id,
            'export_date': datetime.utcnow().isoformat(),
            'records': records,
            'total_records': len(records),
            'data_types': list(set([r.get('resource_type') for r in records]))
        }

        # Audit log
        await self.audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.DATA_PORTABILITY,
            tenant_id=tenant_id,
            action=f"Exported data for subject: {data_subject_id}",
            resource_type="data_export",
            details={"records_exported": len(records)},
            personal_data_involved=True,
            compliance_frameworks=["gdpr"]
        ))

        return export_data

    async def get_compliance_dashboard(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get data governance compliance dashboard."""
        with self._get_connection() as conn:
            base_query = "WHERE 1=1"
            params = []

            if tenant_id:
                base_query += " AND tenant_id = ?"
                params.append(tenant_id)

            # Total records under governance
            total_records = conn.execute(f"SELECT COUNT(*) FROM data_records {base_query}", params).fetchone()[0]

            # Records by classification
            classification_counts = dict(conn.execute(f"""
                SELECT data_classification, COUNT(*) 
                FROM data_records {base_query}
                GROUP BY data_classification
            """, params).fetchall())

            # Records approaching retention deadline
            thirty_days = datetime.utcnow() + timedelta(days=30)
            approaching_retention = conn.execute(f"""
                SELECT COUNT(*) FROM data_records 
                {base_query} AND retention_until <= ? AND scheduled_deletion IS NULL
            """, params + [thirty_days]).fetchone()[0]

            # Scheduled for deletion
            scheduled_deletion = conn.execute(f"""
                SELECT COUNT(*) FROM data_records 
                {base_query} AND scheduled_deletion IS NOT NULL
            """, params).fetchone()[0]

            # Legal holds
            legal_holds = conn.execute(f"""
                SELECT COUNT(*) FROM data_records 
                {base_query} AND legal_hold = TRUE
            """, params).fetchone()[0]

            # Pending data subject requests
            pending_requests = conn.execute(f"""
                SELECT COUNT(*) FROM data_subject_requests 
                {base_query} AND status = 'pending'
            """, params).fetchone()[0]

            # Overdue requests
            overdue_requests = conn.execute(f"""
                SELECT COUNT(*) FROM data_subject_requests 
                {base_query} AND status = 'pending' AND due_date < ?
            """, params + [datetime.utcnow()]).fetchone()[0]

            return {
                'total_records': total_records,
                'records_by_classification': classification_counts,
                'approaching_retention': approaching_retention,
                'scheduled_for_deletion': scheduled_deletion,
                'legal_holds': legal_holds,
                'pending_requests': pending_requests,
                'overdue_requests': overdue_requests,
                'compliance_health': 'healthy' if overdue_requests == 0 else 'warning',
                'generated_at': datetime.utcnow().isoformat()
            }
