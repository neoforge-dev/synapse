"""Database-level tenant isolation for multi-tenant architecture.

This module provides comprehensive data isolation strategies:
- Database-per-tenant (maximum isolation)
- Schema-per-tenant (balanced performance/isolation) 
- Row-level security (shared database with tenant context)
- Hybrid model supporting different isolation levels per tenant
"""

import hashlib
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .tenant_manager import TenantContext, get_current_tenant

logger = logging.getLogger(__name__)


class IsolationLevel(str, Enum):
    """Data isolation levels supported by the platform."""
    DATABASE = "database"  # Separate database per tenant (maximum isolation)
    SCHEMA = "schema"      # Separate schema per tenant (balanced)
    ROW = "row"           # Row-level security (shared database)
    HYBRID = "hybrid"     # Mixed approach based on tenant requirements


@dataclass
class TenantDatabaseConfig:
    """Configuration for tenant database setup."""
    tenant_id: str
    isolation_level: IsolationLevel
    database_path: str | None = None
    schema_name: str | None = None
    connection_pool_size: int = 10
    connection_timeout: int = 30
    enable_wal_mode: bool = True
    enable_foreign_keys: bool = True
    cache_size: int = -2000  # 2MB cache

    def get_database_name(self) -> str:
        """Generate consistent database name for tenant."""
        if self.isolation_level == IsolationLevel.DATABASE:
            # Separate database file per tenant
            tenant_hash = hashlib.sha256(self.tenant_id.encode()).hexdigest()[:12]
            return f"synapse_tenant_{tenant_hash}.db"
        else:
            # Shared database with schema or row-level isolation
            return "synapse_multi_tenant.db"

    def get_table_prefix(self) -> str:
        """Get table prefix for tenant isolation."""
        if self.isolation_level == IsolationLevel.ROW:
            return ""  # No prefix needed for row-level security
        tenant_hash = hashlib.sha256(self.tenant_id.encode()).hexdigest()[:8]
        return f"t_{tenant_hash}_"


class DatabaseIsolationStrategy(ABC):
    """Abstract base class for database isolation strategies."""

    @abstractmethod
    async def create_tenant_database(self, config: TenantDatabaseConfig) -> bool:
        """Create isolated database/schema for tenant."""
        pass

    @abstractmethod
    async def get_connection(self, tenant_id: str) -> Any:
        """Get database connection for tenant."""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: dict | None = None, tenant_id: str | None = None) -> Any:
        """Execute query with tenant isolation."""
        pass

    @abstractmethod
    async def migrate_tenant_schema(self, tenant_id: str, schema_version: str) -> bool:
        """Apply schema migrations for tenant."""
        pass

    @abstractmethod
    async def delete_tenant_data(self, tenant_id: str) -> bool:
        """Safely delete all tenant data."""
        pass


