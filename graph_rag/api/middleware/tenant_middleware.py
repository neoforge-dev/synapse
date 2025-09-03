"""Tenant isolation middleware for multi-tenant architecture."""

import logging
from typing import Callable, Optional
from uuid import UUID

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..auth.enterprise_models import TenantUser
from ..auth.enterprise_providers import EnterpriseAuthProvider
from ...config import get_settings
from ...infrastructure.multi_tenancy.tenant_isolation import (
    TenantContext,
    TenantIsolationError,
    tenant_network_isolation,
    tenant_resource_quota,
    tenant_security_boundary,
)

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce tenant isolation at the request level."""

    def __init__(self, app, auth_provider: Optional[EnterpriseAuthProvider] = None):
        super().__init__(app)
        self.auth_provider = auth_provider
        self.settings = get_settings()
        
        # Paths that don't require tenant isolation
        self.exempt_paths = {
            "/docs",
            "/openapi.json",
            "/redoc",
            "/health",
            "/metrics",
            "/auth/login",
            "/auth/register",
            "/auth/enterprise/saml/metadata"
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant isolation."""
        
        # Skip tenant isolation for exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        try:
            # Extract tenant information from request
            tenant_id, user_id = await self._extract_tenant_info(request)
            
            if not tenant_id:
                # For non-tenant endpoints, skip isolation
                return await call_next(request)
            
            # Set tenant context for the request
            TenantContext.set_tenant(tenant_id, user_id)
            
            # Validate network access
            if not self._validate_network_access(tenant_id, request):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Network access denied for tenant"
                )
            
            # Check resource quotas
            if not self._check_resource_quota(tenant_id, request):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Tenant resource quota exceeded"
                )
            
            # Log access attempt
            await self._log_tenant_access(tenant_id, user_id, request)
            
            # Process request
            response = await call_next(request)
            
            # Update resource usage
            self._update_resource_usage(tenant_id, request, response)
            
            return response
            
        except TenantIsolationError as e:
            logger.error(f"Tenant isolation violation: {e}")
            return Response(
                content=f"Tenant isolation error: {str(e)}",
                status_code=status.HTTP_403_FORBIDDEN
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            return Response(
                content="Internal server error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Always clear tenant context after request
            TenantContext.clear()

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from tenant isolation."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    async def _extract_tenant_info(self, request: Request) -> tuple[Optional[UUID], Optional[UUID]]:
        """Extract tenant and user information from request."""
        
        # Method 1: From subdomain (e.g., tenant1.synapse.com)
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain != "www" and subdomain != "api":
                tenant = await self._get_tenant_by_subdomain(subdomain)
                if tenant:
                    user_id = await self._get_user_from_auth(request)
                    return tenant.id, user_id
        
        # Method 2: From X-Tenant-ID header
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            try:
                tenant_id = UUID(tenant_header)
                user_id = await self._get_user_from_auth(request)
                return tenant_id, user_id
            except ValueError:
                logger.warning(f"Invalid tenant ID in header: {tenant_header}")
        
        # Method 3: From authentication token
        if self.auth_provider:
            user = await self._get_authenticated_user(request)
            if user:
                # Get tenant from user context (implementation depends on auth provider)
                tenant_users = getattr(self.auth_provider, '_tenant_users', {})
                for tenant_user in tenant_users.values():
                    if tenant_user.user_id == user.id:
                        return tenant_user.tenant_id, user.id
        
        # Method 4: From URL path (e.g., /api/v1/tenants/{tenant_id}/...)
        path_parts = request.url.path.split("/")
        if "tenants" in path_parts:
            try:
                tenant_idx = path_parts.index("tenants") + 1
                if tenant_idx < len(path_parts):
                    tenant_id = UUID(path_parts[tenant_idx])
                    user_id = await self._get_user_from_auth(request)
                    return tenant_id, user_id
            except (ValueError, IndexError):
                pass
        
        return None, None

    async def _get_tenant_by_subdomain(self, subdomain: str):
        """Get tenant by subdomain."""
        if self.auth_provider and hasattr(self.auth_provider, '_tenants'):
            for tenant in self.auth_provider._tenants.values():
                if tenant.subdomain == subdomain:
                    return tenant
        return None

    async def _get_user_from_auth(self, request: Request) -> Optional[UUID]:
        """Get user ID from authentication."""
        user = await self._get_authenticated_user(request)
        return user.id if user else None

    async def _get_authenticated_user(self, request: Request):
        """Get authenticated user from request."""
        # Extract Bearer token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        if self.auth_provider:
            try:
                # Decode JWT token
                token_data = self.auth_provider.jwt_handler.decode_token(token)
                if token_data and not self.auth_provider.jwt_handler.is_token_expired(token_data):
                    return await self.auth_provider.get_user_by_id(token_data.user_id)
                
                # Try API key authentication
                if token.startswith("sk-"):
                    return await self.auth_provider.get_user_by_api_key(token)
            except Exception:
                pass
        
        return None

    def _validate_network_access(self, tenant_id: UUID, request: Request) -> bool:
        """Validate network access for tenant."""
        client_ip = self._get_client_ip(request)
        return tenant_network_isolation.validate_network_access(tenant_id, client_ip)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check X-Forwarded-For header (for load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Use client host from request
        if request.client:
            return request.client.host
        
        return "unknown"

    def _check_resource_quota(self, tenant_id: UUID, request: Request) -> bool:
        """Check resource quotas for tenant."""
        # Check API call quota
        return tenant_resource_quota.check_quota(tenant_id, "api_calls", 1)

    async def _log_tenant_access(self, tenant_id: UUID, user_id: Optional[UUID], request: Request):
        """Log tenant access for audit purposes."""
        try:
            operation = f"{request.method} {request.url.path}"
            tenant_security_boundary.validate_cross_tenant_access(
                tenant_id, tenant_id, operation
            )
            
            if self.auth_provider:
                await self.auth_provider.log_audit_event(
                    tenant_id=tenant_id,
                    event_type="DATA_ACCESS",  # Using string instead of enum
                    user_id=user_id,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("User-Agent"),
                    action=operation,
                    result="success"
                )
        except Exception as e:
            logger.error(f"Failed to log tenant access: {e}")

    def _update_resource_usage(self, tenant_id: UUID, request: Request, response: Response):
        """Update resource usage after request processing."""
        try:
            # Increment API call count
            tenant_resource_quota.increment_usage(tenant_id, "api_calls", 1)
            
            # Track storage usage for upload endpoints
            if request.method in ["POST", "PUT", "PATCH"]:
                content_length = request.headers.get("Content-Length")
                if content_length:
                    storage_mb = int(content_length) / (1024 * 1024)  # Convert to MB
                    tenant_resource_quota.increment_usage(tenant_id, "storage_mb", int(storage_mb))
        except Exception as e:
            logger.error(f"Failed to update resource usage: {e}")


class TenantHeaderMiddleware(BaseHTTPMiddleware):
    """Middleware to add tenant-specific response headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add tenant headers to response."""
        response = await call_next(request)
        
        tenant_id = TenantContext.get_tenant_id()
        if tenant_id:
            response.headers["X-Tenant-ID"] = str(tenant_id)
            response.headers["X-Tenant-Isolation"] = "enabled"
        
        return response


class TenantCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure tenant-isolated caching."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add tenant-specific cache headers."""
        response = await call_next(request)
        
        tenant_id = TenantContext.get_tenant_id()
        if tenant_id:
            # Prevent cross-tenant cache contamination
            response.headers["Cache-Control"] = f"private, tenant-{tenant_id}"
            response.headers["Vary"] = "X-Tenant-ID, Authorization"
        
        return response


class TenantSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add tenant-specific security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add tenant-specific security headers."""
        response = await call_next(request)
        
        tenant_id = TenantContext.get_tenant_id()
        if tenant_id:
            # Add Content Security Policy with tenant-specific restrictions
            csp = f"default-src 'self' *.tenant-{tenant_id}.synapse.com; " \
                  f"frame-ancestors 'none'; " \
                  f"base-uri 'self'"
            response.headers["Content-Security-Policy"] = csp
            
            # Add tenant-specific security headers
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response