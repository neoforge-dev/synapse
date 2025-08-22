"""
Authentication dependencies for FastAPI.

Provides dependency injection for protected routes with role-based access control.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .jwt import verify_token, TokenData
from ...infrastructure.database import get_db_session
from ...infrastructure.database.models import User, Organization

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Authentication error exception."""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Authorization error exception."""
    
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Extract and verify JWT token from request.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Verified token data
        
    Raises:
        AuthenticationError: If token is invalid
    """
    token = credentials.credentials
    token_data = verify_token(token, expected_type="access")
    
    if token_data is None:
        logger.warning("Invalid or expired token")
        raise AuthenticationError("Invalid or expired token")
    
    return token_data


async def get_current_user(
    token_data: TokenData = Depends(get_token_data),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Get current authenticated user from database.
    
    Args:
        token_data: Verified token data
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        AuthenticationError: If user not found
    """
    try:
        # Query user from database
        result = await db.execute(
            select(User)
            .where(User.id == token_data.user_id)
            .where(User.organization_id == token_data.organization_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            logger.warning(f"User {token_data.user_id} not found in database")
            raise AuthenticationError("User not found")
        
        return user
        
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise AuthenticationError("Authentication failed")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Active user object
        
    Raises:
        AuthenticationError: If user is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user {current_user.id} attempted access")
        raise AuthenticationError("Account is inactive")
    
    if current_user.deleted_at is not None:
        logger.warning(f"Deleted user {current_user.id} attempted access")
        raise AuthenticationError("Account not found")
    
    return current_user


async def get_organization_from_user(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> Organization:
    """
    Get organization for current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User's organization
        
    Raises:
        AuthenticationError: If organization not found
    """
    try:
        result = await db.execute(
            select(Organization)
            .where(Organization.id == current_user.organization_id)
            .where(Organization.deleted_at.is_(None))
        )
        organization = result.scalar_one_or_none()
        
        if organization is None:
            logger.error(f"Organization {current_user.organization_id} not found")
            raise AuthenticationError("Organization not found")
        
        return organization
        
    except Exception as e:
        logger.error(f"Error fetching organization: {e}")
        raise AuthenticationError("Organization access failed")


def require_organization_access(organization_id: Optional[str] = None):
    """
    Dependency factory to require specific organization access.
    
    Args:
        organization_id: Required organization ID (if None, uses user's org)
        
    Returns:
        Dependency function
    """
    async def _check_organization_access(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if organization_id is not None and str(current_user.organization_id) != organization_id:
            logger.warning(
                f"User {current_user.id} attempted access to org {organization_id}, "
                f"but belongs to {current_user.organization_id}"
            )
            raise AuthorizationError("Organization access denied")
        
        return current_user
    
    return _check_organization_access


def require_role(required_roles: list[str]):
    """
    Dependency factory to require specific user roles.
    
    Args:
        required_roles: List of required roles (owner, admin, member)
        
    Returns:
        Dependency function
    """
    async def _check_role(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in required_roles:
            logger.warning(
                f"User {current_user.id} with role {current_user.role} "
                f"attempted access requiring roles: {required_roles}"
            )
            raise AuthorizationError(f"Role '{current_user.role}' insufficient. Required: {required_roles}")
        
        return current_user
    
    return _check_role


def require_owner_or_admin():
    """Dependency to require owner or admin role."""
    return require_role(["owner", "admin"])


def require_owner():
    """Dependency to require owner role."""
    return require_role(["owner"])


# Optional authentication (for public endpoints with optional auth)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    
    Useful for endpoints that have optional authentication.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current user if authenticated, None otherwise
    """
    if credentials is None:
        return None
    
    try:
        token_data = verify_token(credentials.credentials, expected_type="access")
        if token_data is None:
            return None
        
        result = await db.execute(
            select(User)
            .where(User.id == token_data.user_id)
            .where(User.organization_id == token_data.organization_id)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        return user
        
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None