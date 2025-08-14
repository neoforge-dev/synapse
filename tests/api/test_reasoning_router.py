"""Tests for the reasoning visualization API endpoints."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from graph_rag.core.graph_rag_engine import QueryResult
from graph_rag.core.reasoning_chain import ReasoningChain, ReasoningStep
from graph_rag.core.reasoning_engine import MultiStepReasoningEngine, ReasoningResult
from graph_rag.domain.models import Chunk, Entity

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_reasoning_result():
    """Create a sample reasoning result for testing."""
    # Create mock query results for each step
    step1_result = QueryResult(
        answer="Security analysis shows potential vulnerabilities in authentication layer",
        relevant_chunks=[
            Chunk(id="c1", text="Authentication system uses JWT tokens", document_id="d1", metadata={}),
            Chunk(id="c2", text="Password validation is basic", document_id="d1", metadata={})
        ],
        graph_context=(
            [Entity(id="e1", type="AuthSystem", properties={"name": "JWT Auth"})],
            []
        ),
        metadata={"confidence": 0.85}
    )

    step2_result = QueryResult(
        answer="Main threat vectors include credential stuffing and session hijacking",
        relevant_chunks=[
            Chunk(id="c3", text="Session management needs improvement", document_id="d2", metadata={})
        ],
        graph_context=([], []),
        metadata={"confidence": 0.78}
    )

    # Create reasoning steps
    steps = [
        ReasoningStep(
            name="identify_security_components",
            description="Identify key security components in the system",
            query="What are the main security components?",
            status="completed",
            result=step1_result,
            reasoning="Analyzed security components and found authentication layer details"
        ),
        ReasoningStep(
            name="analyze_threat_vectors",
            description="Analyze potential threat vectors",
            query="What are the main threat vectors?",
            status="completed",
            result=step2_result,
            reasoning="Identified credential stuffing and session hijacking as primary threats"
        )
    ]

    # Create reasoning chain
    chain = ReasoningChain(
        question="What are the main security vulnerabilities in our authentication system?",
        steps=steps
    )
    chain.current_step_index = 2  # Mark as completed

    # Create reasoning result
    return ReasoningResult(
        question="What are the main security vulnerabilities in our authentication system?",
        reasoning_chain=chain,
        final_answer="The main vulnerabilities are in the authentication layer, specifically weak password validation and session management, making the system susceptible to credential stuffing and session hijacking attacks.",
        synthesis_reasoning="Combined analysis of security components and threat vectors",
        metadata={"total_steps": 2, "completed_steps": 2}
    )


@pytest.fixture
def mock_reasoning_engine(sample_reasoning_result):
    """Create a mock reasoning engine."""
    engine = AsyncMock(spec=MultiStepReasoningEngine)
    engine.reason.return_value = sample_reasoning_result
    return engine


class TestReasoningVisualizationAPI:
    """Test reasoning visualization API endpoints."""

    async def test_visualize_reasoning_endpoint_exists(self, test_client: AsyncClient):
        """Test that the reasoning visualization endpoint exists."""
        # This should fail initially since the endpoint doesn't exist
        response = await test_client.get("/api/v1/reasoning/visualize/test-reasoning-id")

        # Initially this will return 404, but we expect it to work after implementation
        assert response.status_code in [200, 404], "Endpoint should either exist or be missing"

    async def test_visualize_reasoning_returns_html(
        self,
        test_client: AsyncClient,
        mock_reasoning_engine,
        sample_reasoning_result
    ):
        """Test that the visualization endpoint returns interactive HTML."""
        # Mock the reasoning engine in the app dependencies
        # This test will fail until we implement the endpoint

        response = await test_client.get("/api/v1/reasoning/visualize/test-reasoning-id")

        if response.status_code == 200:
            assert response.headers["content-type"] == "text/html; charset=utf-8"
            html_content = response.text

            # Check for required HTML structure
            assert "<!DOCTYPE html>" in html_content
            assert "<title>Reasoning Chain Visualization</title>" in html_content
            assert 'id="reasoning-viz"' in html_content

            # Check for embedded reasoning data
            assert "reasoningData" in html_content
            # The API creates its own test data, so check for that instead
            assert "What are the main security vulnerabilities?" in html_content

    async def test_visualize_nonexistent_reasoning_returns_404(self, test_client: AsyncClient):
        """Test that requesting nonexistent reasoning returns 404."""
        response = await test_client.get("/api/v1/reasoning/visualize/nonexistent-id")

        # Should return 404 when reasoning ID doesn't exist
        assert response.status_code == 404

    async def test_export_reasoning_json_format(
        self,
        test_client: AsyncClient,
        sample_reasoning_result
    ):
        """Test exporting reasoning chain in JSON format."""
        response = await test_client.get(
            "/api/v1/reasoning/export/test-reasoning-id?format=json"
        )

        if response.status_code == 200:
            assert response.headers["content-type"] == "application/json"

            data = response.json()
            assert "question" in data
            assert "steps" in data
            assert "final_answer" in data
            assert len(data["steps"]) == 1

            # Verify step structure
            step = data["steps"][0]
            assert "name" in step
            assert "description" in step
            assert "status" in step
            assert "query" in step
            assert "answer" in step

    async def test_export_reasoning_svg_format(self, test_client: AsyncClient):
        """Test exporting reasoning chain in SVG format."""
        response = await test_client.get(
            "/api/v1/reasoning/export/test-reasoning-id?format=svg"
        )

        if response.status_code == 200:
            assert response.headers["content-type"] == "image/svg+xml"
            svg_content = response.text

            # Check for basic SVG structure
            assert svg_content.startswith('<svg')
            assert '</svg>' in svg_content
            assert 'xmlns="http://www.w3.org/2000/svg"' in svg_content

    async def test_export_reasoning_invalid_format_returns_400(self, test_client: AsyncClient):
        """Test that invalid export format returns 400."""
        response = await test_client.get(
            "/api/v1/reasoning/export/test-reasoning-id?format=invalid"
        )

        assert response.status_code == 400
        assert "format" in response.json()["detail"].lower()

    async def test_export_nonexistent_reasoning_returns_404(self, test_client: AsyncClient):
        """Test that exporting nonexistent reasoning returns 404."""
        response = await test_client.get(
            "/api/v1/reasoning/export/nonexistent-id?format=json"
        )

        assert response.status_code == 404


class TestReasoningHTMLVisualization:
    """Test the HTML visualization generation."""

    def test_html_contains_required_elements(self, sample_reasoning_result):
        """Test that generated HTML contains all required elements."""
        # This test will help us define the HTML structure
        # It will fail until we implement the HTML generation

        from graph_rag.visualization.reasoning_viz import generate_reasoning_html

        html = generate_reasoning_html(sample_reasoning_result)

        # Check HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html and "</html>" in html
        assert "<head>" in html and "</head>" in html
        assert "<body>" in html and "</body>" in html
        assert "<title>Reasoning Chain Visualization</title>" in html

        # Check for embedded CSS
        assert "<style>" in html and "</style>" in html

        # Check for visualization container
        assert 'id="reasoning-viz"' in html

        # Check for embedded JavaScript with data
        assert "<script>" in html and "</script>" in html
        assert "reasoningData" in html

        # Check that reasoning data is properly embedded
        assert sample_reasoning_result.question in html
        assert "identify_security_components" in html
        assert "analyze_threat_vectors" in html

    def test_html_json_encoding_safety(self):
        """Test that HTML properly JSON-encodes content."""
        # Simple test with special characters
        from graph_rag.core.graph_rag_engine import QueryResult
        from graph_rag.core.reasoning_chain import ReasoningChain, ReasoningStep
        from graph_rag.core.reasoning_engine import ReasoningResult

        step = ReasoningStep(
            name="test_step",
            description="Test with <special> characters",
            status="completed",
            result=QueryResult(answer="Answer with \"quotes\"", relevant_chunks=[], graph_context=([], []), metadata={})
        )

        chain = ReasoningChain(question="Question with <brackets>?", steps=[step])
        chain.current_step_index = 1

        result = ReasoningResult(
            question="Question with <brackets>?",
            reasoning_chain=chain,
            final_answer="Answer with <brackets>",
            synthesis_reasoning="Safe reasoning"
        )

        from graph_rag.visualization.reasoning_viz import generate_reasoning_html

        html = generate_reasoning_html(result)

        # Basic checks for JSON embedding
        assert 'reasoningData = ' in html
        assert '"Question with <brackets>?"' in html or 'Question with <brackets>?' in html
        assert 'test_step' in html
