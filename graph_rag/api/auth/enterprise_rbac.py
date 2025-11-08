"""Enterprise Role-Based Access Control with hierarchical roles and multi-tenant isolation."""

import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from .models import User, UserRole

logger = logging.getLogger(__name__)


class EnterpriseUserRole(str, Enum):
    """Enterprise user roles with hierarchical permissions."""

    # System-wide roles (highest level)
    SYSTEM_ADMIN = "system_admin"          # Full system access across all tenants
    PLATFORM_ADMIN = "platform_admin"     # Platform management, tenant creation

    # Enterprise client roles (per-client/tenant)
    ENTERPRISE_ADMIN = "enterprise_admin"  # Full access within client boundary
    DEPARTMENT_MANAGER = "department_manager"  # Department-level management
    POWER_USER = "power_user"             # Advanced features, no admin functions
    BUSINESS_USER = "business_user"       # Standard business functionality
    END_USER = "end_user"                 # Basic GraphRAG access

    # Special purpose roles
    AUDITOR = "auditor"                   # Audit logs and compliance reporting
    API_CLIENT = "api_client"             # Programmatic API access only
    READONLY = "readonly"                 # Read-only access to all resources


class Permission(str, Enum):
    """Granular permissions for enterprise access control."""

    # System-level permissions
    SYSTEM_MANAGE = "system:manage"
    PLATFORM_MANAGE = "platform:manage"
    TENANT_CREATE = "tenant:create"
    TENANT_MANAGE = "tenant:manage"

    # User management permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"

    # Document and knowledge permissions
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_INGEST = "document:ingest"

    # Search and query permissions
    SEARCH_BASIC = "search:basic"
    SEARCH_ADVANCED = "search:advanced"
    QUERY_EXECUTE = "query:execute"
    QUERY_CREATE_COMPLEX = "query:create_complex"

    # Graph and analytics permissions
    GRAPH_READ = "graph:read"
    GRAPH_MODIFY = "graph:modify"
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"

    # API and integration permissions
    API_KEY_CREATE = "api_key:create"
    API_KEY_MANAGE = "api_key:manage"
    WEBHOOK_MANAGE = "webhook:manage"

    # Audit and compliance permissions
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    COMPLIANCE_REPORT = "compliance:report"

    # Configuration permissions
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"
    SSO_MANAGE = "sso:manage"


class ResourceType(str, Enum):
    """Resource types for access control."""

    SYSTEM = "system"
    TENANT = "tenant"
    USER = "user"
    DOCUMENT = "document"
    SEARCH = "search"
    QUERY = "query"
    GRAPH = "graph"
    API_KEY = "api_key"
    AUDIT_LOG = "audit_log"
    CONFIG = "config"


