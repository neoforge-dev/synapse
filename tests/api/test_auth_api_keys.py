"""API Key Authentication Tests.

This module contains comprehensive tests for API key generation, authentication,
expiration handling, revocation, and hash-based storage validation.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from graph_rag.api.auth.jwt_handler import JWTHandler, JWTSettings
from graph_rag.api.auth.models import APIKey, APIKeyCreate, User, UserRole
from graph_rag.api.auth.providers import InMemoryAuthProvider
from graph_rag.api.auth.time_service import FixedTimeService


class TestAPIKeyGeneration:
    """Test API key generation functionality."""

    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler for testing."""
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        return JWTHandler(settings)

    def test_generate_api_key_format(self, jwt_handler):
        """Test that generated API keys have correct format."""
        api_key, api_key_hash = jwt_handler.generate_api_key()

        # Check API key format
        assert api_key.startswith("sk-")
        assert len(api_key) > 40  # Should be sk- + 32+ base64url chars

        # Check that it contains only valid base64url characters after prefix
        key_part = api_key[3:]  # Remove "sk-" prefix
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in key_part)

    def test_generate_api_key_hash_format(self, jwt_handler):
        """Test that API key hashes have correct format."""
        api_key, api_key_hash = jwt_handler.generate_api_key()

        # Check hash format - should be SHA256 hex
        assert len(api_key_hash) == 64
        assert all(c in "0123456789abcdef" for c in api_key_hash)

        # Verify hash is actually SHA256 of the key
        expected_hash = hashlib.sha256(api_key.encode()).hexdigest()
        assert api_key_hash == expected_hash

    def test_api_key_uniqueness(self, jwt_handler):
        """Test that each generated API key is unique."""
        keys = []
        hashes = []

        for _ in range(100):  # Generate many keys to check uniqueness
            api_key, api_key_hash = jwt_handler.generate_api_key()
            keys.append(api_key)
            hashes.append(api_key_hash)

        # All keys should be unique
        assert len(set(keys)) == 100
        assert len(set(hashes)) == 100

    def test_api_key_entropy(self, jwt_handler):
        """Test that API keys have sufficient entropy."""
        api_key, _ = jwt_handler.generate_api_key()

        # Remove prefix for entropy calculation
        key_data = api_key[3:]

        # Basic entropy check - should have varied characters
        unique_chars = set(key_data)
        assert len(unique_chars) > 10  # Should use many different characters

        # Should not be predictable patterns
        assert not all(c == key_data[0] for c in key_data)  # Not all same char
        assert key_data != key_data[::-1]  # Not palindrome (very unlikely)


