"""Tenant isolation middleware for multi-tenant architecture."""

import logging
import time
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from ...architecture.multi_tenant.resource_isolation import (
    ResourceContext,
    ResourceType,
    get_resource_manager,
)
from ...architecture.multi_tenant.tenant_manager import TenantContext as NewTenantContext
from ...architecture.multi_tenant.tenant_manager import (
    TenantManager,
    TenantStatus,
    get_tenant_manager,
)
from ...config import get_settings
from ..auth.enterprise_providers import EnterpriseAuthProvider

# Legacy import for backward compatibility
try:
    from ...infrastructure.multi_tenancy.tenant_isolation import (
        TenantContext,
        TenantIsolationError,
        tenant_network_isolation,
        tenant_resource_quota,
        tenant_security_boundary,
    )
except ImportError:
    # Create minimal compatibility layer if old system not available
    class TenantContext:
        @staticmethod
        def set_tenant(tenant_id, user_id): pass
        @staticmethod
        def get_tenant_id(): return None
        @staticmethod
        def clear(): pass

    class TenantIsolationError(Exception): pass

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce tenant isolation at the request level."""

    def __init__(self, app, auth_provider: EnterpriseAuthProvider | None = None):
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

    async def _extract_tenant_info(self, request: Request) -> tuple[UUID | None, UUID | None]:
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

    async def _get_user_from_auth(self, request: Request) -> UUID | None:
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

    async def _log_tenant_access(self, tenant_id: UUID, user_id: UUID | None, request: Request):
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


# NEW EPIC 12 PHASE 2 MULTI-TENANT MIDDLEWARE

class EnhancedTenantMiddleware(BaseHTTPMiddleware):
    """Enhanced tenant middleware for Epic 12 Phase 2 multi-tenant architecture."""

    def __init__(
        self,
        app,
        tenant_manager: TenantManager | None = None,
        enable_resource_tracking: bool = True,
        enable_audit_logging: bool = True,
        require_tenant_for_all_requests: bool = False
    ):
        """Initialize enhanced tenant middleware."""
        super().__init__(app)
        self.tenant_manager = tenant_manager or get_tenant_manager()
        self.resource_manager = get_resource_manager()
        self.enable_resource_tracking = enable_resource_tracking
        self.enable_audit_logging = enable_audit_logging
        self.require_tenant_for_all_requests = require_tenant_for_all_requests

        # Exempt paths that don't need tenant context
        self.exempt_paths = {
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
            "/auth/enterprise/",
            "/api/onboarding/",  # Allow onboarding without tenant context
        }

        # Paths that require tenant context
        self.tenant_required_paths = {
            "/api/v1/",
            "/api/enterprise/",
            "/api/tenant/",
        }

        logger.info("EnhancedTenantMiddleware initialized for Epic 12 Phase 2")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with enhanced tenant context."""
        start_time = time.time()
        tenant_context: NewTenantContext | None = None

        try:
            # Skip tenant processing for exempt paths
            if self._is_exempt_path(request.url.path):
                return await call_next(request)

            # Detect tenant from request
            tenant_id = self.tenant_manager.detect_tenant_from_request(request)

            if tenant_id:
                # Create tenant context
                tenant_context = self.tenant_manager.create_tenant_context(tenant_id)

                if tenant_context:
                    # Validate tenant status
                    if tenant_context.status != TenantStatus.ACTIVE:
                        raise HTTPException(
                            status_code=503,
                            detail=f"Tenant {tenant_id} is not active (status: {tenant_context.status})"
                        )

                    # Check if tenant context is required
                    if self._requires_tenant_context(request.url.path) or self.require_tenant_for_all_requests:
                        # Process request within tenant scope
                        response = await self._process_with_tenant_scope(
                            request, call_next, tenant_context
                        )
                    else:
                        # Process without tenant scope but with context available
                        request.state.tenant_context = tenant_context
                        response = await call_next(request)

                else:
                    # Tenant context creation failed
                    if self._requires_tenant_context(request.url.path):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot create context for tenant: {tenant_id}"
                        )
                    else:
                        response = await call_next(request)

            else:
                # No tenant detected
                if self._requires_tenant_context(request.url.path) or self.require_tenant_for_all_requests:
                    raise HTTPException(
                        status_code=400,
                        detail="Tenant identification required for this endpoint"
                    )
                else:
                    response = await call_next(request)

            # Add tenant information to response headers
            if tenant_context:
                response.headers["X-Tenant-ID"] = tenant_context.tenant_id
                response.headers["X-Tenant-Name"] = tenant_context.tenant_name
                response.headers["X-Tenant-Type"] = tenant_context.tenant_type.value
                response.headers["X-Tenant-Isolation"] = tenant_context.isolation_level

            # Log request if audit logging enabled
            if self.enable_audit_logging:
                await self._log_request(request, response, tenant_context, time.time() - start_time)

            return response

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Enhanced tenant middleware error: {e}")

            # Log error if audit logging enabled
            if self.enable_audit_logging:
                await self._log_error(request, e, tenant_context, time.time() - start_time)

            # Return generic error to avoid information leakage
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )

    async def _process_with_tenant_scope(
        self,
        request: Request,
        call_next: Callable,
        tenant_context: NewTenantContext
    ) -> Response:
        """Process request within tenant scope."""
        with self.tenant_manager.tenant_scope(tenant_context.tenant_id):
            # Add tenant context to request state
            request.state.tenant_context = tenant_context

            # Add tenant metadata to request
            request.state.tenant_database = tenant_context.database_name
            request.state.tenant_resource_limits = tenant_context.resource_limits
            request.state.tenant_feature_flags = tenant_context.feature_flags

            # Handle resource management if enabled
            if self.enable_resource_tracking:
                # Check API rate limiting
                available, error = await self.resource_manager.check_resource_availability(
                    ResourceType.API_CALLS, tenant_context=tenant_context
                )
                if not available:
                    raise HTTPException(
                        status_code=429,
                        detail=f"API rate limit exceeded: {error}"
                    )

                # Process with concurrent request limiting
                async with ResourceContext(ResourceType.CONCURRENT_REQUESTS):
                    response = await call_next(request)

                # Update API call counter
                await self.resource_manager.acquire_resource(
                    ResourceType.API_CALLS, tenant_context=tenant_context
                )
            else:
                response = await call_next(request)

            return response

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from tenant processing."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    def _requires_tenant_context(self, path: str) -> bool:
        """Check if path requires tenant context."""
        return any(path.startswith(required) for required in self.tenant_required_paths)

    async def _log_request(
        self,
        request: Request,
        response: Response,
        tenant_context: NewTenantContext | None,
        duration: float
    ) -> None:
        """Log request for audit purposes."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "status_code": response.status_code,
            "duration_seconds": round(duration, 3),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }

        if tenant_context:
            log_entry.update({
                "tenant_id": tenant_context.tenant_id,
                "tenant_name": tenant_context.tenant_name,
                "tenant_type": tenant_context.tenant_type.value,
                "isolation_level": tenant_context.isolation_level,
            })

        # Log to appropriate tenant-specific logger
        audit_logger = logging.getLogger(f"audit.tenant.{tenant_context.tenant_id if tenant_context else 'system'}")
        audit_logger.info(f"API_REQUEST: {log_entry}")

    async def _log_error(
        self,
        request: Request,
        error: Exception,
        tenant_context: NewTenantContext | None,
        duration: float
    ) -> None:
        """Log error for audit purposes."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "error": str(error),
            "error_type": type(error).__name__,
            "duration_seconds": round(duration, 3),
            "client_ip": request.client.host if request.client else "unknown",
        }

        if tenant_context:
            log_entry.update({
                "tenant_id": tenant_context.tenant_id,
                "tenant_name": tenant_context.tenant_name,
                "tenant_type": tenant_context.tenant_type.value,
            })

        # Log error to appropriate tenant-specific logger
        error_logger = logging.getLogger(f"error.tenant.{tenant_context.tenant_id if tenant_context else 'system'}")
        error_logger.error(f"API_ERROR: {log_entry}")


class TenantSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware for tenant isolation enforcement."""

    def __init__(
        self,
        app,
        enable_cross_tenant_protection: bool = True,
        enable_data_access_logging: bool = True,
        blocked_cross_tenant_paths: set | None = None
    ):
        """Initialize tenant security middleware."""
        super().__init__(app)
        self.enable_cross_tenant_protection = enable_cross_tenant_protection
        self.enable_data_access_logging = enable_data_access_logging
        self.blocked_cross_tenant_paths = blocked_cross_tenant_paths or {
            "/api/v1/documents",
            "/api/v1/search",
            "/api/v1/query",
            "/api/v1/graph",
            "/api/enterprise/",
        }

        logger.info("TenantSecurityMiddleware initialized for Epic 12 Phase 2")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with security enforcement."""
        tenant_context = getattr(request.state, 'tenant_context', None)

        if not tenant_context:
            return await call_next(request)

        try:
            # Validate tenant access to requested path
            if self.enable_cross_tenant_protection:
                await self._validate_tenant_access(request, tenant_context)

            # Process request
            response = await call_next(request)

            # Log data access if enabled
            if self.enable_data_access_logging:
                await self._log_data_access(request, response, tenant_context)

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error for tenant {tenant_context.tenant_id}: {e}")
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

    async def _validate_tenant_access(self, request: Request, tenant_context: NewTenantContext) -> None:
        """Validate tenant access to requested resource."""
        # Check if path requires tenant validation
        path = request.url.path

        if any(path.startswith(blocked_path) for blocked_path in self.blocked_cross_tenant_paths):
            # Validate that any tenant_id parameters match current tenant
            query_params = dict(request.query_params)
            path_params = getattr(request.path_params, 'items', lambda: [])()

            # Check query parameters
            if 'tenant_id' in query_params:
                if query_params['tenant_id'] != tenant_context.tenant_id:
                    logger.warning(
                        f"Cross-tenant access attempt: {tenant_context.tenant_id} -> {query_params['tenant_id']}"
                    )
                    raise HTTPException(
                        status_code=403,
                        detail="Cross-tenant access denied"
                    )

            # Check path parameters
            for key, value in path_params:
                if key == 'tenant_id' and value != tenant_context.tenant_id:
                    logger.warning(
                        f"Cross-tenant access attempt via path: {tenant_context.tenant_id} -> {value}"
                    )
                    raise HTTPException(
                        status_code=403,
                        detail="Cross-tenant access denied"
                    )

    async def _log_data_access(
        self,
        request: Request,
        response: Response,
        tenant_context: NewTenantContext
    ) -> None:
        """Log data access for security audit."""
        if response.status_code < 400:  # Only log successful requests
            security_logger = logging.getLogger(f"security.tenant.{tenant_context.tenant_id}")
            security_logger.info(
                f"DATA_ACCESS: tenant={tenant_context.tenant_id} "
                f"method={request.method} path={request.url.path} "
                f"status={response.status_code} isolation={tenant_context.isolation_level}"
            )


# Helper functions for request handling
def get_tenant_from_request(request: Request) -> NewTenantContext | None:
    """Helper function to get tenant context from request."""
    return getattr(request.state, 'tenant_context', None)


def require_tenant_from_request(request: Request) -> NewTenantContext:
    """Helper function that requires tenant context from request."""
    tenant_context = get_tenant_from_request(request)
    if not tenant_context:
        raise HTTPException(
            status_code=400,
            detail="Tenant context required"
        )
    return tenant_context
