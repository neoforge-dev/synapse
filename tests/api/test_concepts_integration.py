"""Integration tests for Epic 9.3 content strategy endpoints in concepts router."""

import pytest
from httpx import AsyncClient


class TestConceptExtractionEndpoints:
    """Test concept extraction and analysis endpoints."""

    @pytest.mark.asyncio
    async def test_concept_extraction(self, test_client: AsyncClient):
        """Test basic concept extraction functionality."""
        request_data = {
            "text": "FastAPI is a modern Python web framework with excellent performance and developer experience",
            "platform": "linkedin",
            "context": {"topic": "technical"}
        }

        response = await test_client.post("/api/v1/concepts/extract", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "concepts" in data
        assert "relationships" in data
        assert "extraction_time_ms" in data
        assert isinstance(data["concepts"], list)
        assert isinstance(data["relationships"], list)

    @pytest.mark.asyncio
    async def test_concept_search(self, test_client: AsyncClient):
        """Test concept search endpoint."""
        params = {
            "concept_types": ["technology", "framework"],
            "limit": 5
        }

        response = await test_client.get("/api/v1/concepts/search", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "concepts" in data
        assert "total_count" in data
        assert isinstance(data["concepts"], list)

    @pytest.mark.asyncio
    async def test_concept_correlation(self, test_client: AsyncClient):
        """Test concept correlation analysis."""
        request_data = {
            "concept_pairs": [
                {"concept_a": "FastAPI", "concept_b": "Python"},
                {"concept_a": "Performance", "concept_b": "Framework"}
            ],
            "analysis_type": "semantic"
        }

        response = await test_client.post("/api/v1/concepts/correlate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "correlations" in data
        assert "analysis_metadata" in data


class TestBeliefAnalysisEndpoints:
    """Test belief extraction and consistency analysis endpoints."""

    @pytest.mark.asyncio
    async def test_belief_extraction(self, test_client: AsyncClient):
        """Test belief extraction from content."""
        request_data = {
            "content": "I believe microservices are overused in most startups. Simple architectures win.",
            "extraction_config": {
                "confidence_threshold": 0.7,
                "include_implicit": True
            }
        }

        response = await test_client.post("/api/v1/concepts/beliefs/extract", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "beliefs" in data
        assert "confidence_scores" in data
        assert "extraction_metadata" in data

    @pytest.mark.asyncio
    async def test_belief_consistency_analysis(self, test_client: AsyncClient):
        """Test belief consistency checking."""
        params = {
            "belief_set": "technical_opinions",
            "time_range": "last_6_months"
        }

        response = await test_client.get("/api/v1/concepts/beliefs/consistency", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "consistency_score" in data
        assert "contradictions" in data
        assert "stability_metrics" in data


class TestHotTakeAnalysisEndpoints:
    """Test controversial content analysis and optimization endpoints."""

    @pytest.mark.asyncio
    async def test_hot_take_analysis(self, test_client: AsyncClient):
        """Test hot take analysis for controversial content."""
        request_data = {
            "content": "FastAPI isn't the silver bullet everyone claims. Here's why Flask might be better for your startup.",
            "platform": "linkedin",
            "analysis_depth": "comprehensive"
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "controversy_score" in data
        assert "engagement_prediction" in data
        assert "risk_assessment" in data
        assert "optimization_suggestions" in data

    @pytest.mark.asyncio
    async def test_quick_score_endpoint(self, test_client: AsyncClient):
        """Test quick scoring for content engagement potential."""
        request_data = {
            "content": "Microservices are killing startup productivity",
            "platform": "linkedin"
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/quick-score", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "engagement_score" in data
        assert "controversy_level" in data
        assert "recommendation" in data

    @pytest.mark.asyncio
    async def test_content_optimization(self, test_client: AsyncClient):
        """Test content optimization for better engagement."""
        request_data = {
            "original_content": "I think FastAPI has some limitations",
            "optimization_goals": ["increase_engagement", "maintain_authenticity"],
            "platform": "linkedin"
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/optimize", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "optimized_content" in data
        assert "improvement_score" in data
        assert "optimization_rationale" in data

    @pytest.mark.asyncio
    async def test_trending_analysis(self, test_client: AsyncClient):
        """Test trending hot takes identification."""
        params = {
            "time_window": "7d",
            "platform": "linkedin",
            "category": "technical"
        }

        response = await test_client.get("/api/v1/concepts/hot-takes/trending", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "trending_topics" in data
        assert "engagement_metrics" in data
        assert "trend_analysis" in data

    @pytest.mark.asyncio
    async def test_batch_analysis(self, test_client: AsyncClient):
        """Test batch analysis of multiple hot takes."""
        request_data = {
            "content_items": [
                {"id": "1", "content": "FastAPI vs Flask: The controversial truth", "platform": "linkedin"},
                {"id": "2", "content": "Why microservices are overhyped", "platform": "twitter"},
                {"id": "3", "content": "The Docker debate nobody talks about", "platform": "linkedin"}
            ],
            "analysis_options": {
                "include_optimization": True,
                "risk_assessment": True
            }
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/batch-analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "batch_summary" in data
        assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_safety_check(self, test_client: AsyncClient):
        """Test brand safety checking for controversial content."""
        request_data = {
            "content": "Here's my controversial take on startup culture",
            "safety_level": "corporate",
            "context": {"industry": "technology", "audience": "professionals"}
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/safety-check", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "safety_score" in data
        assert "risk_factors" in data
        assert "recommendations" in data


class TestAudienceIntelligenceEndpoints:
    """Test audience analysis and segmentation endpoints."""

    @pytest.mark.asyncio
    async def test_audience_analysis(self, test_client: AsyncClient):
        """Test audience analysis for content targeting."""
        request_data = {
            "content": "FastAPI performance optimization techniques for enterprise applications",
            "platform": "linkedin",
            "analysis_depth": "detailed"
        }

        response = await test_client.post("/api/v1/concepts/audience/analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "target_audience" in data
        assert "engagement_predictions" in data
        assert "demographic_insights" in data

    @pytest.mark.asyncio
    async def test_resonance_analysis(self, test_client: AsyncClient):
        """Test content resonance analysis with specific audiences."""
        request_data = {
            "content": "The hidden costs of technical debt in startup scaling",
            "target_segments": ["startup_founders", "technical_leaders"],
            "platform": "linkedin"
        }

        response = await test_client.post("/api/v1/concepts/audience/resonance", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "resonance_scores" in data
        assert "segment_analysis" in data
        assert "optimization_suggestions" in data

    @pytest.mark.asyncio
    async def test_audience_segments(self, test_client: AsyncClient):
        """Test audience segmentation analysis."""
        params = {
            "platform": "linkedin",
            "content_category": "technical",
            "include_demographics": True
        }

        response = await test_client.get("/api/v1/concepts/audience/segments", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "segments" in data
        assert "segment_characteristics" in data
        assert "targeting_recommendations" in data


class TestAnalyticsEndpoints:
    """Test analytics and insights endpoints."""

    @pytest.mark.asyncio
    async def test_analytics_gaps(self, test_client: AsyncClient):
        """Test content gap analysis."""
        params = {
            "platform": "linkedin",
            "time_range": "30d",
            "category": "technical"
        }

        response = await test_client.get("/api/v1/concepts/analytics/gaps", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "content_gaps" in data
        assert "opportunity_scores" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_platform_transitions(self, test_client: AsyncClient):
        """Test platform transition analysis."""
        params = {
            "source_platform": "linkedin",
            "target_platform": "twitter",
            "content_type": "technical"
        }

        response = await test_client.get("/api/v1/concepts/analytics/platform-transitions", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "transition_strategy" in data
        assert "adaptation_suggestions" in data
        assert "success_predictions" in data

    @pytest.mark.asyncio
    async def test_hot_takes_analytics(self, test_client: AsyncClient):
        """Test hot takes analytics dashboard."""
        params = {
            "time_range": "30d",
            "platform": "linkedin",
            "include_trends": True
        }

        response = await test_client.get("/api/v1/concepts/hot-takes/analytics", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "performance_metrics" in data
        assert "trend_analysis" in data
        assert "success_patterns" in data


class TestWorkflowIntegrationEndpoints:
    """Test end-to-end workflow integration scenarios."""

    @pytest.mark.asyncio
    async def test_content_strategy_workflow(self, test_client: AsyncClient):
        """Test complete content strategy workflow from analysis to optimization."""
        # Step 1: Analyze original content
        analysis_request = {
            "content": "Here's why I think FastAPI is overrated for most startups",
            "platform": "linkedin",
            "analysis_depth": "comprehensive"
        }

        analysis_response = await test_client.post("/api/v1/concepts/hot-takes/analyze", json=analysis_request)
        assert analysis_response.status_code == 200
        analysis_response.json()

        # Step 2: Check brand safety
        safety_request = {
            "content": analysis_request["content"],
            "safety_level": "corporate",
            "context": {"industry": "technology"}
        }

        safety_response = await test_client.post("/api/v1/concepts/hot-takes/safety-check", json=safety_request)
        assert safety_response.status_code == 200
        safety_data = safety_response.json()

        # Step 3: Optimize content if safe
        if safety_data["safety_score"] > 0.7:
            optimization_request = {
                "original_content": analysis_request["content"],
                "optimization_goals": ["increase_engagement", "maintain_safety"],
                "platform": "linkedin"
            }

            optimization_response = await test_client.post("/api/v1/concepts/hot-takes/optimize", json=optimization_request)
            assert optimization_response.status_code == 200
            optimization_data = optimization_response.json()

            # Verify optimization improved the content
            assert "optimized_content" in optimization_data
            assert "improvement_score" in optimization_data

    @pytest.mark.asyncio
    async def test_audience_content_matching_workflow(self, test_client: AsyncClient):
        """Test workflow for matching content to specific audience segments."""
        # Step 1: Get available audience segments
        segments_response = await test_client.get("/api/v1/concepts/audience/segments", params={
            "platform": "linkedin",
            "content_category": "technical"
        })
        assert segments_response.status_code == 200
        segments_data = segments_response.json()

        # Step 2: Analyze content for audience targeting
        content_analysis_request = {
            "content": "Advanced Python async programming patterns for scalable applications",
            "platform": "linkedin",
            "analysis_depth": "detailed"
        }

        audience_response = await test_client.post("/api/v1/concepts/audience/analyze", json=content_analysis_request)
        assert audience_response.status_code == 200
        audience_response.json()

        # Step 3: Test resonance with specific segments
        if segments_data["segments"]:
            resonance_request = {
                "content": content_analysis_request["content"],
                "target_segments": [segments_data["segments"][0]["id"]] if segments_data["segments"] else ["technical_leaders"],
                "platform": "linkedin"
            }

            resonance_response = await test_client.post("/api/v1/concepts/audience/resonance", json=resonance_request)
            assert resonance_response.status_code == 200
            resonance_data = resonance_response.json()

            # Verify resonance analysis provides actionable insights
            assert "resonance_scores" in resonance_data
            assert "optimization_suggestions" in resonance_data


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for Epic 9.3 endpoints."""

    @pytest.mark.asyncio
    async def test_invalid_content_extraction(self, test_client: AsyncClient):
        """Test concept extraction with invalid or empty content."""
        request_data = {
            "text": "",  # Empty content
            "platform": "linkedin"
        }

        response = await test_client.post("/api/v1/concepts/extract", json=request_data)

        # Should handle gracefully, either with 400 or empty results
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_malformed_batch_request(self, test_client: AsyncClient):
        """Test batch analysis with malformed request data."""
        request_data = {
            "content_items": [
                {"id": "1"},  # Missing required content field
                {"content": "Valid content", "platform": "linkedin"}
            ]
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/batch-analyze", json=request_data)

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unsupported_platform(self, test_client: AsyncClient):
        """Test endpoints with unsupported platform values."""
        request_data = {
            "content": "Test content",
            "platform": "unsupported_platform"
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/analyze", json=request_data)

        # Should handle gracefully or return appropriate error
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_large_content_handling(self, test_client: AsyncClient):
        """Test endpoints with very large content inputs."""
        large_content = "Large content " * 1000  # Very large content

        request_data = {
            "content": large_content,
            "platform": "linkedin"
        }

        response = await test_client.post("/api/v1/concepts/hot-takes/analyze", json=request_data)

        # Should handle large content gracefully
        assert response.status_code in [200, 413, 422]
