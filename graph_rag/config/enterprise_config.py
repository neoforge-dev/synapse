"""Enterprise configuration management for Fortune 500 client SSO integration."""

import logging
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass
from cryptography.fernet import Fernet

from pydantic import BaseModel, Field, SecretStr, validator
from ..api.auth.enterprise_sso import SSOProvider


logger = logging.getLogger(__name__)


@dataclass
class EnterpriseClient:
    """Fortune 500 enterprise client configuration."""
    
    client_id: str
    company_name: str
    contract_value: float  # Annual contract value in USD
    tier: str  # "basic", "professional", "enterprise"
    is_active: bool
    created_at: datetime
    contact_email: str
    security_contact: str
    compliance_requirements: List[str]  # ["soc2", "gdpr", "hipaa", etc.]


class EncryptionConfig(BaseModel):
    """Configuration for enterprise data encryption."""
    
    encryption_key: SecretStr
    key_rotation_days: int = Field(default=90, ge=30, le=365)
    algorithm: str = Field(default="AES-256-GCM")
    
    @classmethod
    def generate_key(cls) -> "EncryptionConfig":
        """Generate new encryption configuration."""
        key = Fernet.generate_key()
        return cls(encryption_key=key.decode())


class TenantConfiguration(BaseModel):
    """Per-tenant enterprise configuration."""
    
    tenant_id: str = Field(..., regex=r'^[a-zA-Z0-9_-]+$')
    client_id: str
    
    # SSO Configuration
    sso_providers: List[str] = Field(default_factory=list)
    require_sso: bool = Field(default=False)
    allow_local_auth: bool = Field(default=True)
    
    # Security Policies
    password_policy: Dict[str, Any] = Field(default_factory=lambda: {
        "min_length": 12,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special_chars": True,
        "max_age_days": 90
    })
    
    session_policy: Dict[str, Any] = Field(default_factory=lambda: {
        "timeout_minutes": 480,  # 8 hours
        "idle_timeout_minutes": 60,
        "max_concurrent_sessions": 5,
        "require_mfa": False
    })
    
    # API Limits
    rate_limits: Dict[str, int] = Field(default_factory=lambda: {
        "requests_per_minute": 1000,
        "requests_per_hour": 10000,
        "requests_per_day": 100000,
        "concurrent_connections": 100
    })
    
    # Data Governance
    data_retention_days: int = Field(default=2555, ge=365)  # 7 years default
    data_classification: str = Field(default="confidential")  # "public", "internal", "confidential", "restricted"
    encryption_at_rest: bool = Field(default=True)
    encryption_in_transit: bool = Field(default=True)
    
    # Compliance Settings
    audit_logging: bool = Field(default=True)
    compliance_frameworks: List[str] = Field(default_factory=list)
    gdpr_processing_basis: Optional[str] = None
    hipaa_covered_entity: bool = Field(default=False)
    
    # Feature Flags
    enabled_features: List[str] = Field(default_factory=lambda: [
        "document_ingestion", "search", "query", "analytics"
    ])
    disabled_features: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('rate_limits')
    def validate_rate_limits(cls, v):
        """Ensure rate limits are sensible."""
        if v.get('requests_per_minute', 0) * 60 > v.get('requests_per_hour', float('inf')):
            raise ValueError("Hourly rate limit must be >= 60x minute rate limit")
        return v