class TestAPIKeyVerification:
    """Test API key verification functionality."""

    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler for testing."""
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        return JWTHandler(settings)

    def test_verify_valid_api_key(self, jwt_handler):
        """Test verification of valid API key."""
        api_key, api_key_hash = jwt_handler.generate_api_key()

        # Valid key should verify
        assert jwt_handler.verify_api_key(api_key, api_key_hash)

    def test_verify_invalid_api_key(self, jwt_handler):
        """Test verification rejects invalid API keys."""
        _, api_key_hash = jwt_handler.generate_api_key()

        invalid_keys = [
            "sk-invalid-key-here",
            "sk-" + "a" * 43,  # Wrong content
            "wrong-prefix-" + secrets.token_urlsafe(32),
            "",
            "not-an-api-key",
            "sk-",  # Just prefix
        ]

        for invalid_key in invalid_keys:
            assert not jwt_handler.verify_api_key(invalid_key, api_key_hash)

    def test_verify_with_wrong_hash(self, jwt_handler):
        """Test that verification fails with wrong hash."""
        api_key, _ = jwt_handler.generate_api_key()
        wrong_hash = "a" * 64  # Valid format but wrong hash

        assert not jwt_handler.verify_api_key(api_key, wrong_hash)

    def test_verify_timing_attack_resistance(self, jwt_handler):
        """Test that verification uses constant-time comparison."""
        api_key, api_key_hash = jwt_handler.generate_api_key()

        # This should use secrets.compare_digest internally
        # We can't directly test timing, but we can verify behavior consistency

        # Correct verification
        assert jwt_handler.verify_api_key(api_key, api_key_hash)

        # Various incorrect verifications should all return False consistently
        wrong_keys = [
            api_key[:-1] + "x",  # One char different
            api_key[:-10] + "x" * 10,  # Multiple chars different
            "sk-" + "x" * (len(api_key) - 3),  # Completely different but same length
        ]

        for wrong_key in wrong_keys:
            assert not jwt_handler.verify_api_key(wrong_key, api_key_hash)


class TestAPIKeyProvider:
    """Test API key functionality in the auth provider."""

    @pytest.fixture
    def auth_provider(self):
        """Create auth provider for testing."""
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)
        return InMemoryAuthProvider(jwt_handler)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            role=UserRole.USER
        )

    @pytest.mark.asyncio
    async def test_create_api_key_basic(self, auth_provider, sample_user):
        """Test basic API key creation."""
        # Add user to provider
        auth_provider._users[sample_user.id] = sample_user

        key_data = APIKeyCreate(
            name="Test Key",
            description="A test API key"
        )

        api_key_model, actual_key = await auth_provider.create_api_key(
            sample_user.id, key_data
        )

        # Check API key model
        assert isinstance(api_key_model, APIKey)
        assert api_key_model.name == "Test Key"
        assert api_key_model.description == "A test API key"
        assert api_key_model.user_id == sample_user.id
        assert api_key_model.is_active is True
        assert api_key_model.expires_at is None  # No expiration set
        assert isinstance(api_key_model.created_at, datetime)

        # Check actual key
        assert actual_key.startswith("sk-")
        assert len(actual_key) > 40

        # Verify key can be used to get user
        retrieved_user = await auth_provider.get_user_by_api_key(actual_key)
        assert retrieved_user.id == sample_user.id

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self, auth_provider, sample_user):
        """Test API key creation with expiration."""
        auth_provider._users[sample_user.id] = sample_user

        key_data = APIKeyCreate(
            name="Expiring Key",
            description="Key that expires",
            expires_days=30
        )

        api_key_model, actual_key = await auth_provider.create_api_key(
            sample_user.id, key_data
        )

        # Check expiration is set correctly
        assert api_key_model.expires_at is not None
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        # Allow small variance
        assert abs((api_key_model.expires_at - expected_expiry).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_create_api_key_nonexistent_user(self, auth_provider):
        """Test API key creation for nonexistent user fails."""
        nonexistent_user_id = uuid4()

        key_data = APIKeyCreate(name="Test Key")

        with pytest.raises(ValueError, match="User not found"):
            await auth_provider.create_api_key(nonexistent_user_id, key_data)

    @pytest.mark.asyncio
    async def test_get_user_by_api_key_success(self, auth_provider, sample_user):
        """Test successful user retrieval by API key."""
        auth_provider._users[sample_user.id] = sample_user

        key_data = APIKeyCreate(name="Test Key")
        _, actual_key = await auth_provider.create_api_key(sample_user.id, key_data)

        retrieved_user = await auth_provider.get_user_by_api_key(actual_key)

        assert retrieved_user is not None
        assert retrieved_user.id == sample_user.id
        assert retrieved_user.username == sample_user.username

    @pytest.mark.asyncio
    async def test_get_user_by_invalid_api_key(self, auth_provider):
        """Test user retrieval with invalid API key returns None."""
        invalid_keys = [
            "sk-invalid-key-here",
            "not-an-api-key",
            "",
            "sk-" + "a" * 43,
        ]

        for invalid_key in invalid_keys:
            user = await auth_provider.get_user_by_api_key(invalid_key)
            assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_expired_api_key(self, sample_user):
        """Test that expired API keys return None."""
        # Create auth provider with fixed time service
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)
        
        # Set initial time
        start_time = datetime(2024, 1, 1)
        time_service = FixedTimeService(start_time)
        auth_provider = InMemoryAuthProvider(jwt_handler, time_service)
        auth_provider._users[sample_user.id] = sample_user

        # Create key that expires in 1 day from start_time
        key_data = APIKeyCreate(name="Expired Key", expires_days=1)
        _, actual_key = await auth_provider.create_api_key(sample_user.id, key_data)

        # Key should work initially
        user = await auth_provider.get_user_by_api_key(actual_key)
        assert user is not None

        # Advance time past expiration (10 days later)
        time_service.advance_days(10)
        
        # Key should now be expired
        user = await auth_provider.get_user_by_api_key(actual_key)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_revoked_api_key(self, auth_provider, sample_user):
        """Test that revoked API keys return None."""
        auth_provider._users[sample_user.id] = sample_user

        key_data = APIKeyCreate(name="To Be Revoked")
        api_key_model, actual_key = await auth_provider.create_api_key(
            sample_user.id, key_data
        )

        # Key should work initially
        user = await auth_provider.get_user_by_api_key(actual_key)
        assert user is not None

        # Revoke the key
        success = await auth_provider.revoke_api_key(sample_user.id, api_key_model.id)
        assert success is True

        # Key should no longer work
        user = await auth_provider.get_user_by_api_key(actual_key)
        assert user is None

    @pytest.mark.asyncio
    async def test_last_used_timestamp_update(self, sample_user):
        """Test that last_used timestamp is updated when key is used."""
        # Create auth provider with fixed time service
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)
        
        # Set fixed time
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        time_service = FixedTimeService(fixed_time)
        auth_provider = InMemoryAuthProvider(jwt_handler, time_service)
        auth_provider._users[sample_user.id] = sample_user

        key_data = APIKeyCreate(name="Usage Tracking Key")
        api_key_model, actual_key = await auth_provider.create_api_key(
            sample_user.id, key_data
        )

        # Initially last_used should be None
        assert api_key_model.last_used is None

        # Use the key
        user = await auth_provider.get_user_by_api_key(actual_key)
        assert user is not None

        # Check that last_used was updated
        updated_key = auth_provider._api_keys[api_key_model.id]
        assert updated_key.last_used is not None
        assert updated_key.last_used == fixed_time


class TestAPIKeyRevocation:
    """Test API key revocation functionality."""

    @pytest.fixture
    def auth_provider(self):
        """Create auth provider for testing."""
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)
        return InMemoryAuthProvider(jwt_handler)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            role=UserRole.USER
        )

    @pytest.mark.asyncio
    async def test_revoke_valid_api_key(self, auth_provider, sample_user):
        """Test successful API key revocation."""
        auth_provider._users[sample_user.id] = sample_user

        key_data = APIKeyCreate(name="To Revoke")
        api_key_model, actual_key = await auth_provider.create_api_key(
            sample_user.id, key_data
        )

        # Key should be active initially
        assert api_key_model.is_active is True

        # Revoke the key
        success = await auth_provider.revoke_api_key(sample_user.id, api_key_model.id)
        assert success is True

        # Key should be marked as inactive
        updated_key = auth_provider._api_keys[api_key_model.id]
        assert updated_key.is_active is False

        # Key should no longer authenticate
        user = await auth_provider.get_user_by_api_key(actual_key)
        assert user is None

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_api_key(self, auth_provider, sample_user):
        """Test revoking nonexistent API key returns False."""
        nonexistent_key_id = uuid4()

        success = await auth_provider.revoke_api_key(sample_user.id, nonexistent_key_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_revoke_api_key_wrong_user(self, auth_provider):
        """Test that users cannot revoke other users' API keys."""
        # Create two users
        user1 = User(id=uuid4(), username="user1", email="user1@example.com")
        user2 = User(id=uuid4(), username="user2", email="user2@example.com")

        auth_provider._users[user1.id] = user1
        auth_provider._users[user2.id] = user2

        # User1 creates API key
        key_data = APIKeyCreate(name="User1 Key")
        api_key_model, _ = await auth_provider.create_api_key(user1.id, key_data)

        # User2 tries to revoke User1's key
        success = await auth_provider.revoke_api_key(user2.id, api_key_model.id)
        assert success is False

        # Key should still be active
        updated_key = auth_provider._api_keys[api_key_model.id]
        assert updated_key.is_active is True

    @pytest.mark.asyncio
    async def test_revoke_already_revoked_key(self, auth_provider, sample_user):
        """Test revoking an already revoked key."""
        auth_provider._users[sample_user.id] = sample_user

        key_data = APIKeyCreate(name="To Revoke Twice")
        api_key_model, _ = await auth_provider.create_api_key(sample_user.id, key_data)

        # Revoke the key first time
        success1 = await auth_provider.revoke_api_key(sample_user.id, api_key_model.id)
        assert success1 is True

        # Try to revoke again
        success2 = await auth_provider.revoke_api_key(sample_user.id, api_key_model.id)
        assert success2 is False  # Should return False as key is already inactive


