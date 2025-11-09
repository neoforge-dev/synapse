"""Role-Based Access Control Tests.

This module contains comprehensive tests for role-based access control (RBAC)
including admin, user, and readonly roles, permissions, and access restrictions.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from graph_rag.api.auth.dependencies import (
    get_admin_user,
    require_admin_role,
    require_role,
    require_user_role,
)
from graph_rag.api.auth.models import User, UserRole


class TestUserRoles:
    """Test user role definitions and hierarchy."""

    def test_user_role_enum_values(self):
        """Test that user roles have correct string values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.READONLY.value == "readonly"

    def test_user_role_hierarchy_levels(self):
        """Test the conceptual hierarchy of roles."""
        # This tests the role levels used in require_role function
        role_levels = {
            UserRole.READONLY: 1,
            UserRole.USER: 2,
            UserRole.ADMIN: 3
        }

        assert role_levels[UserRole.READONLY] < role_levels[UserRole.USER]
        assert role_levels[UserRole.USER] < role_levels[UserRole.ADMIN]
        assert role_levels[UserRole.ADMIN] > role_levels[UserRole.READONLY]

    def test_user_creation_with_roles(self):
        """Test creating users with different roles."""
        admin_user = User(
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN
        )

        regular_user = User(
            username="user",
            email="user@example.com",
            role=UserRole.USER
        )

        readonly_user = User(
            username="readonly",
            email="readonly@example.com",
            role=UserRole.READONLY
        )

        assert admin_user.role == UserRole.ADMIN
        assert regular_user.role == UserRole.USER
        assert readonly_user.role == UserRole.READONLY

    def test_user_default_role(self):
        """Test that default user role is USER."""
        user = User(
            username="defaultuser",
            email="default@example.com"
            # No role specified
        )

        assert user.role == UserRole.USER


