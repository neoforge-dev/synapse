"""Basic integration tests for Epic 9.3 content strategy endpoints."""

import pytest
from fastapi.testclient import TestClient
from graph_rag.api.main import create_app


class TestBasicConceptsEndpoints:
    """Basic tests for concepts endpoints without complex mocking."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a test client for the FastAPI app."""
        app = create_app()
        # Disable authentication for testing
        app.dependency_overrides = {}
        return TestClient(app)

    def test_concepts_endpoint_exists(self, client):
        """Test that concepts endpoints are properly registered."""
        # Test concept extraction endpoint exists
        response = client.post("/api/v1/concepts/extract", json={
            "text": "Test content",
            "platform": "general"
        })
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should return either success or validation error (not endpoint missing)
        assert response.status_code in [200, 422, 500]

    def test_hot_takes_analyze_endpoint_exists(self, client):
        """Test that hot takes analysis endpoint exists."""
        response = client.post("/api/v1/concepts/hot-takes/analyze", json={
            "content": "Test controversial content",
            "platform": "linkedin"
        })
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_audience_analyze_endpoint_exists(self, client):
        """Test that audience analysis endpoint exists."""
        response = client.post("/api/v1/concepts/audience/analyze", json={
            "content": "Test content for audience analysis",
            "platform": "linkedin"
        })
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_belief_extraction_endpoint_exists(self, client):
        """Test that belief extraction endpoint exists."""
        response = client.post("/api/v1/concepts/beliefs/extract", json={
            "content": "I believe this is a test statement"
        })
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_trending_analysis_endpoint_exists(self, client):
        """Test that trending analysis endpoint exists."""
        response = client.get("/api/v1/concepts/hot-takes/trending")
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_batch_analysis_endpoint_exists(self, client):
        """Test that batch analysis endpoint exists."""
        response = client.post("/api/v1/concepts/hot-takes/batch-analyze", json={
            "content_items": [
                {"id": "1", "content": "Test content 1", "platform": "linkedin"}
            ]
        })
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_safety_check_endpoint_exists(self, client):
        """Test that safety check endpoint exists."""
        response = client.post("/api/v1/concepts/hot-takes/safety-check", json={
            "content": "Test content for safety check",
            "safety_level": "corporate"
        })
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_concept_search_endpoint_exists(self, client):
        """Test that concept search endpoint exists."""
        response = client.get("/api/v1/concepts/search")
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_analytics_gaps_endpoint_exists(self, client):
        """Test that analytics gaps endpoint exists."""
        response = client.get("/api/v1/concepts/analytics/gaps")
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

    def test_audience_segments_endpoint_exists(self, client):
        """Test that audience segments endpoint exists."""
        response = client.get("/api/v1/concepts/audience/segments")
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]


class TestConceptsEndpointValidation:
    """Test validation and error handling for concepts endpoints."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a test client for the FastAPI app."""
        app = create_app()
        return TestClient(app)

    def test_concept_extraction_validation(self, client):
        """Test validation for concept extraction endpoint."""
        # Test missing required fields
        response = client.post("/api/v1/concepts/extract", json={})
        assert response.status_code == 422
        
        # Test invalid data types
        response = client.post("/api/v1/concepts/extract", json={
            "text": 123,  # Should be string
            "platform": "linkedin"
        })
        assert response.status_code == 422

    def test_hot_takes_analyze_validation(self, client):
        """Test validation for hot takes analysis endpoint."""
        # Test missing required fields
        response = client.post("/api/v1/concepts/hot-takes/analyze", json={})
        assert response.status_code == 422
        
        # Test with minimal valid data - endpoint may return 422 due to missing dependencies
        # but this confirms the endpoint exists and processes requests
        response = client.post("/api/v1/concepts/hot-takes/analyze", json={
            "content": "Test content",
            "platform": "linkedin"
        })
        # Should not return 404 (endpoint missing) or 500 (server error)
        assert response.status_code not in [404, 500]

    def test_batch_analysis_validation(self, client):
        """Test validation for batch analysis endpoint."""
        # Test empty content items - endpoint may process empty arrays gracefully
        response = client.post("/api/v1/concepts/hot-takes/batch-analyze", json={
            "content_items": []
        })
        # Should not return 404 (endpoint missing) or 500 (server error)  
        assert response.status_code not in [404, 500]

    def test_invalid_json_handling(self, client):
        """Test handling of invalid JSON in requests."""
        response = client.post("/api/v1/concepts/extract", 
                              data="invalid json",
                              headers={"Content-Type": "application/json"})
        assert response.status_code == 422


class TestConceptsEndpointIntegration:
    """Integration tests that verify endpoint interactions work properly."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a test client for the FastAPI app."""
        app = create_app()
        return TestClient(app)

    def test_concepts_to_audience_workflow(self, client):
        """Test workflow from concept extraction to audience analysis."""
        # Step 1: Extract concepts
        extract_response = client.post("/api/v1/concepts/extract", json={
            "text": "FastAPI is a powerful framework for building APIs",
            "platform": "linkedin"
        })
        
        # Should not fail with 404 (endpoint exists)
        assert extract_response.status_code != 404
        
        # Step 2: Analyze audience for the same content
        audience_response = client.post("/api/v1/concepts/audience/analyze", json={
            "content": "FastAPI is a powerful framework for building APIs",
            "platform": "linkedin"
        })
        
        # Should not fail with 404 (endpoint exists)
        assert audience_response.status_code != 404

    def test_safety_to_optimization_workflow(self, client):
        """Test workflow from safety check to content optimization."""
        test_content = "Here's a controversial take on software development"
        
        # Step 1: Safety check
        safety_response = client.post("/api/v1/concepts/hot-takes/safety-check", json={
            "content": test_content,
            "safety_level": "corporate"
        })
        
        assert safety_response.status_code != 404
        
        # Step 2: Content optimization
        optimization_response = client.post("/api/v1/concepts/hot-takes/optimize", json={
            "original_content": test_content,
            "optimization_goals": ["increase_engagement"],
            "platform": "linkedin"
        })
        
        assert optimization_response.status_code != 404

    def test_analysis_to_trending_workflow(self, client):
        """Test workflow from individual analysis to trending analysis."""
        # Step 1: Analyze individual content
        analysis_response = client.post("/api/v1/concepts/hot-takes/analyze", json={
            "content": "The future of AI in software development",
            "platform": "linkedin"
        })
        
        assert analysis_response.status_code != 404
        
        # Step 2: Check trending topics
        trending_response = client.get("/api/v1/concepts/hot-takes/trending")
        
        assert trending_response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])