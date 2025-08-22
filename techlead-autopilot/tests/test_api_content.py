"""
Test content management functionality.
Covers 100% of good weather scenarios for content operations.
"""
import pytest
from fastapi.testclient import TestClient


class TestContentGeneration:
    """Test content generation functionality."""
    
    def test_generate_content_success(self, client: TestClient, auth_headers, sample_content_data):
        """Test successful content generation."""
        response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content_type"] == sample_content_data["content_type"]
        assert data["topic"] == sample_content_data["topic"]
        assert data["target_audience"] == sample_content_data["target_audience"]
        assert "generated_content" in data
        assert "id" in data
        assert "created_at" in data
        assert data["status"] == "draft"
    
    def test_generate_different_content_types(self, client: TestClient, auth_headers):
        """Test generating different content types."""
        content_types = [
            "linkedin_post", "twitter_thread", "technical_article", 
            "case_study", "thought_leadership", "industry_insight",
            "team_highlight", "tech_tutorial"
        ]
        
        for content_type in content_types:
            content_data = {
                "content_type": content_type,
                "topic": f"Topic for {content_type}",
                "target_audience": "engineering_managers",
                "consultation_focused": True
            }
            
            response = client.post("/api/v1/content/generate", json=content_data, headers=auth_headers)
            assert response.status_code == 201
            data = response.json()
            assert data["content_type"] == content_type


class TestContentManagement:
    """Test content management operations."""
    
    def test_list_content_success(self, client: TestClient, auth_headers, sample_content_data):
        """Test listing user's content."""
        # Generate some content first
        client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        
        response = client.get("/api/v1/content/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["items"]) > 0
    
    def test_list_content_with_filters(self, client: TestClient, auth_headers, sample_content_data):
        """Test listing content with filters."""
        # Generate content
        client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        
        # Test status filter
        response = client.get("/api/v1/content/?status=draft", headers=auth_headers)
        assert response.status_code == 200
        
        # Test content type filter
        response = client.get(f"/api/v1/content/?content_type={sample_content_data['content_type']}", headers=auth_headers)
        assert response.status_code == 200
        
        # Test date range filter
        response = client.get("/api/v1/content/?start_date=2024-01-01&end_date=2024-12-31", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_content_by_id(self, client: TestClient, auth_headers, sample_content_data):
        """Test getting specific content by ID."""
        # Generate content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        response = client.get(f"/api/v1/content/{content_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == content_id
        assert data["content_type"] == sample_content_data["content_type"]
    
    def test_update_content_success(self, client: TestClient, auth_headers, sample_content_data):
        """Test updating content."""
        # Generate content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        update_data = {
            "topic": "Updated Topic",
            "generated_content": "Updated content body",
            "notes": "Updated notes"
        }
        
        response = client.put(f"/api/v1/content/{content_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == update_data["topic"]
        assert data["generated_content"] == update_data["generated_content"]
        assert data["notes"] == update_data["notes"]
    
    def test_delete_content_success(self, client: TestClient, auth_headers, sample_content_data):
        """Test deleting content."""
        # Generate content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        response = client.delete(f"/api/v1/content/{content_id}", headers=auth_headers)
        
        assert response.status_code == 204


class TestContentApproval:
    """Test content approval workflow."""
    
    def test_approve_content_success(self, client: TestClient, auth_headers, sample_content_data):
        """Test approving content for posting."""
        # Generate content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        approval_data = {
            "approved": True,
            "approval_notes": "Content looks great, ready to post"
        }
        
        response = client.post(f"/api/v1/content/{content_id}/approve", json=approval_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved"] is True
        assert data["approval_notes"] == approval_data["approval_notes"]
    
    def test_reject_content_success(self, client: TestClient, auth_headers, sample_content_data):
        """Test rejecting content."""
        # Generate content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        rejection_data = {
            "approved": False,
            "approval_notes": "Needs revision before posting"
        }
        
        response = client.post(f"/api/v1/content/{content_id}/approve", json=rejection_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["approved"] is False
        assert data["approval_notes"] == rejection_data["approval_notes"]


class TestContentScheduling:
    """Test content scheduling functionality."""
    
    def test_schedule_content_success(self, client: TestClient, auth_headers, sample_content_data):
        """Test scheduling content for future posting."""
        # Generate and approve content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        client.post(f"/api/v1/content/{content_id}/approve", json={"approved": True}, headers=auth_headers)
        
        schedule_data = {
            "scheduled_at": "2024-12-31T10:00:00Z",
            "platforms": ["linkedin"]
        }
        
        response = client.post(f"/api/v1/content/{content_id}/schedule", json=schedule_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "scheduled"
        assert data["scheduled_at"] == schedule_data["scheduled_at"]
        assert data["platforms"] == schedule_data["platforms"]
    
    def test_post_content_immediately(self, client: TestClient, auth_headers, sample_content_data):
        """Test posting content immediately."""
        # Generate and approve content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        client.post(f"/api/v1/content/{content_id}/approve", json={"approved": True}, headers=auth_headers)
        
        post_data = {
            "platforms": ["linkedin"],
            "post_immediately": True
        }
        
        response = client.post(f"/api/v1/content/{content_id}/post", json=post_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "posted"
        assert data["platforms"] == post_data["platforms"]
        assert "posted_at" in data


class TestContentAnalytics:
    """Test content analytics functionality."""
    
    def test_get_content_analytics(self, client: TestClient, auth_headers):
        """Test getting content analytics."""
        response = client.get("/api/v1/content/analytics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_content" in data
        assert "content_by_status" in data
        assert "content_by_type" in data
        assert "engagement_metrics" in data
        assert "performance_trends" in data
    
    def test_get_content_performance(self, client: TestClient, auth_headers, sample_content_data):
        """Test getting individual content performance."""
        # Generate content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        response = client.get(f"/api/v1/content/{content_id}/analytics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "views" in data
        assert "engagement_rate" in data
        assert "lead_generation" in data
        assert "platform_performance" in data


class TestContentTemplates:
    """Test content template functionality."""
    
    def test_list_content_templates(self, client: TestClient, auth_headers):
        """Test listing available content templates."""
        response = client.get("/api/v1/content/templates", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify template structure
        template = data[0]
        assert "id" in template
        assert "name" in template
        assert "content_type" in template
        assert "description" in template
        assert "template_content" in template
    
    def test_generate_content_from_template(self, client: TestClient, auth_headers):
        """Test generating content from a specific template."""
        # Get available templates first
        templates_response = client.get("/api/v1/content/templates", headers=auth_headers)
        template_id = templates_response.json()[0]["id"]
        
        template_data = {
            "template_id": template_id,
            "topic": "Engineering Leadership in Remote Teams",
            "target_audience": "engineering_managers",
            "custom_variables": {
                "company_name": "TechCorp",
                "team_size": "15 engineers"
            }
        }
        
        response = client.post("/api/v1/content/generate-from-template", json=template_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == template_data["topic"]
        assert "generated_content" in data
        assert data["status"] == "draft"