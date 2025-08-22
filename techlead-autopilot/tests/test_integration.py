"""
Integration tests for TechLead AutoPilot.
Tests complete workflows and system integration scenarios.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


class TestContentWorkflow:
    """Test complete content generation and posting workflow."""
    
    @patch('src.techlead_autopilot.services.content_service.openai_client')
    @patch('src.techlead_autopilot.services.linkedin_service.linkedin_api_client')
    def test_complete_content_workflow(self, mock_linkedin, mock_openai, client: TestClient, auth_headers, mock_openai_responses, mock_linkedin_api_responses):
        """Test complete workflow: generate → approve → schedule → post → analyze."""
        # Mock external APIs
        mock_openai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=mock_openai_responses["content_generation"]["choices"][0]["message"]["content"]))]
        )
        mock_linkedin.post_content.return_value = mock_linkedin_api_responses["post_success"]
        mock_linkedin.get_post_analytics.return_value = {
            "impressions": 2500,
            "clicks": 75,
            "likes": 40,
            "comments": 12,
            "shares": 8
        }
        
        # Step 1: Generate content
        content_data = {
            "content_type": "linkedin_post",
            "topic": "Engineering Leadership Best Practices",
            "target_audience": "engineering_managers",
            "consultation_focused": True
        }
        
        generate_response = client.post("/api/v1/content/generate", json=content_data, headers=auth_headers)
        assert generate_response.status_code == 201
        content_id = generate_response.json()["id"]
        
        # Step 2: Approve content
        approval_response = client.post(
            f"/api/v1/content/{content_id}/approve",
            json={"approved": True, "approval_notes": "Great content, ready to post"},
            headers=auth_headers
        )
        assert approval_response.status_code == 200
        assert approval_response.json()["status"] == "approved"
        
        # Step 3: Schedule content
        schedule_response = client.post(
            f"/api/v1/content/{content_id}/schedule",
            json={"scheduled_at": "2024-12-31T10:00:00Z", "platforms": ["linkedin"]},
            headers=auth_headers
        )
        assert schedule_response.status_code == 200
        assert schedule_response.json()["status"] == "scheduled"
        
        # Step 4: Post content immediately
        post_response = client.post(
            f"/api/v1/content/{content_id}/post",
            json={"platforms": ["linkedin"], "post_immediately": True},
            headers=auth_headers
        )
        assert post_response.status_code == 200
        post_data = post_response.json()
        assert post_data["status"] == "posted"
        assert "posted_at" in post_data
        
        # Step 5: Verify content appears in analytics
        analytics_response = client.get("/api/v1/content/analytics", headers=auth_headers)
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        assert analytics_data["total_content"] >= 1
        assert "posted" in analytics_data["content_by_status"]
        
        # Verify all external API calls were made
        mock_openai.chat.completions.create.assert_called_once()
        mock_linkedin.post_content.assert_called_once()


class TestLeadWorkflow:
    """Test complete lead detection and management workflow."""
    
    @patch('src.techlead_autopilot.services.lead_service.openai_client')
    def test_complete_lead_workflow(self, mock_openai, client: TestClient, auth_headers, mock_openai_responses, sample_lead_data):
        """Test complete workflow: detect → analyze → score → convert → track."""
        # Mock AI analysis
        mock_openai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=mock_openai_responses["lead_analysis"]["choices"][0]["message"]["content"]))]
        )
        
        # Step 1: Detect lead
        detect_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        assert detect_response.status_code == 201
        lead_id = detect_response.json()["id"]
        lead_data = detect_response.json()
        
        # Verify initial lead detection
        assert lead_data["priority"] in ["low", "medium", "high"]
        assert 1 <= lead_data["lead_score"] <= 10
        
        # Step 2: Update lead status (initial contact)
        status_response = client.put(
            f"/api/v1/leads/{lead_id}/status",
            json={"status": "contacted", "notes": "Sent initial LinkedIn message"},
            headers=auth_headers
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "contacted"
        
        # Step 3: Add follow-up note
        note_response = client.post(
            f"/api/v1/leads/{lead_id}/notes",
            json={"content": "Positive response, scheduling discovery call", "note_type": "follow_up"},
            headers=auth_headers
        )
        assert note_response.status_code == 201
        
        # Step 4: Convert to opportunity
        conversion_response = client.post(
            f"/api/v1/leads/{lead_id}/convert",
            json={
                "opportunity_type": "consultation",
                "estimated_value_euros": 8000,
                "probability": 0.75,
                "expected_close_date": "2024-02-15"
            },
            headers=auth_headers
        )
        assert conversion_response.status_code == 201
        conversion_data = conversion_response.json()
        assert conversion_data["status"] == "opportunity"
        
        # Step 5: Track conversion stage progression
        stage_response = client.put(
            f"/api/v1/leads/{lead_id}/conversion-stage",
            json={"stage": "proposal_sent", "probability": 0.85, "notes": "Proposal sent for review"},
            headers=auth_headers
        )
        assert stage_response.status_code == 200
        assert stage_response.json()["probability"] == 0.85
        
        # Step 6: Verify lead appears in analytics
        analytics_response = client.get("/api/v1/leads/analytics", headers=auth_headers)
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        assert analytics_data["total_leads"] >= 1
        assert analytics_data["pipeline_value"] >= 8000


class TestContentToLeadAttribution:
    """Test attribution between content and lead generation."""
    
    @patch('src.techlead_autopilot.services.content_service.openai_client')
    @patch('src.techlead_autopilot.services.lead_service.openai_client')
    @patch('src.techlead_autopilot.services.linkedin_service.linkedin_api_client')
    def test_content_lead_attribution(self, mock_linkedin, mock_lead_ai, mock_content_ai, client: TestClient, auth_headers, mock_openai_responses):
        """Test attribution tracking from content to lead generation."""
        # Mock AI responses
        mock_content_ai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=mock_openai_responses["content_generation"]["choices"][0]["message"]["content"]))]
        )
        mock_lead_ai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content=mock_openai_responses["lead_analysis"]["choices"][0]["message"]["content"]))]
        )
        mock_linkedin.post_content.return_value = {"id": "urn:li:share:test-post-123"}
        
        # Step 1: Generate and post content
        content_data = {
            "content_type": "linkedin_post",
            "topic": "Scaling Engineering Teams",
            "target_audience": "engineering_managers",
            "consultation_focused": True
        }
        
        content_response = client.post("/api/v1/content/generate", json=content_data, headers=auth_headers)
        content_id = content_response.json()["id"]
        
        # Approve and post content
        client.post(f"/api/v1/content/{content_id}/approve", json={"approved": True}, headers=auth_headers)
        post_response = client.post(
            f"/api/v1/content/{content_id}/post",
            json={"platforms": ["linkedin"], "post_immediately": True},
            headers=auth_headers
        )
        posted_content = post_response.json()
        
        # Step 2: Generate lead from that content
        lead_data = {
            "content": "Great post about scaling engineering teams! We're facing similar challenges. Can we discuss consulting opportunities?",
            "source_platform": "linkedin",
            "source_post_id": "test-post-123",  # Link to posted content
            "source_content_id": content_id,     # Direct attribution
            "author_info": {
                "name": "Sarah Johnson",
                "title": "VP Engineering",
                "company": "GrowthTech",
                "linkedin_profile": "https://linkedin.com/in/sarahjohnson"
            }
        }
        
        lead_response = client.post("/api/v1/leads/detect", json=lead_data, headers=auth_headers)
        assert lead_response.status_code == 201
        lead_id = lead_response.json()["id"]
        
        # Step 3: Verify attribution in analytics
        attribution_response = client.get("/api/v1/leads/analytics/by-content", headers=auth_headers)
        assert attribution_response.status_code == 200
        attribution_data = attribution_response.json()
        
        # Should show the content generated leads
        assert "content_performance" in attribution_data
        content_performance = attribution_data["content_performance"]
        
        # Find our content in the performance data
        our_content_found = False
        for content_item in content_performance:
            if content_item.get("content_id") == content_id:
                assert content_item["leads_generated"] >= 1
                assert content_item["total_value"] >= 0
                our_content_found = True
                break
        
        assert our_content_found, "Content should appear in attribution analytics"


class TestMultiUserIsolation:
    """Test multi-tenant data isolation."""
    
    def test_organization_data_isolation(self, client: TestClient, sample_user_data, sample_organization_data, sample_content_data):
        """Test that users from different organizations cannot access each other's data."""
        # Create first organization and user
        org1_response = client.post("/api/v1/organizations/", json={
            **sample_organization_data,
            "name": "Organization One"
        })
        org1_id = org1_response.json()["id"]
        
        user1_data = {**sample_user_data, "email": "user1@org1.com", "organization_id": org1_id}
        client.post("/api/v1/auth/register", json=user1_data)
        
        login1_response = client.post("/api/v1/auth/login", json={
            "email": user1_data["email"],
            "password": user1_data["password"]
        })
        user1_headers = {"Authorization": f"Bearer {login1_response.json()['access_token']}"}
        
        # Create second organization and user
        org2_response = client.post("/api/v1/organizations/", json={
            **sample_organization_data,
            "name": "Organization Two"
        })
        org2_id = org2_response.json()["id"]
        
        user2_data = {**sample_user_data, "email": "user2@org2.com", "organization_id": org2_id}
        client.post("/api/v1/auth/register", json=user2_data)
        
        login2_response = client.post("/api/v1/auth/login", json={
            "email": user2_data["email"],
            "password": user2_data["password"]
        })
        user2_headers = {"Authorization": f"Bearer {login2_response.json()['access_token']}"}
        
        # User 1 creates content
        content_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=user1_headers)
        assert content_response.status_code == 201
        content_id = content_response.json()["id"]
        
        # User 2 should not be able to access User 1's content
        forbidden_response = client.get(f"/api/v1/content/{content_id}", headers=user2_headers)
        assert forbidden_response.status_code == 404  # Should not find content from different org
        
        # User 2 should not see User 1's content in list
        user2_content_list = client.get("/api/v1/content/", headers=user2_headers)
        assert user2_content_list.status_code == 200
        assert user2_content_list.json()["total"] == 0  # Should see no content


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""
    
    @patch('src.techlead_autopilot.services.linkedin_service.linkedin_api_client')
    def test_linkedin_api_failure_handling(self, mock_linkedin, client: TestClient, auth_headers, sample_content_data):
        """Test graceful handling of LinkedIn API failures."""
        # Mock LinkedIn API failure
        mock_linkedin.post_content.side_effect = Exception("LinkedIn API temporarily unavailable")
        
        # Generate and approve content
        content_response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        content_id = content_response.json()["id"]
        
        client.post(f"/api/v1/content/{content_id}/approve", json={"approved": True}, headers=auth_headers)
        
        # Attempt to post should handle the error gracefully
        post_response = client.post(
            f"/api/v1/content/{content_id}/post",
            json={"platforms": ["linkedin"], "post_immediately": True},
            headers=auth_headers
        )
        
        # Should return error but not crash
        assert post_response.status_code in [400, 500, 502, 503]
        error_data = post_response.json()
        assert "error" in error_data or "detail" in error_data
    
    @patch('src.techlead_autopilot.services.content_service.openai_client')
    def test_ai_service_failure_handling(self, mock_openai, client: TestClient, auth_headers, sample_content_data):
        """Test graceful handling of AI service failures."""
        # Mock OpenAI API failure
        mock_openai.chat.completions.create.side_effect = Exception("OpenAI API rate limit exceeded")
        
        # Attempt content generation should handle the error gracefully
        response = client.post("/api/v1/content/generate", json=sample_content_data, headers=auth_headers)
        
        # Should return error but not crash
        assert response.status_code in [400, 500, 502, 503]
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data