class EnterpriseRolePermissions:
    """Defines permissions for each enterprise role."""

    ROLE_PERMISSIONS = {
        EnterpriseUserRole.SYSTEM_ADMIN: [
            # Full system access
            Permission.SYSTEM_MANAGE, Permission.PLATFORM_MANAGE,
            Permission.TENANT_CREATE, Permission.TENANT_MANAGE,
            Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
            Permission.USER_DELETE, Permission.USER_MANAGE_ROLES,
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE, Permission.DOCUMENT_INGEST,
            Permission.SEARCH_BASIC, Permission.SEARCH_ADVANCED,
            Permission.QUERY_EXECUTE, Permission.QUERY_CREATE_COMPLEX,
            Permission.GRAPH_READ, Permission.GRAPH_MODIFY,
            Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
            Permission.API_KEY_CREATE, Permission.API_KEY_MANAGE,
            Permission.WEBHOOK_MANAGE, Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
            Permission.COMPLIANCE_REPORT, Permission.CONFIG_READ, Permission.CONFIG_UPDATE,
            Permission.SSO_MANAGE
        ],

        EnterpriseUserRole.PLATFORM_ADMIN: [
            # Platform management within tenant boundary
            Permission.PLATFORM_MANAGE, Permission.TENANT_MANAGE,
            Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
            Permission.USER_DELETE, Permission.USER_MANAGE_ROLES,
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE, Permission.DOCUMENT_INGEST,
            Permission.SEARCH_BASIC, Permission.SEARCH_ADVANCED,
            Permission.QUERY_EXECUTE, Permission.QUERY_CREATE_COMPLEX,
            Permission.GRAPH_READ, Permission.GRAPH_MODIFY,
            Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
            Permission.API_KEY_CREATE, Permission.API_KEY_MANAGE,
            Permission.WEBHOOK_MANAGE, Permission.CONFIG_READ, Permission.CONFIG_UPDATE,
            Permission.SSO_MANAGE
        ],

        EnterpriseUserRole.ENTERPRISE_ADMIN: [
            # Full access within enterprise client boundary
            Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
            Permission.USER_MANAGE_ROLES,
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE, Permission.DOCUMENT_INGEST,
            Permission.SEARCH_BASIC, Permission.SEARCH_ADVANCED,
            Permission.QUERY_EXECUTE, Permission.QUERY_CREATE_COMPLEX,
            Permission.GRAPH_READ, Permission.GRAPH_MODIFY,
            Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
            Permission.API_KEY_CREATE, Permission.API_KEY_MANAGE,
            Permission.WEBHOOK_MANAGE, Permission.AUDIT_READ,
            Permission.CONFIG_READ, Permission.CONFIG_UPDATE
        ],

        EnterpriseUserRole.DEPARTMENT_MANAGER: [
            # Department-level management
            Permission.USER_READ, Permission.USER_UPDATE,
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_INGEST,
            Permission.SEARCH_BASIC, Permission.SEARCH_ADVANCED,
            Permission.QUERY_EXECUTE, Permission.QUERY_CREATE_COMPLEX,
            Permission.GRAPH_READ,
            Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
            Permission.API_KEY_CREATE, Permission.CONFIG_READ
        ],

        EnterpriseUserRole.POWER_USER: [
            # Advanced features, no admin functions
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_INGEST,
            Permission.SEARCH_BASIC, Permission.SEARCH_ADVANCED,
            Permission.QUERY_EXECUTE, Permission.QUERY_CREATE_COMPLEX,
            Permission.GRAPH_READ,
            Permission.ANALYTICS_VIEW,
            Permission.API_KEY_CREATE
        ],

        EnterpriseUserRole.BUSINESS_USER: [
            # Standard business functionality
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ,
            Permission.DOCUMENT_INGEST,
            Permission.SEARCH_BASIC, Permission.SEARCH_ADVANCED,
            Permission.QUERY_EXECUTE,
            Permission.GRAPH_READ,
            Permission.ANALYTICS_VIEW
        ],

        EnterpriseUserRole.END_USER: [
            # Basic GraphRAG access
            Permission.DOCUMENT_READ,
            Permission.SEARCH_BASIC,
            Permission.QUERY_EXECUTE,
            Permission.GRAPH_READ
        ],

        EnterpriseUserRole.AUDITOR: [
            # Audit and compliance access
            Permission.USER_READ,
            Permission.DOCUMENT_READ,
            Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
            Permission.COMPLIANCE_REPORT,
            Permission.ANALYTICS_VIEW, Permission.CONFIG_READ
        ],

        EnterpriseUserRole.API_CLIENT: [
            # Programmatic access
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_INGEST,
            Permission.SEARCH_BASIC, Permission.SEARCH_ADVANCED,
            Permission.QUERY_EXECUTE,
            Permission.GRAPH_READ
        ],

        EnterpriseUserRole.READONLY: [
            # Read-only access
            Permission.USER_READ, Permission.DOCUMENT_READ,
            Permission.SEARCH_BASIC, Permission.QUERY_EXECUTE,
            Permission.GRAPH_READ, Permission.ANALYTICS_VIEW,
            Permission.CONFIG_READ
        ]
    }

    @classmethod
    def get_permissions(cls, role: EnterpriseUserRole) -> set[Permission]:
        """Get all permissions for a role."""
        return set(cls.ROLE_PERMISSIONS.get(role, []))

    @classmethod
    def has_permission(cls, role: EnterpriseUserRole, permission: Permission) -> bool:
        """Check if role has specific permission."""
        return permission in cls.get_permissions(role)

    @classmethod
    def get_role_hierarchy(cls) -> dict[EnterpriseUserRole, list[EnterpriseUserRole]]:
        """Get role hierarchy - higher roles inherit permissions from lower roles."""
        return {
            EnterpriseUserRole.SYSTEM_ADMIN: [
                EnterpriseUserRole.PLATFORM_ADMIN, EnterpriseUserRole.ENTERPRISE_ADMIN,
                EnterpriseUserRole.DEPARTMENT_MANAGER, EnterpriseUserRole.POWER_USER,
                EnterpriseUserRole.BUSINESS_USER, EnterpriseUserRole.END_USER,
                EnterpriseUserRole.AUDITOR, EnterpriseUserRole.API_CLIENT,
                EnterpriseUserRole.READONLY
            ],
            EnterpriseUserRole.PLATFORM_ADMIN: [
                EnterpriseUserRole.ENTERPRISE_ADMIN, EnterpriseUserRole.DEPARTMENT_MANAGER,
                EnterpriseUserRole.POWER_USER, EnterpriseUserRole.BUSINESS_USER,
                EnterpriseUserRole.END_USER, EnterpriseUserRole.API_CLIENT,
                EnterpriseUserRole.READONLY
            ],
            EnterpriseUserRole.ENTERPRISE_ADMIN: [
                EnterpriseUserRole.DEPARTMENT_MANAGER, EnterpriseUserRole.POWER_USER,
                EnterpriseUserRole.BUSINESS_USER, EnterpriseUserRole.END_USER,
                EnterpriseUserRole.API_CLIENT, EnterpriseUserRole.READONLY
            ],
            EnterpriseUserRole.DEPARTMENT_MANAGER: [
                EnterpriseUserRole.POWER_USER, EnterpriseUserRole.BUSINESS_USER,
                EnterpriseUserRole.END_USER, EnterpriseUserRole.READONLY
            ],
            EnterpriseUserRole.POWER_USER: [
                EnterpriseUserRole.BUSINESS_USER, EnterpriseUserRole.END_USER,
                EnterpriseUserRole.READONLY
            ],
            EnterpriseUserRole.BUSINESS_USER: [
                EnterpriseUserRole.END_USER, EnterpriseUserRole.READONLY
            ]
        }


