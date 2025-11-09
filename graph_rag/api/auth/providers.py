"""Authentication providers for user management."""

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from .jwt_handler import JWTHandler
from .models import APIKey, APIKeyCreate, User, UserCreate, UserRole
from .time_service import TimeService, default_time_service

logger = logging.getLogger(__name__)


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    def __init__(self, jwt_handler: JWTHandler, time_service: TimeService = None):
        self.jwt_handler = jwt_handler
        self.time_service = time_service or default_time_service

    @abstractmethod
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        pass

    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate user with username/password."""
        pass

    @abstractmethod
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        pass

    @abstractmethod
    async def create_api_key(self, user_id: UUID, key_data: APIKeyCreate) -> tuple[APIKey, str]:
        """Create an API key for a user. Returns (api_key_model, actual_key)."""
        pass

    @abstractmethod
    async def get_user_by_api_key(self, api_key: str) -> User | None:
        """Get user associated with an API key."""
        pass

    @abstractmethod
    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke an API key."""
        pass


class InMemoryAuthProvider(AuthProvider):
    """In-memory authentication provider for development and testing."""

    def __init__(self, jwt_handler: JWTHandler, time_service: TimeService = None):
        super().__init__(jwt_handler, time_service)
        self._users: dict[UUID, User] = {}
        self._usernames: dict[str, UUID] = {}
        self._passwords: dict[UUID, str] = {}  # user_id -> hashed_password
        self._api_keys: dict[UUID, APIKey] = {}
        self._api_key_hashes: dict[str, UUID] = {}  # key_hash -> api_key_id

        # Create default admin user
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user for initial setup."""
        admin_data = UserCreate(
            username="admin",
            email="admin@graph-rag.local",
            password="admin123",  # Should be changed in production
            role=UserRole.ADMIN
        )

        import asyncio
        try:
            # Use asyncio.run only if not already in an event loop
            asyncio.get_running_loop()
            # If we're in a loop, create the user synchronously for this init
            self._create_user_sync(admin_data)
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            asyncio.run(self.create_user(admin_data))

        logger.info("Created default admin user (username: admin, password: admin123)")

    def _create_user_sync(self, user_data: UserCreate) -> User:
        """Synchronous version for initialization."""
        user = User(
            username=user_data.username,
            email=user_data.email,
            role=user_data.role
        )

        hashed_password = self.jwt_handler.hash_password(user_data.password)

        self._users[user.id] = user
        self._usernames[user.username] = user.id
        self._passwords[user.id] = hashed_password

        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if username already exists
        if user_data.username in self._usernames:
            raise ValueError(f"Username '{user_data.username}' already exists")

        user = User(
            username=user_data.username,
            email=user_data.email,
            role=user_data.role
        )

        hashed_password = self.jwt_handler.hash_password(user_data.password)

        self._users[user.id] = user
        self._usernames[user.username] = user.id
        self._passwords[user.id] = hashed_password

        logger.info(f"Created user: {user.username} with role: {user.role}")
        return user

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        user_id = self._usernames.get(username)
        if user_id:
            return self._users.get(user_id)
        return None

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        return self._users.get(user_id)

    async def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate user with username/password."""
        user = await self.get_user_by_username(username)
        if not user or not user.is_active:
            return None

        stored_password = self._passwords.get(user.id)
        if not stored_password:
            return None

        if self.jwt_handler.verify_password(password, stored_password):
            return user

        return None

    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        user = self._users.get(user_id)
        if user:
            user.last_login = self.time_service.utcnow()

    async def create_api_key(self, user_id: UUID, key_data: APIKeyCreate) -> tuple[APIKey, str]:
        """Create an API key for a user."""
        user = self._users.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Generate API key and hash
        api_key, api_key_hash = self.jwt_handler.generate_api_key()

        # Calculate expiration
        expires_at = None
        if key_data.expires_days:
            expires_at = self.time_service.add_days(days=key_data.expires_days)

        # Create API key model
        api_key_model = APIKey(
            name=key_data.name,
            description=key_data.description,
            key_hash=api_key_hash,
            user_id=user_id,
            expires_at=expires_at
        )

        self._api_keys[api_key_model.id] = api_key_model
        self._api_key_hashes[api_key_hash] = api_key_model.id

        logger.info(f"Created API key '{key_data.name}' for user {user.username}")
        return api_key_model, api_key

    async def get_user_by_api_key(self, api_key: str) -> User | None:
        """Get user associated with an API key."""
        # Hash the provided key
        import hashlib
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        api_key_id = self._api_key_hashes.get(key_hash)
        if not api_key_id:
            return None

        api_key_model = self._api_keys.get(api_key_id)
        if not api_key_model or not api_key_model.is_active:
            return None

        # Check expiration
        if api_key_model.expires_at and self.time_service.utcnow() > api_key_model.expires_at:
            return None

        # Update last used timestamp
        api_key_model.last_used = self.time_service.utcnow()

        user = self._users.get(api_key_model.user_id)
        if user and not user.is_active:
            return None
        return user

    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke an API key."""
        api_key = self._api_keys.get(key_id)
        if api_key and api_key.user_id == user_id:
            if not api_key.is_active:
                return False  # Already revoked
            api_key.is_active = False
            logger.info(f"Revoked API key {key_id} for user {user_id}")
            return True
        return False

    async def list_user_api_keys(self, user_id: UUID) -> list[APIKey]:
        """List all API keys for a user."""
        return [
            key for key in self._api_keys.values()
            if key.user_id == user_id and key.is_active
        ]
