"""Authentication module for TechLead AutoPilot."""

from .jwt import JWTManager, create_access_token, create_refresh_token, verify_token, get_jwt_manager
from .password import PasswordManager, hash_password, verify_password, validate_password_strength
from .dependencies import (
    get_current_user, 
    get_current_active_user,
    get_organization_from_user,
    require_organization_access,
    require_role
)

__all__ = [
    "JWTManager",
    "create_access_token",
    "create_refresh_token", 
    "verify_token",
    "get_jwt_manager",
    "PasswordManager",
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "get_current_user",
    "get_current_active_user", 
    "get_organization_from_user",
    "require_organization_access",
    "require_role"
]