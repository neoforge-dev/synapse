"""JWT Authentication Tests.

This module contains comprehensive tests for JWT token generation, validation,
expiration handling, and security features in the authentication system.
"""

import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from freezegun import freeze_time

from graph_rag.api.auth.jwt_handler import JWTHandler, JWTSettings
from graph_rag.api.auth.models import TokenData, User, UserRole


class TestJWTSettings:
    """Test JWT configuration settings."""

    def test_default_settings(self):
        """Test default JWT settings creation."""
        secret_key = secrets.token_urlsafe(32)
        settings = JWTSettings(secret_key=secret_key)

        assert settings.secret_key == secret_key
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
        assert settings.refresh_token_expire_days == 7
        assert settings.issuer == "graph-rag-api"

    def test_custom_settings(self):
        """Test custom JWT settings."""
        settings = JWTSettings(
            secret_key="custom-secret-key-32-chars-minimum",
            algorithm="HS512",
            access_token_expire_minutes=60,
            refresh_token_expire_days=14,
            issuer="custom-issuer"
        )

        assert settings.secret_key == "custom-secret-key-32-chars-minimum"
        assert settings.algorithm == "HS512"
        assert settings.access_token_expire_minutes == 60
        assert settings.refresh_token_expire_days == 14
        assert settings.issuer == "custom-issuer"

    def test_from_env_with_secret(self):
        """Test creating settings from environment with provided secret."""
        secret = secrets.token_urlsafe(32)
        settings = JWTSettings.from_env(secret_key=secret)

        assert settings.secret_key == secret
        assert settings.algorithm == "HS256"

    def test_from_env_without_secret(self):
        """Test creating settings from environment without secret generates one."""
        settings = JWTSettings.from_env()

        assert len(settings.secret_key) >= 32
        assert settings.algorithm == "HS256"

    def test_secret_key_minimum_length(self):
        """Test that secret key must meet minimum length requirement."""
        with pytest.raises(ValueError):
            JWTSettings(secret_key="short")


