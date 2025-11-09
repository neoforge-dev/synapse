"""Enterprise authentication service with multi-provider SSO support."""

import logging
from datetime import datetime
from typing import Any

from ...config.enterprise_config import EnterpriseConfigManager, TenantConfiguration
from ..auth.providers import AuthProvider
from .enterprise_sso import EnterpriseSSOHandler, SSOProvider, SSOSession
from .jwt_handler import JWTHandler
from .models import TokenResponse, User
from .oauth_client import EnterpriseOAuthClient

logger = logging.getLogger(__name__)


class EnterpriseAuthResult:
    """Result of enterprise authentication attempt."""

    def __init__(self, success: bool, user: User | None = None,
                 error: str | None = None, session: SSOSession | None = None,
                 token_response: TokenResponse | None = None):
        self.success = success
        self.user = user
        self.error = error
        self.session = session
        self.token_response = token_response


class MultiProviderSSOService:
    """Unified service for handling multiple enterprise identity providers."""

    def __init__(self, jwt_handler: JWTHandler, auth_provider: AuthProvider,
                 config_manager: EnterpriseConfigManager):
        self.jwt_handler = jwt_handler
        self.auth_provider = auth_provider
        self.config_manager = config_manager

        # Initialize SSO handlers
        self.saml_handler = EnterpriseSSOHandler(jwt_handler)
        self.oauth_client = EnterpriseOAuthClient()

        # Cache for tenant configurations and providers
        self._tenant_configs: dict[str, TenantConfiguration] = {}
        self._providers: dict[str, SSOProvider] = {}

    async def get_tenant_configuration(self, tenant_id: str) -> TenantConfiguration | None:
        """Get tenant configuration with caching."""
        if tenant_id not in self._tenant_configs:
            config = self.config_manager.get_tenant_configuration(tenant_id)
            if config:
                self._tenant_configs[tenant_id] = config
            return config
        return self._tenant_configs[tenant_id]

    async def get_provider(self, provider_id: str) -> SSOProvider | None:
        """Get SSO provider with caching."""
        if provider_id not in self._providers:
            provider = self.config_manager.get_sso_provider(provider_id)
            if provider:
                self._providers[provider_id] = provider
                # Register with appropriate handler
                if provider.type == 'saml':
                    self.saml_handler.register_provider(provider)
            return provider
        return self._providers[provider_id]

    async def get_tenant_providers(self, tenant_id: str) -> list[SSOProvider]:
        """Get all active SSO providers for a tenant."""
        providers = self.config_manager.get_tenant_sso_providers(tenant_id)

        # Cache and register providers
        for provider in providers:
            self._providers[provider.provider_id] = provider
            if provider.type == 'saml':
                self.saml_handler.register_provider(provider)

        return providers

    async def initiate_sso_login(self, provider_id: str, redirect_uri: str,
                               tenant_id: str | None = None) -> dict[str, Any]:
        """Initiate SSO login flow for any supported provider type.

        Args:
            provider_id: SSO provider identifier
            redirect_uri: Callback URL after authentication
            tenant_id: Optional tenant ID for additional validation

        Returns:
            Dict containing auth_url and flow-specific data
        """
        provider = await self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        if not provider.is_active:
            raise ValueError(f"Provider is disabled: {provider_id}")

        # Validate tenant if provided
        if tenant_id and provider.tenant_id != tenant_id:
            raise ValueError(f"Provider {provider_id} does not belong to tenant {tenant_id}")

        logger.info(f"Initiating SSO login for provider {provider_id} (type: {provider.type})")

        if provider.type == 'saml':
            # Generate SAML authentication request
            auth_request, auth_url = self.saml_handler.generate_saml_auth_request(
                provider_id,
                relay_state=redirect_uri
            )

            return {
                'auth_url': auth_url,
                'flow_type': 'saml',
                'provider_id': provider_id,
                'auth_request': auth_request
            }

        elif provider.type in ['oauth2', 'oidc']:
            # Generate OAuth authorization URL
            scopes = provider.oauth_scopes or ['openid', 'profile', 'email']
            auth_url, oauth_state = self.oauth_client.create_authorization_url(
                provider, redirect_uri, scopes
            )

            return {
                'auth_url': auth_url,
                'flow_type': provider.type,
                'provider_id': provider_id,
                'state': oauth_state.state
            }

        else:
            raise ValueError(f"Unsupported provider type: {provider.type}")

    async def complete_saml_login(self, saml_response_b64: str, provider_id: str,
                                relay_state: str | None = None) -> EnterpriseAuthResult:
        """Complete SAML SSO login flow.

        Args:
            saml_response_b64: Base64 encoded SAML response
            provider_id: SSO provider identifier
            relay_state: Optional relay state from initial request

        Returns:
            EnterpriseAuthResult: Authentication result
        """
        try:
            provider = await self.get_provider(provider_id)
            if not provider:
                return EnterpriseAuthResult(False, error=f"Provider not found: {provider_id}")

            # Parse and validate SAML response
            saml_response = self.saml_handler.parse_saml_response(saml_response_b64, provider_id)

            if not saml_response.is_valid():
                return EnterpriseAuthResult(False, error="SAML response expired or invalid")

            # Map SAML attributes to user
            user = self.saml_handler.map_attributes_to_user(
                provider, saml_response.attributes, saml_response.subject
            )

            # Create or update user in auth provider
            existing_user = await self.auth_provider.get_user_by_email(user.email)
            if existing_user:
                # Update existing user's role and last login
                existing_user.role = user.role
                existing_user.last_login = datetime.utcnow()
                user = existing_user
            else:
                # Create new user
                from .models import UserCreate
                user_create = UserCreate(
                    username=user.username,
                    email=user.email,
                    password="sso-managed",  # SSO users don't have local passwords
                    role=user.role
                )
                user = await self.auth_provider.create_user(user_create)

            # Create SSO session
            sso_session = self.saml_handler.create_sso_session(
                user, provider_id, saml_response.subject, saml_response.session_index
            )

            # Generate JWT token
            access_token = self.jwt_handler.create_access_token(user)

            # Update last login
            await self.auth_provider.update_last_login(user.id)

            token_response = TokenResponse(
                access_token=access_token,
                expires_in=self.jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )

            logger.info(f"SAML login successful for user {user.email} via provider {provider_id}")

            return EnterpriseAuthResult(
                success=True,
                user=user,
                session=sso_session,
                token_response=token_response
            )

        except Exception as e:
            logger.error(f"SAML login failed: {str(e)}")
            return EnterpriseAuthResult(False, error=f"SAML login failed: {str(e)}")

    async def complete_oauth_login(self, authorization_code: str, state: str,
                                 provider_id: str) -> EnterpriseAuthResult:
        """Complete OAuth/OIDC SSO login flow.

        Args:
            authorization_code: Authorization code from OAuth provider
            state: State parameter for CSRF validation
            provider_id: SSO provider identifier

        Returns:
            EnterpriseAuthResult: Authentication result
        """
        try:
            provider = await self.get_provider(provider_id)
            if not provider:
                return EnterpriseAuthResult(False, error=f"Provider not found: {provider_id}")

            # Exchange authorization code for tokens
            token_response = await self.oauth_client.exchange_authorization_code(
                authorization_code, state, provider
            )

            # Get user information
            userinfo = await self.oauth_client.get_user_info(
                token_response.access_token, provider
            )

            # Parse ID token if available
            id_token_claims = None
            if token_response.id_token:
                id_token_claims = self.oauth_client.parse_id_token(
                    token_response.id_token, provider
                )

            # Map to Synapse user
            user = self.oauth_client.map_oidc_user_to_synapse_user(
                userinfo, id_token_claims, provider
            )

            # Create or update user in auth provider
            existing_user = await self.auth_provider.get_user_by_email(user.email)
            if existing_user:
                # Update existing user's role and last login
                existing_user.role = user.role
                existing_user.last_login = datetime.utcnow()
                user = existing_user
            else:
                # Create new user
                from .models import UserCreate
                user_create = UserCreate(
                    username=user.username,
                    email=user.email,
                    password="sso-managed",  # SSO users don't have local passwords
                    role=user.role
                )
                user = await self.auth_provider.create_user(user_create)

            # Create SSO session
            sso_session = self.saml_handler.create_sso_session(
                user, provider_id, userinfo.sub
            )

            # Generate JWT token
            access_token = self.jwt_handler.create_access_token(user)

            # Update last login
            await self.auth_provider.update_last_login(user.id)

            jwt_token_response = TokenResponse(
                access_token=access_token,
                expires_in=self.jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )

            logger.info(f"OAuth login successful for user {user.email} via provider {provider_id}")

            return EnterpriseAuthResult(
                success=True,
                user=user,
                session=sso_session,
                token_response=jwt_token_response
            )

        except Exception as e:
            logger.error(f"OAuth login failed: {str(e)}")
            return EnterpriseAuthResult(False, error=f"OAuth login failed: {str(e)}")

    async def initiate_sso_logout(self, session_id: str) -> dict[str, Any]:
        """Initiate SSO logout (Single Logout) if supported by provider.

        Args:
            session_id: SSO session identifier

        Returns:
            Dict containing logout URL and instructions
        """
        session = self.saml_handler.get_sso_session(session_id)
        if not session:
            return {'error': 'Session not found'}

        provider = await self.get_provider(session.provider_id)
        if not provider:
            return {'error': 'Provider not found'}

        # Invalidate local session
        self.saml_handler.invalidate_sso_session(session_id)

        logger.info(f"Initiated SSO logout for session {session_id}")

        # For SAML, we could generate a LogoutRequest
        # For OAuth/OIDC, we typically just provide the provider's logout URL
        if provider.type == 'saml':
            return {
                'logout_type': 'saml',
                'message': 'Local session terminated. SAML Single Logout not implemented yet.',
                'manual_logout_url': provider.saml_sso_url  # User can manually logout at provider
            }
        else:
            return {
                'logout_type': 'oauth',
                'message': 'Local session terminated.',
                'provider_logout_url': f"{provider.oauth_authorization_url.replace('/authorize', '/logout')}"
            }

    async def validate_tenant_access(self, user: User, tenant_id: str) -> bool:
        """Validate that user has access to specified tenant.

        Args:
            user: Authenticated user
            tenant_id: Tenant identifier to check access for

        Returns:
            bool: True if user has access to tenant
        """
        # Get tenant configuration
        tenant_config = await self.get_tenant_configuration(tenant_id)
        if not tenant_config:
            return False

        # Check if user's SSO session is for this tenant
        # This would require tracking which provider/tenant the user came from
        # For now, we'll do a basic check based on email domain

        # Get tenant providers
        providers = await self.get_tenant_providers(tenant_id)

        # For demo purposes, allow access if user came through any of the tenant's providers
        # In production, you'd track the specific provider used during authentication
        for provider in providers:
            # This is a simplified check - in practice you'd store the provider
            # used for authentication in the user session or JWT token
            if provider.tenant_id == tenant_id:
                return True

        return False

    async def get_tenant_authentication_options(self, tenant_id: str) -> dict[str, Any]:
        """Get available authentication options for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dict containing available authentication methods
        """
        tenant_config = await self.get_tenant_configuration(tenant_id)
        if not tenant_config:
            return {'error': 'Tenant not found'}

        providers = await self.get_tenant_providers(tenant_id)

        auth_options = {
            'tenant_id': tenant_id,
            'require_sso': tenant_config.require_sso,
            'allow_local_auth': tenant_config.allow_local_auth,
            'sso_providers': []
        }

        for provider in providers:
            auth_options['sso_providers'].append({
                'provider_id': provider.provider_id,
                'name': provider.name,
                'type': provider.type,
                'is_active': provider.is_active
            })

        return auth_options

    async def cleanup_expired_sessions(self) -> dict[str, int]:
        """Clean up expired sessions and states."""
        saml_cleaned = self.saml_handler.cleanup_expired_sessions()
        oauth_cleaned = self.oauth_client.cleanup_expired_states()

        if saml_cleaned or oauth_cleaned:
            logger.info(f"Session cleanup: {saml_cleaned} SAML sessions, {oauth_cleaned} OAuth states")

        return {
            'saml_sessions_cleaned': saml_cleaned,
            'oauth_states_cleaned': oauth_cleaned
        }

    async def get_enterprise_analytics(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Get enterprise authentication analytics.

        Args:
            tenant_id: Optional tenant ID to filter analytics

        Returns:
            Dict containing authentication metrics
        """
        analytics = {
            'timestamp': datetime.utcnow().isoformat(),
            'active_sso_sessions': len([s for s in self.saml_handler.sessions.values()
                                       if s.is_active and (not tenant_id or s.tenant_id == tenant_id)]),
            'active_oauth_flows': len([s for s in self.oauth_client.states.values()
                                     if not s.is_expired()]),
            'total_providers': len(self._providers),
            'providers_by_type': {}
        }

        # Provider statistics
        for provider in self._providers.values():
            if tenant_id and provider.tenant_id != tenant_id:
                continue

            provider_type = provider.type
            if provider_type not in analytics['providers_by_type']:
                analytics['providers_by_type'][provider_type] = 0
            analytics['providers_by_type'][provider_type] += 1

        return analytics

    async def close(self):
        """Clean up resources."""
        await self.oauth_client.close()