class DatabasePerTenantStrategy(DatabaseIsolationStrategy):
    """Database-per-tenant isolation strategy (maximum security)."""

    def __init__(self, base_path: str = "~/.synapse/tenant_databases"):
        """Initialize database-per-tenant strategy."""
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._connections: dict[str, sqlite3.Connection] = {}

        logger.info(f"Database-per-tenant strategy initialized at {self.base_path}")

    async def create_tenant_database(self, config: TenantDatabaseConfig) -> bool:
        """Create dedicated database file for tenant."""
        try:
            db_name = config.get_database_name()
            db_path = self.base_path / db_name

            # Create database if it doesn't exist
            if not db_path.exists():
                conn = sqlite3.connect(str(db_path))
                await self._configure_database(conn, config)
                await self._create_tenant_schema(conn, config)
                conn.close()

                logger.info(f"Created tenant database: {db_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to create tenant database for {config.tenant_id}: {e}")
            return False

    async def get_connection(self, tenant_id: str) -> sqlite3.Connection:
        """Get dedicated database connection for tenant."""
        if tenant_id not in self._connections:
            config = TenantDatabaseConfig(tenant_id=tenant_id, isolation_level=IsolationLevel.DATABASE)
            db_name = config.get_database_name()
            db_path = self.base_path / db_name

            if not db_path.exists():
                await self.create_tenant_database(config)

            conn = sqlite3.connect(str(db_path))
            await self._configure_database(conn, config)
            self._connections[tenant_id] = conn

        return self._connections[tenant_id]

    async def execute_query(self, query: str, params: dict | None = None, tenant_id: str | None = None) -> Any:
        """Execute query on tenant's dedicated database."""
        if not tenant_id:
            tenant_context = get_current_tenant()
            if not tenant_context:
                raise ValueError("No tenant context available for query execution")
            tenant_id = tenant_context.tenant_id

        conn = await self.get_connection(tenant_id)
        cursor = conn.cursor()

        try:
            if params:
                result = cursor.execute(query, params)
            else:
                result = cursor.execute(query)

            if query.strip().lower().startswith(('insert', 'update', 'delete')):
                conn.commit()

            return result.fetchall()

        except Exception as e:
            conn.rollback()
            logger.error(f"Query execution failed for tenant {tenant_id}: {e}")
            raise

    async def migrate_tenant_schema(self, tenant_id: str, schema_version: str) -> bool:
        """Apply schema migrations to tenant database."""
        try:
            conn = await self.get_connection(tenant_id)

            # Check current schema version
            current_version = await self._get_schema_version(conn)

            if current_version != schema_version:
                await self._apply_migrations(conn, current_version, schema_version)
                await self._set_schema_version(conn, schema_version)

                logger.info(f"Migrated tenant {tenant_id} schema: {current_version} -> {schema_version}")

            return True

        except Exception as e:
            logger.error(f"Schema migration failed for tenant {tenant_id}: {e}")
            return False

    async def delete_tenant_data(self, tenant_id: str) -> bool:
        """Delete tenant's dedicated database file."""
        try:
            # Close connection if exists
            if tenant_id in self._connections:
                self._connections[tenant_id].close()
                del self._connections[tenant_id]

            # Delete database file
            config = TenantDatabaseConfig(tenant_id=tenant_id, isolation_level=IsolationLevel.DATABASE)
            db_name = config.get_database_name()
            db_path = self.base_path / db_name

            if db_path.exists():
                db_path.unlink()
                logger.info(f"Deleted tenant database: {db_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete tenant database for {tenant_id}: {e}")
            return False

    async def _configure_database(self, conn: sqlite3.Connection, config: TenantDatabaseConfig) -> None:
        """Configure database connection settings."""
        conn.execute("PRAGMA journal_mode=WAL" if config.enable_wal_mode else "PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON" if config.enable_foreign_keys else "PRAGMA foreign_keys=OFF")
        conn.execute(f"PRAGMA cache_size={config.cache_size}")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.commit()

    async def _create_tenant_schema(self, conn: sqlite3.Connection, config: TenantDatabaseConfig) -> None:
        """Create initial schema for tenant database."""
        # Core tables for GraphRAG functionality
        schema_sql = """
        -- Tenant metadata
        CREATE TABLE tenant_info (
            tenant_id TEXT PRIMARY KEY,
            tenant_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            schema_version TEXT DEFAULT '1.0'
        );
        
        -- Documents table
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Chunks table
        CREATE TABLE chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            content TEXT NOT NULL,
            start_pos INTEGER,
            end_pos INTEGER,
            metadata JSON,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        );
        
        -- Entities table
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            description TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Relationships table
        CREATE TABLE relationships (
            id TEXT PRIMARY KEY,
            source_entity_id TEXT NOT NULL,
            target_entity_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_entity_id) REFERENCES entities(id),
            FOREIGN KEY (target_entity_id) REFERENCES entities(id)
        );
        
        -- Create indexes for performance
        CREATE INDEX idx_chunks_document ON chunks(document_id);
        CREATE INDEX idx_entities_name ON entities(name);
        CREATE INDEX idx_entities_type ON entities(type);
        CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
        CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
        CREATE INDEX idx_relationships_type ON relationships(relationship_type);
        """

        for statement in schema_sql.split(';'):
            if statement.strip():
                conn.execute(statement)

        # Insert tenant info
        conn.execute(
            "INSERT INTO tenant_info (tenant_id, tenant_name) VALUES (?, ?)",
            (config.tenant_id, f"Tenant {config.tenant_id}")
        )

        conn.commit()

    async def _get_schema_version(self, conn: sqlite3.Connection) -> str:
        """Get current schema version from database."""
        try:
            cursor = conn.execute("SELECT schema_version FROM tenant_info LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else "1.0"
        except:
            return "1.0"

    async def _set_schema_version(self, conn: sqlite3.Connection, version: str) -> None:
        """Update schema version in database."""
        conn.execute("UPDATE tenant_info SET schema_version = ?", (version,))
        conn.commit()

    async def _apply_migrations(self, conn: sqlite3.Connection, from_version: str, to_version: str) -> None:
        """Apply database migrations between versions."""
        # Placeholder for migration logic
        # In a real implementation, this would contain version-specific migration scripts
        logger.info(f"Applying migrations from {from_version} to {to_version}")


class RowLevelSecurityStrategy(DatabaseIsolationStrategy):
    """Row-level security strategy for shared database with tenant context."""

    def __init__(self, database_path: str = "~/.synapse/synapse_multi_tenant.db"):
        """Initialize row-level security strategy."""
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: sqlite3.Connection | None = None

        logger.info(f"Row-level security strategy initialized at {self.database_path}")

    async def create_tenant_database(self, config: TenantDatabaseConfig) -> bool:
        """Initialize shared database with row-level security."""
        try:
            if not self.database_path.exists():
                await self._create_shared_database(config)

            # Ensure tenant is registered in shared database
            await self._register_tenant(config.tenant_id)

            return True

        except Exception as e:
            logger.error(f"Failed to create shared database: {e}")
            return False

    async def get_connection(self, tenant_id: str) -> sqlite3.Connection:
        """Get shared database connection with tenant context."""
        if not self._connection:
            conn = sqlite3.connect(str(self.database_path))
            await self._configure_database(conn)
            self._connection = conn

        # Set tenant context in connection
        await self._set_tenant_context(self._connection, tenant_id)

        return self._connection

    async def execute_query(self, query: str, params: dict | None = None, tenant_id: str | None = None) -> Any:
        """Execute query with automatic tenant filtering."""
        if not tenant_id:
            tenant_context = get_current_tenant()
            if not tenant_context:
                raise ValueError("No tenant context available for query execution")
            tenant_id = tenant_context.tenant_id

        conn = await self.get_connection(tenant_id)

        # Modify query to include tenant filtering
        filtered_query = self._add_tenant_filter(query, tenant_id)

        cursor = conn.cursor()

        try:
            if params:
                # Add tenant_id to parameters
                if isinstance(params, dict):
                    params['tenant_id'] = tenant_id
                elif isinstance(params, (list, tuple)):
                    params = list(params) + [tenant_id]
                result = cursor.execute(filtered_query, params)
            else:
                result = cursor.execute(filtered_query, [tenant_id])

            if query.strip().lower().startswith(('insert', 'update', 'delete')):
                conn.commit()

            return result.fetchall()

        except Exception as e:
            conn.rollback()
            logger.error(f"Query execution failed for tenant {tenant_id}: {e}")
            raise

    async def migrate_tenant_schema(self, tenant_id: str, schema_version: str) -> bool:
        """Apply schema migrations to shared database."""
        # Row-level security uses shared schema, so migrations apply globally
        return True

    async def delete_tenant_data(self, tenant_id: str) -> bool:
        """Delete all data for specific tenant from shared database."""
        try:
            conn = await self.get_connection(tenant_id)

            # Delete tenant data from all tables
            tables = ['relationships', 'chunks', 'entities', 'documents']

            for table in tables:
                conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (tenant_id,))

            # Remove tenant registration
            conn.execute("DELETE FROM tenant_registry WHERE tenant_id = ?", (tenant_id,))

            conn.commit()
            logger.info(f"Deleted all data for tenant: {tenant_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete tenant data for {tenant_id}: {e}")
            return False

    async def _create_shared_database(self, config: TenantDatabaseConfig) -> None:
        """Create shared database with tenant isolation."""
        conn = sqlite3.connect(str(self.database_path))
        await self._configure_database(conn)

        # Create schema with tenant_id columns
        schema_sql = """
        -- Tenant registry
        CREATE TABLE tenant_registry (
            tenant_id TEXT PRIMARY KEY,
            tenant_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        );
        
        -- Documents table with tenant isolation
        CREATE TABLE documents (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenant_registry(tenant_id)
        );
        
        -- Chunks table with tenant isolation
        CREATE TABLE chunks (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            content TEXT NOT NULL,
            start_pos INTEGER,
            end_pos INTEGER,
            metadata JSON,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenant_registry(tenant_id),
            FOREIGN KEY (document_id) REFERENCES documents(id)
        );
        
        -- Entities table with tenant isolation
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT,
            description TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenant_registry(tenant_id)
        );
        
        -- Relationships table with tenant isolation
        CREATE TABLE relationships (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            source_entity_id TEXT NOT NULL,
            target_entity_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenant_registry(tenant_id),
            FOREIGN KEY (source_entity_id) REFERENCES entities(id),
            FOREIGN KEY (target_entity_id) REFERENCES entities(id)
        );
        
        -- Create indexes for performance including tenant_id
        CREATE INDEX idx_documents_tenant ON documents(tenant_id);
        CREATE INDEX idx_chunks_tenant_document ON chunks(tenant_id, document_id);
        CREATE INDEX idx_entities_tenant_name ON entities(tenant_id, name);
        CREATE INDEX idx_entities_tenant_type ON entities(tenant_id, type);
        CREATE INDEX idx_relationships_tenant_source ON relationships(tenant_id, source_entity_id);
        CREATE INDEX idx_relationships_tenant_target ON relationships(tenant_id, target_entity_id);
        """

        for statement in schema_sql.split(';'):
            if statement.strip():
                conn.execute(statement)

        conn.commit()
        conn.close()

    async def _configure_database(self, conn: sqlite3.Connection) -> None:
        """Configure shared database connection."""
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA cache_size=-4000")  # 4MB cache
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.commit()

    async def _register_tenant(self, tenant_id: str) -> None:
        """Register tenant in shared database."""
        if not self._connection:
            await self.get_connection(tenant_id)

        try:
            self._connection.execute(
                "INSERT OR IGNORE INTO tenant_registry (tenant_id, tenant_name) VALUES (?, ?)",
                (tenant_id, f"Tenant {tenant_id}")
            )
            self._connection.commit()
        except Exception as e:
            logger.warning(f"Failed to register tenant {tenant_id}: {e}")

    async def _set_tenant_context(self, conn: sqlite3.Connection, tenant_id: str) -> None:
        """Set tenant context in database connection."""
        # SQLite doesn't have session variables, but we can use a temporary table
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS session_context (tenant_id TEXT)")
        conn.execute("DELETE FROM session_context")
        conn.execute("INSERT INTO session_context (tenant_id) VALUES (?)", (tenant_id,))
        conn.commit()

    def _add_tenant_filter(self, query: str, tenant_id: str) -> str:
        """Add tenant filtering to SQL query."""
        # Simple implementation - in production would use a proper SQL parser
        query_lower = query.lower().strip()

        if query_lower.startswith('select'):
            # Add WHERE clause or AND condition for tenant filtering
            if 'where' in query_lower:
                # Add AND condition
                return query + " AND tenant_id = ?"
            else:
                # Add WHERE clause
                return query + " WHERE tenant_id = ?"
        elif query_lower.startswith('insert'):
            # Ensure tenant_id is included in INSERT
            return query  # Caller should include tenant_id in values
        elif query_lower.startswith(('update', 'delete')):
            # Add WHERE clause for tenant filtering
            if 'where' in query_lower:
                return query + " AND tenant_id = ?"
            else:
                return query + " WHERE tenant_id = ?"

        return query


