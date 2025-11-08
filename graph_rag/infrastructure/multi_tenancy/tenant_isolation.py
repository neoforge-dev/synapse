"""Multi-tenancy infrastructure with database-level isolation and security boundaries."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from graph_rag.api.auth.enterprise_models import Tenant
from graph_rag.config import get_settings

logger = logging.getLogger(__name__)


class TenantIsolationError(Exception):
    """Exception raised when tenant isolation is violated."""
    pass


class TenantContext:
    """Thread-local context for tenant isolation."""

    _context: dict[str, Any] = {}

    @classmethod
    def set_tenant(cls, tenant_id: UUID, user_id: UUID | None = None):
        """Set the current tenant context."""
        cls._context = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow()
        }

    @classmethod
    def get_tenant_id(cls) -> UUID | None:
        """Get the current tenant ID."""
        return cls._context.get("tenant_id")

    @classmethod
    def get_user_id(cls) -> UUID | None:
        """Get the current user ID."""
        return cls._context.get("user_id")

    @classmethod
    def clear(cls):
        """Clear the tenant context."""
        cls._context.clear()

    @classmethod
    def validate_tenant_access(cls, tenant_id: UUID) -> bool:
        """Validate that the current context has access to the specified tenant."""
        current_tenant = cls.get_tenant_id()
        if current_tenant is None:
            raise TenantIsolationError("No tenant context set")
        if current_tenant != tenant_id:
            raise TenantIsolationError(f"Access denied to tenant {tenant_id}")
        return True


class TenantDataFilter:
    """Filter data operations based on tenant context."""

    @staticmethod
    def add_tenant_filter(query: str, tenant_id: UUID) -> str:
        """Add tenant filtering to a database query."""
        # For PostgreSQL with tenant_id column
        if "WHERE" in query.upper():
            return query + f" AND tenant_id = '{tenant_id}'"
        else:
            return query + f" WHERE tenant_id = '{tenant_id}'"

    @staticmethod
    def validate_tenant_data(data: dict[str, Any], tenant_id: UUID) -> bool:
        """Validate that data belongs to the correct tenant."""
        data_tenant_id = data.get("tenant_id")
        if data_tenant_id is None:
            raise TenantIsolationError("Data missing tenant_id")
        if str(data_tenant_id) != str(tenant_id):
            raise TenantIsolationError(f"Data belongs to different tenant: {data_tenant_id}")
        return True

    @staticmethod
    def inject_tenant_id(data: dict[str, Any], tenant_id: UUID) -> dict[str, Any]:
        """Inject tenant_id into data for storage operations."""
        data = data.copy()
        data["tenant_id"] = tenant_id
        return data


class TenantDatabaseManager:
    """Manage tenant-specific database operations and isolation."""

    def __init__(self):
        self.settings = get_settings()
        self.tenant_databases: dict[UUID, str] = {}
        self.connection_pools: dict[UUID, Any] = {}

    async def create_tenant_database(self, tenant: Tenant) -> str:
        """Create isolated database for tenant."""
        db_name = f"tenant_{str(tenant.id).replace('-', '_')}"

        if self.settings.tenant_isolation_level == "database":
            # Create separate database
            await self._create_physical_database(db_name)

        elif self.settings.tenant_isolation_level == "schema":
            # Create separate schema within main database
            await self._create_tenant_schema(tenant.id)

        else:
            # Row-level isolation - no separate DB needed
            logger.info(f"Using row-level isolation for tenant {tenant.id}")

        self.tenant_databases[tenant.id] = db_name
        return db_name

    async def get_tenant_connection(self, tenant_id: UUID) -> Any:
        """Get database connection for specific tenant."""
        # Validate tenant context
        TenantContext.validate_tenant_access(tenant_id)

        if tenant_id not in self.connection_pools:
            await self._create_tenant_connection_pool(tenant_id)

        return self.connection_pools[tenant_id]

    async def _create_physical_database(self, db_name: str):
        """Create a new physical database for tenant."""
        # Implementation would depend on specific database system
        logger.info(f"Creating physical database: {db_name}")
        # Example for PostgreSQL:
        # CREATE DATABASE {db_name} WITH TEMPLATE template0 ENCODING 'UTF8'

    async def _create_tenant_schema(self, tenant_id: UUID):
        """Create tenant-specific schema."""
        schema_name = f"tenant_{str(tenant_id).replace('-', '_')}"
        logger.info(f"Creating schema: {schema_name}")
        # Example for PostgreSQL:
        # CREATE SCHEMA IF NOT EXISTS {schema_name}

    async def _create_tenant_connection_pool(self, tenant_id: UUID):
        """Create connection pool for tenant database."""
        # Implementation would create actual connection pool
        logger.info(f"Creating connection pool for tenant {tenant_id}")
        self.connection_pools[tenant_id] = f"connection_pool_{tenant_id}"


class SecureTenantRepository(ABC):
    """Abstract base for tenant-aware data repositories."""

    def __init__(self, db_manager: TenantDatabaseManager):
        self.db_manager = db_manager
        self.data_filter = TenantDataFilter()

    def _get_current_tenant(self) -> UUID:
        """Get current tenant from context."""
        tenant_id = TenantContext.get_tenant_id()
        if tenant_id is None:
            raise TenantIsolationError("No tenant context available")
        return tenant_id

    def _ensure_tenant_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Ensure data includes tenant isolation."""
        tenant_id = self._get_current_tenant()
        return self.data_filter.inject_tenant_id(data, tenant_id)

    def _validate_tenant_data(self, data: dict[str, Any]):
        """Validate data belongs to current tenant."""
        tenant_id = self._get_current_tenant()
        self.data_filter.validate_tenant_data(data, tenant_id)

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> str:
        """Create entity with tenant isolation."""
        pass

    @abstractmethod
    async def read(self, entity_id: str) -> dict[str, Any] | None:
        """Read entity with tenant filtering."""
        pass

    @abstractmethod
    async def update(self, entity_id: str, data: dict[str, Any]) -> bool:
        """Update entity with tenant validation."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete entity with tenant validation."""
        pass


