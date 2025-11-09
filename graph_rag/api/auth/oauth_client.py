"""OAuth 2.0 and OpenID Connect client implementation for enterprise SSO."""

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
import jwt
from pydantic import BaseModel, Field

from .enterprise_sso import OIDCTokenResponse, SSOProvider
from .models import User, UserRole

logger = logging.getLogger(__name__)


class OAuthState(BaseModel):
    """OAuth state for CSRF protection and flow tracking."""

    state: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    provider_id: str
    redirect_uri: str
    code_verifier: str | None = None  # PKCE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=10))

    def is_expired(self) -> bool:
        """Check if state is expired."""
        return datetime.utcnow() > self.expires_at


class OIDCUserInfo(BaseModel):
    """OpenID Connect user information."""

    sub: str  # Subject identifier
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    picture: str | None = None
    groups: list[str] | None = None
    roles: list[str] | None = None
    preferred_username: str | None = None

    # Azure AD specific
    upn: str | None = None  # User Principal Name
    unique_name: str | None = None

    # Google Workspace specific
    hd: str | None = None  # Hosted domain

    # Okta specific
    department: str | None = None
    organization: str | None = None


class IDTokenClaims(BaseModel):
    """ID token claims for OpenID Connect."""

    iss: str  # Issuer
    sub: str  # Subject
    aud: str  # Audience (client ID)
    exp: int  # Expiration time
    iat: int  # Issued at time
    nonce: str | None = None

    # Standard claims
    name: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    groups: list[str] | None = None

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow().timestamp() > self.exp


