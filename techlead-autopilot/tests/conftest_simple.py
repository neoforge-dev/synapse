"""
Simple pytest configuration for business logic tests.
"""
import pytest
import os

# Set test environment variables
os.environ["TECHLEAD_ENVIRONMENT"] = "testing"
os.environ["TECHLEAD_DATABASE_URL"] = "sqlite:///./test.db"
os.environ["TECHLEAD_JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"

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