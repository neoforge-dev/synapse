"""Enterprise authentication models for SSO, multi-tenancy, and compliance."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IdentityProvider(str, Enum):
    """Supported enterprise identity providers."""
    SAML = "saml"
    OAUTH2 = "oauth2"
    LDAP = "ldap"
    ACTIVE_DIRECTORY = "active_directory"
    OKTA = "okta"
    AZURE_AD = "azure_ad"
    GOOGLE_WORKSPACE = "google_workspace"


class MFAType(str, Enum):
    """Multi-factor authentication types."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    HARDWARE_TOKEN = "hardware_token"
    BIOMETRIC = "biometric"
    PUSH_NOTIFICATION = "push_notification"


class TenantRole(str, Enum):
    """Tenant-specific user roles."""
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"
    TENANT_READONLY = "tenant_readonly"
    TENANT_GUEST = "tenant_guest"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    GDPR = "gdpr"
    SOC2_TYPE_I = "soc2_type_i"
    SOC2_TYPE_II = "soc2_type_ii"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"


class AuditEventType(str, Enum):
    """Types of audit events for compliance tracking."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    PASSWORD_CHANGED = "password_changed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    ROLE_GRANTED = "role_granted"
    ROLE_REVOKED = "role_revoked"
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    TENANT_CREATED = "tenant_created"
    TENANT_UPDATED = "tenant_updated"
    TENANT_DELETED = "tenant_deleted"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    CONFIGURATION_CHANGED = "configuration_changed"
    SECURITY_VIOLATION = "security_violation"


class Tenant(BaseModel):
    """Multi-tenant organization model with isolation and compliance."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    domain: str = Field(..., pattern=r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$')
    subdomain: str = Field(..., pattern=r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    is_active: bool = Field(default=True)
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list)
    data_region: str = Field(default="us-east-1")  # For data residency requirements
    encryption_key_id: str | None = None  # Customer-managed encryption key
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    settings: Dict[str, Any] = Field(default_factory=dict)  # Tenant-specific configuration

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class TenantUser(BaseModel):
    """User within a specific tenant context."""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID  # Reference to the main User
    tenant_id: UUID
    tenant_role: TenantRole = Field(default=TenantRole.TENANT_USER)
    is_active: bool = Field(default=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_access: datetime | None = None
    permissions: List[str] = Field(default_factory=list)  # Tenant-specific permissions

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class SAMLConfiguration(BaseModel):
    """SAML 2.0 identity provider configuration."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    entity_id: str  # SAML Entity ID
    sso_url: str  # Identity Provider SSO URL
    slo_url: str | None = None  # Single Logout URL
    x509_cert: str  # X.509 certificate for signature verification
    attribute_mapping: Dict[str, str] = Field(default_factory=dict)  # SAML attributes to user fields
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class OAuthConfiguration(BaseModel):
    """OAuth 2.0/OpenID Connect provider configuration."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    provider: IdentityProvider
    name: str = Field(..., min_length=1, max_length=100)
    client_id: str
    client_secret: str  # Should be encrypted in storage
    authorization_url: str
    token_url: str
    userinfo_url: str | None = None
    jwks_url: str | None = None  # For JWT verification
    scopes: List[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    attribute_mapping: Dict[str, str] = Field(default_factory=dict)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class LDAPConfiguration(BaseModel):
    """LDAP/Active Directory configuration."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    server_uri: str  # LDAP server URI (ldap://... or ldaps://...)
    bind_dn: str  # Service account DN for binding
    bind_password: str  # Should be encrypted in storage
    user_search_base: str  # Base DN for user searches
    user_search_filter: str = Field(default="(uid={username})")
    group_search_base: str | None = None
    group_search_filter: str | None = None
    attribute_mapping: Dict[str, str] = Field(default_factory=dict)
    use_ssl: bool = Field(default=True)
    verify_cert: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class MFAConfiguration(BaseModel):
    """Multi-factor authentication configuration."""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    mfa_type: MFAType
    is_enabled: bool = Field(default=True)
    is_primary: bool = Field(default=False)
    secret_key: str | None = None  # For TOTP, encrypted in storage
    phone_number: str | None = None  # For SMS
    email: str | None = None  # For email-based MFA
    device_id: str | None = None  # For hardware tokens or biometrics
    backup_codes: List[str] = Field(default_factory=list)  # Emergency backup codes
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class AuditEvent(BaseModel):
    """Comprehensive audit event for compliance tracking."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    event_type: AuditEventType
    user_id: UUID | None = None
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: str
    result: str  # "success", "failure", "error"
    details: Dict[str, Any] = Field(default_factory=dict)
    risk_score: int = Field(default=0, ge=0, le=100)  # Security risk assessment
    compliance_tags: List[ComplianceFramework] = Field(default_factory=list)
    retention_period_days: int = Field(default=2555)  # 7 years for compliance
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Digital signature for tamper-evidence
    signature: str | None = None
    signature_algorithm: str = Field(default="SHA256-RSA")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class SecurityPolicy(BaseModel):
    """Tenant security policy configuration."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    policy_name: str
    
    # Password policy
    min_password_length: int = Field(default=12)
    require_uppercase: bool = Field(default=True)
    require_lowercase: bool = Field(default=True)
    require_numbers: bool = Field(default=True)
    require_special_chars: bool = Field(default=True)
    password_history_count: int = Field(default=12)
    password_max_age_days: int = Field(default=90)
    
    # Session policy
    session_timeout_minutes: int = Field(default=30)
    max_concurrent_sessions: int = Field(default=5)
    require_mfa: bool = Field(default=True)
    mfa_required_for_admin: bool = Field(default=True)
    
    # Access policy
    ip_whitelist: List[str] = Field(default_factory=list)
    ip_blacklist: List[str] = Field(default_factory=list)
    allowed_countries: List[str] = Field(default_factory=list)
    blocked_countries: List[str] = Field(default_factory=list)
    
    # Rate limiting
    api_rate_limit_per_minute: int = Field(default=1000)
    login_attempt_limit: int = Field(default=5)
    lockout_duration_minutes: int = Field(default=30)
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class ComplianceReport(BaseModel):
    """Automated compliance reporting model."""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    framework: ComplianceFramework
    report_period_start: datetime
    report_period_end: datetime
    
    # Compliance metrics
    total_audit_events: int
    security_violations: int
    data_access_events: int
    user_management_events: int
    system_configuration_changes: int
    
    # Risk assessment
    overall_risk_score: float = Field(ge=0.0, le=100.0)
    high_risk_events: int
    medium_risk_events: int
    low_risk_events: int
    
    # Data protection metrics
    data_encryption_percentage: float = Field(ge=0.0, le=100.0)
    backup_success_rate: float = Field(ge=0.0, le=100.0)
    access_control_compliance: float = Field(ge=0.0, le=100.0)
    
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: UUID  # User who generated the report

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


# Request/Response models for enterprise features

class TenantCreateRequest(BaseModel):
    """Request model for creating a new tenant."""
    name: str = Field(..., min_length=1, max_length=100)
    domain: str = Field(..., pattern=r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$')
    subdomain: str = Field(..., pattern=r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list)
    data_region: str = Field(default="us-east-1")
    admin_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    admin_username: str = Field(..., min_length=3, max_length=50)


class SAMLAuthRequest(BaseModel):
    """SAML authentication request."""
    saml_response: str  # Base64 encoded SAML response
    relay_state: str | None = None


class OAuthAuthRequest(BaseModel):
    """OAuth authentication request."""
    provider_id: UUID
    authorization_code: str
    state: str | None = None
    redirect_uri: str | None = None


class LDAPAuthRequest(BaseModel):
    """LDAP authentication request."""
    username: str
    password: str
    tenant_id: UUID


class MFAChallengeRequest(BaseModel):
    """MFA challenge request."""
    user_id: UUID
    mfa_type: MFAType
    challenge_code: str | None = None  # For TOTP, SMS codes


class ComplianceReportRequest(BaseModel):
    """Request for generating compliance report."""
    tenant_id: UUID
    framework: ComplianceFramework
    start_date: datetime
    end_date: datetime
    include_details: bool = Field(default=False)