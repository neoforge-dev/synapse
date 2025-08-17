"""JWT token handling for authentication."""

import hashlib
import secrets
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from .models import TokenData, User, UserRole


class JWTSettings(BaseModel):
    """JWT configuration settings."""
    secret_key: str = Field(..., min_length=32)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    issuer: str = Field(default="graph-rag-api")

    @classmethod
    def from_env(cls, secret_key: str | None = None) -> "JWTSettings":
        """Create settings from environment or generate secure defaults."""
        if not secret_key:
            # Generate a secure random key for development
            secret_key = secrets.token_urlsafe(32)

        return cls(secret_key=secret_key)


class JWTHandler:
    """Handles JWT token operations with secure defaults."""

    def __init__(self, settings: JWTSettings):
        self.settings = settings
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        """Hash a password securely."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user: User) -> str:
        """Create a JWT access token for a user."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.settings.access_token_expire_minutes)

        payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "iat": now,
            "exp": expire,
            "iss": self.settings.issuer,
            "type": "access"
        }

        return jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create a JWT refresh token for a user."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.settings.refresh_token_expire_days)

        payload = {
            "sub": str(user.id),
            "iat": now,
            "exp": expire,
            "iss": self.settings.issuer,
            "type": "refresh"
        }

        return jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.algorithm)

    def decode_token(self, token: str) -> TokenData | None:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.algorithm],
                issuer=self.settings.issuer
            )

            # Extract user information
            user_id = payload.get("sub")
            username = payload.get("username")
            role = payload.get("role")
            exp = payload.get("exp")

            if not all([user_id, username, role, exp]):
                return None

            return TokenData(
                user_id=user_id,
                username=username,
                role=UserRole(role),
                exp=datetime.fromtimestamp(exp)
            )

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except ValueError:
            return None

    def generate_api_key(self) -> tuple[str, str]:
        """Generate a new API key and its hash.
        
        Returns:
            tuple: (api_key, api_key_hash)
        """
        # Generate a secure random API key
        api_key = f"sk-{secrets.token_urlsafe(32)}"

        # Hash the key for storage
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        return api_key, api_key_hash

    def verify_api_key(self, api_key: str, stored_hash: str) -> bool:
        """Verify an API key against its stored hash."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return secrets.compare_digest(key_hash, stored_hash)

    def is_token_expired(self, token_data: TokenData) -> bool:
        """Check if a token is expired."""
        return datetime.utcnow() > token_data.exp
