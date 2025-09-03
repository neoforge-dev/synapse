"""Zero-Trust Access Control with identity-based resource access."""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from .identity_verification import Identity, IdentityLevel

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """Resource access levels."""
    DENY = "deny"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


class ResourceType(Enum):
    """Types of resources under access control."""
    DOCUMENT = "document"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    API_ENDPOINT = "api_endpoint"
    ENCRYPTION_KEY = "encryption_key"
    TENANT_DATA = "tenant_data"
    SYSTEM_CONFIG = "system_config"
    AUDIT_LOG = "audit_log"


@dataclass
class Resource:
    """Resource under access control."""
    resource_id: str
    resource_type: ResourceType
    tenant_id: UUID
    owner_id: UUID
    classification_level: str  # public, internal, confidential, restricted
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AccessPolicy:
    """Access control policy definition."""
    policy_id: str
    name: str
    resource_type: ResourceType
    required_identity_level: IdentityLevel
    allowed_access_levels: Set[AccessLevel]
    tenant_isolation: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    time_restrictions: Optional[Dict[str, Any]] = None
    ip_restrictions: Optional[List[str]] = None
    compliance_tags: List[str] = field(default_factory=list)


@dataclass
class AccessRequest:
    """Access request context."""
    identity: Identity
    resource: Resource
    requested_access_level: AccessLevel
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)


class ZeroTrustAccessControl:
    """Zero-Trust access control system with identity-based authorization."""
    
    def __init__(self):
        """Initialize zero-trust access control."""
        self.access_policies: Dict[str, AccessPolicy] = {}
        self.resources: Dict[str, Resource] = {}
        self.access_decisions: List[Dict[str, Any]] = []
        
        # Setup default policies
        self._setup_default_policies()
        
        # Access monitoring
        self.access_violations: List[Dict[str, Any]] = []
        self.privileged_access_log: List[Dict[str, Any]] = []
        
        # Metrics
        self.metrics = {
            "total_access_requests": 0,
            "granted_requests": 0,
            "denied_requests": 0,
            "policy_violations": 0,
            "privilege_escalations": 0,
            "cross_tenant_attempts": 0
        }
        
        logger.info("Initialized ZeroTrustAccessControl")
    
    def _setup_default_policies(self):
        """Setup default access control policies."""
        
        # Document access policy
        self.access_policies["document_access"] = AccessPolicy(
            policy_id="document_access",
            name="Standard Document Access",
            resource_type=ResourceType.DOCUMENT,
            required_identity_level=IdentityLevel.BASIC,
            allowed_access_levels={AccessLevel.READ, AccessLevel.WRITE},
            tenant_isolation=True,
            conditions={"same_tenant_required": True},
            compliance_tags=["data_protection"]
        )
        
        # Knowledge graph access policy
        self.access_policies["knowledge_graph_access"] = AccessPolicy(
            policy_id="knowledge_graph_access",
            name="Knowledge Graph Access",
            resource_type=ResourceType.KNOWLEDGE_GRAPH,
            required_identity_level=IdentityLevel.VERIFIED,
            allowed_access_levels={AccessLevel.READ, AccessLevel.WRITE},
            tenant_isolation=True,
            conditions={
                "same_tenant_required": True,
                "encryption_required": True
            },
            compliance_tags=["encryption", "audit_required"]
        )
        
        # Encryption key access policy
        self.access_policies["encryption_key_access"] = AccessPolicy(
            policy_id="encryption_key_access",
            name="Encryption Key Access",
            resource_type=ResourceType.ENCRYPTION_KEY,
            required_identity_level=IdentityLevel.PRIVILEGED,
            allowed_access_levels={AccessLevel.READ},
            tenant_isolation=True,
            conditions={
                "same_tenant_required": True,
                "audit_required": True,
                "mfa_required": True
            },
            compliance_tags=["maximum_security", "key_management"]
        )
        
        # Admin API access policy
        self.access_policies["admin_api_access"] = AccessPolicy(
            policy_id="admin_api_access",
            name="Administrative API Access",
            resource_type=ResourceType.API_ENDPOINT,
            required_identity_level=IdentityLevel.ADMIN,
            allowed_access_levels={AccessLevel.ADMIN},
            tenant_isolation=False,  # Admin can cross tenants
            conditions={
                "audit_required": True,
                "certificate_required": True,
                "continuous_monitoring": True
            },
            time_restrictions={
                "allowed_hours": list(range(8, 18)),  # 8 AM to 6 PM UTC
                "timezone": "UTC"
            },
            compliance_tags=["administrative", "high_privilege"]
        )
        
        # Audit log access policy
        self.access_policies["audit_log_access"] = AccessPolicy(
            policy_id="audit_log_access",
            name="Audit Log Access",
            resource_type=ResourceType.AUDIT_LOG,
            required_identity_level=IdentityLevel.PRIVILEGED,
            allowed_access_levels={AccessLevel.READ},
            tenant_isolation=True,
            conditions={
                "audit_required": True,
                "read_only": True,
                "retention_aware": True
            },
            compliance_tags=["audit", "compliance", "read_only"]
        )
        
        logger.info(f"Setup {len(self.access_policies)} default access policies")
    
    def register_resource(self, resource_id: str, resource_type: ResourceType,
                         tenant_id: UUID, owner_id: UUID, 
                         classification_level: str = "internal",
                         attributes: Optional[Dict[str, Any]] = None) -> bool:
        """Register resource for access control."""
        try:
            resource = Resource(
                resource_id=resource_id,
                resource_type=resource_type,
                tenant_id=tenant_id,
                owner_id=owner_id,
                classification_level=classification_level,
                attributes=attributes or {}
            )
            
            self.resources[resource_id] = resource
            
            logger.debug(f"Registered resource {resource_id} for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register resource {resource_id}: {str(e)}")
            return False
    
    def check_access(self, identity: Identity, resource_id: str,
                    requested_access_level: AccessLevel,
                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check access permissions using zero-trust principles."""
        start_time = time.time()
        
        try:
            # Get resource
            if resource_id not in self.resources:
                return self._create_access_result(False, "Resource not found")
            
            resource = self.resources[resource_id]
            
            # Create access request
            access_request = AccessRequest(
                identity=identity,
                resource=resource,
                requested_access_level=requested_access_level,
                context=context or {}
            )
            
            # Find applicable policy
            policy = self._get_applicable_policy(resource.resource_type)
            if not policy:
                return self._create_access_result(False, "No applicable access policy")
            
            # Perform zero-trust access evaluation
            access_decision = self._evaluate_access_request(access_request, policy)
            
            # Record access decision
            decision_time = time.time() - start_time
            self._record_access_decision(access_request, policy, access_decision, decision_time)
            
            # Update metrics
            self.metrics["total_access_requests"] += 1
            if access_decision["granted"]:
                self.metrics["granted_requests"] += 1
            else:
                self.metrics["denied_requests"] += 1
            
            return access_decision
            
        except Exception as e:
            logger.error(f"Access check failed: {str(e)}")
            return self._create_access_result(False, f"Access check error: {str(e)}")
    
    def _evaluate_access_request(self, request: AccessRequest, policy: AccessPolicy) -> Dict[str, Any]:
        """Evaluate access request against policy using zero-trust principles."""
        
        # 1. Identity level check
        if request.identity.identity_level.value < policy.required_identity_level.value:
            return self._create_access_result(
                False, 
                f"Insufficient identity level: {request.identity.identity_level.value} < {policy.required_identity_level.value}"
            )
        
        # 2. Access level check
        if request.requested_access_level not in policy.allowed_access_levels:
            return self._create_access_result(
                False,
                f"Access level {request.requested_access_level.value} not allowed by policy"
            )
        
        # 3. Tenant isolation check
        if policy.tenant_isolation and request.identity.tenant_id != request.resource.tenant_id:
            self._record_cross_tenant_attempt(request)
            return self._create_access_result(False, "Cross-tenant access denied")
        
        # 4. Resource ownership check
        if (request.requested_access_level in [AccessLevel.ADMIN, AccessLevel.OWNER] and 
            request.identity.user_id != request.resource.owner_id):
            return self._create_access_result(False, "Ownership required for admin access")
        
        # 5. Classification level check
        if not self._check_classification_access(request.identity, request.resource.classification_level):
            return self._create_access_result(False, "Insufficient clearance for classification level")
        
        # 6. Condition checks
        condition_result = self._evaluate_policy_conditions(request, policy)
        if not condition_result["passed"]:
            return self._create_access_result(False, f"Policy condition failed: {condition_result['reason']}")
        
        # 7. Time restrictions check
        if policy.time_restrictions and not self._check_time_restrictions(policy.time_restrictions):
            return self._create_access_result(False, "Access denied due to time restrictions")
        
        # 8. IP restrictions check
        if policy.ip_restrictions and not self._check_ip_restrictions(request.identity.ip_address, policy.ip_restrictions):
            return self._create_access_result(False, "Access denied due to IP restrictions")
        
        # All checks passed - grant access
        access_result = self._create_access_result(True, "Access granted")
        
        # Record privileged access
        if request.requested_access_level in [AccessLevel.ADMIN, AccessLevel.OWNER]:
            self._record_privileged_access(request, policy)
        
        return access_result
    
    def _get_applicable_policy(self, resource_type: ResourceType) -> Optional[AccessPolicy]:
        """Get applicable access policy for resource type."""
        for policy in self.access_policies.values():
            if policy.resource_type == resource_type:
                return policy
        return None
    
    def _check_classification_access(self, identity: Identity, classification: str) -> bool:
        """Check if identity has access to classification level."""
        # Classification hierarchy: public < internal < confidential < restricted
        classification_levels = {
            "public": 0,
            "internal": 1,
            "confidential": 2,
            "restricted": 3
        }
        
        # Identity clearance mapping
        identity_clearance = {
            IdentityLevel.ANONYMOUS: 0,
            IdentityLevel.BASIC: 1,
            IdentityLevel.VERIFIED: 2,
            IdentityLevel.PRIVILEGED: 3,
            IdentityLevel.ADMIN: 3
        }
        
        required_level = classification_levels.get(classification, 999)
        user_clearance = identity_clearance.get(identity.identity_level, 0)
        
        return user_clearance >= required_level
    
    def _evaluate_policy_conditions(self, request: AccessRequest, policy: AccessPolicy) -> Dict[str, Any]:
        """Evaluate policy-specific conditions."""
        
        for condition, value in policy.conditions.items():
            
            if condition == "same_tenant_required" and value:
                if request.identity.tenant_id != request.resource.tenant_id:
                    return {"passed": False, "reason": "Same tenant required"}
            
            elif condition == "encryption_required" and value:
                # Check if resource supports encryption
                if not request.resource.attributes.get("encrypted", False):
                    return {"passed": False, "reason": "Resource must be encrypted"}
            
            elif condition == "audit_required" and value:
                # Audit logging will be handled separately
                pass
            
            elif condition == "mfa_required" and value:
                from .identity_verification import AuthenticationMethod
                if AuthenticationMethod.MFA not in request.identity.authenticated_methods:
                    return {"passed": False, "reason": "Multi-factor authentication required"}
            
            elif condition == "certificate_required" and value:
                from .identity_verification import AuthenticationMethod
                if AuthenticationMethod.CERTIFICATE not in request.identity.authenticated_methods:
                    return {"passed": False, "reason": "Certificate authentication required"}
            
            elif condition == "read_only" and value:
                if request.requested_access_level not in [AccessLevel.READ, AccessLevel.DENY]:
                    return {"passed": False, "reason": "Read-only access policy"}
            
            elif condition == "continuous_monitoring" and value:
                # Mark for continuous monitoring
                request.context["requires_continuous_monitoring"] = True
        
        return {"passed": True, "reason": "All conditions satisfied"}
    
    def _check_time_restrictions(self, time_restrictions: Dict[str, Any]) -> bool:
        """Check if current time meets restrictions."""
        current_time = datetime.utcnow()
        
        if "allowed_hours" in time_restrictions:
            allowed_hours = time_restrictions["allowed_hours"]
            if current_time.hour not in allowed_hours:
                return False
        
        if "allowed_days" in time_restrictions:
            allowed_days = time_restrictions["allowed_days"]  # 0-6, Monday=0
            if current_time.weekday() not in allowed_days:
                return False
        
        return True
    
    def _check_ip_restrictions(self, ip_address: str, allowed_ips: List[str]) -> bool:
        """Check if IP address meets restrictions."""
        # Simplified IP checking - in production use proper CIDR matching
        for allowed_ip in allowed_ips:
            if ip_address.startswith(allowed_ip.split('/')[0]):
                return True
        return False
    
    def _record_access_decision(self, request: AccessRequest, policy: AccessPolicy, 
                              decision: Dict[str, Any], decision_time: float):
        """Record access decision for audit purposes."""
        entry = {
            "timestamp": request.timestamp.isoformat(),
            "user_id": str(request.identity.user_id),
            "tenant_id": str(request.identity.tenant_id),
            "session_id": request.identity.session_id,
            "resource_id": request.resource.resource_id,
            "resource_type": request.resource.resource_type.value,
            "requested_access_level": request.requested_access_level.value,
            "policy_id": policy.policy_id,
            "granted": decision["granted"],
            "reason": decision["message"],
            "decision_time_ms": decision_time * 1000,
            "ip_address": request.identity.ip_address
        }
        
        self.access_decisions.append(entry)
        
        # Keep decisions manageable
        if len(self.access_decisions) > 10000:
            self.access_decisions = self.access_decisions[-5000:]
    
    def _record_privileged_access(self, request: AccessRequest, policy: AccessPolicy):
        """Record privileged access for enhanced monitoring."""
        entry = {
            "timestamp": request.timestamp.isoformat(),
            "user_id": str(request.identity.user_id),
            "tenant_id": str(request.identity.tenant_id),
            "session_id": request.identity.session_id,
            "resource_id": request.resource.resource_id,
            "access_level": request.requested_access_level.value,
            "policy_id": policy.policy_id,
            "ip_address": request.identity.ip_address,
            "identity_level": request.identity.identity_level.value
        }
        
        self.privileged_access_log.append(entry)
        self.metrics["privilege_escalations"] += 1
        
        # Keep privileged access log manageable
        if len(self.privileged_access_log) > 1000:
            self.privileged_access_log = self.privileged_access_log[-500:]
        
        logger.info(f"Privileged access granted: {request.identity.user_id} -> {request.resource.resource_id}")
    
    def _record_cross_tenant_attempt(self, request: AccessRequest):
        """Record cross-tenant access attempt."""
        violation = {
            "timestamp": request.timestamp.isoformat(),
            "user_id": str(request.identity.user_id),
            "user_tenant_id": str(request.identity.tenant_id),
            "resource_id": request.resource.resource_id,
            "resource_tenant_id": str(request.resource.tenant_id),
            "attempted_access": request.requested_access_level.value,
            "ip_address": request.identity.ip_address,
            "type": "cross_tenant_access"
        }
        
        self.access_violations.append(violation)
        self.metrics["cross_tenant_attempts"] += 1
        
        logger.warning(f"Cross-tenant access attempt: {request.identity.user_id} -> {request.resource.resource_id}")
    
    def _create_access_result(self, granted: bool, message: str, 
                            data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create standardized access result."""
        result = {
            "granted": granted,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if data:
            result["data"] = data
        
        return result
    
    def create_custom_policy(self, policy_id: str, name: str, 
                           resource_type: ResourceType,
                           required_identity_level: IdentityLevel,
                           allowed_access_levels: Set[AccessLevel],
                           conditions: Optional[Dict[str, Any]] = None) -> bool:
        """Create custom access policy."""
        try:
            policy = AccessPolicy(
                policy_id=policy_id,
                name=name,
                resource_type=resource_type,
                required_identity_level=required_identity_level,
                allowed_access_levels=allowed_access_levels,
                conditions=conditions or {}
            )
            
            self.access_policies[policy_id] = policy
            
            logger.info(f"Created custom access policy: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create custom policy {policy_id}: {str(e)}")
            return False
    
    def get_user_accessible_resources(self, identity: Identity, 
                                    resource_type: Optional[ResourceType] = None) -> List[Dict[str, Any]]:
        """Get list of resources accessible to user."""
        accessible_resources = []
        
        for resource_id, resource in self.resources.items():
            if resource_type and resource.resource_type != resource_type:
                continue
            
            # Check if user can access resource (read level)
            access_result = self.check_access(identity, resource_id, AccessLevel.READ)
            
            if access_result["granted"]:
                # Determine maximum access level
                max_access = AccessLevel.DENY
                for access_level in [AccessLevel.READ, AccessLevel.WRITE, AccessLevel.ADMIN, AccessLevel.OWNER]:
                    test_result = self.check_access(identity, resource_id, access_level)
                    if test_result["granted"]:
                        max_access = access_level
                
                accessible_resources.append({
                    "resource_id": resource_id,
                    "resource_type": resource.resource_type.value,
                    "tenant_id": str(resource.tenant_id),
                    "classification": resource.classification_level,
                    "max_access_level": max_access.value,
                    "is_owner": resource.owner_id == identity.user_id
                })
        
        return accessible_resources
    
    def revoke_resource_access(self, resource_id: str, reason: str = "Security policy") -> bool:
        """Revoke all access to a resource."""
        if resource_id not in self.resources:
            return False
        
        # Mark resource as access revoked
        self.resources[resource_id].attributes["access_revoked"] = True
        self.resources[resource_id].attributes["revocation_reason"] = reason
        self.resources[resource_id].attributes["revoked_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Revoked access to resource {resource_id}: {reason}")
        return True
    
    def get_access_metrics(self) -> Dict[str, Any]:
        """Get comprehensive access control metrics."""
        return {
            **self.metrics,
            "total_resources": len(self.resources),
            "total_policies": len(self.access_policies),
            "access_decision_entries": len(self.access_decisions),
            "privileged_access_entries": len(self.privileged_access_log),
            "access_violation_entries": len(self.access_violations),
            "grant_rate": (
                self.metrics["granted_requests"] / 
                max(self.metrics["total_access_requests"], 1)
            ) * 100
        }
    
    def get_security_violations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent security violations."""
        return self.access_violations[-limit:]
    
    def get_privileged_access_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent privileged access attempts."""
        return self.privileged_access_log[-limit:]