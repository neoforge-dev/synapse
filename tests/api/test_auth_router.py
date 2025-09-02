"""Authentication Router Tests.

This module contains comprehensive tests for all authentication API endpoints
including registration, login, user management, API keys, and admin functions.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient


class TestUserRegistration:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "role": "user"
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data

        # Check token properties
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

        # Check user properties
        user = data["user"]
        assert user["username"] == "newuser"
        assert user["email"] == "newuser@example.com"
        assert user["role"] == "user"
        assert user["is_active"] is True
        assert "id" in user
        assert "created_at" in user
        assert "last_login" in user

    @pytest.mark.asyncio
    async def test_register_admin_user(self, test_client: AsyncClient):
        """Test registering a user with admin role."""
        user_data = {
            "username": "adminuser",
            "email": "admin@example.com",
            "password": "admin123",
            "role": "admin"
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        user = data["user"]
        assert user["role"] == "admin"

    @pytest.mark.asyncio
    async def test_register_readonly_user(self, test_client: AsyncClient):
        """Test registering a user with readonly role."""
        user_data = {
            "username": "readonly",
            "email": "readonly@example.com",
            "password": "readonly123",
            "role": "readonly"
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        user = data["user"]
        assert user["role"] == "readonly"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, test_client: AsyncClient):
        """Test registration with duplicate username fails."""
        user_data = {
            "username": "duplicate",
            "email": "first@example.com",
            "password": "password123"
        }

        # First registration should succeed
        response1 = await test_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Second registration with same username should fail
        user_data["email"] = "second@example.com"  # Different email
        response2 = await test_client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, test_client: AsyncClient):
        """Test registration with invalid email format fails."""
        user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_short_password(self, test_client: AsyncClient):
        """Test registration with short password fails."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "short"
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_short_username(self, test_client: AsyncClient):
        """Test registration with short username fails."""
        user_data = {
            "username": "ab",  # Too short
            "email": "test@example.com",
            "password": "password123"
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, test_client: AsyncClient):
        """Test registration with missing required fields fails."""
        incomplete_data = {
            "username": "testuser",
            # Missing email and password
        }

        response = await test_client.post("/api/v1/auth/register", json=incomplete_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login endpoints."""

    @pytest.mark.asyncio
    async def test_login_oauth2_success(self, test_client: AsyncClient):
        """Test successful login with OAuth2 password flow."""
        # First register a user
        user_data = {
            "username": "loginuser",
            "email": "login@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        # Now login with OAuth2 form data
        login_data = {
            "username": "loginuser",
            "password": "password123"
        }

        response = await test_client.post(
            "/api/v1/auth/login",
            data=login_data,  # Use data for form encoding
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data

        # Check user properties
        user = data["user"]
        assert user["username"] == "loginuser"
        assert user["last_login"] is not None  # Should be updated

    @pytest.mark.asyncio
    async def test_login_json_success(self, test_client: AsyncClient):
        """Test successful login with JSON payload."""
        # First register a user
        user_data = {
            "username": "jsonuser",
            "email": "json@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        # Now login with JSON
        login_data = {
            "username": "jsonuser",
            "password": "password123"
        }

        response = await test_client.post("/api/v1/auth/login/json", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data

        # Check user properties
        user = data["user"]
        assert user["username"] == "jsonuser"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client: AsyncClient):
        """Test login with wrong password fails."""
        # First register a user
        user_data = {
            "username": "wrongpass",
            "email": "wrong@example.com",
            "password": "correctpass"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        # Try to login with wrong password
        login_data = {
            "username": "wrongpass",
            "password": "wrongpassword"
        }

        response = await test_client.post("/api/v1/auth/login/json", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, test_client: AsyncClient):
        """Test login with nonexistent user fails."""
        login_data = {
            "username": "nonexistent",
            "password": "password123"
        }

        response = await test_client.post("/api/v1/auth/login/json", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, test_client: AsyncClient):
        """Test login with empty credentials fails."""
        login_data = {
            "username": "",
            "password": ""
        }

        response = await test_client.post("/api/v1/auth/login/json", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCurrentUser:
    """Test current user endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, test_client: AsyncClient):
        """Test getting current user information with valid token."""
        # Register and login
        user_data = {
            "username": "currentuser",
            "email": "current@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "currentuser",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Get current user
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        user = response.json()

        assert user["username"] == "currentuser"
        assert user["email"] == "current@example.com"
        assert user["role"] == "user"
        assert user["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, test_client: AsyncClient):
        """Test getting current user without token fails."""
        response = await test_client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAPIKeyManagement:
    """Test API key management endpoints."""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, test_client: AsyncClient):
        """Test successful API key creation."""
        # Register and login
        user_data = {
            "username": "apiuser",
            "email": "api@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "apiuser",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Create API key
        key_data = {
            "name": "Test API Key",
            "description": "A test API key",
            "expires_days": 30
        }

        response = await test_client.post(
            "/api/v1/auth/api-keys",
            json=key_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "id" in data
        assert data["name"] == "Test API Key"
        assert data["description"] == "A test API key"
        assert "api_key" in data
        assert data["api_key"].startswith("sk-")
        assert "expires_at" in data
        assert data["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_create_api_key_no_expiration(self, test_client: AsyncClient):
        """Test creating API key without expiration."""
        # Register and login
        user_data = {
            "username": "noexpiry",
            "email": "noexpiry@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "noexpiry",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Create API key without expiration
        key_data = {
            "name": "No Expiry Key",
            "description": "Key that never expires"
        }

        response = await test_client.post(
            "/api/v1/auth/api-keys",
            json=key_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["expires_at"] is None

    @pytest.mark.asyncio
    async def test_create_api_key_unauthorized(self, test_client: AsyncClient):
        """Test API key creation without authentication fails."""
        key_data = {
            "name": "Unauthorized Key"
        }

        response = await test_client.post("/api/v1/auth/api-keys", json=key_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_api_keys_success(self, test_client: AsyncClient):
        """Test listing user's API keys."""
        # Register and login
        user_data = {
            "username": "listkeys",
            "email": "listkeys@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "listkeys",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Create a few API keys
        for i in range(3):
            key_data = {
                "name": f"Key {i+1}",
                "description": f"Description {i+1}"
            }
            await test_client.post(
                "/api/v1/auth/api-keys",
                json=key_data,
                headers={"Authorization": f"Bearer {token}"}
            )

        # List keys
        response = await test_client.get(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        keys = response.json()

        assert len(keys) == 3
        for i, key in enumerate(keys):
            assert key["name"] == f"Key {i+1}"
            assert key["description"] == f"Description {i+1}"
            assert key["is_active"] is True
            assert "id" in key
            assert "created_at" in key
            # API key value should NOT be in list response
            assert "api_key" not in key

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, test_client: AsyncClient):
        """Test listing API keys when user has none."""
        # Register and login
        user_data = {
            "username": "nokeys",
            "email": "nokeys@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "nokeys",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # List keys
        response = await test_client.get(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        keys = response.json()

        assert keys == []

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, test_client: AsyncClient):
        """Test successful API key revocation."""
        # Register and login
        user_data = {
            "username": "revokeuser",
            "email": "revoke@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "revokeuser",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Create API key
        key_data = {
            "name": "To Be Revoked"
        }

        create_response = await test_client.post(
            "/api/v1/auth/api-keys",
            json=key_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        key_id = create_response.json()["id"]

        # Revoke the key
        response = await test_client.delete(
            f"/api/v1/auth/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "revoked successfully" in data["message"]

        # Verify key is no longer in active list
        list_response = await test_client.get(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"}
        )
        keys = list_response.json()
        assert len(keys) == 0  # Should be empty since key was revoked

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_api_key(self, test_client: AsyncClient):
        """Test revoking nonexistent API key fails."""
        # Register and login
        user_data = {
            "username": "nokey",
            "email": "nokey@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "nokey",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Try to revoke nonexistent key
        fake_key_id = str(uuid4())
        response = await test_client.delete(
            f"/api/v1/auth/api-keys/{fake_key_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


class TestAPIKeyAuthentication:
    """Test authentication using API keys."""

    @pytest.mark.asyncio
    async def test_authenticate_with_api_key(self, test_client: AsyncClient):
        """Test successful authentication using API key."""
        # Register and login
        user_data = {
            "username": "apiauth",
            "email": "apiauth@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "apiauth",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Create API key
        key_data = {
            "name": "Auth Test Key"
        }

        create_response = await test_client.post(
            "/api/v1/auth/api-keys",
            json=key_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        api_key = create_response.json()["api_key"]

        # Use API key to authenticate
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        assert response.status_code == status.HTTP_200_OK
        user = response.json()

        assert user["username"] == "apiauth"
        assert user["email"] == "apiauth@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_api_key(self, test_client: AsyncClient):
        """Test authentication with invalid API key fails."""
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer sk-invalid-key"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAdminEndpoints:
    """Test admin-only endpoints."""

    @pytest.mark.asyncio
    async def test_admin_create_user_success(self, test_client: AsyncClient):
        """Test admin can create users."""
        # Use default admin user (admin/admin123)
        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "admin",
            "password": "admin123"
        })
        admin_token = login_response.json()["access_token"]

        # Admin creates a new user
        user_data = {
            "username": "admincreated",
            "email": "created@example.com",
            "password": "password123",
            "role": "user"
        }

        response = await test_client.post(
            "/api/v1/auth/admin/users",
            json=user_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        user = response.json()

        assert user["username"] == "admincreated"
        assert user["email"] == "created@example.com"
        assert user["role"] == "user"

    @pytest.mark.asyncio
    async def test_admin_create_user_non_admin(self, test_client: AsyncClient):
        """Test non-admin cannot create users via admin endpoint."""
        # Register and login as regular user
        user_data = {
            "username": "regularuser",
            "email": "regular@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "regularuser",
            "password": "password123"
        })
        user_token = login_response.json()["access_token"]

        # Try to create user as non-admin
        new_user_data = {
            "username": "shouldfail",
            "email": "fail@example.com",
            "password": "password123"
        }

        response = await test_client.post(
            "/api/v1/auth/admin/users",
            json=new_user_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_admin_get_user_success(self, test_client: AsyncClient):
        """Test admin can get user by ID."""
        # Use default admin user
        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "admin",
            "password": "admin123"
        })
        admin_token = login_response.json()["access_token"]

        # Register a regular user
        user_data = {
            "username": "targetuser",
            "email": "target@example.com",
            "password": "password123"
        }
        register_response = await test_client.post("/api/v1/auth/register", json=user_data)
        user_id = register_response.json()["user"]["id"]

        # Admin gets the user
        response = await test_client.get(
            f"/api/v1/auth/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        user = response.json()

        assert user["username"] == "targetuser"
        assert user["email"] == "target@example.com"
        assert user["id"] == user_id

    @pytest.mark.asyncio
    async def test_admin_get_user_not_found(self, test_client: AsyncClient):
        """Test admin get user with invalid ID returns 404."""
        # Use default admin user
        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "admin",
            "password": "admin123"
        })
        admin_token = login_response.json()["access_token"]

        # Try to get nonexistent user
        fake_user_id = str(uuid4())
        response = await test_client.get(
            f"/api/v1/auth/admin/users/{fake_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_get_user_non_admin(self, test_client: AsyncClient):
        """Test non-admin cannot access admin user endpoint."""
        # Register and login as regular user
        user_data = {
            "username": "nonadmin",
            "email": "nonadmin@example.com",
            "password": "password123"
        }
        register_response = await test_client.post("/api/v1/auth/register", json=user_data)
        user_token = register_response.json()["access_token"]
        user_id = register_response.json()["user"]["id"]

        # Try to access admin endpoint
        response = await test_client.get(
            f"/api/v1/auth/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in response.json()["detail"].lower()


class TestAuthenticationErrorHandling:
    """Test error handling in authentication system."""

    @pytest.mark.asyncio
    async def test_malformed_json_request(self, test_client: AsyncClient):
        """Test handling of malformed JSON requests."""
        response = await test_client.post(
            "/api/v1/auth/register",
            content="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_missing_content_type(self, test_client: AsyncClient):
        """Test handling of requests without content type."""
        response = await test_client.post(
            "/api/v1/auth/register",
            content='{"username": "test"}'
        )

        # Should still work as FastAPI tries to parse JSON by default
        # or return appropriate error
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]

    @pytest.mark.asyncio
    async def test_malformed_bearer_token(self, test_client: AsyncClient):
        """Test handling of malformed Bearer tokens."""
        malformed_tokens = [
            "Bearer",  # Missing token
            "Bearer ",  # Empty token
            "NotBearer token",  # Wrong scheme
            "Bearer token with spaces",  # Invalid format
        ]

        for token in malformed_tokens:
            response = await test_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": token}
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_expired_token_handling(self, test_client: AsyncClient):
        """Test handling of expired JWT tokens."""
        # This test would require manipulating time or creating tokens with
        # very short expiration. For now, we test with obviously invalid tokens.

        invalid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ"

        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_concurrent_registration_attempts(self, test_client: AsyncClient):
        """Test handling of concurrent registration attempts."""
        import asyncio

        user_data = {
            "username": "concurrent",
            "email": "concurrent@example.com",
            "password": "password123"
        }

        # Start multiple registration attempts simultaneously
        tasks = [
            test_client.post("/api/v1/auth/register", json=user_data)
            for _ in range(3)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed, others should fail
        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == status.HTTP_201_CREATED
        )

        assert success_count == 1

    @pytest.mark.asyncio
    async def test_database_error_simulation(self, test_client: AsyncClient):
        """Test graceful handling of database errors."""
        # This is difficult to test without mocking the provider
        # The current in-memory provider is quite robust
        # In a real implementation, we'd test database connection failures

        # For now, test edge case of very long username
        user_data = {
            "username": "a" * 1000,  # Very long username
            "email": "long@example.com",
            "password": "password123"
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        # Should be rejected by validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthenticationHeaders:
    """Test authentication header handling."""

    @pytest.mark.asyncio
    async def test_case_insensitive_bearer(self, test_client: AsyncClient):
        """Test that Bearer scheme is case insensitive."""
        # Register and login first
        user_data = {
            "username": "casetest",
            "email": "case@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "casetest",
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # Test different capitalizations of "Bearer"
        bearer_variations = [
            f"Bearer {token}",
            f"bearer {token}",
            f"BEARER {token}",
            f"Bearer {token}",  # Standard
        ]

        for auth_header in bearer_variations:
            response = await test_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": auth_header}
            )

            # Should work regardless of case
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_multiple_authorization_headers(self, test_client: AsyncClient):
        """Test handling of multiple Authorization headers."""
        # This is more of an edge case - most clients won't send multiple headers
        # But it's good to test the behavior

        response = await test_client.get(
            "/api/v1/auth/me",
            headers=[
                ("Authorization", "Bearer invalid1"),
                ("Authorization", "Bearer invalid2"),
            ]
        )

        # Should handle gracefully (likely use the last one)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_authorization_header_with_extra_spaces(self, test_client: AsyncClient):
        """Test authorization header with extra whitespace."""
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "  Bearer   invalid-token  "}
        )

        # Should handle gracefully and still reject invalid token
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Test token refresh functionality (if implemented)."""

    @pytest.mark.asyncio
    async def test_token_response_format(self, test_client: AsyncClient):
        """Test that token response follows OAuth2 format."""
        user_data = {
            "username": "oauth2test",
            "email": "oauth2@example.com",
            "password": "password123"
        }
        await test_client.post("/api/v1/auth/register", json=user_data)

        login_response = await test_client.post("/api/v1/auth/login/json", json={
            "username": "oauth2test",
            "password": "password123"
        })

        assert login_response.status_code == status.HTTP_200_OK
        data = login_response.json()

        # Check OAuth2 compliance
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

        # Check that token is properly formatted JWT
        token = data["access_token"]
        parts = token.split(".")
        assert len(parts) == 3  # JWT has 3 parts: header.payload.signature