class TenantAwareDocumentRepository(SecureTenantRepository):
    """Document repository with tenant isolation."""

    def __init__(self, db_manager: TenantDatabaseManager):
        super().__init__(db_manager)
        self._documents: dict[str, dict[str, Any]] = {}

    async def create(self, data: dict[str, Any]) -> str:
        """Create document with tenant isolation."""
        data = self._ensure_tenant_data(data)
        document_id = f"doc_{len(self._documents) + 1}"
        self._documents[document_id] = data

        logger.info(f"Created document {document_id} for tenant {data['tenant_id']}")
        return document_id

    async def read(self, entity_id: str) -> dict[str, Any] | None:
        """Read document with tenant filtering."""
        document = self._documents.get(entity_id)
        if document:
            self._validate_tenant_data(document)
            return document
        return None

    async def update(self, entity_id: str, data: dict[str, Any]) -> bool:
        """Update document with tenant validation."""
        existing = await self.read(entity_id)
        if not existing:
            return False

        data = self._ensure_tenant_data(data)
        self._documents[entity_id] = {**existing, **data}

        logger.info(f"Updated document {entity_id} for tenant {data['tenant_id']}")
        return True

    async def delete(self, entity_id: str) -> bool:
        """Delete document with tenant validation."""
        existing = await self.read(entity_id)
        if not existing:
            return False

        del self._documents[entity_id]
        logger.info(f"Deleted document {entity_id} for tenant {existing['tenant_id']}")
        return True

    async def list_tenant_documents(self) -> list[dict[str, Any]]:
        """List all documents for current tenant."""
        tenant_id = self._get_current_tenant()
        return [
            doc for doc in self._documents.values()
            if doc.get("tenant_id") == tenant_id
        ]