class TestAPIKeyListing:
    """Test API key listing functionality."""

    @pytest.fixture
    def auth_provider(self):
        """Create auth provider for testing."""
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)
        return InMemoryAuthProvider(jwt_handler)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            role=UserRole.USER
        )

    @pytest.mark.asyncio
    async def test_list_user_api_keys_empty(self, auth_provider, sample_user):
        """Test listing API keys for user with no keys."""
        auth_provider._users[sample_user.id] = sample_user

        keys = await auth_provider.list_user_api_keys(sample_user.id)
        assert keys == []

    @pytest.mark.asyncio
    async def test_list_user_api_keys_multiple(self, auth_provider, sample_user):
        """Test listing multiple API keys for a user."""
        auth_provider._users[sample_user.id] = sample_user

        # Create multiple keys
        key_names = ["Key 1", "Key 2", "Key 3"]
        created_keys = []

        for name in key_names:
            key_data = APIKeyCreate(name=name)
            api_key_model, _ = await auth_provider.create_api_key(sample_user.id, key_data)
            created_keys.append(api_key_model)

        # List keys
        listed_keys = await auth_provider.list_user_api_keys(sample_user.id)

        assert len(listed_keys) == 3

        # Check that all created keys are in the list
        listed_names = {key.name for key in listed_keys}
        assert listed_names == set(key_names)

        # Check that all keys belong to the user
        assert all(key.user_id == sample_user.id for key in listed_keys)
        assert all(key.is_active for key in listed_keys)

    @pytest.mark.asyncio
    async def test_list_user_api_keys_excludes_revoked(self, auth_provider, sample_user):
        """Test that revoked keys are excluded from listing."""
        auth_provider._users[sample_user.id] = sample_user

        # Create multiple keys
        key_data1 = APIKeyCreate(name="Active Key")
        key_data2 = APIKeyCreate(name="To Be Revoked")

        api_key1, _ = await auth_provider.create_api_key(sample_user.id, key_data1)
        api_key2, _ = await auth_provider.create_api_key(sample_user.id, key_data2)

        # Initially should see both keys
        keys = await auth_provider.list_user_api_keys(sample_user.id)
        assert len(keys) == 2

        # Revoke one key
        await auth_provider.revoke_api_key(sample_user.id, api_key2.id)

        # Should now see only the active key
        keys = await auth_provider.list_user_api_keys(sample_user.id)
        assert len(keys) == 1
        assert keys[0].name == "Active Key"
        assert keys[0].is_active is True

    @pytest.mark.asyncio
    async def test_list_user_api_keys_isolation(self, auth_provider):
        """Test that users only see their own API keys."""
        # Create two users
        user1 = User(id=uuid4(), username="user1", email="user1@example.com")
        user2 = User(id=uuid4(), username="user2", email="user2@example.com")

        auth_provider._users[user1.id] = user1
        auth_provider._users[user2.id] = user2

        # Each user creates keys
        key_data1 = APIKeyCreate(name="User1 Key")
        key_data2 = APIKeyCreate(name="User2 Key")

        await auth_provider.create_api_key(user1.id, key_data1)
        await auth_provider.create_api_key(user2.id, key_data2)

        # Each user should only see their own keys
        user1_keys = await auth_provider.list_user_api_keys(user1.id)
        user2_keys = await auth_provider.list_user_api_keys(user2.id)

        assert len(user1_keys) == 1
        assert len(user2_keys) == 1
        assert user1_keys[0].name == "User1 Key"
        assert user2_keys[0].name == "User2 Key"
        assert user1_keys[0].user_id == user1.id
        assert user2_keys[0].user_id == user2.id