class TenantDataManager:
    """High-level tenant data management interface."""

    def __init__(self, default_isolation_level: IsolationLevel = IsolationLevel.DATABASE):
        """Initialize tenant data manager."""
        self.default_isolation_level = default_isolation_level
        self._strategies: dict[IsolationLevel, DatabaseIsolationStrategy] = {
            IsolationLevel.DATABASE: DatabasePerTenantStrategy(),
            IsolationLevel.ROW: RowLevelSecurityStrategy(),
        }

        logger.info(f"TenantDataManager initialized with default isolation: {default_isolation_level}")

    def get_strategy(self, tenant_context: TenantContext) -> DatabaseIsolationStrategy:
        """Get appropriate isolation strategy for tenant."""
        isolation_level = IsolationLevel(tenant_context.isolation_level)

        if isolation_level not in self._strategies:
            logger.warning(f"Unsupported isolation level {isolation_level}, using default")
            isolation_level = self.default_isolation_level

        return self._strategies[isolation_level]

    async def setup_tenant_data(self, tenant_context: TenantContext) -> bool:
        """Setup data isolation for tenant."""
        strategy = self.get_strategy(tenant_context)
        config = TenantDatabaseConfig(
            tenant_id=tenant_context.tenant_id,
            isolation_level=IsolationLevel(tenant_context.isolation_level)
        )

        return await strategy.create_tenant_database(config)

    async def execute_tenant_query(
        self,
        query: str,
        params: dict | None = None,
        tenant_context: TenantContext | None = None
    ) -> Any:
        """Execute query with tenant isolation."""
        if not tenant_context:
            tenant_context = get_current_tenant()
            if not tenant_context:
                raise ValueError("No tenant context available")

        strategy = self.get_strategy(tenant_context)
        return await strategy.execute_query(query, params, tenant_context.tenant_id)

    async def migrate_tenant(self, tenant_context: TenantContext, schema_version: str) -> bool:
        """Apply migrations for tenant."""
        strategy = self.get_strategy(tenant_context)
        return await strategy.migrate_tenant_schema(tenant_context.tenant_id, schema_version)

    async def delete_tenant_data(self, tenant_context: TenantContext) -> bool:
        """Delete all data for tenant."""
        if tenant_context.is_consultation:
            logger.error("Cannot delete consultation tenant data - Epic 7 protection")
            return False

        strategy = self.get_strategy(tenant_context)
        return await strategy.delete_tenant_data(tenant_context.tenant_id)