class EnterpriseConfigManager:
    """Manages enterprise client configurations and SSO provider settings."""
    
    def __init__(self, config_dir: Path, encryption_key: Optional[str] = None):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.config_dir / "enterprise_config.db"
        self.encryption = Fernet(encryption_key.encode() if encryption_key else Fernet.generate_key())
        
        # Initialize database
        self._init_database()
        
        # In-memory caches
        self._clients_cache: Dict[str, EnterpriseClient] = {}
        self._tenants_cache: Dict[str, TenantConfiguration] = {}
        self._providers_cache: Dict[str, SSOProvider] = {}
        self._cache_last_refresh = datetime.utcnow()
    
    def _init_database(self) -> None:
        """Initialize enterprise configuration database."""
        with self._get_db_connection() as conn:
            # Enterprise clients table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS enterprise_clients (
                    client_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    contract_value REAL NOT NULL,
                    tier TEXT NOT NULL CHECK (tier IN ('basic', 'professional', 'enterprise')),
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL,
                    contact_email TEXT NOT NULL,
                    security_contact TEXT NOT NULL,
                    compliance_requirements TEXT NOT NULL  -- JSON array
                )
            """)
            
            # Tenant configurations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_configurations (
                    tenant_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    config_data TEXT NOT NULL,  -- Encrypted JSON
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (client_id) REFERENCES enterprise_clients (client_id)
                )
            """)
            
            # SSO providers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sso_providers (
                    provider_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    provider_data TEXT NOT NULL,  -- Encrypted JSON
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenant_configurations (tenant_id)
                )
            """)
            
            # Audit log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    old_values TEXT,  -- JSON
                    new_values TEXT,  -- JSON
                    user_id TEXT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_active ON enterprise_clients (is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_providers_tenant ON sso_providers (tenant_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON config_audit_log (tenant_id, timestamp)")
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive configuration data."""
        return self.encryption.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt configuration data."""
        return self.encryption.decrypt(encrypted_data.encode()).decode()
    
    def _log_audit_event(self, tenant_id: Optional[str], action: str, resource_type: str,
                        resource_id: Optional[str] = None, old_values: Optional[Dict] = None,
                        new_values: Optional[Dict] = None, user_id: Optional[str] = None) -> None:
        """Log configuration change for compliance audit."""
        with self._get_db_connection() as conn:
            conn.execute("""
                INSERT INTO config_audit_log 
                (tenant_id, action, resource_type, resource_id, old_values, new_values, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                tenant_id, action, resource_type, resource_id,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                user_id
            ))
            conn.commit()
    
    def create_enterprise_client(self, client_data: EnterpriseClient, user_id: Optional[str] = None) -> None:
        """Create new Fortune 500 enterprise client."""
        with self._get_db_connection() as conn:
            conn.execute("""
                INSERT INTO enterprise_clients 
                (client_id, company_name, contract_value, tier, is_active, created_at, 
                 contact_email, security_contact, compliance_requirements)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_data.client_id,
                client_data.company_name,
                client_data.contract_value,
                client_data.tier,
                client_data.is_active,
                client_data.created_at,
                client_data.contact_email,
                client_data.security_contact,
                json.dumps(client_data.compliance_requirements)
            ))
            conn.commit()
        
        # Update cache
        self._clients_cache[client_data.client_id] = client_data
        
        # Audit log
        self._log_audit_event(
            tenant_id=None,
            action="CREATE",
            resource_type="enterprise_client",
            resource_id=client_data.client_id,
            new_values={
                "company_name": client_data.company_name,
                "contract_value": client_data.contract_value,
                "tier": client_data.tier
            },
            user_id=user_id
        )
        
        logger.info(f"Created enterprise client: {client_data.company_name} ({client_data.client_id})")
    
    def get_enterprise_client(self, client_id: str) -> Optional[EnterpriseClient]:
        """Get enterprise client by ID."""
        # Check cache first
        if client_id in self._clients_cache:
            return self._clients_cache[client_id]
        
        with self._get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM enterprise_clients WHERE client_id = ?",
                (client_id,)
            ).fetchone()
            
            if row:
                client = EnterpriseClient(
                    client_id=row['client_id'],
                    company_name=row['company_name'],
                    contract_value=row['contract_value'],
                    tier=row['tier'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    contact_email=row['contact_email'],
                    security_contact=row['security_contact'],
                    compliance_requirements=json.loads(row['compliance_requirements'])
                )
                
                # Cache the result
                self._clients_cache[client_id] = client
                return client
        
        return None
    
    def create_tenant_configuration(self, tenant_config: TenantConfiguration, user_id: Optional[str] = None) -> None:
        """Create tenant configuration for enterprise client."""
        # Verify client exists
        if not self.get_enterprise_client(tenant_config.client_id):
            raise ValueError(f"Enterprise client not found: {tenant_config.client_id}")
        
        # Encrypt configuration data
        config_json = tenant_config.json()
        encrypted_config = self._encrypt_data(config_json)
        
        with self._get_db_connection() as conn:
            conn.execute("""
                INSERT INTO tenant_configurations 
                (tenant_id, client_id, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tenant_config.tenant_id,
                tenant_config.client_id,
                encrypted_config,
                tenant_config.created_at,
                tenant_config.updated_at
            ))
            conn.commit()
        
        # Update cache
        self._tenants_cache[tenant_config.tenant_id] = tenant_config
        
        # Audit log
        self._log_audit_event(
            tenant_id=tenant_config.tenant_id,
            action="CREATE",
            resource_type="tenant_configuration",
            resource_id=tenant_config.tenant_id,
            new_values={"client_id": tenant_config.client_id, "features": tenant_config.enabled_features},
            user_id=user_id
        )
        
        logger.info(f"Created tenant configuration: {tenant_config.tenant_id}")
    
    def get_tenant_configuration(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """Get tenant configuration by ID."""
        # Check cache first
        if tenant_id in self._tenants_cache:
            return self._tenants_cache[tenant_id]
        
        with self._get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tenant_configurations WHERE tenant_id = ?",
                (tenant_id,)
            ).fetchone()
            
            if row:
                # Decrypt configuration data
                decrypted_config = self._decrypt_data(row['config_data'])
                tenant_config = TenantConfiguration.parse_raw(decrypted_config)
                
                # Cache the result
                self._tenants_cache[tenant_id] = tenant_config
                return tenant_config
        
        return None
    
    def update_tenant_configuration(self, tenant_id: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        """Update tenant configuration."""
        current_config = self.get_tenant_configuration(tenant_id)
        if not current_config:
            return False
        
        # Store old values for audit
        old_values = current_config.dict()
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(current_config, key):
                setattr(current_config, key, value)
        
        current_config.updated_at = datetime.utcnow()
        
        # Encrypt and save
        config_json = current_config.json()
        encrypted_config = self._encrypt_data(config_json)
        
        with self._get_db_connection() as conn:
            conn.execute("""
                UPDATE tenant_configurations 
                SET config_data = ?, updated_at = ?
                WHERE tenant_id = ?
            """, (encrypted_config, current_config.updated_at, tenant_id))
            conn.commit()
        
        # Update cache
        self._tenants_cache[tenant_id] = current_config
        
        # Audit log
        self._log_audit_event(
            tenant_id=tenant_id,
            action="UPDATE",
            resource_type="tenant_configuration",
            resource_id=tenant_id,
            old_values={k: v for k, v in old_values.items() if k in updates},
            new_values=updates,
            user_id=user_id
        )
        
        logger.info(f"Updated tenant configuration: {tenant_id}")
        return True
    
    def register_sso_provider(self, provider: SSOProvider, user_id: Optional[str] = None) -> None:
        """Register SSO provider for tenant."""
        # Verify tenant exists
        if not self.get_tenant_configuration(provider.tenant_id):
            raise ValueError(f"Tenant not found: {provider.tenant_id}")
        
        # Encrypt provider data
        provider_json = provider.json()
        encrypted_provider = self._encrypt_data(provider_json)
        
        with self._get_db_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sso_providers 
                (provider_id, tenant_id, provider_data, is_active, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                provider.provider_id,
                provider.tenant_id,
                encrypted_provider,
                provider.is_active,
                provider.created_at
            ))
            conn.commit()
        
        # Update cache
        self._providers_cache[provider.provider_id] = provider
        
        # Audit log
        self._log_audit_event(
            tenant_id=provider.tenant_id,
            action="CREATE",
            resource_type="sso_provider",
            resource_id=provider.provider_id,
            new_values={"name": provider.name, "type": provider.type},
            user_id=user_id
        )
        
        logger.info(f"Registered SSO provider: {provider.name} ({provider.provider_id}) for tenant {provider.tenant_id}")
    
    def get_sso_provider(self, provider_id: str) -> Optional[SSOProvider]:
        """Get SSO provider by ID."""
        # Check cache first
        if provider_id in self._providers_cache:
            return self._providers_cache[provider_id]
        
        with self._get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sso_providers WHERE provider_id = ? AND is_active = 1",
                (provider_id,)
            ).fetchone()
            
            if row:
                # Decrypt provider data
                decrypted_data = self._decrypt_data(row['provider_data'])
                provider = SSOProvider.parse_raw(decrypted_data)
                
                # Cache the result
                self._providers_cache[provider_id] = provider
                return provider
        
        return None
    
    def get_tenant_sso_providers(self, tenant_id: str) -> List[SSOProvider]:
        """Get all SSO providers for a tenant."""
        providers = []
        
        with self._get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sso_providers WHERE tenant_id = ? AND is_active = 1",
                (tenant_id,)
            ).fetchall()
            
            for row in rows:
                decrypted_data = self._decrypt_data(row['provider_data'])
                provider = SSOProvider.parse_raw(decrypted_data)
                providers.append(provider)
                
                # Cache the provider
                self._providers_cache[provider.provider_id] = provider
        
        return providers
    
    def get_high_value_clients(self, min_contract_value: float = 150000) -> List[EnterpriseClient]:
        """Get Fortune 500 clients with high contract values."""
        clients = []
        
        with self._get_db_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM enterprise_clients 
                WHERE contract_value >= ? AND is_active = 1
                ORDER BY contract_value DESC
            """, (min_contract_value,)).fetchall()
            
            for row in rows:
                client = EnterpriseClient(
                    client_id=row['client_id'],
                    company_name=row['company_name'],
                    contract_value=row['contract_value'],
                    tier=row['tier'],
                    is_active=bool(row['is_active']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    contact_email=row['contact_email'],
                    security_contact=row['security_contact'],
                    compliance_requirements=json.loads(row['compliance_requirements'])
                )
                clients.append(client)
        
        return clients
    
    def get_compliance_audit_log(self, tenant_id: Optional[str] = None, 
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get compliance audit log for tenant or all tenants."""
        query = "SELECT * FROM config_audit_log WHERE 1=1"
        params = []
        
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC"
        
        with self._get_db_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
            return [dict(row) for row in rows]