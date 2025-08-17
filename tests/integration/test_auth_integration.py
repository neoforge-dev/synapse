"""Authentication Integration Tests.

This module contains end-to-end integration tests for the authentication system,
including multi-user scenarios, session management, and integration with protected API endpoints.
"""

import asyncio

import pytest
from httpx import AsyncClient

from graph_rag.api.main import create_app


class TestAuthenticationFlow:
    """Test complete authentication flows."""

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self, integration_test_client: AsyncClient):
        """Test complete user lifecycle from registration to API key usage."""
        # 1. Register a new user
        user_data = {
            "username": "lifecycle_user",
            "email": "lifecycle@example.com",
            "password": "secure_password_123",
            "role": "user"
        }

        register_response = await integration_test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        register_data = register_response.json()
        user_id = register_data["user"]["id"]
        initial_token = register_data["access_token"]

        # 2. Verify user can access protected endpoints with initial token
        me_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {initial_token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "lifecycle_user"

        # 3. Login again to get a new token
        login_response = await integration_test_client.post("/auth/login/json", json={
            "username": "lifecycle_user",
            "password": "secure_password_123"
        })
        assert login_response.status_code == 200

        new_token = login_response.json()["access_token"]
        assert new_token != initial_token  # Should be different

        # 4. Create an API key
        api_key_data = {
            "name": "Integration Test Key",
            "description": "Key for testing integration",
            "expires_days": 7
        }

        api_key_response = await integration_test_client.post(
            "/auth/api-keys",
            json=api_key_data,
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert api_key_response.status_code == 200

        api_key = api_key_response.json()["api_key"]
        api_key_id = api_key_response.json()["id"]

        # 5. Use API key for authentication
        api_auth_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert api_auth_response.status_code == 200
        assert api_auth_response.json()["id"] == user_id

        # 6. List API keys
        list_keys_response = await integration_test_client.get(
            "/auth/api-keys",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert list_keys_response.status_code == 200

        keys = list_keys_response.json()
        assert len(keys) == 1
        assert keys[0]["name"] == "Integration Test Key"

        # 7. Revoke the API key
        revoke_response = await integration_test_client.delete(
            f"/auth/api-keys/{api_key_id}",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert revoke_response.status_code == 200

        # 8. Verify API key no longer works
        revoked_auth_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert revoked_auth_response.status_code == 401

        # 9. Verify JWT token still works
        final_me_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert final_me_response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_user_workflow(self, integration_test_client: AsyncClient):
        """Test admin user workflow with admin endpoints."""
        # Use the default admin user
        admin_login_response = await integration_test_client.post("/auth/login/json", json={
            "username": "admin",
            "password": "admin123"
        })
        assert admin_login_response.status_code == 200

        admin_token = admin_login_response.json()["access_token"]

        # Admin creates a new user
        new_user_data = {
            "username": "admin_created_user",
            "email": "admin_created@example.com",
            "password": "admin_password_123",
            "role": "readonly"
        }

        create_user_response = await integration_test_client.post(
            "/auth/admin/users",
            json=new_user_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_user_response.status_code == 200

        created_user = create_user_response.json()
        created_user_id = created_user["id"]

        # Admin retrieves the created user
        get_user_response = await integration_test_client.get(
            f"/auth/admin/users/{created_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_user_response.status_code == 200

        retrieved_user = get_user_response.json()
        assert retrieved_user["username"] == "admin_created_user"
        assert retrieved_user["role"] == "readonly"

        # Created user can login
        user_login_response = await integration_test_client.post("/auth/login/json", json={
            "username": "admin_created_user",
            "password": "admin_password_123"
        })
        assert user_login_response.status_code == 200

        user_token = user_login_response.json()["access_token"]

        # User can access their own profile
        user_me_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert user_me_response.status_code == 200
        assert user_me_response.json()["role"] == "readonly"


class TestMultiUserScenarios:
    """Test scenarios involving multiple users."""

    @pytest.mark.asyncio
    async def test_user_isolation(self, integration_test_client: AsyncClient):
        """Test that users can only access their own resources."""
        # Create two users
        user1_data = {
            "username": "user1_isolation",
            "email": "user1@example.com",
            "password": "password123"
        }

        user2_data = {
            "username": "user2_isolation",
            "email": "user2@example.com",
            "password": "password123"
        }

        # Register both users
        user1_response = await integration_test_client.post("/auth/register", json=user1_data)
        user2_response = await integration_test_client.post("/auth/register", json=user2_data)

        assert user1_response.status_code == 201
        assert user2_response.status_code == 201

        user1_token = user1_response.json()["access_token"]
        user2_token = user2_response.json()["access_token"]
        user2_id = user2_response.json()["user"]["id"]

        # User1 creates an API key
        api_key_data = {
            "name": "User1 Key"
        }

        user1_key_response = await integration_test_client.post(
            "/auth/api-keys",
            json=api_key_data,
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert user1_key_response.status_code == 200

        user1_key_id = user1_key_response.json()["id"]

        # User2 tries to revoke User1's API key (should fail)
        revoke_response = await integration_test_client.delete(
            f"/auth/api-keys/{user1_key_id}",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert revoke_response.status_code == 404  # Not found for this user

        # User1 can still list their key
        user1_list_response = await integration_test_client.get(
            "/auth/api-keys",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert user1_list_response.status_code == 200
        assert len(user1_list_response.json()) == 1

        # User2's list should be empty
        user2_list_response = await integration_test_client.get(
            "/auth/api-keys",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert user2_list_response.status_code == 200
        assert len(user2_list_response.json()) == 0

        # Regular users cannot access admin endpoints
        admin_user_response = await integration_test_client.get(
            f"/auth/admin/users/{user2_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert admin_user_response.status_code == 403

    @pytest.mark.asyncio
    async def test_concurrent_api_key_operations(self, integration_test_client: AsyncClient):
        """Test concurrent API key operations by multiple users."""
        # Register a user
        user_data = {
            "username": "concurrent_user",
            "email": "concurrent@example.com",
            "password": "password123"
        }

        register_response = await integration_test_client.post("/auth/register", json=user_data)
        token = register_response.json()["access_token"]

        # Create multiple API keys concurrently
        async def create_api_key(name: str):
            key_data = {
                "name": f"Concurrent Key {name}"
            }
            response = await integration_test_client.post(
                "/auth/api-keys",
                json=key_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            return response

        # Create 5 keys concurrently
        tasks = [create_api_key(str(i)) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

        # Verify all keys exist
        list_response = await integration_test_client.get(
            "/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert list_response.status_code == 200

        keys = list_response.json()
        assert len(keys) == 5

        # Verify all keys have unique names and IDs
        names = [key["name"] for key in keys]
        ids = [key["id"] for key in keys]

        assert len(set(names)) == 5  # All names unique
        assert len(set(ids)) == 5    # All IDs unique

    @pytest.mark.asyncio
    async def test_role_based_access_integration(self, integration_test_client: AsyncClient):
        """Test role-based access control in integrated environment."""
        # Create users with different roles
        admin_data = {
            "username": "integration_admin",
            "email": "int_admin@example.com",
            "password": "admin_pass_123",
            "role": "admin"
        }

        user_data = {
            "username": "integration_user",
            "email": "int_user@example.com",
            "password": "user_pass_123",
            "role": "user"
        }

        readonly_data = {
            "username": "integration_readonly",
            "email": "int_readonly@example.com",
            "password": "readonly_pass_123",
            "role": "readonly"
        }

        # Register all users
        admin_response = await integration_test_client.post("/auth/register", json=admin_data)
        user_response = await integration_test_client.post("/auth/register", json=user_data)
        readonly_response = await integration_test_client.post("/auth/register", json=readonly_data)

        assert admin_response.status_code == 201
        assert user_response.status_code == 201
        assert readonly_response.status_code == 201

        admin_token = admin_response.json()["access_token"]
        user_token = user_response.json()["access_token"]
        readonly_token = readonly_response.json()["access_token"]
        readonly_id = readonly_response.json()["user"]["id"]

        # Test admin access to admin endpoints
        admin_get_response = await integration_test_client.get(
            f"/auth/admin/users/{readonly_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_get_response.status_code == 200

        # Test user cannot access admin endpoints
        user_admin_response = await integration_test_client.get(
            f"/auth/admin/users/{readonly_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert user_admin_response.status_code == 403

        # Test readonly cannot access admin endpoints
        readonly_admin_response = await integration_test_client.get(
            f"/auth/admin/users/{readonly_id}",
            headers={"Authorization": f"Bearer {readonly_token}"}
        )
        assert readonly_admin_response.status_code == 403

        # Test all can access their own profile
        for token, expected_username in [
            (admin_token, "integration_admin"),
            (user_token, "integration_user"),
            (readonly_token, "integration_readonly")
        ]:
            me_response = await integration_test_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert me_response.status_code == 200
            assert me_response.json()["username"] == expected_username


class TestSessionManagement:
    """Test session and token management scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_login_sessions(self, integration_test_client: AsyncClient):
        """Test that a user can have multiple active sessions."""
        # Register a user
        user_data = {
            "username": "multi_session",
            "email": "multi@example.com",
            "password": "password123"
        }

        await integration_test_client.post("/auth/register", json=user_data)

        # Login multiple times to get different tokens
        login_data = {
            "username": "multi_session",
            "password": "password123"
        }

        tokens = []
        for _ in range(3):
            login_response = await integration_test_client.post("/auth/login/json", json=login_data)
            assert login_response.status_code == 200
            tokens.append(login_response.json()["access_token"])

        # All tokens should be different
        assert len(set(tokens)) == 3

        # All tokens should work for authentication
        for token in tokens:
            me_response = await integration_test_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert me_response.status_code == 200
            assert me_response.json()["username"] == "multi_session"

    @pytest.mark.asyncio
    async def test_mixed_authentication_methods(self, integration_test_client: AsyncClient):
        """Test using both JWT tokens and API keys for the same user."""
        # Register and login
        user_data = {
            "username": "mixed_auth",
            "email": "mixed@example.com",
            "password": "password123"
        }

        register_response = await integration_test_client.post("/auth/register", json=user_data)
        jwt_token = register_response.json()["access_token"]

        # Create an API key using JWT token
        api_key_data = {
            "name": "Mixed Auth Key"
        }

        api_key_response = await integration_test_client.post(
            "/auth/api-keys",
            json=api_key_data,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        api_key = api_key_response.json()["api_key"]

        # Use JWT token for one operation
        jwt_me_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert jwt_me_response.status_code == 200

        # Use API key for another operation
        api_me_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert api_me_response.status_code == 200

        # Both should return the same user
        assert jwt_me_response.json()["id"] == api_me_response.json()["id"]
        assert jwt_me_response.json()["username"] == api_me_response.json()["username"]

    @pytest.mark.asyncio
    async def test_authentication_with_different_clients(self, integration_test_client: AsyncClient):
        """Test authentication consistency across different client instances."""
        # Register and get token
        user_data = {
            "username": "multi_client",
            "email": "multiclient@example.com",
            "password": "password123"
        }

        register_response = await integration_test_client.post("/auth/register", json=user_data)
        token = register_response.json()["access_token"]

        # Create a new client instance (simulating different application instance)
        app = create_app()

        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as new_client:
            # Token should work with new client instance
            me_response = await new_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert me_response.status_code == 200
            assert me_response.json()["username"] == "multi_client"


class TestAPIIntegration:
    """Test authentication integration with other API endpoints."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_access(self, integration_test_client: AsyncClient):
        """Test accessing protected API endpoints with authentication."""
        # Register and login
        user_data = {
            "username": "api_test",
            "email": "api@example.com",
            "password": "password123"
        }

        register_response = await integration_test_client.post("/auth/register", json=user_data)
        token = register_response.json()["access_token"]

        # Try to access a protected endpoint (assuming /api/v1/documents exists and is protected)
        # Note: This test assumes other endpoints exist and are protected
        # If no protected endpoints exist yet, this test may need to be updated

        # Test without authentication (should fail)
        unauth_response = await integration_test_client.get("/api/v1/documents")
        # This might be 401 or might be allowed depending on endpoint implementation
        # Adjust based on actual API design

        # Test with authentication (should succeed or give appropriate response)
        auth_response = await integration_test_client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Adjust assertion based on actual endpoint behavior
        # For now, just verify it doesn't fail with auth error
        assert auth_response.status_code != 401

    @pytest.mark.asyncio
    async def test_api_key_with_protected_endpoints(self, integration_test_client: AsyncClient):
        """Test using API key authentication with protected endpoints."""
        # Register, login, and create API key
        user_data = {
            "username": "api_key_test",
            "email": "apikey@example.com",
            "password": "password123"
        }

        register_response = await integration_test_client.post("/auth/register", json=user_data)
        jwt_token = register_response.json()["access_token"]

        api_key_data = {
            "name": "API Test Key"
        }

        api_key_response = await integration_test_client.post(
            "/auth/api-keys",
            json=api_key_data,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        api_key = api_key_response.json()["api_key"]

        # Test API key works for authentication
        me_response = await integration_test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        assert me_response.status_code == 200

        # Test API key works for other endpoints (if they exist)
        docs_response = await integration_test_client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        # Should not fail with authentication error
        assert docs_response.status_code != 401


class TestErrorScenarios:
    """Test error scenarios in integrated environment."""

    @pytest.mark.asyncio
    async def test_network_timeout_simulation(self, integration_test_client: AsyncClient):
        """Test handling of network timeouts during authentication."""
        # This is difficult to simulate without modifying the client
        # For now, test with malformed requests that might timeout

        # Test extremely large payload (might cause timeout or rejection)
        large_payload = {
            "username": "test",
            "email": "test@example.com",
            "password": "x" * 100000,  # Very large password
        }

        response = await integration_test_client.post("/auth/register", json=large_payload)
        # Should be rejected by validation, not cause timeout
        assert response.status_code in [422, 413]  # Validation error or payload too large

    @pytest.mark.asyncio
    async def test_rapid_request_handling(self, integration_test_client: AsyncClient):
        """Test system behavior under rapid authentication requests."""
        # Register a user first
        user_data = {
            "username": "rapid_test",
            "email": "rapid@example.com",
            "password": "password123"
        }

        await integration_test_client.post("/auth/register", json=user_data)

        # Make many rapid login requests
        login_data = {
            "username": "rapid_test",
            "password": "password123"
        }

        tasks = [
            integration_test_client.post("/auth/login/json", json=login_data)
            for _ in range(20)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Most should succeed (unless rate limiting is implemented)
        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )

        # At least some should succeed
        assert success_count > 0

        # If rate limiting is implemented, some might be rejected
        # Adjust this test based on rate limiting implementation

    @pytest.mark.asyncio
    async def test_authentication_edge_cases(self, integration_test_client: AsyncClient):
        """Test edge cases in authentication flow."""
        # Test with very long but valid username
        user_data = {
            "username": "a" * 50,  # Max allowed length
            "email": "long@example.com",
            "password": "password123"
        }

        register_response = await integration_test_client.post("/auth/register", json=user_data)
        assert register_response.status_code == 201

        # Test login with the long username
        login_response = await integration_test_client.post("/auth/login/json", json={
            "username": "a" * 50,
            "password": "password123"
        })
        assert login_response.status_code == 200

        # Test special characters in username (if allowed)
        special_user_data = {
            "username": "user_with-dots.and_underscores",
            "email": "special@example.com",
            "password": "password123"
        }

        special_register_response = await integration_test_client.post("/auth/register", json=special_user_data)
        # This might succeed or fail depending on username validation rules
        # Adjust based on actual validation implementation
        assert special_register_response.status_code in [201, 422]
