"""Enterprise SSO integration for SAML 2.0 and OAuth/OpenID Connect."""

import base64
import logging
import secrets
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseModel, Field, HttpUrl, validator

from .jwt_handler import JWTHandler
from .models import User, UserRole

logger = logging.getLogger(__name__)


class SSOProvider(BaseModel):
    """Enterprise SSO provider configuration."""

    provider_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern=r'^(saml|oidc|oauth2)$')

    # SAML Configuration
    saml_sso_url: HttpUrl | None = None
    saml_entity_id: str | None = None
    saml_x509_cert: str | None = None
    saml_attribute_mapping: dict[str, str] | None = None

    # OAuth2/OIDC Configuration
    oauth_client_id: str | None = None
    oauth_client_secret: str | None = None
    oauth_authorization_url: HttpUrl | None = None
    oauth_token_url: HttpUrl | None = None
    oauth_userinfo_url: HttpUrl | None = None
    oauth_scopes: list[str] | None = Field(default_factory=lambda: ["openid", "profile", "email"])

    # Tenant Configuration
    tenant_id: str = Field(..., description="Fortune 500 client tenant identifier")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Role Mapping Configuration
    default_role: UserRole = Field(default=UserRole.USER)
    role_attribute: str | None = Field(default="groups")
    role_mapping: dict[str, UserRole] | None = Field(default_factory=dict)

    @validator('saml_x509_cert')
    def validate_x509_cert(cls, v):
        """Validate X.509 certificate format."""
        if v and not v.startswith('-----BEGIN CERTIFICATE-----'):
            raise ValueError("X.509 certificate must be in PEM format")
        return v

    @validator('role_mapping')
    def validate_role_mapping(cls, v):
        """Validate role mapping contains valid roles."""
        if v:
            valid_roles = {role.value for role in UserRole}
            for mapped_role in v.values():
                if isinstance(mapped_role, str):
                    if mapped_role not in valid_roles:
                        raise ValueError(f"Invalid role in mapping: {mapped_role}")
                elif not isinstance(mapped_role, UserRole):
                    raise ValueError("Role mapping values must be UserRole enum or valid role strings")
        return v


class SAMLResponse(BaseModel):
    """SAML response validation and parsing."""

    raw_response: str
    issuer: str
    subject: str
    attributes: dict[str, Any]
    session_index: str | None = None
    not_before: datetime | None = None
    not_on_or_after: datetime | None = None

    def is_valid(self) -> bool:
        """Check if SAML response is still valid."""
        now = datetime.utcnow()

        if self.not_before and now < self.not_before:
            return False

        if self.not_on_or_after and now > self.not_on_or_after:
            return False

        return True