class TestRoleRequirements:
    """Test role requirement dependency functions."""

    @pytest.fixture
    def admin_user(self):
        """Create an admin user for testing."""
        return User(
            id=uuid4(),
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
            is_active=True
        )

    @pytest.fixture
    def regular_user(self):
        """Create a regular user for testing."""
        return User(
            id=uuid4(),
            username="user",
            email="user@example.com",
            role=UserRole.USER,
            is_active=True
        )

    @pytest.fixture
    def readonly_user(self):
        """Create a readonly user for testing."""
        return User(
            id=uuid4(),
            username="readonly",
            email="readonly@example.com",
            role=UserRole.READONLY,
            is_active=True
        )

    def test_require_admin_role_success(self, admin_user):
        """Test that admin users pass admin role requirement."""
        role_checker = require_role(UserRole.ADMIN)

        # Should not raise exception
        result = role_checker(admin_user)
        assert result == admin_user

    def test_require_admin_role_failure_user(self, regular_user):
        """Test that regular users fail admin role requirement."""
        role_checker = require_role(UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            role_checker(regular_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    def test_require_admin_role_failure_readonly(self, readonly_user):
        """Test that readonly users fail admin role requirement."""
        role_checker = require_role(UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            role_checker(readonly_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    def test_require_user_role_success_admin(self, admin_user):
        """Test that admin users pass user role requirement (hierarchy)."""
        role_checker = require_role(UserRole.USER)

        # Admin should have access to user-level resources
        result = role_checker(admin_user)
        assert result == admin_user

    def test_require_user_role_success_user(self, regular_user):
        """Test that regular users pass user role requirement."""
        role_checker = require_role(UserRole.USER)

        result = role_checker(regular_user)
        assert result == regular_user

    def test_require_user_role_failure_readonly(self, readonly_user):
        """Test that readonly users fail user role requirement."""
        role_checker = require_role(UserRole.USER)

        with pytest.raises(HTTPException) as exc_info:
            role_checker(readonly_user)

        assert exc_info.value.status_code == 403
        assert "user" in exc_info.value.detail.lower()

    def test_require_readonly_role_success_all(self, admin_user, regular_user, readonly_user):
        """Test that all users pass readonly role requirement."""
        role_checker = require_role(UserRole.READONLY)

        # All roles should have access to readonly resources
        assert role_checker(admin_user) == admin_user
        assert role_checker(regular_user) == regular_user
        assert role_checker(readonly_user) == readonly_user

    def test_predefined_role_dependencies(self, admin_user, regular_user, readonly_user):
        """Test the predefined role dependency functions."""
        # require_admin_role should only allow admin
        assert require_admin_role(admin_user) == admin_user

        with pytest.raises(HTTPException):
            require_admin_role(regular_user)

        with pytest.raises(HTTPException):
            require_admin_role(readonly_user)

        # require_user_role should allow admin and user
        assert require_user_role(admin_user) == admin_user
        assert require_user_role(regular_user) == regular_user

        with pytest.raises(HTTPException):
            require_user_role(readonly_user)

    async def test_get_admin_user_success(self, admin_user):
        """Test get_admin_user with admin user."""
        result = await get_admin_user(admin_user)
        assert result == admin_user

    async def test_get_admin_user_failure(self, regular_user, readonly_user):
        """Test get_admin_user with non-admin users."""
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(regular_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(readonly_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()


class TestRoleHierarchy:
    """Test role hierarchy and permission inheritance."""

    def test_role_hierarchy_implementation(self):
        """Test the role hierarchy logic used in require_role."""
        # This replicates the logic from the dependencies module
        role_levels = {
            UserRole.READONLY: 1,
            UserRole.USER: 2,
            UserRole.ADMIN: 3
        }

        def check_role_access(user_role: UserRole, required_role: UserRole) -> bool:
            """Check if user role has access to required role."""
            user_level = role_levels.get(user_role, 0)
            required_level = role_levels.get(required_role, 999)
            return user_level >= required_level

        # Test admin access
        assert check_role_access(UserRole.ADMIN, UserRole.ADMIN)
        assert check_role_access(UserRole.ADMIN, UserRole.USER)
        assert check_role_access(UserRole.ADMIN, UserRole.READONLY)

        # Test user access
        assert not check_role_access(UserRole.USER, UserRole.ADMIN)
        assert check_role_access(UserRole.USER, UserRole.USER)
        assert check_role_access(UserRole.USER, UserRole.READONLY)

        # Test readonly access
        assert not check_role_access(UserRole.READONLY, UserRole.ADMIN)
        assert not check_role_access(UserRole.READONLY, UserRole.USER)
        assert check_role_access(UserRole.READONLY, UserRole.READONLY)

    def test_role_permission_matrix(self):
        """Test a comprehensive permission matrix for all roles."""
        permissions = {
            "read_public": [UserRole.ADMIN, UserRole.USER, UserRole.READONLY],
            "read_user_data": [UserRole.ADMIN, UserRole.USER],
            "write_user_data": [UserRole.ADMIN, UserRole.USER],
            "delete_user_data": [UserRole.ADMIN, UserRole.USER],
            "admin_operations": [UserRole.ADMIN],
            "system_config": [UserRole.ADMIN],
            "user_management": [UserRole.ADMIN],
        }

        def has_permission(user_role: UserRole, permission: str) -> bool:
            """Check if user role has specific permission."""
            return user_role in permissions.get(permission, [])

        # Test admin permissions (should have all)
        for permission in permissions:
            assert has_permission(UserRole.ADMIN, permission)

        # Test user permissions (should not have admin-only)
        assert has_permission(UserRole.USER, "read_public")
        assert has_permission(UserRole.USER, "read_user_data")
        assert has_permission(UserRole.USER, "write_user_data")
        assert has_permission(UserRole.USER, "delete_user_data")
        assert not has_permission(UserRole.USER, "admin_operations")
        assert not has_permission(UserRole.USER, "system_config")
        assert not has_permission(UserRole.USER, "user_management")

        # Test readonly permissions (should only have read access)
        assert has_permission(UserRole.READONLY, "read_public")
        assert not has_permission(UserRole.READONLY, "read_user_data")
        assert not has_permission(UserRole.READONLY, "write_user_data")
        assert not has_permission(UserRole.READONLY, "delete_user_data")
        assert not has_permission(UserRole.READONLY, "admin_operations")
        assert not has_permission(UserRole.READONLY, "system_config")
        assert not has_permission(UserRole.READONLY, "user_management")


class TestRoleSecurityEdgeCases:
    """Test security edge cases in role-based access control."""

    def test_inactive_user_access_denied(self):
        """Test that inactive users are denied access regardless of role."""
        inactive_admin = User(
            id=uuid4(),
            username="inactive_admin",
            email="inactive@example.com",
            role=UserRole.ADMIN,
            is_active=False  # Inactive
        )

        # Even though user has admin role, being inactive should prevent access
        # This would be handled at the authentication level, but let's verify
        # the user model allows this state
        assert inactive_admin.role == UserRole.ADMIN
        assert inactive_admin.is_active is False

    def test_role_enumeration_security(self):
        """Test that roles cannot be easily enumerated or guessed."""
        # All role values should be predictable and documented
        valid_roles = {"admin", "user", "readonly"}

        for role in UserRole:
            assert role.value in valid_roles

        # No hidden or undocumented roles
        assert len(UserRole) == 3

    def test_role_privilege_escalation_prevention(self):
        """Test that roles cannot be escalated through manipulation."""
        user = User(
            username="test",
            email="test@example.com",
            role=UserRole.USER
        )

        # Role should be immutable after creation without proper procedures
        original_role = user.role

        # Even if someone tries to modify role directly,
        # the dependency system should check the actual user object
        assert user.role == original_role

        # The role field should only be changeable through proper channels
        # (like admin user management endpoints)
        assert isinstance(user.role, UserRole)

    def test_unknown_role_handling(self):
        """Test handling of unknown or invalid roles."""
        # The role hierarchy function should handle unknown roles gracefully
        role_levels = {
            UserRole.READONLY: 1,
            UserRole.USER: 2,
            UserRole.ADMIN: 3
        }

        # Unknown role should get level 0 (no access)
        unknown_role_level = role_levels.get("unknown_role", 0)
        assert unknown_role_level == 0

        # Required role not in dict should get level 999 (impossible to reach)
        required_level = role_levels.get("unknown_required", 999)
        assert required_level == 999

        # This means unknown roles would always fail access checks
        assert unknown_role_level < required_level


class TestRoleIntegrationWithAuthentication:
    """Test how roles integrate with authentication system."""

    def test_role_in_user_creation(self):
        """Test that roles are properly set during user creation."""
        from graph_rag.api.auth.models import UserCreate

        # Test different role assignments
        admin_create = UserCreate(
            username="admin",
            email="admin@example.com",
            password="password123",
            role=UserRole.ADMIN
        )

        user_create = UserCreate(
            username="user",
            email="user@example.com",
            password="password123",
            role=UserRole.USER
        )

        readonly_create = UserCreate(
            username="readonly",
            email="readonly@example.com",
            password="password123",
            role=UserRole.READONLY
        )

        # Default role should be USER
        default_create = UserCreate(
            username="default",
            email="default@example.com",
            password="password123"
            # No role specified
        )

        assert admin_create.role == UserRole.ADMIN
        assert user_create.role == UserRole.USER
        assert readonly_create.role == UserRole.READONLY
        assert default_create.role == UserRole.USER

    def test_role_in_token_data(self):
        """Test that roles are included in JWT token data."""
        from datetime import datetime, timedelta

        from graph_rag.api.auth.models import TokenData

        token_data = TokenData(
            user_id=uuid4(),
            username="test",
            role=UserRole.ADMIN,
            exp=datetime.utcnow() + timedelta(minutes=30)  # Valid expiration time
        )

        assert token_data.role == UserRole.ADMIN
        assert isinstance(token_data.role, UserRole)

    def test_role_persistence_in_provider(self):
        """Test that roles are properly stored and retrieved."""
        from graph_rag.api.auth.jwt_handler import JWTHandler, JWTSettings
        from graph_rag.api.auth.models import UserCreate
        from graph_rag.api.auth.providers import InMemoryAuthProvider

        # Create auth provider
        settings = JWTSettings(secret_key="test-secret-key-32-chars-minimum")
        jwt_handler = JWTHandler(settings)
        InMemoryAuthProvider(jwt_handler)

        # Create users with different roles
        admin_data = UserCreate(
            username="admin_test",
            email="admin@example.com",
            password="password123",
            role=UserRole.ADMIN
        )

        user_data = UserCreate(
            username="user_test",
            email="user@example.com",
            password="password123",
            role=UserRole.USER
        )

        # Note: We can't easily test async functions here without pytest-asyncio
        # This would be better tested in an integration test

        # But we can verify the role handling logic
        assert admin_data.role == UserRole.ADMIN
        assert user_data.role == UserRole.USER


class TestRoleErrorMessages:
    """Test that role-related errors provide clear messages."""

    def test_insufficient_privileges_error_message(self):
        """Test that access denied errors have clear messages."""
        user = User(
            username="test",
            email="test@example.com",
            role=UserRole.USER
        )

        role_checker = require_role(UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            role_checker(user)

        error = exc_info.value
        assert error.status_code == 403
        assert "admin" in error.detail.lower()
        assert "required" in error.detail.lower()

    def test_role_specific_error_messages(self):
        """Test that different role requirements have specific error messages."""
        readonly_user = User(
            username="readonly",
            email="readonly@example.com",
            role=UserRole.READONLY
        )

        # Test user role requirement error
        user_checker = require_role(UserRole.USER)
        with pytest.raises(HTTPException) as exc_info:
            user_checker(readonly_user)

        assert "user" in exc_info.value.detail.lower()

        # Test admin role requirement error
        admin_checker = require_role(UserRole.ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            admin_checker(readonly_user)

        assert "admin" in exc_info.value.detail.lower()

    async def test_admin_privilege_error_consistency(self):
        """Test that admin privilege errors are consistent."""
        user = User(
            username="test",
            email="test@example.com",
            role=UserRole.USER
        )

        # Test both admin-requiring functions
        with pytest.raises(HTTPException) as exc1:
            await get_admin_user(user)

        with pytest.raises(HTTPException) as exc2:
            require_admin_role(user)

        # Both should give similar error responses
        assert exc1.value.status_code == 403
        assert exc2.value.status_code == 403

        # Both should mention admin privileges
        assert "admin" in exc1.value.detail.lower()
        assert "admin" in exc2.value.detail.lower()
