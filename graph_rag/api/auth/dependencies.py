"""FastAPI authentication dependencies."""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...config import Settings, get_settings
from .jwt_handler import JWTHandler, JWTSettings
from .models import User, UserRole
from .providers import AuthProvider, InMemoryAuthProvider
from .enterprise_providers import EnterpriseAuthProvider

logger = logging.getLogger(__name__)

# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)


def get_jwt_settings(settings: Settings = Depends(get_settings)) -> JWTSettings:
    """Get JWT settings from application configuration."""
    # Get JWT secret from environment or use a default for development
    secret = "dev-secret-key-change-in-production-32-chars-min"  # Default

    if hasattr(settings, 'jwt_secret_key') and settings.jwt_secret_key:
        secret = settings.jwt_secret_key.get_secret_value()
        logger.info("Using configured JWT secret key")
    else:
        logger.warning("No JWT_SECRET_KEY configured, using development default")

    return JWTSettings.from_env(secret_key=secret)


# Global singletons for auth components
_jwt_handler_instance = None
_auth_provider_instance = None

def get_jwt_handler(jwt_settings: JWTSettings = Depends(get_jwt_settings)) -> JWTHandler:
    """Get JWT handler instance (singleton)."""
    global _jwt_handler_instance
    if _jwt_handler_instance is None:
        _jwt_handler_instance = JWTHandler(jwt_settings)
        logger.info("Created singleton JWTHandler instance")
    return _jwt_handler_instance

def get_auth_provider(
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    settings: Settings = Depends(get_settings)
) -> AuthProvider:
    """Get authentication provider instance (singleton)."""
    global _auth_provider_instance
    if _auth_provider_instance is None:
        # Choose provider based on enterprise authentication setting
        if getattr(settings, 'enable_enterprise_auth', False):
            _auth_provider_instance = EnterpriseAuthProvider(jwt_handler)
            logger.info("Created singleton EnterpriseAuthProvider instance")
        else:
            _auth_provider_instance = InMemoryAuthProvider(jwt_handler)
            logger.info("Created singleton InMemoryAuthProvider instance")
    return _auth_provider_instance


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_provider: AuthProvider = Depends(get_auth_provider),
    jwt_handler: JWTHandler = Depends(get_jwt_handler)
) -> User | None:
    """Get current user from JWT token (optional - returns None if not authenticated)."""
    if not credentials:
        return None

    token = credentials.credentials

    # Try JWT token first
    token_data = jwt_handler.decode_token(token)
    if token_data and not jwt_handler.is_token_expired(token_data):
        user = await auth_provider.get_user_by_id(token_data.user_id)
        if user and user.is_active:
            return user

    # Try API key authentication
    if token.startswith("sk-"):
        user = await auth_provider.get_user_by_api_key(token)
        if user and user.is_active:
            return user

    return None


async def get_current_user(
    user: User | None = Depends(get_current_user_optional)
) -> User:
    """Get current authenticated user (required)."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role for access."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


def require_auth(
    user: User = Depends(get_current_user)
) -> User:
    """Simple dependency to require authentication."""
    return user


def require_role(required_role: UserRole):
    """Create a dependency that requires a specific role or higher."""

    def role_checker(user: User = Depends(get_current_user)) -> User:
        # Role hierarchy: ADMIN > USER > READONLY
        role_levels = {
            UserRole.READONLY: 1,
            UserRole.USER: 2,
            UserRole.ADMIN: 3
        }

        user_level = role_levels.get(user.role, 0)
        required_level = role_levels.get(required_role, 999)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' or higher required"
            )

        return user

    return role_checker


# Convenience dependencies for different role levels
require_user_role = require_role(UserRole.USER)
require_admin_role = require_role(UserRole.ADMIN)