class TestAPIKeyEdgeCases:
    """Test edge cases and error conditions for API keys."""

    @pytest.fixture
    def auth_provider(self):
        """Create auth provider for testing."""
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)
        return InMemoryAuthProvider(jwt_handler)

    @pytest.mark.asyncio
    async def test_api_key_name_validation(self, auth_provider):
        """Test API key name validation through the model."""
        user = User(id=uuid4(), username="test", email="test@example.com")
        auth_provider._users[user.id] = user

        # Empty name should be rejected by Pydantic model
        with pytest.raises(ValueError):
            APIKeyCreate(name="")

        # Very long name should be rejected
        with pytest.raises(ValueError):
            APIKeyCreate(name="x" * 101)  # Max is 100

    @pytest.mark.asyncio
    async def test_api_key_description_validation(self, auth_provider):
        """Test API key description validation."""
        user = User(id=uuid4(), username="test", email="test@example.com")
        auth_provider._users[user.id] = user

        # Valid description
        key_data = APIKeyCreate(
            name="Test Key",
            description="A" * 500  # Max is 500
        )

        api_key_model, _ = await auth_provider.create_api_key(user.id, key_data)
        assert len(api_key_model.description) == 500

        # Too long description should be rejected by Pydantic
        with pytest.raises(ValueError):
            APIKeyCreate(
                name="Test Key",
                description="A" * 501  # Over limit
            )

    @pytest.mark.asyncio
    async def test_api_key_expiration_validation(self, auth_provider):
        """Test API key expiration validation."""
        user = User(id=uuid4(), username="test", email="test@example.com")
        auth_provider._users[user.id] = user

        # Valid expiration
        key_data = APIKeyCreate(name="Test Key", expires_days=365)  # Max is 365
        api_key_model, _ = await auth_provider.create_api_key(user.id, key_data)
        assert api_key_model.expires_at is not None

        # Invalid expiration should be rejected by Pydantic
        with pytest.raises(ValueError):
            APIKeyCreate(name="Test Key", expires_days=0)  # Min is 1

        with pytest.raises(ValueError):
            APIKeyCreate(name="Test Key", expires_days=366)  # Max is 365

    @pytest.mark.asyncio
    async def test_api_key_hash_collision_resistance(self, auth_provider):
        """Test that hash collisions are extremely unlikely."""
        # This is more of a theoretical test since SHA256 collisions are
        # computationally infeasible, but we can test the implementation

        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)

        # Generate many API keys and ensure no hash collisions
        hashes = set()
        for _ in range(1000):
            _, api_key_hash = jwt_handler.generate_api_key()
            assert api_key_hash not in hashes, "Hash collision detected!"
            hashes.add(api_key_hash)

    @pytest.mark.asyncio
    async def test_api_key_inactive_user(self, auth_provider):
        """Test API key behavior with inactive user."""
        user = User(
            id=uuid4(),
            username="test",
            email="test@example.com",
            is_active=False  # Inactive user
        )
        auth_provider._users[user.id] = user

        # Should still be able to create key for inactive user
        key_data = APIKeyCreate(name="Test Key")
        _, actual_key = await auth_provider.create_api_key(user.id, key_data)

        # But authentication should fail due to inactive user
        retrieved_user = await auth_provider.get_user_by_api_key(actual_key)
        assert retrieved_user is None  # Should return None for inactive user
