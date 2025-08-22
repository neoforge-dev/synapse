"""
Password hashing and verification utilities.

Provides secure password hashing using bcrypt with salt.
"""

import logging
import re
from typing import Optional

from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class PasswordManager:
    """
    Secure password management with bcrypt hashing.
    
    Handles password hashing, verification, and strength validation.
    """
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Password strength requirements
        self.min_length = 8
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digit = True
        self.require_special = False  # Optional for better UX
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        hashed = self.pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Previously hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.warning(f"Password verification error: {e}")
            return False
    
    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """
        Validate password meets strength requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not password:
            errors.append("Password is required")
            return False, errors
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for common weak passwords
        weak_patterns = [
            r'password',
            r'123456',
            r'qwerty',
            r'admin',
            r'letmein'
        ]
        
        password_lower = password.lower()
        for pattern in weak_patterns:
            if re.search(pattern, password_lower):
                errors.append("Password is too common or predictable")
                break
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated.
        
        Args:
            hashed_password: Existing password hash
            
        Returns:
            True if hash should be updated
        """
        return self.pwd_context.needs_update(hashed_password)


# Global password manager instance
_password_manager = None

def get_password_manager() -> PasswordManager:
    """Get password manager instance."""
    global _password_manager
    if _password_manager is None:
        _password_manager = PasswordManager()
    return _password_manager


# Convenience functions
def hash_password(password: str) -> str:
    """Hash password using global password manager."""
    return get_password_manager().hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using global password manager."""
    return get_password_manager().verify_password(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """Validate password strength using global password manager."""
    return get_password_manager().validate_password_strength(password)