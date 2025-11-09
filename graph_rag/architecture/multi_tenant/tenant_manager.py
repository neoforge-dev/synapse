"""Central tenant management and routing for multi-tenant architecture.

This module provides the core tenant management functionality including:
- Tenant context detection and management
- Request routing to tenant-specific resources
- Tenant boundary enforcement and security
- Cross-tenant data access prevention
"""

import hashlib
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Thread-local tenant context
_tenant_context: ContextVar[Optional['TenantContext']] = ContextVar('tenant_context', default=None)


class TenantType(str, Enum):
    """Types of tenants supported by the platform."""
    ENTERPRISE = "enterprise"
    CONSULTATION = "consultation"
    TRIAL = "trial"
    INTERNAL = "internal"


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    MIGRATING = "migrating"
    DECOMMISSIONED = "decommissioned"


@dataclass
class TenantContext:
    """Runtime context for the current tenant."""
    tenant_id: str
    tenant_name: str
    tenant_type: TenantType
    status: TenantStatus
    database_config: dict[str, Any]
    resource_limits: dict[str, Any]
    feature_flags: dict[str, bool]
    custom_settings: dict[str, Any]
    isolation_level: str = "database"
    created_at: datetime | None = None
    last_accessed: datetime | None = None

    def __post_init__(self):
        """Initialize computed fields after creation."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()

    @property
    def database_name(self) -> str:
        """Generate consistent database name for tenant."""
        # Use consistent naming: synapse_tenant_{tenant_id_hash}
        tenant_hash = hashlib.sha256(self.tenant_id.encode()).hexdigest()[:8]
        return f"synapse_tenant_{tenant_hash}"

    @property
    def is_enterprise(self) -> bool:
        """Check if this is an enterprise tenant."""
        return self.tenant_type == TenantType.ENTERPRISE

    @property
    def is_consultation(self) -> bool:
        """Check if this is a consultation tenant (Epic 7 protection)."""
        return self.tenant_type == TenantType.CONSULTATION


class TenantConfiguration(BaseModel):
    """Persistent tenant configuration model."""
    tenant_id: str
    tenant_name: str
    tenant_type: TenantType
    status: TenantStatus
    domain: str | None = None

    # Database Configuration
    database_config: dict[str, Any] = {}
    isolation_level: str = "database"

    # Resource Limits
    max_users: int = 100
    max_documents: int = 10000
    max_api_calls_per_hour: int = 1000
    storage_limit_gb: int = 100

    # Feature Flags
    enable_advanced_analytics: bool = True
    enable_white_label: bool = False
    enable_api_access: bool = True
    enable_export: bool = True

    # Custom Settings
    custom_branding: dict[str, Any] = {}
    integration_settings: dict[str, Any] = {}
    compliance_settings: dict[str, Any] = {}

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    contact_email: str | None = None

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class TenantManager:
    """Central tenant management system."""

    def __init__(self):
        """Initialize tenant manager."""
        self._tenant_configs: dict[str, TenantConfiguration] = {}
        self._tenant_contexts: dict[str, TenantContext] = {}
        self._domain_to_tenant: dict[str, str] = {}
        self._consultation_tenant_id: str | None = None  # Epic 7 protection

        # Initialize with consultation tenant for Epic 7 compatibility
        self._ensure_consultation_tenant()

        logger.info("TenantManager initialized with multi-tenant support")

    def _ensure_consultation_tenant(self) -> None:
        """Ensure consultation tenant exists for Epic 7 compatibility."""
        consultation_id = "consultation_synapse"

        if consultation_id not in self._tenant_configs:
            config = TenantConfiguration(
                tenant_id=consultation_id,
                tenant_name="Synapse Consultation Services",
                tenant_type=TenantType.CONSULTATION,
                status=TenantStatus.ACTIVE,
                max_users=10,
                max_documents=5000,
                max_api_calls_per_hour=500,
                storage_limit_gb=50,
                enable_advanced_analytics=True,
                enable_white_label=False,
                enable_api_access=True,
                enable_export=True,
                database_config={
                    "use_existing_databases": True,  # Use current Epic 11 databases
                    "database_names": [
                        "synapse_analytics_intelligence.db",
                        "synapse_business_crm.db",
                        "synapse_content_intelligence.db",
                        "synapse_system_infrastructure.db"
                    ]
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by="system",
                contact_email="consultation@synapse.ai"
            )

            self._tenant_configs[consultation_id] = config
            self._consultation_tenant_id = consultation_id

            logger.info(f"Created consultation tenant {consultation_id} for Epic 7 compatibility")

    def get_current_tenant(self) -> TenantContext | None:
        """Get the current tenant context from thread-local storage."""
        return _tenant_context.get()

    def detect_tenant_from_request(self, request: Request) -> str | None:
        """Detect tenant ID from incoming request.

        Tenant detection priority:
        1. Explicit tenant_id header (X-Tenant-ID)
        2. Subdomain extraction (tenant.domain.com)
        3. JWT token tenant claim
        4. Default consultation tenant (Epic 7 compatibility)
        """
        # Method 1: Explicit tenant header
        tenant_id = request.headers.get("x-tenant-id")
        if tenant_id:
            logger.debug(f"Tenant detected from header: {tenant_id}")
            return tenant_id

        # Method 2: Subdomain detection
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain in self._tenant_configs:
                logger.debug(f"Tenant detected from subdomain: {subdomain}")
                return subdomain

            # Check domain mapping
            if host in self._domain_to_tenant:
                tenant_id = self._domain_to_tenant[host]
                logger.debug(f"Tenant detected from domain mapping: {tenant_id}")
                return tenant_id

        # Method 3: JWT token (if available)
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            # Note: JWT tenant extraction can be added by decoding token and reading
            # 'tenant_id' claim using graph_rag.api.auth.jwt_handler.JWTHandler
            # Currently handled by Method 1 (subdomain) and Method 2 (header) in production
            pass

        # Method 4: Default to consultation tenant for compatibility
        logger.debug(f"Using default consultation tenant: {self._consultation_tenant_id}")
        return self._consultation_tenant_id

    def get_tenant_config(self, tenant_id: str) -> TenantConfiguration | None:
        """Get tenant configuration by ID."""
        return self._tenant_configs.get(tenant_id)

    def create_tenant_context(self, tenant_id: str) -> TenantContext | None:
        """Create runtime tenant context from configuration."""
        config = self.get_tenant_config(tenant_id)
        if not config:
            logger.warning(f"Tenant configuration not found: {tenant_id}")
            return None

        context = TenantContext(
            tenant_id=config.tenant_id,
            tenant_name=config.tenant_name,
            tenant_type=config.tenant_type,
            status=config.status,
            database_config=config.database_config,
            resource_limits={
                "max_users": config.max_users,
                "max_documents": config.max_documents,
                "max_api_calls_per_hour": config.max_api_calls_per_hour,
                "storage_limit_gb": config.storage_limit_gb,
            },
            feature_flags={
                "enable_advanced_analytics": config.enable_advanced_analytics,
                "enable_white_label": config.enable_white_label,
                "enable_api_access": config.enable_api_access,
                "enable_export": config.enable_export,
            },
            custom_settings={
                "custom_branding": config.custom_branding,
                "integration_settings": config.integration_settings,
                "compliance_settings": config.compliance_settings,
            },
            isolation_level=config.isolation_level,
            created_at=config.created_at,
        )

        self._tenant_contexts[tenant_id] = context
        return context

    @contextmanager
    def tenant_scope(self, tenant_id: str):
        """Context manager for executing code within a tenant scope."""
        previous_context = _tenant_context.get()
        context = self.create_tenant_context(tenant_id)

        if not context:
            raise ValueError(f"Cannot create tenant context for: {tenant_id}")

        if context.status != TenantStatus.ACTIVE:
            raise HTTPException(
                status_code=503,
                detail=f"Tenant {tenant_id} is not active (status: {context.status})"
            )

        _tenant_context.set(context)

        try:
            logger.debug(f"Entered tenant scope: {tenant_id}")
            yield context
        finally:
            _tenant_context.set(previous_context)
            logger.debug(f"Exited tenant scope: {tenant_id}")

    def validate_tenant_access(self, tenant_id: str, required_feature: str | None = None) -> bool:
        """Validate if tenant has access to specific features."""
        context = self.get_current_tenant()

        if not context or context.tenant_id != tenant_id:
            logger.warning("Tenant access validation failed - context mismatch")
            return False

        if context.status != TenantStatus.ACTIVE:
            logger.warning(f"Tenant access validation failed - inactive status: {context.status}")
            return False

        if required_feature and not context.feature_flags.get(required_feature, False):
            logger.warning(f"Tenant access validation failed - feature disabled: {required_feature}")
            return False

        return True

    def register_tenant(self, config: TenantConfiguration) -> str:
        """Register a new tenant configuration."""
        # Validate configuration
        if config.tenant_id in self._tenant_configs:
            raise ValueError(f"Tenant already exists: {config.tenant_id}")

        # Store configuration
        self._tenant_configs[config.tenant_id] = config

        # Setup domain mapping if domain specified
        if config.domain:
            self._domain_to_tenant[config.domain] = config.tenant_id

        logger.info(f"Registered new tenant: {config.tenant_id} ({config.tenant_type})")
        return config.tenant_id

    def get_all_tenants(self) -> list[TenantConfiguration]:
        """Get all registered tenant configurations."""
        return list(self._tenant_configs.values())

    def get_tenants_by_type(self, tenant_type: TenantType) -> list[TenantConfiguration]:
        """Get tenants filtered by type."""
        return [
            config for config in self._tenant_configs.values()
            if config.tenant_type == tenant_type
        ]

    def update_tenant_status(self, tenant_id: str, status: TenantStatus) -> bool:
        """Update tenant status."""
        config = self._tenant_configs.get(tenant_id)
        if not config:
            return False

        old_status = config.status
        config.status = status
        config.updated_at = datetime.utcnow()

        logger.info(f"Updated tenant {tenant_id} status: {old_status} -> {status}")
        return True

    def deregister_tenant(self, tenant_id: str) -> bool:
        """Remove a tenant registration (use with caution)."""
        if tenant_id == self._consultation_tenant_id:
            logger.error("Cannot deregister consultation tenant - Epic 7 protection")
            return False

        config = self._tenant_configs.pop(tenant_id, None)
        if not config:
            return False

        # Remove domain mapping
        if config.domain:
            self._domain_to_tenant.pop(config.domain, None)

        # Remove cached context
        self._tenant_contexts.pop(tenant_id, None)

        logger.warning(f"Deregistered tenant: {tenant_id}")
        return True


# Global tenant manager instance
_tenant_manager: TenantManager | None = None


def get_tenant_manager() -> TenantManager:
    """Get the global tenant manager instance."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


def get_current_tenant() -> TenantContext | None:
    """Helper function to get current tenant context."""
    return get_tenant_manager().get_current_tenant()


def require_tenant() -> TenantContext:
    """Helper function that requires a tenant context to be set."""
    context = get_current_tenant()
    if not context:
        raise HTTPException(
            status_code=400,
            detail="Operation requires tenant context"
        )
    return context
