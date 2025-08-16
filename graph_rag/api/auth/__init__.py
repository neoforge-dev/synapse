"""Authentication and authorization module for Graph-RAG API."""

from .jwt_handler import JWTHandler, JWTSettings
from .models import User, UserRole, TokenData, UserCreate, UserLogin
from .dependencies import get_current_user, get_admin_user, require_auth
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