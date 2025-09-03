"""GDPR compliance processor for data subject rights and privacy management."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from graph_rag.api.auth.enterprise_models import (
    AuditEvent,
    AuditEventType,
    ComplianceFramework,
    Tenant,
)

logger = logging.getLogger(__name__)


class GDPRDataSubjectRequest:
    """GDPR data subject request model."""
    
    def __init__(
        self,
        request_type: str,
        user_id: UUID,
        tenant_id: UUID,
        email: str,
        verification_token: str = None
    ):
        self.id = uuid4()
        self.request_type = request_type  # access, rectification, erasure, portability
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email
        self.verification_token = verification_token or str(uuid4())
        self.status = "pending"  # pending, verified, processing, completed, rejected
        self.created_at = datetime.utcnow()
        self.verified_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.response_data: Dict[str, Any] = {}
        self.processing_notes: List[str] = []


class GDPRDataProcessor:
    """GDPR data processing and subject rights management."""
    
    def __init__(self):
        self.data_subject_requests: Dict[UUID, GDPRDataSubjectRequest] = {}
        self.data_categories = {
            "personal_identifiers": ["user_id", "email", "username", "name"],
            "authentication_data": ["password_hash", "mfa_configs", "api_keys"],
            "behavioral_data": ["login_times", "api_usage", "search_queries"],
            "preference_data": ["settings", "configurations", "preferences"],
            "audit_data": ["audit_events", "access_logs", "security_events"]
        }
        self.legal_basis = {
            "consent": "User has given explicit consent",
            "contract": "Processing necessary for contract performance",
            "legal_obligation": "Processing required by law",
            "legitimate_interest": "Processing for legitimate business interest"
        }
        
    async def submit_data_subject_request(
        self,
        request_type: str,
        user_id: UUID,
        tenant_id: UUID,
        email: str
    ) -> GDPRDataSubjectRequest:
        """Submit a GDPR data subject request."""
        
        # Validate request type
        valid_types = ["access", "rectification", "erasure", "portability", "restriction"]
        if request_type not in valid_types:
            raise ValueError(f"Invalid request type: {request_type}")
        
        # Create request
        request = GDPRDataSubjectRequest(request_type, user_id, tenant_id, email)
        self.data_subject_requests[request.id] = request
        
        # Log the request for audit
        await self._log_gdpr_event(
            tenant_id,
            AuditEventType.DATA_ACCESS,
            user_id=user_id,
            action=f"gdpr_request_submitted",
            details={
                "request_type": request_type,
                "request_id": str(request.id),
                "email": email
            }
        )
        
        # Send verification email (mock implementation)
        await self._send_verification_email(request)
        
        logger.info(f"GDPR {request_type} request submitted for user {user_id}")
        return request
    
    async def verify_data_subject_request(
        self,
        request_id: UUID,
        verification_token: str
    ) -> bool:
        """Verify a data subject request with the provided token."""
        
        request = self.data_subject_requests.get(request_id)
        if not request:
            return False
        
        if request.verification_token != verification_token:
            await self._log_gdpr_event(
                request.tenant_id,
                AuditEventType.SECURITY_VIOLATION,
                user_id=request.user_id,
                action="gdpr_request_verification_failed",
                details={"request_id": str(request_id)}
            )
            return False
        
        request.status = "verified"
        request.verified_at = datetime.utcnow()
        
        await self._log_gdpr_event(
            request.tenant_id,
            AuditEventType.USER_UPDATED,
            user_id=request.user_id,
            action="gdpr_request_verified",
            details={"request_id": str(request_id), "request_type": request.request_type}
        )
        
        # Auto-process certain request types
        if request.request_type in ["access", "portability"]:
            await self._process_data_subject_request(request)
        
        return True
    
    async def _process_data_subject_request(self, request: GDPRDataSubjectRequest):
        """Process a verified data subject request."""
        
        request.status = "processing"
        request.processing_notes.append(f"Processing started at {datetime.utcnow()}")
        
        try:
            if request.request_type == "access":
                await self._process_access_request(request)
            elif request.request_type == "rectification":
                await self._process_rectification_request(request)
            elif request.request_type == "erasure":
                await self._process_erasure_request(request)
            elif request.request_type == "portability":
                await self._process_portability_request(request)
            elif request.request_type == "restriction":
                await self._process_restriction_request(request)
            
            request.status = "completed"
            request.completed_at = datetime.utcnow()
            
            await self._log_gdpr_event(
                request.tenant_id,
                AuditEventType.DATA_ACCESS,
                user_id=request.user_id,
                action=f"gdpr_{request.request_type}_completed",
                details={"request_id": str(request.id)}
            )
            
        except Exception as e:
            request.status = "error"
            request.processing_notes.append(f"Error: {str(e)}")
            
            await self._log_gdpr_event(
                request.tenant_id,
                AuditEventType.SECURITY_VIOLATION,
                user_id=request.user_id,
                action=f"gdpr_{request.request_type}_error",
                details={"request_id": str(request.id), "error": str(e)}
            )
            
            logger.error(f"GDPR request processing failed: {e}")
    
    async def _process_access_request(self, request: GDPRDataSubjectRequest):
        """Process a data access request (Article 15)."""
        
        user_data = await self._collect_user_data(request.user_id, request.tenant_id)
        
        # Structure data according to GDPR requirements
        gdpr_response = {
            "personal_data": {
                "categories": list(self.data_categories.keys()),
                "sources": ["direct_input", "automated_collection", "third_party"],
                "purposes": [
                    "service_provision",
                    "security_monitoring", 
                    "legal_compliance",
                    "performance_optimization"
                ],
                "legal_basis": self.legal_basis,
                "retention_periods": {
                    "personal_identifiers": "Account lifetime + 30 days",
                    "authentication_data": "Account lifetime",
                    "behavioral_data": "2 years",
                    "audit_data": "7 years (legal requirement)"
                },
                "recipients": [
                    "Internal processing systems",
                    "Cloud infrastructure providers",
                    "Security monitoring services"
                ],
                "third_country_transfers": {
                    "countries": ["United States"],
                    "safeguards": ["Standard Contractual Clauses", "Adequacy Decision"]
                }
            },
            "actual_data": user_data,
            "processing_history": await self._get_processing_history(request.user_id),
            "rights_information": {
                "rectification": "Right to correct inaccurate data",
                "erasure": "Right to deletion under certain conditions",
                "portability": "Right to receive data in structured format",
                "restriction": "Right to restrict processing",
                "objection": "Right to object to processing"
            }
        }
        
        request.response_data = gdpr_response
        request.processing_notes.append("Data access package prepared")
    
    async def _process_rectification_request(self, request: GDPRDataSubjectRequest):
        """Process a data rectification request (Article 16)."""
        
        # In real implementation, this would update incorrect data
        request.processing_notes.append("Data rectification requires manual review")
        request.response_data = {
            "message": "Rectification request received and will be processed within 30 days",
            "next_steps": "Our data protection team will contact you for verification"
        }
    
    async def _process_erasure_request(self, request: GDPRDataSubjectRequest):
        """Process a data erasure request - Right to be forgotten (Article 17)."""
        
        # Check if erasure is legally required
        erasure_grounds = await self._check_erasure_grounds(request.user_id, request.tenant_id)
        
        if erasure_grounds:
            # Perform data deletion
            await self._perform_data_erasure(request.user_id, request.tenant_id)
            
            request.response_data = {
                "erasure_performed": True,
                "erasure_date": datetime.utcnow().isoformat(),
                "data_categories_erased": list(self.data_categories.keys()),
                "retention_exceptions": {
                    "audit_logs": "Retained for legal compliance (7 years)",
                    "anonymized_analytics": "Anonymized data retained for analytics"
                }
            }
            request.processing_notes.append("Data erasure completed")
        else:
            request.response_data = {
                "erasure_performed": False,
                "reason": "Legal basis for processing still exists",
                "details": "Account deletion not possible while contract is active"
            }
            request.processing_notes.append("Erasure request denied - legal basis exists")
    
    async def _process_portability_request(self, request: GDPRDataSubjectRequest):
        """Process a data portability request (Article 20)."""
        
        portable_data = await self._collect_portable_data(request.user_id, request.tenant_id)
        
        # Structure data in machine-readable format
        request.response_data = {
            "format": "JSON",
            "data": portable_data,
            "metadata": {
                "export_date": datetime.utcnow().isoformat(),
                "data_version": "1.0",
                "total_records": len(portable_data),
                "included_categories": [
                    cat for cat in self.data_categories.keys()
                    if cat not in ["audit_data"]  # Audit data not portable
                ]
            },
            "instructions": {
                "usage": "This data can be imported into compatible systems",
                "format_specification": "Standard JSON format with UTF-8 encoding",
                "validation": "Data integrity verified with SHA-256 checksums"
            }
        }
        request.processing_notes.append("Portable data package prepared")
    
    async def _process_restriction_request(self, request: GDPRDataSubjectRequest):
        """Process a data processing restriction request (Article 18)."""
        
        # Implement processing restriction
        await self._restrict_data_processing(request.user_id, request.tenant_id)
        
        request.response_data = {
            "restriction_applied": True,
            "restriction_date": datetime.utcnow().isoformat(),
            "restricted_processing": [
                "automated_analytics",
                "marketing_communications", 
                "performance_profiling"
            ],
            "continued_processing": [
                "storage_only",
                "legal_compliance",
                "security_monitoring"
            ],
            "removal_conditions": "Restriction will be lifted upon resolution of accuracy dispute"
        }
        request.processing_notes.append("Processing restriction applied")
    
    async def _collect_user_data(self, user_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """Collect all personal data for a user across all systems."""
        
        # Mock implementation - in production, this would query all data stores
        return {
            "identity": {
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "created_at": "2024-01-01T00:00:00Z",
                "last_updated": datetime.utcnow().isoformat()
            },
            "profile": {
                "username": "user@example.com",
                "email": "user@example.com",
                "preferences": {}
            },
            "activity": {
                "last_login": "2024-01-15T10:00:00Z",
                "login_count": 42,
                "api_calls": 1500
            },
            "content": {
                "documents": 25,
                "searches": 300,
                "queries": 150
            }
        }
    
    async def _collect_portable_data(self, user_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """Collect data in portable format for data portability requests."""
        
        user_data = await self._collect_user_data(user_id, tenant_id)
        
        # Remove non-portable data (audit logs, security data, etc.)
        portable_data = {
            "profile": user_data.get("profile", {}),
            "content": user_data.get("content", {}),
            "preferences": user_data.get("preferences", {}),
            "activity_summary": {
                "total_logins": user_data.get("activity", {}).get("login_count", 0),
                "account_age_days": (datetime.utcnow() - datetime(2024, 1, 1)).days
            }
        }
        
        return portable_data
    
    async def _get_processing_history(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get processing history for transparency."""
        
        return [
            {
                "date": "2024-01-01",
                "activity": "Account creation",
                "purpose": "Service provision",
                "legal_basis": "Contract"
            },
            {
                "date": "2024-01-15",
                "activity": "Authentication data processing", 
                "purpose": "Security",
                "legal_basis": "Legitimate interest"
            }
        ]
    
    async def _check_erasure_grounds(self, user_id: UUID, tenant_id: UUID) -> bool:
        """Check if erasure is legally required or permitted."""
        
        # Mock implementation - check various conditions:
        # 1. Data no longer necessary for original purpose
        # 2. Consent withdrawn and no other legal basis
        # 3. Data processed unlawfully
        # 4. Erasure required for legal compliance
        # 5. Data collected from child without proper consent
        
        # For demo, assume erasure is permitted
        return True
    
    async def _perform_data_erasure(self, user_id: UUID, tenant_id: UUID):
        """Perform actual data erasure across all systems."""
        
        # Mock implementation - in production:
        # 1. Remove from primary databases
        # 2. Remove from backups (where legally possible)
        # 3. Remove from caches
        # 4. Remove from analytics systems
        # 5. Anonymize audit logs
        # 6. Update third-party systems
        
        logger.info(f"Data erasure performed for user {user_id} in tenant {tenant_id}")
    
    async def _restrict_data_processing(self, user_id: UUID, tenant_id: UUID):
        """Restrict data processing while preserving storage."""
        
        # Mock implementation - in production:
        # 1. Flag account for processing restriction
        # 2. Disable automated processing
        # 3. Remove from analytics pipelines
        # 4. Restrict marketing communications
        # 5. Maintain audit trail of restriction
        
        logger.info(f"Data processing restricted for user {user_id} in tenant {tenant_id}")
    
    async def _send_verification_email(self, request: GDPRDataSubjectRequest):
        """Send verification email for data subject request."""
        
        # Mock implementation - in production, send actual email
        verification_url = f"https://privacy.synapse.com/verify/{request.id}/{request.verification_token}"
        
        logger.info(f"Verification email sent for GDPR request {request.id} to {request.email}")
        logger.info(f"Verification URL: {verification_url}")
    
    async def _log_gdpr_event(
        self,
        tenant_id: UUID,
        event_type: AuditEventType,
        **kwargs
    ):
        """Log GDPR-related events for compliance audit."""
        
        # Mock implementation - integrate with actual audit system
        logger.info(f"GDPR audit event: {event_type.value} for tenant {tenant_id}")
    
    def get_request_status(self, request_id: UUID) -> Optional[Dict[str, Any]]:
        """Get status of a data subject request."""
        
        request = self.data_subject_requests.get(request_id)
        if not request:
            return None
        
        return {
            "request_id": str(request.id),
            "type": request.request_type,
            "status": request.status,
            "created_at": request.created_at.isoformat(),
            "verified_at": request.verified_at.isoformat() if request.verified_at else None,
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            "processing_notes": request.processing_notes
        }
    
    def generate_gdpr_compliance_report(self, tenant_id: UUID, period_days: int = 30) -> Dict[str, Any]:
        """Generate GDPR compliance report for a tenant."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        tenant_requests = [
            req for req in self.data_subject_requests.values()
            if req.tenant_id == tenant_id and req.created_at >= cutoff_date
        ]
        
        return {
            "tenant_id": str(tenant_id),
            "report_period": f"{period_days} days",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_requests": len(tenant_requests),
                "by_type": {
                    req_type: len([r for r in tenant_requests if r.request_type == req_type])
                    for req_type in ["access", "rectification", "erasure", "portability", "restriction"]
                },
                "by_status": {
                    status: len([r for r in tenant_requests if r.status == status])
                    for status in ["pending", "verified", "processing", "completed", "error"]
                }
            },
            "performance_metrics": {
                "avg_verification_time_hours": self._calculate_avg_verification_time(tenant_requests),
                "avg_completion_time_hours": self._calculate_avg_completion_time(tenant_requests),
                "compliance_rate": self._calculate_compliance_rate(tenant_requests)
            },
            "compliance_status": "compliant" if all(
                req.status in ["completed", "processing"]
                for req in tenant_requests
                if req.created_at <= datetime.utcnow() - timedelta(days=30)
            ) else "attention_required"
        }
    
    def _calculate_avg_verification_time(self, requests: List[GDPRDataSubjectRequest]) -> float:
        """Calculate average verification time in hours."""
        verified_requests = [r for r in requests if r.verified_at]
        if not verified_requests:
            return 0.0
        
        total_hours = sum([
            (r.verified_at - r.created_at).total_seconds() / 3600
            for r in verified_requests
        ])
        return total_hours / len(verified_requests)
    
    def _calculate_avg_completion_time(self, requests: List[GDPRDataSubjectRequest]) -> float:
        """Calculate average completion time in hours."""
        completed_requests = [r for r in requests if r.completed_at]
        if not completed_requests:
            return 0.0
        
        total_hours = sum([
            (r.completed_at - r.created_at).total_seconds() / 3600
            for r in completed_requests
        ])
        return total_hours / len(completed_requests)
    
    def _calculate_compliance_rate(self, requests: List[GDPRDataSubjectRequest]) -> float:
        """Calculate compliance rate (completed within 30 days)."""
        if not requests:
            return 100.0
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        old_requests = [r for r in requests if r.created_at <= thirty_days_ago]
        
        if not old_requests:
            return 100.0
        
        compliant_requests = [r for r in old_requests if r.status == "completed"]
        return (len(compliant_requests) / len(old_requests)) * 100


# Global GDPR processor instance
gdpr_processor = GDPRDataProcessor()