class OIDCTokenResponse(BaseModel):
    """OpenID Connect token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str | None = None


class SSOSession(BaseModel):
    """Enterprise SSO session tracking."""

    session_id: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    provider_id: str
    tenant_id: str
    user_id: str
    external_user_id: str
    saml_session_index: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_active: bool = Field(default=True)

    @validator('expires_at', pre=True, always=True)
    def set_expires_at(cls, v, values):
        """Set session expiration to 8 hours from creation."""
        if v is None:
            return values.get('created_at', datetime.utcnow()) + timedelta(hours=8)
        return v


class EnterpriseSSOHandler:
    """Handles enterprise SSO authentication flows."""

    def __init__(self, jwt_handler: JWTHandler):
        self.jwt_handler = jwt_handler
        self.providers: dict[str, SSOProvider] = {}
        self.sessions: dict[str, SSOSession] = {}
        self._private_key = self._generate_rsa_key()
        self._public_key = self._private_key.public_key()

    def _generate_rsa_key(self):
        """Generate RSA key pair for SAML signing."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

    def register_provider(self, provider: SSOProvider) -> None:
        """Register a new enterprise SSO provider."""
        logger.info(f"Registering SSO provider: {provider.name} ({provider.type}) for tenant {provider.tenant_id}")
        self.providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> SSOProvider | None:
        """Get SSO provider by ID."""
        return self.providers.get(provider_id)

    def get_providers_by_tenant(self, tenant_id: str) -> list[SSOProvider]:
        """Get all SSO providers for a tenant."""
        return [p for p in self.providers.values() if p.tenant_id == tenant_id]

    def generate_saml_auth_request(self, provider_id: str, relay_state: str | None = None) -> tuple[str, str]:
        """Generate SAML authentication request.

        Returns:
            tuple: (auth_request_xml, auth_url)
        """
        provider = self.get_provider(provider_id)
        if not provider or provider.type != 'saml':
            raise ValueError(f"Invalid SAML provider: {provider_id}")

        request_id = f"id{secrets.token_urlsafe(32)}"
        issue_instant = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        # Build SAML AuthnRequest
        auth_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{provider.saml_sso_url}"
    AssertionConsumerServiceURL="https://api.synapse-rag.com/api/v1/auth/sso/saml/acs"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>synapse-rag-sp</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Base64 encode the request
        encoded_request = base64.b64encode(auth_request.encode()).decode()

        # Build authentication URL
        auth_url = f"{provider.saml_sso_url}?SAMLRequest={encoded_request}"
        if relay_state:
            auth_url += f"&RelayState={relay_state}"

        return auth_request, auth_url

    def parse_saml_response(self, saml_response_b64: str, provider_id: str) -> SAMLResponse:
        """Parse and validate SAML response.

        Args:
            saml_response_b64: Base64 encoded SAML response
            provider_id: SSO provider identifier

        Returns:
            SAMLResponse: Parsed and validated response
        """
        provider = self.get_provider(provider_id)
        if not provider or provider.type != 'saml':
            raise ValueError(f"Invalid SAML provider: {provider_id}")

        # Decode SAML response
        try:
            saml_xml = base64.b64decode(saml_response_b64).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Invalid SAML response encoding: {e}") from e

        # Parse XML
        try:
            root = ET.fromstring(saml_xml)
        except ET.ParseError as e:
            raise ValueError(f"Invalid SAML response XML: {e}") from e

        # Define namespaces
        ns = {
            'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol'
        }

        # Extract issuer
        issuer_elem = root.find('.//saml:Issuer', ns)
        if issuer_elem is None:
            raise ValueError("SAML response missing issuer")
        issuer = issuer_elem.text

        # Verify issuer matches provider
        if provider.saml_entity_id and issuer != provider.saml_entity_id:
            raise ValueError(f"SAML issuer mismatch: expected {provider.saml_entity_id}, got {issuer}")

        # Extract assertion
        assertion = root.find('.//saml:Assertion', ns)
        if assertion is None:
            raise ValueError("SAML response missing assertion")

        # Extract subject
        subject_elem = assertion.find('.//saml:Subject/saml:NameID', ns)
        if subject_elem is None:
            raise ValueError("SAML response missing subject")
        subject = subject_elem.text

        # Extract session index
        authn_statement = assertion.find('.//saml:AuthnStatement', ns)
        session_index = None
        if authn_statement is not None:
            session_index = authn_statement.get('SessionIndex')

        # Extract conditions (validity period)
        conditions = assertion.find('.//saml:Conditions', ns)
        not_before = None
        not_on_or_after = None

        if conditions is not None:
            not_before_str = conditions.get('NotBefore')
            not_on_or_after_str = conditions.get('NotOnOrAfter')

            if not_before_str:
                not_before = datetime.fromisoformat(not_before_str.replace('Z', '+00:00')).replace(tzinfo=None)
            if not_on_or_after_str:
                not_on_or_after = datetime.fromisoformat(not_on_or_after_str.replace('Z', '+00:00')).replace(tzinfo=None)

        # Extract attributes
        attributes = {}
        attr_statements = assertion.findall('.//saml:AttributeStatement', ns)
        for attr_statement in attr_statements:
            for attr in attr_statement.findall('.//saml:Attribute', ns):
                attr_name = attr.get('Name')
                attr_values = [val.text for val in attr.findall('.//saml:AttributeValue', ns) if val.text]
                if attr_values:
                    attributes[attr_name] = attr_values[0] if len(attr_values) == 1 else attr_values

        # TODO: Verify signature if certificate is provided
        # This would require cryptography implementation for production use

        return SAMLResponse(
            raw_response=saml_xml,
            issuer=issuer,
            subject=subject,
            attributes=attributes,
            session_index=session_index,
            not_before=not_before,
            not_on_or_after=not_on_or_after
        )

    def generate_oauth_auth_url(self, provider_id: str, state: str | None = None) -> str:
        """Generate OAuth2/OIDC authorization URL.

        Args:
            provider_id: SSO provider identifier
            state: Optional state parameter for CSRF protection

        Returns:
            str: Authorization URL
        """
        provider = self.get_provider(provider_id)
        if not provider or provider.type not in ['oauth2', 'oidc']:
            raise ValueError(f"Invalid OAuth provider: {provider_id}")

        if not state:
            state = secrets.token_urlsafe(32)

        scopes = ' '.join(provider.oauth_scopes or ['openid', 'profile', 'email'])

        auth_url = (f"{provider.oauth_authorization_url}?"
                   f"response_type=code&"
                   f"client_id={provider.oauth_client_id}&"
                   f"redirect_uri=https://api.synapse-rag.com/api/v1/auth/sso/oauth/callback&"
                   f"scope={scopes}&"
                   f"state={state}")

        return auth_url

    def exchange_oauth_code(self, code: str, provider_id: str, state: str) -> OIDCTokenResponse:
        """Exchange OAuth authorization code for tokens.

        Args:
            code: Authorization code from OAuth provider
            provider_id: SSO provider identifier
            state: State parameter for validation

        Returns:
            OIDCTokenResponse: Token response from provider
        """
        provider = self.get_provider(provider_id)
        if not provider or provider.type not in ['oauth2', 'oidc']:
            raise ValueError(f"Invalid OAuth provider: {provider_id}")

        # In production, this would make HTTP requests to the OAuth provider
        # For now, return a mock response for implementation
        return OIDCTokenResponse(
            access_token=f"mock_access_token_{secrets.token_urlsafe(16)}",
            token_type="Bearer",
            expires_in=3600,
            id_token=f"mock_id_token_{secrets.token_urlsafe(16)}"
        )

    def map_attributes_to_user(self, provider: SSOProvider, attributes: dict[str, Any], subject: str) -> User:
        """Map SSO provider attributes to User object.

        Args:
            provider: SSO provider configuration
            attributes: User attributes from SSO response
            subject: Subject identifier from SSO response

        Returns:
            User: Mapped user object
        """
        # Get attribute mapping or use defaults
        attr_mapping = provider.saml_attribute_mapping or {
            'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
            'username': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name',
            'groups': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/groups'
        }

        # Extract basic user info
        email = attributes.get(attr_mapping.get('email', 'email'), subject)
        username = attributes.get(attr_mapping.get('username', 'username'), subject.split('@')[0] if '@' in subject else subject)

        # Determine user role based on groups/attributes
        role = provider.default_role
        if provider.role_attribute and provider.role_mapping:
            user_groups = attributes.get(attr_mapping.get(provider.role_attribute, provider.role_attribute), [])
            if isinstance(user_groups, str):
                user_groups = [user_groups]

            # Check for role mapping matches
            for group in user_groups:
                if group in provider.role_mapping:
                    mapped_role = provider.role_mapping[group]
                    if isinstance(mapped_role, str):
                        role = UserRole(mapped_role)
                    else:
                        role = mapped_role
                    break

        # Create user object
        user = User(
            username=username,
            email=email,
            role=role,
            is_active=True,
            created_at=datetime.utcnow()
        )

        return user

    def create_sso_session(self, user: User, provider_id: str, external_user_id: str,
                          saml_session_index: str | None = None) -> SSOSession:
        """Create enterprise SSO session.

        Args:
            user: Authenticated user
            provider_id: SSO provider identifier
            external_user_id: External user identifier from SSO provider
            saml_session_index: SAML session index for logout

        Returns:
            SSOSession: Created session object
        """
        provider = self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        session = SSOSession(
            provider_id=provider_id,
            tenant_id=provider.tenant_id,
            user_id=str(user.id),
            external_user_id=external_user_id,
            saml_session_index=saml_session_index,
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )

        self.sessions[session.session_id] = session

        logger.info(f"Created SSO session {session.session_id} for user {user.username} via {provider_id}")

        return session

    def get_sso_session(self, session_id: str) -> SSOSession | None:
        """Get SSO session by ID."""
        session = self.sessions.get(session_id)
        if session and session.is_active and datetime.utcnow() < session.expires_at:
            return session
        elif session:
            # Clean up expired session
            del self.sessions[session_id]
        return None

    def invalidate_sso_session(self, session_id: str) -> bool:
        """Invalidate SSO session."""
        session = self.sessions.get(session_id)
        if session:
            session.is_active = False
            logger.info(f"Invalidated SSO session {session_id}")
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired SSO sessions.

        Returns:
            int: Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if not session.is_active or now >= session.expires_at
        ]

        for session_id in expired_sessions:
            del self.sessions[session_id]

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired SSO sessions")

        return len(expired_sessions)
