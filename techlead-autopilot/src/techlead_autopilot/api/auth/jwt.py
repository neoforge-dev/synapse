"""
JWT token management for authentication.

Provides secure access and refresh token handling with blacklisting support.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Union
from uuid import UUID, uuid4

from jose import JWTError, jwt
from pydantic import BaseModel

from ...config import get_settings

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """Token payload data structure."""
    user_id: str
    organization_id: str
    email: str
    role: str
    token_type: str  # "access" or "refresh"
    jti: str  # JWT ID for blacklisting
    exp: int
    iat: int


class JWTManager:
    """
    JWT token manager with blacklisting support.
    
    Handles access tokens (30 min) and refresh tokens (7 days) with
    secure token invalidation for logout.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.algorithm = "HS256"
        self.blacklisted_tokens = set()  # In production, use Redis
        
    def create_access_token(
        self, 
        user_id: Union[str, UUID], 
        organization_id: Union[str, UUID],
        email: str,
        role: str = "member"
    ) -> str:
        """
        Create a new access token.
        
        Args:
            user_id: User ID
            organization_id: Organization ID for multi-tenancy
            email: User email
            role: User role (owner, admin, member)
            
        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=self.settings.access_token_expire_minutes)
        token_id = str(uuid4())
        
        payload = {
            "user_id": str(user_id),
            "organization_id": str(organization_id),
            "email": email,
            "role": role,
            "token_type": "access",
            "jti": token_id,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp())
        }
        
        token = jwt.encode(payload, self.settings.secret_key, algorithm=self.algorithm)
        
        logger.info(f"Created access token for user {user_id}")
        return token
    
    def create_refresh_token(
        self,
        user_id: Union[str, UUID],
        organization_id: Union[str, UUID],
        email: str,
        role: str = "member"
    ) -> str:
        """
        Create a new refresh token.
        
        Args:
            user_id: User ID
            organization_id: Organization ID
            email: User email
            role: User role
            
        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expires = now + timedelta(days=self.settings.refresh_token_expire_days)
        token_id = str(uuid4())
        
        payload = {
            "user_id": str(user_id),
            "organization_id": str(organization_id),
            "email": email,
            "role": role,
            "token_type": "refresh",
            "jti": token_id,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp())
        }
        
        token = jwt.encode(payload, self.settings.secret_key, algorithm=self.algorithm)
        
        logger.info(f"Created refresh token for user {user_id}")
        return token
    
    def verify_token(self, token: str, expected_type: str = "access") -> Optional[TokenData]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            expected_type: Expected token type ("access" or "refresh")
            
        Returns:
            TokenData if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.settings.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Check token type
            token_type = payload.get("token_type")
            if token_type != expected_type:
                logger.warning(f"Token type mismatch: expected {expected_type}, got {token_type}")
                return None
            
            # Check if token is blacklisted
            token_id = payload.get("jti")
            if token_id in self.blacklisted_tokens:
                logger.warning(f"Token {token_id} is blacklisted")
                return None
            
            # Validate required fields
            required_fields = ["user_id", "organization_id", "email", "role", "jti", "exp", "iat"]
            for field in required_fields:
                if field not in payload:
                    logger.warning(f"Token missing required field: {field}")
                    return None
            
            return TokenData(**payload)
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def blacklist_token(self, token: str) -> bool:
        """
        Blacklist a token (for logout).
        
        Args:
            token: JWT token to blacklist
            
        Returns:
            True if successfully blacklisted
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Allow expired tokens to be blacklisted
            )
            
            token_id = payload.get("jti")
            if token_id:
                self.blacklisted_tokens.add(token_id)
                logger.info(f"Blacklisted token {token_id}")
                return True
                
        except JWTError as e:
            logger.warning(f"Failed to blacklist token: {e}")
            
        return False
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate new access token from valid refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dict with new access_token and refresh_token, or None if invalid
        """
        token_data = self.verify_token(refresh_token, expected_type="refresh")
        if not token_data:
            return None
        
        # Create new tokens
        new_access_token = self.create_access_token(
            user_id=token_data.user_id,
            organization_id=token_data.organization_id,
            email=token_data.email,
            role=token_data.role
        )
        
        new_refresh_token = self.create_refresh_token(
            user_id=token_data.user_id,
            organization_id=token_data.organization_id,
            email=token_data.email,
            role=token_data.role
        )
        
        # Blacklist old refresh token
        self.blacklist_token(refresh_token)
        
        logger.info(f"Refreshed tokens for user {token_data.user_id}")
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }


# Global JWT manager instance
_jwt_manager = None

def get_jwt_manager() -> JWTManager:
    """Get JWT manager instance."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


# Convenience functions
def create_access_token(user_id: Union[str, UUID], organization_id: Union[str, UUID], 
                       email: str, role: str = "member") -> str:
    """Create access token using global JWT manager."""
    return get_jwt_manager().create_access_token(user_id, organization_id, email, role)


def create_refresh_token(user_id: Union[str, UUID], organization_id: Union[str, UUID], 
                        email: str, role: str = "member") -> str:
    """Create refresh token using global JWT manager."""
    return get_jwt_manager().create_refresh_token(user_id, organization_id, email, role)


def verify_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """Verify token using global JWT manager."""
    return get_jwt_manager().verify_token(token, expected_type)