class TenantSecurityBoundary:
    """Enforce security boundaries between tenants."""

    def __init__(self):
        self.access_logs: list[dict[str, Any]] = []
        self.blocked_attempts: list[dict[str, Any]] = []

    def validate_cross_tenant_access(self, source_tenant: UUID, target_tenant: UUID,
                                   operation: str) -> bool:
        """Validate cross-tenant access attempts."""
        if source_tenant != target_tenant:
            # Log potential security violation
            violation = {
                "timestamp": datetime.utcnow(),
                "source_tenant": source_tenant,
                "target_tenant": target_tenant,
                "operation": operation,
                "blocked": True
            }
            self.blocked_attempts.append(violation)

            logger.warning(f"Blocked cross-tenant access: {source_tenant} -> {target_tenant}")
            raise TenantIsolationError(
                f"Cross-tenant access denied: {source_tenant} cannot access {target_tenant}"
            )

        # Log legitimate access
        access_log = {
            "timestamp": datetime.utcnow(),
            "tenant": source_tenant,
            "operation": operation,
            "allowed": True
        }
        self.access_logs.append(access_log)
        return True

    def get_security_violations(self, tenant_id: UUID | None = None) -> list[dict[str, Any]]:
        """Get security violations for monitoring."""
        if tenant_id:
            return [
                attempt for attempt in self.blocked_attempts
                if attempt["source_tenant"] == tenant_id or attempt["target_tenant"] == tenant_id
            ]
        return self.blocked_attempts

    def get_access_logs(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Get access logs for a specific tenant."""
        return [
            log for log in self.access_logs
            if log["tenant"] == tenant_id
        ]


class TenantNetworkIsolation:
    """Network-level isolation for tenant traffic."""

    def __init__(self):
        self.tenant_ip_ranges: dict[UUID, list[str]] = {}
        self.tenant_network_policies: dict[UUID, dict[str, Any]] = {}

    def configure_tenant_network(self, tenant_id: UUID, ip_ranges: list[str],
                               network_policy: dict[str, Any]):
        """Configure network isolation for tenant."""
        self.tenant_ip_ranges[tenant_id] = ip_ranges
        self.tenant_network_policies[tenant_id] = network_policy

        logger.info(f"Configured network isolation for tenant {tenant_id}")

    def validate_network_access(self, tenant_id: UUID, client_ip: str) -> bool:
        """Validate network access for tenant."""
        allowed_ranges = self.tenant_ip_ranges.get(tenant_id, [])

        if not allowed_ranges:
            # No restrictions configured
            return True

        # Simple IP range validation (in production, use proper CIDR matching)
        for ip_range in allowed_ranges:
            if client_ip.startswith(ip_range.split('/')[0]):
                return True

        logger.warning(f"Network access denied for tenant {tenant_id} from IP {client_ip}")
        return False


class TenantResourceQuota:
    """Resource quota management for tenants."""

    def __init__(self):
        self.tenant_quotas: dict[UUID, dict[str, Any]] = {}
        self.tenant_usage: dict[UUID, dict[str, Any]] = {}

    def set_tenant_quota(self, tenant_id: UUID, quotas: dict[str, Any]):
        """Set resource quotas for tenant."""
        self.tenant_quotas[tenant_id] = quotas
        if tenant_id not in self.tenant_usage:
            self.tenant_usage[tenant_id] = {
                "documents": 0,
                "storage_mb": 0,
                "api_calls": 0,
                "users": 0
            }

    def check_quota(self, tenant_id: UUID, resource_type: str, requested_amount: int = 1) -> bool:
        """Check if tenant can use additional resources."""
        quotas = self.tenant_quotas.get(tenant_id, {})
        usage = self.tenant_usage.get(tenant_id, {})

        if resource_type not in quotas:
            # No quota set, allow unlimited
            return True

        current_usage = usage.get(resource_type, 0)
        quota_limit = quotas[resource_type]

        if current_usage + requested_amount > quota_limit:
            logger.warning(f"Quota exceeded for tenant {tenant_id}: {resource_type}")
            return False

        return True

    def increment_usage(self, tenant_id: UUID, resource_type: str, amount: int = 1):
        """Increment resource usage for tenant."""
        if tenant_id not in self.tenant_usage:
            self.tenant_usage[tenant_id] = {}

        current = self.tenant_usage[tenant_id].get(resource_type, 0)
        self.tenant_usage[tenant_id][resource_type] = current + amount

    def get_usage_report(self, tenant_id: UUID) -> dict[str, Any]:
        """Get resource usage report for tenant."""
        quotas = self.tenant_quotas.get(tenant_id, {})
        usage = self.tenant_usage.get(tenant_id, {})

        report = {
            "tenant_id": tenant_id,
            "quotas": quotas,
            "usage": usage,
            "utilization": {}
        }

        for resource, quota in quotas.items():
            current_usage = usage.get(resource, 0)
            utilization = (current_usage / quota * 100) if quota > 0 else 0
            report["utilization"][resource] = utilization

        return report


# Global instances for tenant isolation
tenant_db_manager = TenantDatabaseManager()
tenant_security_boundary = TenantSecurityBoundary()
tenant_network_isolation = TenantNetworkIsolation()
tenant_resource_quota = TenantResourceQuota()
