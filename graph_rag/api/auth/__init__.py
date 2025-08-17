"""Authentication and authorization module for Graph-RAG API."""

from .dependencies import get_admin_user, get_current_user, require_auth
from .jwt_handler import JWTHandler, JWTSettings
from .models import TokenData, User, UserCreate, UserLogin, UserRole
from .providers import AuthProvider, InMemoryAuthProvider

__all__ = [
    "JWTHandler",
    "JWTSettings",
    "User",
    "UserRole",
    "TokenData",
    "UserCreate",
    "UserLogin",
    "get_current_user",
    "get_admin_user",
    "require_auth",
    "AuthProvider",
    "InMemoryAuthProvider",
]
