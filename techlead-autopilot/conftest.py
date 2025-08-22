"""
Pytest configuration and shared fixtures for TechLead AutoPilot tests.
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

# Set test environment variables
os.environ["TECHLEAD_ENVIRONMENT"] = "testing"
os.environ["TECHLEAD_DATABASE_URL"] = "sqlite:///./test.db"
os.environ["TECHLEAD_JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["TECHLEAD_REDIS_URL"] = "redis://localhost:6379/1"

from src.techlead_autopilot.api.main import create_app
from src.techlead_autopilot.config import get_settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    return mock_session

@pytest.fixture
def test_app(mock_db_session):
    """Create a test FastAPI app with mocked database."""
    # Mock the database dependency
    async def mock_get_db_session():
        yield mock_db_session
    
    app = create_app()
    
    # Override database dependency
    from src.techlead_autopilot.infrastructure.database import get_db_session
    app.dependency_overrides[get_db_session] = mock_get_db_session
    
    return app

@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = get_settings()
    settings.database_url = "sqlite:///./test.db"
    settings.environment = "testing"
    settings.debug = True
    return settings

# Sample data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "John",
        "last_name": "Doe",
        "job_title": "Senior Engineering Manager",
        "company": "Tech Corp",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "technical_expertise": ["Python", "AWS", "Team Leadership"]
    }

@pytest.fixture
def sample_organization_data():
    """Sample organization data for testing."""
    return {
        "name": "Test Organization",
        "description": "A test organization for unit tests",
        "website": "https://test.com",
        "linkedin_company_id": "test-company"
    }

@pytest.fixture
def sample_content_data():
    """Sample content data for testing."""
    return {
        "content_type": "linkedin_post",
        "topic": "Technical Leadership Best Practices",
        "target_audience": "engineering_managers",
        "consultation_focused": True,
        "target_engagement_rate": 0.05
    }

@pytest.fixture
def sample_lead_data():
    """Sample lead data for testing."""
    return {
        "content": "Hi, I saw your post about scaling engineering teams. We're facing similar challenges at our startup. Could we discuss potential consulting opportunities?",
        "source_platform": "linkedin",
        "source_post_id": "test-post-123",
        "author_info": {
            "name": "Jane Smith",
            "title": "CTO",
            "company": "StartupCo",
            "linkedin_profile": "https://linkedin.com/in/janesmith"
        }
    }

@pytest.fixture
def auth_headers(client, sample_user_data, sample_organization_data):
    """Create authentication headers for API requests."""
    # Mock the responses for testing
    with client as test_client:
        # Mock organization creation response
        org_response_data = {"id": "test-org-123", **sample_organization_data}
        
        # Mock user registration response  
        user_response_data = {"id": "test-user-123", **sample_user_data}
        user_response_data.pop("password", None)  # Remove password from response
        
        # Mock login response
        login_response_data = {
            "access_token": "test-jwt-token",
            "refresh_token": "test-refresh-token",
            "token_type": "bearer",
            "expires_in": 3600
        }
        
        # For auth_headers fixture, we'll just return a valid mock token
        return {"Authorization": "Bearer test-jwt-token"}

# Mock external API responses
@pytest.fixture
def mock_linkedin_api_responses():
    """Mock LinkedIn API responses."""
    return {
        "profile": {
            "id": "12345",
            "firstName": {"localized": {"en_US": "John"}},
            "lastName": {"localized": {"en_US": "Doe"}},
            "headline": {"localized": {"en_US": "Senior Engineering Manager"}},
        },
        "post_success": {
            "id": "urn:li:share:6789",
            "activity": "urn:li:activity:6789"
        }
    }

@pytest.fixture
def mock_openai_responses():
    """Mock OpenAI API responses."""
    return {
        "content_generation": {
            "choices": [{
                "message": {
                    "content": "# Technical Leadership in 2024\n\nLeading engineering teams requires a unique blend of technical expertise and people skills. Here are the key practices I've learned:\n\n1. **Clear Communication** - Technical decisions must be communicated clearly to both technical and non-technical stakeholders.\n\n2. **Continuous Learning** - Technology evolves rapidly. Great leaders stay current while helping their teams grow.\n\n3. **Empathy in Code Reviews** - Code reviews are teaching moments, not critique sessions.\n\nWhat leadership practices have worked best for your team?\n\n#TechnicalLeadership #EngineeringManagement #TeamGrowth"
                }
            }]
        },
        "lead_analysis": {
            "choices": [{
                "message": {
                    "content": "{\n  \"is_consultation_inquiry\": true,\n  \"confidence\": 0.85,\n  \"inquiry_type\": \"consultation\",\n  \"lead_score\": 8,\n  \"priority\": \"high\",\n  \"estimated_value_euros\": 5000,\n  \"company_size\": \"startup\",\n  \"technical_complexity\": \"medium\",\n  \"urgency_indicators\": [\"facing challenges\", \"immediate need\"],\n  \"follow_up_suggested\": \"Schedule a 30-minute discovery call to understand their scaling challenges\"\n}"
                }
            }]
        }
    }