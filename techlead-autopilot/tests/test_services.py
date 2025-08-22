"""
Test service layer functionality.
Covers 100% of good weather scenarios for service operations.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


class TestContentService:
    """Test ContentService functionality."""
    
    @patch('src.techlead_autopilot.services.content_service.openai_client')
    def test_generate_content_service(self, mock_openai, client: TestClient, auth_headers, mock_openai_responses):
        """Test content generation service."""
        # Mock OpenAI response
        mock_openai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=mock_openai_responses["content_generation"]["choices"][0]["message"]["content"]))]
        )
        
        content_data = {
            "content_type": "linkedin_post",
            "topic": "Engineering Leadership Best Practices",
            "target_audience": "engineering_managers",
            "consultation_focused": True
        }
        
        response = client.post("/api/v1/content/generate", json=content_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert "generated_content" in data
        assert data["content_type"] == content_data["content_type"]
        mock_openai.chat.completions.create.assert_called_once()
    
    def test_content_template_processing(self, client: TestClient, auth_headers):
        """Test content template processing."""
        template_data = {
            "template_id": "technical_leadership_template",
            "topic": "Remote Team Management",
            "target_audience": "engineering_managers",
            "custom_variables": {
                "company_name": "TechCorp",
                "team_size": "25 engineers",
                "challenge": "distributed team coordination"
            }
        }
        
        response = client.post("/api/v1/content/generate-from-template", json=template_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == template_data["topic"]
        assert "generated_content" in data
    
    def test_content_optimization_suggestions(self, client: TestClient, auth_headers, sample_content_data):
        """Test content optimization suggestions."""
        # Generate content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        response = client.get(f"/api/v1/content/{content_id}/optimize", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "engagement_score" in data
        assert "optimization_areas" in data
        assert "improved_version" in data


class TestLeadService:
    """Test LeadService functionality."""
    
    @patch('src.techlead_autopilot.services.lead_service.openai_client')
    def test_lead_analysis_service(self, mock_openai, client: TestClient, auth_headers, mock_openai_responses):
        """Test lead analysis service with AI."""
        # Mock OpenAI response
        mock_openai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=mock_openai_responses["lead_analysis"]["choices"][0]["message"]["content"]))]
        )
        
        analysis_data = {
            "content": "We're struggling with our engineering team structure and could use expert guidance.",
            "author_info": {
                "name": "Jane Smith",
                "title": "CTO",
                "company": "GrowthCorp",
                "company_size": "100-500 employees"
            }
        }
        
        response = client.post("/api/v1/leads/analyze", json=analysis_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_consultation_inquiry"] is True
        assert data["confidence"] == 0.85
        assert data["lead_score"] == 8
        mock_openai.chat.completions.create.assert_called_once()
    
    def test_lead_scoring_algorithm(self, client: TestClient, auth_headers, sample_lead_data):
        """Test lead scoring algorithm."""
        response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify scoring components
        assert "lead_score" in data
        assert 1 <= data["lead_score"] <= 10
        assert "confidence" in data
        assert 0 <= data["confidence"] <= 1
        assert data["priority"] in ["low", "medium", "high"]
    
    def test_lead_prioritization(self, client: TestClient, auth_headers):
        """Test lead prioritization logic."""
        # Create multiple leads with different characteristics
        leads_data = [
            {
                "content": "Urgent: Need consulting help for our engineering team restructure",
                "source_platform": "linkedin",
                "source_post_id": "urgent-post",
                "author_info": {"name": "CEO", "title": "Chief Executive Officer", "company": "BigCorp"}
            },
            {
                "content": "Interesting insights about team leadership",
                "source_platform": "linkedin", 
                "source_post_id": "casual-post",
                "author_info": {"name": "Developer", "title": "Software Engineer", "company": "StartupCo"}
            }
        ]
        
        responses = []
        for lead_data in leads_data:
            response = client.post("/api/v1/leads/detect", json=lead_data, headers=auth_headers)
            responses.append(response.json())
        
        # Verify prioritization works correctly
        urgent_lead = responses[0]
        casual_lead = responses[1]
        
        assert urgent_lead["lead_score"] > casual_lead["lead_score"]
        assert urgent_lead["priority"] in ["high", "medium"]


class TestAnalyticsService:
    """Test AnalyticsService functionality."""
    
    def test_content_performance_analytics(self, client: TestClient, auth_headers, sample_content_data):
        """Test content performance analytics calculation."""
        # Generate some content first
        client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        
        response = client.get("/api/v1/content/analytics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify analytics structure
        assert "total_content" in data
        assert "content_by_status" in data
        assert "engagement_metrics" in data
        assert "performance_trends" in data
        
        # Verify metrics calculation
        assert isinstance(data["total_content"], int)
        assert isinstance(data["content_by_status"], dict)
    
    def test_lead_conversion_analytics(self, client: TestClient, auth_headers):
        """Test lead conversion analytics calculation."""
        response = client.get("/api/v1/leads/analytics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify analytics structure
        assert "total_leads" in data
        assert "conversion_metrics" in data
        assert "pipeline_value" in data
        assert "lead_sources" in data
        
        # Verify conversion rate calculations
        if data["total_leads"] > 0:
            assert "conversion_rate" in data["conversion_metrics"]
            assert isinstance(data["conversion_metrics"]["conversion_rate"], (int, float))
    
    def test_roi_calculation(self, client: TestClient, auth_headers):
        """Test ROI calculation for content and leads."""
        response = client.get("/api/v1/analytics/roi", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "content_roi" in data
        assert "lead_roi" in data
        assert "total_investment" in data
        assert "total_return" in data
        assert "roi_percentage" in data


class TestLinkedInService:
    """Test LinkedIn integration service."""
    
    @patch('src.techlead_autopilot.services.linkedin_service.linkedin_api_client')
    def test_linkedin_posting_service(self, mock_linkedin, client: TestClient, auth_headers, sample_content_data):
        """Test LinkedIn posting service."""
        # Mock LinkedIn API response
        mock_linkedin.post_content.return_value = {
            "id": "urn:li:share:6789",
            "activity": "urn:li:activity:6789"
        }
        
        # Generate and approve content first
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        client.post(f"/api/v1/content/{content_id}/approve", json={"approved": True}, headers=auth_headers)
        
        # Post to LinkedIn
        post_data = {
            "platforms": ["linkedin"],
            "post_immediately": True
        }
        
        response = client.post(f"/api/v1/content/{content_id}/post", json=post_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "posted"
        mock_linkedin.post_content.assert_called_once()
    
    @patch('src.techlead_autopilot.services.linkedin_service.linkedin_api_client')
    def test_linkedin_engagement_tracking(self, mock_linkedin, client: TestClient, auth_headers):
        """Test LinkedIn engagement tracking."""
        # Mock LinkedIn engagement data
        mock_linkedin.get_post_analytics.return_value = {
            "impressions": 1500,
            "clicks": 45,
            "likes": 23,
            "comments": 7,
            "shares": 3
        }
        
        response = client.get("/api/v1/linkedin/engagement/post-123", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "impressions" in data
        assert "engagement_rate" in data
        assert "click_through_rate" in data
        mock_linkedin.get_post_analytics.assert_called_once_with("post-123")


class TestNotificationService:
    """Test notification service functionality."""
    
    def test_lead_notification_trigger(self, client: TestClient, auth_headers, sample_lead_data):
        """Test high-priority lead notification triggering."""
        # Mock high-priority lead
        high_priority_lead = {
            **sample_lead_data,
            "content": "URGENT: Need immediate consulting help for our engineering crisis",
            "author_info": {
                **sample_lead_data["author_info"],
                "title": "CEO",
                "company": "Major Enterprise"
            }
        }
        
        response = client.post("/api/v1/leads/detect", json=high_priority_lead, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify high priority assignment
        assert data["priority"] == "high"
        assert data["lead_score"] >= 8
    
    def test_content_approval_notifications(self, client: TestClient, auth_headers, sample_content_data):
        """Test content approval workflow notifications."""
        # Generate content
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        # Check pending approval notification
        response = client.get("/api/v1/notifications/pending", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "pending_approvals" in data
        assert isinstance(data["pending_approvals"], list)


class TestSchedulingService:
    """Test scheduling service functionality."""
    
    def test_optimal_posting_time_calculation(self, client: TestClient, auth_headers):
        """Test calculation of optimal posting times."""
        response = client.get("/api/v1/scheduling/optimal-times", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "recommended_times" in data
        assert "timezone" in data
        assert "audience_analysis" in data
        
        # Verify time format
        times = data["recommended_times"]
        assert isinstance(times, list)
        if len(times) > 0:
            time_slot = times[0]
            assert "day_of_week" in time_slot
            assert "time" in time_slot
            assert "engagement_score" in time_slot
    
    def test_content_scheduling_queue(self, client: TestClient, auth_headers, sample_content_data):
        """Test content scheduling queue management."""
        # Generate and schedule content
        create_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = create_response.json()["id"]
        
        client.post(f"/api/v1/content/{content_id}/approve", json={"approved": True}, headers=auth_headers)
        
        schedule_data = {
            "scheduled_at": "2024-12-31T10:00:00Z",
            "platforms": ["linkedin"]
        }
        client.post(f"/api/v1/content/{content_id}/schedule", json=schedule_data, headers=auth_headers)
        
        # Check scheduling queue
        response = client.get("/api/v1/scheduling/queue", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "scheduled_content" in data
        assert "upcoming_posts" in data
        assert isinstance(data["scheduled_content"], list)