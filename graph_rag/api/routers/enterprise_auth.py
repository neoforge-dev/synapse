"""Enterprise authentication endpoints for SSO, multi-tenancy, and compliance."""

import logging
from datetime import datetime
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from ..auth.dependencies import get_auth_provider, get_current_user, require_admin_role
from ..auth.enterprise_models import (
    AuditEventType,
    ComplianceFramework,
    ComplianceReportRequest,
    LDAPAuthRequest,
    LDAPConfiguration,
    MFAChallengeRequest,
    MFAType,
    OAuthAuthRequest,
    OAuthConfiguration,
    SAMLAuthRequest,
    SAMLConfiguration,
    TenantCreateRequest,
)
from ..auth.enterprise_providers import EnterpriseAuthProvider
from ..auth.models import TokenResponse, User

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def create_enterprise_auth_router() -> APIRouter:
    """Create enterprise authentication router with SSO and compliance endpoints."""
    router = APIRouter(prefix="/auth/enterprise", tags=["Enterprise Authentication"])

    @router.post("/tenants", status_code=status.HTTP_201_CREATED)
    async def create_tenant(
        tenant_data: TenantCreateRequest,
        request: Request,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Create a new enterprise tenant."""
        try:
            tenant = await auth_provider.create_tenant(tenant_data)
            
            # Log audit event
            await auth_provider.log_audit_event(
                tenant_id=tenant.id,
                event_type=AuditEventType.TENANT_CREATED,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                action="create_tenant",
                result="success",
                details={
                    "tenant_name": tenant.name,
                    "domain": tenant.domain,
                    "compliance_frameworks": [f.value for f in tenant.compliance_frameworks]
                }
            )
            
            return {
                "tenant_id": tenant.id,
                "name": tenant.name,
                "domain": tenant.domain,
                "subdomain": tenant.subdomain,
                "compliance_frameworks": tenant.compliance_frameworks,
                "created_at": tenant.created_at
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Tenant creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tenant"
            )

    @router.get("/tenants/{tenant_id}")
    async def get_tenant(
        tenant_id: UUID,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Get tenant information."""
        tenant = await auth_provider.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        return tenant

    # --- SAML 2.0 Endpoints ---

    @router.post("/saml/configure")
    async def configure_saml(
        saml_config: SAMLConfiguration,
        request: Request,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Configure SAML identity provider for a tenant."""
        try:
            config = await auth_provider.configure_saml(saml_config.tenant_id, saml_config)
            
            await auth_provider.log_audit_event(
                tenant_id=config.tenant_id,
                event_type=AuditEventType.CONFIGURATION_CHANGED,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                action="configure_saml",
                result="success",
                details={"provider_name": config.name, "entity_id": config.entity_id}
            )
            
            return {"message": "SAML configuration created", "config_id": config.id}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/saml/login", response_model=TokenResponse)
    async def saml_login(
        saml_request: SAMLAuthRequest,
        request: Request,
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ) -> TokenResponse:
        """Authenticate user with SAML response."""
        try:
            user = await auth_provider.authenticate_saml(
                saml_request.saml_response,
                saml_request.relay_state
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="SAML authentication failed"
                )

            # Generate access token
            access_token = auth_provider.jwt_handler.create_access_token(user)
            
            # Update last login
            await auth_provider.update_last_login(user.id)
            
            return TokenResponse(
                access_token=access_token,
                expires_in=auth_provider.jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"SAML authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SAML authentication failed"
            )

    @router.get("/saml/{tenant_id}/metadata")
    async def get_saml_metadata(
        tenant_id: UUID,
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Get SAML metadata for Service Provider configuration."""
        tenant = await auth_provider.get_tenant_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        
        # Generate SAML metadata (simplified)
        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" 
                     entityID="https://{tenant.subdomain}.synapse.com/saml/metadata">
    <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService 
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="https://{tenant.subdomain}.synapse.com/auth/enterprise/saml/login"
            index="1"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
        
        return {"metadata": metadata}

    # --- OAuth 2.0/OpenID Connect Endpoints ---

    @router.post("/oauth/configure")
    async def configure_oauth(
        oauth_config: OAuthConfiguration,
        request: Request,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Configure OAuth identity provider for a tenant."""
        try:
            config = await auth_provider.configure_oauth(oauth_config.tenant_id, oauth_config)
            
            await auth_provider.log_audit_event(
                tenant_id=config.tenant_id,
                event_type=AuditEventType.CONFIGURATION_CHANGED,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                action="configure_oauth",
                result="success",
                details={"provider": config.provider.value, "name": config.name}
            )
            
            return {"message": "OAuth configuration created", "config_id": config.id}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/oauth/login", response_model=TokenResponse)
    async def oauth_login(
        oauth_request: OAuthAuthRequest,
        request: Request,
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ) -> TokenResponse:
        """Authenticate user with OAuth authorization code."""
        try:
            user = await auth_provider.authenticate_oauth(
                oauth_request.provider_id,
                oauth_request.authorization_code,
                oauth_request.redirect_uri
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="OAuth authentication failed"
                )

            # Generate access token
            access_token = auth_provider.jwt_handler.create_access_token(user)
            
            # Update last login
            await auth_provider.update_last_login(user.id)
            
            return TokenResponse(
                access_token=access_token,
                expires_in=auth_provider.jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"OAuth authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth authentication failed"
            )

    # --- LDAP/Active Directory Endpoints ---

    @router.post("/ldap/configure")
    async def configure_ldap(
        ldap_config: LDAPConfiguration,
        request: Request,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Configure LDAP/Active Directory for a tenant."""
        try:
            config = await auth_provider.configure_ldap(ldap_config.tenant_id, ldap_config)
            
            await auth_provider.log_audit_event(
                tenant_id=config.tenant_id,
                event_type=AuditEventType.CONFIGURATION_CHANGED,
                user_id=current_user.id,
                ip_address=request.client.host if request.client else None,
                action="configure_ldap",
                result="success",
                details={"name": config.name, "server_uri": config.server_uri}
            )
            
            return {"message": "LDAP configuration created", "config_id": config.id}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/ldap/login", response_model=TokenResponse)
    async def ldap_login(
        ldap_request: LDAPAuthRequest,
        request: Request,
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ) -> TokenResponse:
        """Authenticate user with LDAP credentials."""
        try:
            user = await auth_provider.authenticate_ldap(
                ldap_request.tenant_id,
                ldap_request.username,
                ldap_request.password
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LDAP authentication failed"
                )

            # Generate access token
            access_token = auth_provider.jwt_handler.create_access_token(user)
            
            # Update last login
            await auth_provider.update_last_login(user.id)
            
            return TokenResponse(
                access_token=access_token,
                expires_in=auth_provider.jwt_handler.settings.access_token_expire_minutes * 60,
                user=user
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LDAP authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LDAP authentication failed"
            )

    # --- Multi-Factor Authentication Endpoints ---

    @router.post("/mfa/setup")
    async def setup_mfa(
        mfa_type: MFAType,
        request: Request,
        current_user: User = Depends(get_current_user),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider),
        phone_number: str = None,
        email: str = None
    ):
        """Setup multi-factor authentication."""
        try:
            mfa_config = await auth_provider.setup_mfa(
                current_user.id,
                mfa_type,
                phone_number=phone_number,
                email=email
            )
            
            response = {
                "mfa_id": mfa_config.id,
                "mfa_type": mfa_config.mfa_type,
                "setup_complete": True
            }
            
            if mfa_type == MFAType.TOTP:
                # Return QR code data for TOTP setup
                response["totp_secret"] = mfa_config.secret_key
                response["backup_codes"] = mfa_config.backup_codes
            
            return response
            
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/mfa/verify")
    async def verify_mfa(
        mfa_request: MFAChallengeRequest,
        request: Request,
        current_user: User = Depends(get_current_user),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Verify MFA challenge."""
        try:
            is_valid = await auth_provider.verify_mfa(
                mfa_request.user_id or current_user.id,
                mfa_request.mfa_type,
                mfa_request.challenge_code
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code"
                )
            
            return {"verified": True, "message": "MFA verification successful"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"MFA verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MFA verification failed"
            )

    # --- Compliance and Audit Endpoints ---

    @router.get("/audit/events/{tenant_id}")
    async def get_audit_events(
        tenant_id: UUID,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: AuditEventType = None,
        limit: int = 100,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Get audit events for compliance reporting."""
        # Filter audit events (implementation depends on storage backend)
        events = [
            event for event in auth_provider._audit_events
            if event.tenant_id == tenant_id
        ]
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Limit results
        events = events[:limit]
        
        return {"events": events, "total_count": len(events)}

    @router.post("/compliance/report")
    async def generate_compliance_report(
        report_request: ComplianceReportRequest,
        current_user: User = Depends(require_admin_role),
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Generate compliance report for a tenant."""
        try:
            report = await auth_provider.generate_compliance_report(
                report_request.tenant_id,
                report_request.framework,
                report_request.start_date,
                report_request.end_date
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Compliance report generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate compliance report"
            )

    @router.get("/compliance/frameworks")
    async def list_compliance_frameworks():
        """List supported compliance frameworks."""
        return {
            "frameworks": [
                {"name": framework.value, "description": f"{framework.value.upper()} compliance framework"}
                for framework in ComplianceFramework
            ]
        }

    @router.get("/health/enterprise")
    async def enterprise_health_check(
        auth_provider: EnterpriseAuthProvider = Depends(get_auth_provider)
    ):
        """Enterprise authentication system health check."""
        return {
            "status": "healthy",
            "enterprise_features": {
                "saml_enabled": len(auth_provider._saml_configs) > 0,
                "oauth_enabled": len(auth_provider._oauth_configs) > 0,
                "ldap_enabled": len(auth_provider._ldap_configs) > 0,
                "mfa_enabled": len(auth_provider._mfa_configs) > 0,
                "audit_logging": len(auth_provider._audit_events) > 0
            },
            "tenant_count": len(auth_provider._tenants),
            "active_configurations": {
                "saml": len([c for c in auth_provider._saml_configs.values() if c.is_active]),
                "oauth": len([c for c in auth_provider._oauth_configs.values() if c.is_active]),
                "ldap": len([c for c in auth_provider._ldap_configs.values() if c.is_active])
            }
        }

    return router