class TestPerformanceAndScaling:
    """Test performance and scaling scenarios."""
    
    def test_bulk_content_generation(self, client: TestClient, auth_headers):
        """Test handling multiple content generation requests."""
        content_requests = [
            {
                "content_type": "linkedin_post",
                "topic": f"Engineering Topic {i}",
                "target_audience": "engineering_managers",
                "consultation_focused": True
            }
            for i in range(5)
        ]
        
        responses = []
        for content_data in content_requests:
            response = client.post("/api/v1/content/generate", json=content_data, headers=auth_headers)
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 201
        
        # Verify all content appears in listing
        list_response = client.get("/api/v1/content/", headers=auth_headers)
        assert list_response.status_code == 200
        assert list_response.json()["total"] >= len(content_requests)
    
    def test_pagination_performance(self, client: TestClient, auth_headers, sample_content_data):
        """Test pagination performance with multiple content items."""
        # Generate multiple content items
        for i in range(15):
            content_data = {
                **sample_content_data,
                "topic": f"Test Topic {i}"
            }
            client.post("/api/v1/content/generate", json=content_data, headers=auth_headers)
        
        # Test pagination
        page1_response = client.get("/api/v1/content/?page=1&page_size=10", headers=auth_headers)
        assert page1_response.status_code == 200
        page1_data = page1_response.json()
        assert len(page1_data["items"]) == 10
        assert page1_data["page"] == 1
        
        page2_response = client.get("/api/v1/content/?page=2&page_size=10", headers=auth_headers)
        assert page2_response.status_code == 200
        page2_data = page2_response.json()
        assert len(page2_data["items"]) >= 5  # At least 5 items on page 2
        assert page2_data["page"] == 2