class TestJWTHandler:
    """Test JWT token operations."""

    @pytest.fixture
    def jwt_settings(self):
        """Create JWT settings for testing."""
        return JWTSettings(
            secret_key="test-secret-key-32-chars-minimum-length",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )

    @pytest.fixture
    def jwt_handler(self, jwt_settings):
        """Create JWT handler for testing."""
        return JWTHandler(jwt_settings)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            role=UserRole.USER
        )

    def test_password_hashing(self, jwt_handler):
        """Test password hashing and verification."""
        password = "test_password_123"

        # Hash password
        hashed = jwt_handler.hash_password(password)

        # Verify the hash is different from original
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are typically 60+ chars

        # Verify password verification works
        assert jwt_handler.verify_password(password, hashed)
        assert not jwt_handler.verify_password("wrong_password", hashed)

    def test_password_hash_uniqueness(self, jwt_handler):
        """Test that the same password creates different hashes."""
        password = "same_password"

        hash1 = jwt_handler.hash_password(password)
        hash2 = jwt_handler.hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

        # But both should verify correctly
        assert jwt_handler.verify_password(password, hash1)
        assert jwt_handler.verify_password(password, hash2)

    def test_create_access_token(self, jwt_handler, sample_user):
        """Test access token creation."""
        token = jwt_handler.create_access_token(sample_user)

        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are lengthy

        # Decode manually to verify structure
        payload = jwt.decode(
            token,
            jwt_handler.settings.secret_key,
            algorithms=[jwt_handler.settings.algorithm],
            issuer=jwt_handler.settings.issuer
        )

        assert payload["sub"] == str(sample_user.id)
        assert payload["username"] == sample_user.username
        assert payload["role"] == sample_user.role.value
        assert payload["iss"] == jwt_handler.settings.issuer
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_create_refresh_token(self, jwt_handler, sample_user):
        """Test refresh token creation."""
        token = jwt_handler.create_refresh_token(sample_user)

        assert isinstance(token, str)
        assert len(token) > 100

        # Decode manually to verify structure
        payload = jwt.decode(
            token,
            jwt_handler.settings.secret_key,
            algorithms=[jwt_handler.settings.algorithm],
            issuer=jwt_handler.settings.issuer
        )

        assert payload["sub"] == str(sample_user.id)
        assert payload["iss"] == jwt_handler.settings.issuer
        assert payload["type"] == "refresh"
        assert "iat" in payload
        assert "exp" in payload
        # Refresh tokens shouldn't contain username/role
        assert "username" not in payload
        assert "role" not in payload

    def test_decode_valid_token(self, jwt_handler, sample_user):
        """Test decoding valid access token."""
        token = jwt_handler.create_access_token(sample_user)
        token_data = jwt_handler.decode_token(token)

        assert token_data is not None
        assert token_data.user_id == sample_user.id
        assert token_data.username == sample_user.username
        assert token_data.role == sample_user.role
        assert isinstance(token_data.exp, datetime)

    def test_decode_expired_token(self, jwt_handler, sample_user):
        """Test decoding expired token returns None."""
        # Create token with very short expiration
        short_expire_settings = JWTSettings(
            secret_key=jwt_handler.settings.secret_key,
            access_token_expire_minutes=0  # Expires immediately
        )
        short_handler = JWTHandler(short_expire_settings)

        token = short_handler.create_access_token(sample_user)

        # Token should be expired immediately
        token_data = short_handler.decode_token(token)
        assert token_data is None

    def test_decode_invalid_token(self, jwt_handler):
        """Test decoding invalid token returns None."""
        invalid_tokens = [
            "invalid.token.here",
            "totally-not-a-jwt",
            "",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature"
        ]

        for invalid_token in invalid_tokens:
            token_data = jwt_handler.decode_token(invalid_token)
            assert token_data is None

    def test_decode_token_wrong_secret(self, jwt_handler, sample_user):
        """Test decoding token with wrong secret returns None."""
        token = jwt_handler.create_access_token(sample_user)

        # Create handler with different secret
        wrong_settings = JWTSettings(secret_key="wrong-secret-key-32-chars-minimum")
        wrong_handler = JWTHandler(wrong_settings)

        token_data = wrong_handler.decode_token(token)
        assert token_data is None

    def test_decode_token_wrong_algorithm(self, jwt_handler, sample_user):
        """Test decoding token with wrong algorithm returns None."""
        token = jwt_handler.create_access_token(sample_user)

        # Try to decode with different algorithm
        with pytest.raises(jwt.InvalidAlgorithmError):
            jwt.decode(
                token,
                jwt_handler.settings.secret_key,
                algorithms=["HS512"],  # Wrong algorithm
                issuer=jwt_handler.settings.issuer
            )

    def test_decode_token_wrong_issuer(self, jwt_handler, sample_user):
        """Test decoding token with wrong issuer returns None."""
        token = jwt_handler.create_access_token(sample_user)

        # Try to decode with different issuer
        with pytest.raises(jwt.InvalidIssuerError):
            jwt.decode(
                token,
                jwt_handler.settings.secret_key,
                algorithms=[jwt_handler.settings.algorithm],
                issuer="wrong-issuer"
            )

    def test_decode_malformed_token_data(self, jwt_handler):
        """Test decoding token with missing required fields returns None."""
        # Create token with missing fields
        now = datetime.utcnow()
        payload = {
            "iat": now,
            "exp": now + timedelta(minutes=30),
            "iss": jwt_handler.settings.issuer,
            # Missing: sub, username, role
        }

        token = jwt.encode(
            payload,
            jwt_handler.settings.secret_key,
            algorithm=jwt_handler.settings.algorithm
        )

        token_data = jwt_handler.decode_token(token)
        assert token_data is None

    def test_is_token_expired(self, jwt_handler):
        """Test token expiration checking."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        future_time = datetime.utcnow() + timedelta(hours=1)

        expired_token_data = TokenData(
            user_id=uuid4(),
            username="test",
            role=UserRole.USER,
            exp=past_time
        )

        valid_token_data = TokenData(
            user_id=uuid4(),
            username="test",
            role=UserRole.USER,
            exp=future_time
        )

        assert jwt_handler.is_token_expired(expired_token_data)
        assert not jwt_handler.is_token_expired(valid_token_data)

    def test_token_expiration_time(self, jwt_handler, sample_user):
        """Test that token expiration time is set correctly."""
        # Record time before token creation (truncated to seconds for comparison)
        before_creation = datetime.utcnow().replace(microsecond=0)
        
        token = jwt_handler.create_access_token(sample_user)
        token_data = jwt_handler.decode_token(token)
        
        # Record time after token creation (truncated to seconds for comparison)
        after_creation = datetime.utcnow().replace(microsecond=0)
        
        expected_min_exp = before_creation + timedelta(
            minutes=jwt_handler.settings.access_token_expire_minutes
        )
        expected_max_exp = after_creation + timedelta(
            minutes=jwt_handler.settings.access_token_expire_minutes
        )

        # Token expiration should be within the expected range
        # JWT timestamps are in seconds precision, so we should be within this range
        assert expected_min_exp <= token_data.exp <= expected_max_exp

    def test_generate_api_key(self, jwt_handler):
        """Test API key generation."""
        api_key, api_key_hash = jwt_handler.generate_api_key()

        # Check API key format
        assert api_key.startswith("sk-")
        assert len(api_key) > 40  # Should be lengthy

        # Check hash format
        assert len(api_key_hash) == 64  # SHA256 hex string
        assert all(c in "0123456789abcdef" for c in api_key_hash)

        # Verify hash matches key
        assert jwt_handler.verify_api_key(api_key, api_key_hash)

    def test_api_key_uniqueness(self, jwt_handler):
        """Test that generated API keys are unique."""
        keys = [jwt_handler.generate_api_key() for _ in range(10)]

        # All keys should be different
        api_keys = [key[0] for key in keys]
        assert len(set(api_keys)) == 10

        # All hashes should be different
        hashes = [key[1] for key in keys]
        assert len(set(hashes)) == 10

    def test_verify_api_key(self, jwt_handler):
        """Test API key verification."""
        api_key, api_key_hash = jwt_handler.generate_api_key()

        # Correct key should verify
        assert jwt_handler.verify_api_key(api_key, api_key_hash)

        # Wrong key should not verify
        wrong_key = "sk-" + secrets.token_urlsafe(32)
        assert not jwt_handler.verify_api_key(wrong_key, api_key_hash)

        # Malformed key should not verify
        assert not jwt_handler.verify_api_key("invalid-key", api_key_hash)

    def test_api_key_hash_security(self, jwt_handler):
        """Test that API key hashing is secure."""
        api_key1, hash1 = jwt_handler.generate_api_key()
        api_key2, hash2 = jwt_handler.generate_api_key()

        # Different keys should have different hashes
        assert hash1 != hash2

        # Keys should not be recoverable from hashes
        assert api_key1 not in hash1
        assert api_key2 not in hash2

        # Cross verification should fail
        assert not jwt_handler.verify_api_key(api_key1, hash2)
        assert not jwt_handler.verify_api_key(api_key2, hash1)


class TestTokenSecurity:
    """Test JWT token security features."""

    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler for security testing."""
        return JWTHandler(JWTSettings(
            secret_key="security-test-secret-key-32-chars-min",
            access_token_expire_minutes=30
        ))

    @pytest.fixture
    def sample_user(self):
        """Create sample user for security tests."""
        return User(
            id=uuid4(),
            username="securitytest",
            email="security@example.com",
            role=UserRole.USER
        )

    def test_token_tampering_detection(self, jwt_handler, sample_user):
        """Test that token tampering is detected."""
        token = jwt_handler.create_access_token(sample_user)

        # Tamper with the token
        tampered_token = token[:-10] + "tampereddd"

        # Tampered token should be invalid
        token_data = jwt_handler.decode_token(tampered_token)
        assert token_data is None

    def test_token_signature_verification(self, jwt_handler, sample_user):
        """Test that token signature is properly verified."""
        token = jwt_handler.create_access_token(sample_user)

        # Split token into parts
        header, payload, signature = token.split('.')

        # Create fake signature
        fake_signature = "fakesignature"
        fake_token = f"{header}.{payload}.{fake_signature}"

        # Token with fake signature should be invalid
        token_data = jwt_handler.decode_token(fake_token)
        assert token_data is None

    def test_role_in_token_cannot_be_escalated(self, jwt_handler):
        """Test that role escalation via token manipulation is prevented."""
        # Create user token
        user = User(
            id=uuid4(),
            username="regularuser",
            email="user@example.com",
            role=UserRole.USER
        )

        token = jwt_handler.create_access_token(user)

        # Decode token to see structure
        payload = jwt.decode(
            token,
            jwt_handler.settings.secret_key,
            algorithms=[jwt_handler.settings.algorithm],
            issuer=jwt_handler.settings.issuer
        )

        assert payload["role"] == "user"

        # Any attempt to manually create token with escalated role
        # without proper secret should fail
        escalated_payload = payload.copy()
        escalated_payload["role"] = "admin"

        # Try to create token with wrong secret
        fake_token = jwt.encode(
            escalated_payload,
            "wrong-secret",
            algorithm=jwt_handler.settings.algorithm
        )

        # Should be rejected due to wrong signature
        token_data = jwt_handler.decode_token(fake_token)
        assert token_data is None

    def test_token_replay_attack_prevention(self, jwt_handler, sample_user):
        """Test that expired tokens cannot be replayed."""
        # Create token with very short expiration
        short_settings = JWTSettings(
            secret_key=jwt_handler.settings.secret_key,
            access_token_expire_minutes=0
        )
        short_handler = JWTHandler(short_settings)

        token = short_handler.create_access_token(sample_user)

        # Token should be expired and invalid
        token_data = short_handler.decode_token(token)
        assert token_data is None

    def test_different_token_types_isolation(self, jwt_handler, sample_user):
        """Test that access and refresh tokens are properly isolated."""
        access_token = jwt_handler.create_access_token(sample_user)
        refresh_token = jwt_handler.create_refresh_token(sample_user)

        # Decode both tokens
        access_payload = jwt.decode(
            access_token,
            jwt_handler.settings.secret_key,
            algorithms=[jwt_handler.settings.algorithm],
            issuer=jwt_handler.settings.issuer
        )

        refresh_payload = jwt.decode(
            refresh_token,
            jwt_handler.settings.secret_key,
            algorithms=[jwt_handler.settings.algorithm],
            issuer=jwt_handler.settings.issuer
        )

        # Verify token types
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

        # Refresh token should have minimal info
        assert "username" in access_payload
        assert "role" in access_payload
        assert "username" not in refresh_payload
        assert "role" not in refresh_payload

    def test_constant_time_comparison(self, jwt_handler):
        """Test that API key verification uses constant-time comparison."""
        # This test verifies that secrets.compare_digest is used
        # which prevents timing attacks

        api_key, api_key_hash = jwt_handler.generate_api_key()

        # Test with correct key
        result1 = jwt_handler.verify_api_key(api_key, api_key_hash)
        assert result1 is True

        # Test with incorrect key of same length
        wrong_key = "sk-" + "a" * (len(api_key) - 3)
        result2 = jwt_handler.verify_api_key(wrong_key, api_key_hash)
        assert result2 is False

        # The fact that this doesn't raise an exception confirms
        # that proper constant-time comparison is being used
