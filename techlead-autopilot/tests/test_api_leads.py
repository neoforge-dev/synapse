"""
Test lead detection and management functionality.
Covers 100% of good weather scenarios for lead operations.
"""
import pytest
from fastapi.testclient import TestClient


class TestLeadDetection:
    """Test lead detection functionality."""
    
    def test_detect_lead_from_comment(self, client: TestClient, auth_headers, sample_lead_data):
        """Test detecting a lead from social media comment."""
        response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == sample_lead_data["content"]
        assert data["source_platform"] == sample_lead_data["source_platform"]
        assert data["source_post_id"] == sample_lead_data["source_post_id"]
        assert "lead_score" in data
        assert "confidence" in data
        assert "priority" in data
        assert "estimated_value_euros" in data
        assert "id" in data
        assert "detected_at" in data
    
    def test_analyze_lead_content(self, client: TestClient, auth_headers):
        """Test analyzing content for lead potential."""
        analysis_data = {
            "content": "We're struggling with our engineering team structure and could use some guidance on best practices.",
            "author_info": {
                "name": "Tech CEO",
                "title": "Chief Executive Officer",
                "company": "Growing Startup",
                "company_size": "50-100 employees"
            }
        }
        
        response = client.post("/api/v1/leads/analyze", json=analysis_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "is_consultation_inquiry" in data
        assert "confidence" in data
        assert "lead_score" in data
        assert "priority" in data
        assert "estimated_value_euros" in data
        assert "urgency_indicators" in data
        assert "follow_up_suggested" in data
    
    def test_bulk_lead_detection(self, client: TestClient, auth_headers):
        """Test bulk lead detection from multiple comments."""
        bulk_data = {
            "comments": [
                {
                    "content": "Interested in consulting services for team scaling",
                    "source_platform": "linkedin",
                    "source_post_id": "post-1",
                    "author_info": {"name": "CTO", "company": "TechCorp"}
                },
                {
                    "content": "Great insights! Would love to discuss this further",
                    "source_platform": "linkedin", 
                    "source_post_id": "post-2",
                    "author_info": {"name": "VP Engineering", "company": "StartupInc"}
                }
            ]
        }
        
        response = client.post("/api/v1/leads/detect-bulk", json=bulk_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "processed_count" in data
        assert "leads_detected" in data
        assert "leads" in data
        assert len(data["leads"]) <= len(bulk_data["comments"])


class TestLeadManagement:
    """Test lead management operations."""
    
    def test_list_leads_success(self, client: TestClient, auth_headers, sample_lead_data):
        """Test listing user's leads."""
        # Create a lead first
        client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        
        response = client.get("/api/v1/leads/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["items"]) > 0
    
    def test_list_leads_with_filters(self, client: TestClient, auth_headers, sample_lead_data):
        """Test listing leads with various filters."""
        # Create a lead first
        client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        
        # Test priority filter
        response = client.get("/api/v1/leads/?priority=high", headers=auth_headers)
        assert response.status_code == 200
        
        # Test status filter
        response = client.get("/api/v1/leads/?status=new", headers=auth_headers)
        assert response.status_code == 200
        
        # Test platform filter
        response = client.get("/api/v1/leads/?platform=linkedin", headers=auth_headers)
        assert response.status_code == 200
        
        # Test score range filter
        response = client.get("/api/v1/leads/?min_score=7", headers=auth_headers)
        assert response.status_code == 200
    
    def test_get_lead_by_id(self, client: TestClient, auth_headers, sample_lead_data):
        """Test getting specific lead by ID."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        response = client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == lead_id
        assert data["content"] == sample_lead_data["content"]
        assert "scoring_breakdown" in data
        assert "activity_timeline" in data
    
    def test_update_lead_status(self, client: TestClient, auth_headers, sample_lead_data):
        """Test updating lead status."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        update_data = {
            "status": "contacted",
            "notes": "Initial outreach sent via LinkedIn"
        }
        
        response = client.put(f"/api/v1/leads/{lead_id}/status", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == update_data["status"]
        assert data["notes"] == update_data["notes"]
    
    def test_add_lead_note(self, client: TestClient, auth_headers, sample_lead_data):
        """Test adding notes to a lead."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        note_data = {
            "content": "Had a great initial conversation. They're interested in a 3-month engagement.",
            "note_type": "conversation"
        }
        
        response = client.post(f"/api/v1/leads/{lead_id}/notes", json=note_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == note_data["content"]
        assert data["note_type"] == note_data["note_type"]
        assert "created_at" in data
        assert "id" in data


class TestLeadScoring:
    """Test lead scoring functionality."""
    
    def test_update_lead_score(self, client: TestClient, auth_headers, sample_lead_data):
        """Test updating lead score."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        score_data = {
            "lead_score": 9,
            "confidence": 0.92,
            "scoring_factors": {
                "urgency": 8,
                "budget_indicators": 7,
                "decision_maker": 9,
                "company_size": 8,
                "technical_fit": 9
            },
            "reasoning": "High-value opportunity with clear budget and decision-making authority"
        }
        
        response = client.put(f"/api/v1/leads/{lead_id}/score", json=score_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["lead_score"] == score_data["lead_score"]
        assert data["confidence"] == score_data["confidence"]
        assert data["scoring_factors"] == score_data["scoring_factors"]
    
    def test_get_lead_scoring_breakdown(self, client: TestClient, auth_headers, sample_lead_data):
        """Test getting detailed lead scoring breakdown."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        response = client.get(f"/api/v1/leads/{lead_id}/scoring", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "lead_score" in data
        assert "confidence" in data
        assert "scoring_factors" in data
        assert "ai_analysis" in data
        assert "recommendation" in data


class TestLeadConversion:
    """Test lead conversion tracking."""
    
    def test_convert_lead_to_opportunity(self, client: TestClient, auth_headers, sample_lead_data):
        """Test converting lead to business opportunity."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        conversion_data = {
            "opportunity_type": "consultation",
            "estimated_value_euros": 8000,
            "probability": 0.75,
            "expected_close_date": "2024-02-15",
            "engagement_scope": "3-month engineering leadership consultation",
            "decision_makers": ["CTO", "VP Engineering"]
        }
        
        response = client.post(f"/api/v1/leads/{lead_id}/convert", json=conversion_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["lead_id"] == lead_id
        assert data["opportunity_type"] == conversion_data["opportunity_type"]
        assert data["estimated_value_euros"] == conversion_data["estimated_value_euros"]
        assert data["status"] == "opportunity"
    
    def test_track_conversion_stage(self, client: TestClient, auth_headers, sample_lead_data):
        """Test tracking conversion pipeline stages."""
        # Create and convert lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        conversion_data = {
            "opportunity_type": "consultation",
            "estimated_value_euros": 5000,
            "probability": 0.6
        }
        client.post(f"/api/v1/leads/{lead_id}/convert", json=conversion_data, headers=auth_headers)
        
        # Update conversion stage
        stage_data = {
            "stage": "proposal_sent",
            "probability": 0.8,
            "notes": "Proposal sent for 3-month engagement"
        }
        
        response = client.put(f"/api/v1/leads/{lead_id}/conversion-stage", json=stage_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == stage_data["stage"]
        assert data["probability"] == stage_data["probability"]


class TestLeadAnalytics:
    """Test lead analytics functionality."""
    
    def test_get_lead_analytics(self, client: TestClient, auth_headers):
        """Test getting lead analytics overview."""
        response = client.get("/api/v1/leads/analytics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "leads_by_status" in data
        assert "leads_by_priority" in data
        assert "conversion_metrics" in data
        assert "pipeline_value" in data
        assert "lead_sources" in data
    
    def test_get_conversion_funnel(self, client: TestClient, auth_headers):
        """Test getting lead conversion funnel data."""
        response = client.get("/api/v1/leads/analytics/funnel", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert "conversion_rates" in data
        assert "total_value" in data
        
        # Verify funnel stage structure
        stages = data["stages"]
        assert isinstance(stages, list)
        if len(stages) > 0:
            stage = stages[0]
            assert "stage_name" in stage
            assert "count" in stage
            assert "value" in stage
    
    def test_get_lead_performance_by_content(self, client: TestClient, auth_headers):
        """Test getting lead performance attribution to content."""
        response = client.get("/api/v1/leads/analytics/by-content", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "content_performance" in data
        assert "top_performing_content" in data
        assert "lead_generation_trends" in data


class TestLeadCommunication:
    """Test lead communication functionality."""
    
    def test_send_follow_up_message(self, client: TestClient, auth_headers, sample_lead_data):
        """Test sending follow-up message to a lead."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        message_data = {
            "message_type": "linkedin_message",
            "subject": "Following up on your engineering leadership question",
            "content": "Hi Jane, I saw your comment about scaling engineering teams. I'd love to share some insights that might be helpful for your situation.",
            "template_id": "follow_up_template_1"
        }
        
        response = client.post(f"/api/v1/leads/{lead_id}/send-message", json=message_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["message_type"] == message_data["message_type"]
        assert data["subject"] == message_data["subject"]
        assert data["status"] == "sent"
        assert "sent_at" in data
    
    def test_schedule_follow_up(self, client: TestClient, auth_headers, sample_lead_data):
        """Test scheduling follow-up communication."""
        # Create lead first
        create_response = client.post("/api/v1/leads/detect", json=sample_lead_data, headers=auth_headers)
        lead_id = create_response.json()["id"]
        
        schedule_data = {
            "follow_up_type": "email",
            "scheduled_at": "2024-12-25T10:00:00Z",
            "message_template": "consultation_follow_up",
            "notes": "Follow up after holiday break"
        }
        
        response = client.post(f"/api/v1/leads/{lead_id}/schedule-follow-up", json=schedule_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["follow_up_type"] == schedule_data["follow_up_type"]
        assert data["scheduled_at"] == schedule_data["scheduled_at"]
        assert data["status"] == "scheduled"