"""Authentication models and schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles with hierarchical permissions."""
    ADMIN = "admin"      # Full system access
    USER = "user"        # Normal API access
    READONLY = "readonly"  # Read-only access


class User(BaseModel):
    """User model with role-based access control."""
    id: UUID = Field(default_factory=uuid4)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime | None = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class UserCreate(BaseModel):
    """Schema for creating new users."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = Field(default=UserRole.USER)


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: UUID
    username: str
    role: UserRole
    exp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: int(v.timestamp()),
            UUID: str
        }


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: User


class APIKeyCreate(BaseModel):
    """Schema for creating API keys."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    expires_days: int | None = Field(None, ge=1, le=365)


class APIKey(BaseModel):
    """API Key model."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    key_hash: str  # Hashed version for storage
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    last_used: datetime | None = None
    is_active: bool = Field(default=True)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class APIKeyResponse(BaseModel):
    """Response when creating API key (shows actual key only once)."""
    id: UUID
    name: str
    description: str | None
    api_key: str  # Actual key - shown only on creation
    expires_at: datetime | None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }
