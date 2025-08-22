"""Authentication module for TechLead AutoPilot."""

from .jwt import JWTManager, create_access_token, create_refresh_token, verify_token
from .password import PasswordManager, hash_password, verify_password
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
    "PasswordManager",
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_current_active_user", 
    "get_organization_from_user",
    "require_organization_access",
    "require_role"
]