class TenantContext(BaseModel):
    """Context for tenant-specific operations."""

    tenant_id: str
    client_id: str
    user_id: UUID
    user_role: EnterpriseUserRole
    permissions: set[Permission] = Field(default_factory=set)
    resource_restrictions: dict[ResourceType, list[str]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
            set: list
        }


class EnterpriseRBACManager:
    """Enterprise RBAC manager with multi-tenant isolation and hierarchical roles."""

    def __init__(self):
        self.role_permissions = EnterpriseRolePermissions()
        self.tenant_contexts: dict[str, TenantContext] = {}

    def map_legacy_role(self, legacy_role: UserRole) -> EnterpriseUserRole:
        """Map legacy UserRole to EnterpriseUserRole for backward compatibility."""
        mapping = {
            UserRole.ADMIN: EnterpriseUserRole.ENTERPRISE_ADMIN,
            UserRole.USER: EnterpriseUserRole.BUSINESS_USER,
            UserRole.READONLY: EnterpriseUserRole.READONLY
        }
        return mapping.get(legacy_role, EnterpriseUserRole.END_USER)

    def create_tenant_context(self, tenant_id: str, client_id: str, user: User) -> TenantContext:
        """Create tenant context for user with role-based permissions."""
        # Map legacy role if needed
        if isinstance(user.role, UserRole):
            enterprise_role = self.map_legacy_role(user.role)
        else:
            enterprise_role = user.role

        # Get role permissions
        permissions = self.role_permissions.get_permissions(enterprise_role)

        # Create tenant context
        context = TenantContext(
            tenant_id=tenant_id,
            client_id=client_id,
            user_id=user.id,
            user_role=enterprise_role,
            permissions=permissions
        )

        # Cache context
        context_key = f"{tenant_id}:{user.id}"
        self.tenant_contexts[context_key] = context

        logger.info(f"Created tenant context for user {user.username} in tenant {tenant_id} with role {enterprise_role}")

        return context

    def get_tenant_context(self, tenant_id: str, user_id: UUID) -> TenantContext | None:
        """Get cached tenant context."""
        context_key = f"{tenant_id}:{user_id}"
        return self.tenant_contexts.get(context_key)

    def check_permission(self, context: TenantContext, permission: Permission,
                        resource_type: ResourceType | None = None,
                        resource_id: str | None = None) -> bool:
        """Check if user has permission for specific resource in tenant context."""
        # Check if user has the required permission
        if permission not in context.permissions:
            return False

        # Check resource-specific restrictions
        if resource_type and resource_id:
            restrictions = context.resource_restrictions.get(resource_type, [])
            if restrictions and resource_id not in restrictions:
                return False

        return True

    def require_permission(self, context: TenantContext, permission: Permission,
                          resource_type: ResourceType | None = None,
                          resource_id: str | None = None) -> None:
        """Require permission or raise HTTP exception."""
        if not self.check_permission(context, permission, resource_type, resource_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )

    def check_role_hierarchy(self, user_role: EnterpriseUserRole,
                           required_role: EnterpriseUserRole) -> bool:
        """Check if user role is equal or higher in hierarchy than required role."""
        hierarchy = self.role_permissions.get_role_hierarchy()

        if user_role == required_role:
            return True

        # Check if user role inherits from required role
        inherited_roles = hierarchy.get(user_role, [])
        return required_role in inherited_roles

    def get_accessible_resources(self, context: TenantContext,
                               resource_type: ResourceType) -> list[str]:
        """Get list of resources user can access for given type."""
        # For system/platform admins, return all resources marker
        if context.user_role in [EnterpriseUserRole.SYSTEM_ADMIN,
                               EnterpriseUserRole.PLATFORM_ADMIN]:
            return ["*"]  # All resources

        # For tenant-bounded roles, return tenant-specific resources
        restrictions = context.resource_restrictions.get(resource_type, [])
        if not restrictions:
            # If no specific restrictions, user can access tenant resources
            return [f"tenant:{context.tenant_id}:*"]

        return restrictions

    def add_resource_restriction(self, context: TenantContext,
                               resource_type: ResourceType, resource_ids: list[str]) -> None:
        """Add resource-specific restrictions to user context."""
        if resource_type not in context.resource_restrictions:
            context.resource_restrictions[resource_type] = []

        context.resource_restrictions[resource_type].extend(resource_ids)

        logger.info(f"Added resource restrictions for user {context.user_id}: {resource_type} -> {resource_ids}")

    def validate_cross_tenant_access(self, source_context: TenantContext,
                                   target_tenant_id: str) -> bool:
        """Validate if user can access resources across tenants."""
        # Only system and platform admins can access cross-tenant resources
        if source_context.user_role in [EnterpriseUserRole.SYSTEM_ADMIN,
                                       EnterpriseUserRole.PLATFORM_ADMIN]:
            return True

        # Same tenant access is always allowed
        return source_context.tenant_id == target_tenant_id

    def get_user_capabilities(self, context: TenantContext) -> dict[str, Any]:
        """Get user capabilities summary for frontend/API consumers."""
        capabilities = {
            'tenant_id': context.tenant_id,
            'user_role': context.user_role.value,
            'permissions': [p.value for p in context.permissions],
            'can_manage_users': self.check_permission(context, Permission.USER_MANAGE_ROLES),
            'can_access_analytics': self.check_permission(context, Permission.ANALYTICS_VIEW),
            'can_manage_config': self.check_permission(context, Permission.CONFIG_UPDATE),
            'can_view_audit_logs': self.check_permission(context, Permission.AUDIT_READ),
            'is_admin': context.user_role in [
                EnterpriseUserRole.SYSTEM_ADMIN,
                EnterpriseUserRole.PLATFORM_ADMIN,
                EnterpriseUserRole.ENTERPRISE_ADMIN
            ],
            'resource_access': {}
        }

        # Add resource access information
        for resource_type in ResourceType:
            capabilities['resource_access'][resource_type.value] = self.get_accessible_resources(
                context, resource_type
            )

        return capabilities

    def audit_permission_check(self, context: TenantContext, permission: Permission,
                             resource_type: ResourceType | None = None,
                             resource_id: str | None = None, granted: bool = True) -> None:
        """Log permission check for audit trail."""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': context.tenant_id,
            'user_id': str(context.user_id),
            'user_role': context.user_role.value,
            'permission': permission.value,
            'resource_type': resource_type.value if resource_type else None,
            'resource_id': resource_id,
            'granted': granted,
            'context': 'permission_check'
        }

        # In production, this would be sent to audit logging system
        logger.info(f"Permission audit: {audit_entry}")

    def cleanup_expired_contexts(self, max_age_hours: int = 8) -> int:
        """Clean up expired tenant contexts."""
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        expired_contexts = [
            key for key, context in self.tenant_contexts.items()
            if context.created_at.timestamp() < cutoff
        ]

        for key in expired_contexts:
            del self.tenant_contexts[key]

        if expired_contexts:
            logger.info(f"Cleaned up {len(expired_contexts)} expired tenant contexts")

        return len(expired_contexts)