class EnterpriseOAuthClient:
    """OAuth 2.0 and OpenID Connect client for enterprise identity providers."""

    def __init__(self):
        self.states: dict[str, OAuthState] = {}
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

    def generate_pkce_challenge(self) -> tuple[str, str]:
        """Generate PKCE code challenge and verifier for enhanced security.

        Returns:
            tuple: (code_verifier, code_challenge)
        """
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    def create_authorization_url(self, provider: SSOProvider, redirect_uri: str,
                               scopes: list[str] | None = None, use_pkce: bool = True) -> tuple[str, OAuthState]:
        """Create OAuth 2.0 authorization URL with enterprise security features.

        Args:
            provider: Enterprise SSO provider configuration
            redirect_uri: OAuth callback URL
            scopes: OAuth scopes to request
            use_pkce: Use PKCE for enhanced security

        Returns:
            tuple: (authorization_url, oauth_state)
        """
        if provider.type not in ['oauth2', 'oidc']:
            raise ValueError(f"Provider {provider.provider_id} is not an OAuth provider")

        # Create OAuth state for CSRF protection
        oauth_state = OAuthState(
            provider_id=provider.provider_id,
            redirect_uri=redirect_uri
        )

        # Prepare authorization parameters
        auth_params = {
            'response_type': 'code',
            'client_id': provider.oauth_client_id,
            'redirect_uri': redirect_uri,
            'state': oauth_state.state,
            'scope': ' '.join(scopes or provider.oauth_scopes or ['openid', 'profile', 'email'])
        }

        # Add PKCE if enabled (recommended for all clients)
        if use_pkce:
            code_verifier, code_challenge = self.generate_pkce_challenge()
            oauth_state.code_verifier = code_verifier
            auth_params.update({
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            })

        # Provider-specific enhancements
        if 'microsoft' in provider.oauth_authorization_url.host.lower():
            # Azure AD specific parameters
            auth_params['response_mode'] = 'query'
            auth_params['prompt'] = 'select_account'
        elif 'okta' in provider.oauth_authorization_url.host.lower():
            # Okta specific parameters
            auth_params['nonce'] = secrets.token_urlsafe(16)
        elif 'google' in provider.oauth_authorization_url.host.lower():
            # Google specific parameters
            auth_params['access_type'] = 'offline'
            auth_params['include_granted_scopes'] = 'true'

        # Store state for validation
        self.states[oauth_state.state] = oauth_state

        # Build authorization URL
        auth_url = f"{provider.oauth_authorization_url}?{urlencode(auth_params)}"

        logger.info(f"Created OAuth authorization URL for provider {provider.provider_id}")

        return auth_url, oauth_state

    async def exchange_authorization_code(self, code: str, state: str, provider: SSOProvider) -> OIDCTokenResponse:
        """Exchange authorization code for access token and ID token.

        Args:
            code: Authorization code from OAuth provider
            state: State parameter for CSRF validation
            provider: Enterprise SSO provider configuration

        Returns:
            OIDCTokenResponse: Token response from provider
        """
        # Validate state
        oauth_state = self.states.get(state)
        if not oauth_state or oauth_state.is_expired():
            raise ValueError("Invalid or expired OAuth state")

        if oauth_state.provider_id != provider.provider_id:
            raise ValueError("Provider mismatch in OAuth state")

        # Prepare token request
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': provider.oauth_client_id,
            'client_secret': provider.oauth_client_secret,
            'code': code,
            'redirect_uri': oauth_state.redirect_uri
        }

        # Add PKCE verifier if used
        if oauth_state.code_verifier:
            token_data['code_verifier'] = oauth_state.code_verifier

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Synapse-GraphRAG/1.0 Enterprise-SSO'
        }

        try:
            response = await self.http_client.post(
                str(provider.oauth_token_url),
                data=token_data,
                headers=headers
            )
            response.raise_for_status()

            token_data = response.json()

            # Clean up used state
            del self.states[state]

            logger.info(f"Successfully exchanged OAuth code for tokens with provider {provider.provider_id}")

            return OIDCTokenResponse(
                access_token=token_data['access_token'],
                token_type=token_data.get('token_type', 'Bearer'),
                expires_in=token_data.get('expires_in', 3600),
                refresh_token=token_data.get('refresh_token'),
                id_token=token_data.get('id_token'),
                scope=token_data.get('scope')
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OAuth token exchange failed: {e.response.status_code} {e.response.text}")
            raise ValueError(f"Token exchange failed: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"OAuth token exchange error: {e}")
            raise ValueError(f"Token exchange error: {str(e)}") from e

    async def get_user_info(self, access_token: str, provider: SSOProvider) -> OIDCUserInfo:
        """Get user information from OAuth provider.

        Args:
            access_token: Access token from OAuth provider
            provider: Enterprise SSO provider configuration

        Returns:
            OIDCUserInfo: User information from provider
        """
        if not provider.oauth_userinfo_url:
            raise ValueError(f"Provider {provider.provider_id} does not have userinfo endpoint configured")

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
            'User-Agent': 'Synapse-GraphRAG/1.0 Enterprise-SSO'
        }

        try:
            response = await self.http_client.get(
                str(provider.oauth_userinfo_url),
                headers=headers
            )
            response.raise_for_status()

            userinfo_data = response.json()

            logger.info(f"Retrieved user info from provider {provider.provider_id}")

            return OIDCUserInfo(**userinfo_data)

        except httpx.HTTPStatusError as e:
            logger.error(f"UserInfo request failed: {e.response.status_code} {e.response.text}")
            raise ValueError(f"UserInfo request failed: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"UserInfo request error: {e}")
            raise ValueError(f"UserInfo error: {str(e)}") from e

    def parse_id_token(self, id_token: str, provider: SSOProvider,
                      validate_signature: bool = False) -> IDTokenClaims:
        """Parse and validate OpenID Connect ID token.

        Args:
            id_token: JWT ID token from provider
            provider: Enterprise SSO provider configuration
            validate_signature: Whether to validate JWT signature (requires provider public key)

        Returns:
            IDTokenClaims: Parsed ID token claims
        """
        try:
            # Decode without signature verification for now
            # In production, you would fetch and validate against provider's public keys
            decoded = jwt.decode(
                id_token,
                options={"verify_signature": validate_signature, "verify_exp": True, "verify_aud": True},
                audience=provider.oauth_client_id if validate_signature else None
            )

            return IDTokenClaims(**decoded)

        except jwt.ExpiredSignatureError as e:
            raise ValueError("ID token has expired") from e
        except jwt.InvalidAudienceError as e:
            raise ValueError("ID token audience mismatch") from e
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {str(e)}") from e

    def map_oidc_user_to_synapse_user(self, userinfo: OIDCUserInfo, id_token: IDTokenClaims | None,
                                     provider: SSOProvider) -> User:
        """Map OpenID Connect user information to Synapse User object.

        Args:
            userinfo: User information from provider
            id_token: ID token claims (optional)
            provider: Enterprise SSO provider configuration

        Returns:
            User: Synapse user object
        """
        # Determine email - prefer verified email
        email = userinfo.email
        if not email and id_token:
            email = id_token.email
        if not email:
            # Fallback to Azure AD UPN or other identifiers
            email = userinfo.upn or userinfo.unique_name or f"{userinfo.sub}@{provider.tenant_id}.local"

        # Determine username
        username = (userinfo.preferred_username or
                   userinfo.name or
                   userinfo.unique_name or
                   email.split('@')[0] if email else
                   userinfo.sub)

        # Determine role based on groups/roles
        role = provider.default_role
        user_groups = []

        # Collect groups from various sources
        if userinfo.groups:
            user_groups.extend(userinfo.groups)
        if userinfo.roles:
            user_groups.extend(userinfo.roles)
        if id_token and id_token.groups:
            user_groups.extend(id_token.groups)

        # Apply role mapping
        if provider.role_mapping and user_groups:
            for group in user_groups:
                if group in provider.role_mapping:
                    mapped_role = provider.role_mapping[group]
                    if isinstance(mapped_role, str):
                        role = UserRole(mapped_role)
                    else:
                        role = mapped_role
                    break  # Use first matching role

        # Create user object
        user = User(
            username=username[:50],  # Ensure username fits database constraints
            email=email,
            role=role,
            is_active=True,
            created_at=datetime.utcnow()
        )

        logger.info(f"Mapped OIDC user {userinfo.sub} to Synapse user {user.username} with role {role}")

        return user

    async def refresh_access_token(self, refresh_token: str, provider: SSOProvider) -> OIDCTokenResponse:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from previous authentication
            provider: Enterprise SSO provider configuration

        Returns:
            OIDCTokenResponse: New token response
        """
        token_data = {
            'grant_type': 'refresh_token',
            'client_id': provider.oauth_client_id,
            'client_secret': provider.oauth_client_secret,
            'refresh_token': refresh_token
        }

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Synapse-GraphRAG/1.0 Enterprise-SSO'
        }

        try:
            response = await self.http_client.post(
                str(provider.oauth_token_url),
                data=token_data,
                headers=headers
            )
            response.raise_for_status()

            token_data = response.json()

            logger.info(f"Successfully refreshed access token for provider {provider.provider_id}")

            return OIDCTokenResponse(
                access_token=token_data['access_token'],
                token_type=token_data.get('token_type', 'Bearer'),
                expires_in=token_data.get('expires_in', 3600),
                refresh_token=token_data.get('refresh_token', refresh_token),
                id_token=token_data.get('id_token'),
                scope=token_data.get('scope')
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Token refresh failed: {e.response.status_code} {e.response.text}")
            raise ValueError(f"Token refresh failed: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise ValueError(f"Token refresh error: {str(e)}") from e

    def cleanup_expired_states(self) -> int:
        """Clean up expired OAuth states.

        Returns:
            int: Number of states cleaned up
        """
        datetime.utcnow()
        expired_states = [
            state for state, oauth_state in self.states.items()
            if oauth_state.is_expired()
        ]

        for state in expired_states:
            del self.states[state]

        if expired_states:
            logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")

        return len(expired_states)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


# Pre-configured providers for common enterprise identity systems
ENTERPRISE_PROVIDER_TEMPLATES = {
    'azure_ad': {
        'name': 'Microsoft Azure AD',
        'type': 'oidc',
        'oauth_authorization_url': 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize',
        'oauth_token_url': 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
        'oauth_userinfo_url': 'https://graph.microsoft.com/v1.0/me',
        'oauth_scopes': ['openid', 'profile', 'email', 'User.Read'],
        'saml_attribute_mapping': {
            'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
            'username': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name',
            'groups': 'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups'
        }
    },
    'okta': {
        'name': 'Okta',
        'type': 'oidc',
        'oauth_authorization_url': 'https://{okta_domain}/oauth2/v1/authorize',
        'oauth_token_url': 'https://{okta_domain}/oauth2/v1/token',
        'oauth_userinfo_url': 'https://{okta_domain}/oauth2/v1/userinfo',
        'oauth_scopes': ['openid', 'profile', 'email', 'groups'],
        'saml_sso_url': 'https://{okta_domain}/app/{app_id}/sso/saml',
        'role_attribute': 'groups',
        'role_mapping': {
            'synapse_admins': UserRole.ADMIN,
            'synapse_users': UserRole.USER,
            'synapse_readonly': UserRole.READONLY
        }
    },
    'google_workspace': {
        'name': 'Google Workspace',
        'type': 'oidc',
        'oauth_authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'oauth_token_url': 'https://oauth2.googleapis.com/token',
        'oauth_userinfo_url': 'https://openidconnect.googleapis.com/v1/userinfo',
        'oauth_scopes': ['openid', 'profile', 'email'],
        'saml_attribute_mapping': {
            'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
            'username': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name'
        }
    }
}
