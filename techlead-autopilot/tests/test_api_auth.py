"""
Test authentication and authorization functionality.
Covers 100% of good weather scenarios for user management.
"""
import pytest
from fastapi.testclient import TestClient


class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_user_success(self, client: TestClient, sample_user_data, sample_organization_data):
        """Test successful user registration."""
        # First create organization
        org_response = client.post("/api/v1/organizations/", json=sample_organization_data)
        assert org_response.status_code == 201
        org_id = org_response.json()["id"]
        
        # Register user
        user_data = {**sample_user_data, "organization_id": org_id}
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["first_name"] == sample_user_data["first_name"]
        assert data["last_name"] == sample_user_data["last_name"]
        assert data["organization_id"] == org_id
        assert "id" in data
        assert "password" not in data  # Password should not be returned
    
    def test_register_user_with_minimal_data(self, client: TestClient, sample_organization_data):
        """Test user registration with minimal required data."""
        # Create organization
        org_response = client.post("/api/v1/organizations/", json=sample_organization_data)
        org_id = org_response.json()["id"]
        
        minimal_user_data = {
            "email": "minimal@example.com",
            "password": "password123",
            "first_name": "Jane",
            "last_name": "Doe",
            "organization_id": org_id
        }
        
        response = client.post("/api/v1/auth/register", json=minimal_user_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["email"] == minimal_user_data["email"]
        assert data["first_name"] == minimal_user_data["first_name"]


class TestUserLogin:
    """Test user login functionality."""
    
    def test_login_success(self, client: TestClient, sample_user_data, sample_organization_data):
        """Test successful user login."""
        # Register user first
        org_response = client.post("/api/v1/organizations/", json=sample_organization_data)
        org_id = org_response.json()["id"]
        
        user_data = {**sample_user_data, "organization_id": org_id}
        client.post("/api/v1/auth/register", json=user_data)
        
        # Login
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_token_refresh_success(self, client: TestClient, sample_user_data, sample_organization_data):
        """Test token refresh functionality."""
        # Register and login user
        org_response = client.post("/api/v1/organizations/", json=sample_organization_data)
        org_id = org_response.json()["id"]
        
        user_data = {**sample_user_data, "organization_id": org_id}
        client.post("/api/v1/auth/register", json=user_data)
        
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data


class TestUserProfile:
    """Test user profile functionality."""
    
    def test_get_current_user(self, client: TestClient, auth_headers):
        """Test getting current user profile."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "organization_id" in data
        assert "id" in data
    
    def test_update_user_profile(self, client: TestClient, auth_headers):
        """Test updating user profile."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "job_title": "Lead Engineer",
            "linkedin_url": "https://linkedin.com/in/updated"
        }
        
        response = client.put("/api/v1/auth/me", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == update_data["first_name"]
        assert data["last_name"] == update_data["last_name"]
        assert data["job_title"] == update_data["job_title"]
        assert data["linkedin_url"] == update_data["linkedin_url"]


class TestOrganizations:
    """Test organization functionality."""
    
    def test_create_organization_success(self, client: TestClient, sample_organization_data):
        """Test successful organization creation."""
        response = client.post("/api/v1/organizations/", json=sample_organization_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_organization_data["name"]
        assert data["description"] == sample_organization_data["description"]
        assert data["website"] == sample_organization_data["website"]
        assert "id" in data
        assert "created_at" in data
    
    def test_get_organization(self, client: TestClient, auth_headers):
        """Test getting organization details."""
        response = client.get("/api/v1/organizations/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "id" in data
        assert "created_at" in data


class TestPasswordOperations:
    """Test password-related functionality."""
    
    def test_change_password_success(self, client: TestClient, auth_headers, sample_user_data):
        """Test successful password change."""
        change_data = {
            "current_password": sample_user_data["password"],
            "new_password": "newpassword123"
        }
        
        response = client.post(
            "/api/v1/auth/change-password",
            json=change_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"
    
    def test_password_reset_request(self, client: TestClient, sample_user_data, sample_organization_data):
        """Test password reset request."""
        # Register user first
        org_response = client.post("/api/v1/organizations/", json=sample_organization_data)
        org_id = org_response.json()["id"]
        
        user_data = {**sample_user_data, "organization_id": org_id}
        client.post("/api/v1/auth/register", json=user_data)
        
        # Request password reset
        response = client.post(
            "/api/v1/auth/reset-password-request",
            json={"email": sample_user_data["email"]}
        )
        
        assert response.status_code == 200
        assert "message" in response.json()


class TestAuthenticationMiddleware:
    """Test authentication middleware functionality."""
    
    def test_protected_endpoint_with_valid_token(self, client: TestClient, auth_headers):
        """Test accessing protected endpoint with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
    
    def test_token_validation(self, client: TestClient, auth_headers):
        """Test token validation endpoint."""
        response = client.post("/api/v1/auth/validate-token", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user_id" in data
        assert "organization_id" in data