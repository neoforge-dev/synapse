import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any, Dict, List
import uuid

from graph_rag.core.reasoning_engine import MultiStepReasoningEngine, ReasoningResult
from graph_rag.core.reasoning_chain import ReasoningChain, ReasoningStep
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine, QueryResult
from graph_rag.core.interfaces import (
    SearchResultData, 
    ChunkData, 
    GraphRepository, 
    VectorStore
)
from graph_rag.models import Chunk, Entity, Relationship


class TestReasoningChain:
    """Tests for the ReasoningChain class."""

    def test_reasoning_chain_creation(self):
        """Test basic creation of a reasoning chain."""
        chain = ReasoningChain(
            question="What are the security implications of our API design?",
            steps=["identify_api_endpoints", "analyze_auth_patterns"]
        )
        
        assert chain.question == "What are the security implications of our API design?"
        assert len(chain.steps) == 2
        assert chain.current_step_index == 0
        assert chain.is_complete is False

    def test_reasoning_step_creation(self):
        """Test creation of individual reasoning steps."""
        step = ReasoningStep(
            name="identify_api_endpoints",
            description="Identify all API endpoints in the system",
            query="What API endpoints exist in the system?",
            status="pending"
        )
        
        assert step.name == "identify_api_endpoints"
        assert step.status == "pending"
        assert step.result is None

    def test_reasoning_chain_next_step(self):
        """Test advancing to the next step in the chain."""
        chain = ReasoningChain(
            question="Test question",
            steps=["step1", "step2", "step3"]
        )
        
        # Initially at step 0
        assert chain.current_step_index == 0
        assert chain.is_complete is False
        
        # Advance to next step
        chain.advance_to_next_step()
        assert chain.current_step_index == 1
        assert chain.is_complete is False
        
        # Advance again
        chain.advance_to_next_step()
        assert chain.current_step_index == 2
        assert chain.is_complete is False
        
        # Advance one more time to complete
        chain.advance_to_next_step()
        assert chain.current_step_index == 3
        assert chain.is_complete is True

    def test_reasoning_chain_get_current_step(self):
        """Test getting the current step from the chain."""
        chain = ReasoningChain(
            question="Test question",
            steps=["step1", "step2"]
        )
        
        current = chain.get_current_step()
        assert current.name == "step1"
        
        chain.advance_to_next_step()
        current = chain.get_current_step()
        assert current.name == "step2"


class TestMultiStepReasoningEngine:
    """Tests for the MultiStepReasoningEngine class."""

    @pytest.fixture
    def mock_graph_rag_engine(self) -> SimpleGraphRAGEngine:
        """Create a mock GraphRAGEngine for testing."""
        mock_graph_store = MagicMock(spec=GraphRepository)
        mock_vector_store = MagicMock(spec=VectorStore)
        mock_entity_extractor = MagicMock()
        
        engine = SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor
        )
        
        # Mock the query method
        engine.query = AsyncMock(return_value=QueryResult(
            answer="Mock answer",
            relevant_chunks=[],
            graph_context=None,
            metadata={}
        ))
        
        return engine

    @pytest.fixture
    def reasoning_engine(self, mock_graph_rag_engine) -> MultiStepReasoningEngine:
        """Create a MultiStepReasoningEngine for testing."""
        return MultiStepReasoningEngine(mock_graph_rag_engine)

    def test_reasoning_engine_creation(self, reasoning_engine):
        """Test basic creation of the reasoning engine."""
        assert reasoning_engine is not None
        assert reasoning_engine.graph_rag_engine is not None

    @pytest.mark.asyncio
    async def test_reason_with_predefined_steps(self, reasoning_engine):
        """Test reasoning with predefined steps."""
        question = "What are the security implications of our API design?"
        steps = [
            "identify_api_endpoints",
            "analyze_auth_patterns", 
            "check_vulnerability_patterns",
            "synthesize_recommendations"
        ]
        
        result = await reasoning_engine.reason(question=question, steps=steps)
        
        # Verify result structure
        assert isinstance(result, ReasoningResult)
        assert result.question == question
        assert result.reasoning_chain is not None
        assert len(result.reasoning_chain.steps) == 4
        assert result.reasoning_chain.is_complete is True
        assert result.final_answer is not None

    @pytest.mark.asyncio
    async def test_reason_with_step_dependencies(self, reasoning_engine):
        """Test that each step uses results from previous steps."""
        question = "How does user authentication work?"
        steps = ["find_auth_components", "analyze_auth_flow"]
        
        # Mock the graph_rag_engine to return different results for each step
        def mock_query_side_effect(query_text, config=None):
            # Check for more specific patterns - order matters!
            # The second step will contain context from first step, so check for analyze_auth_flow first
            if "analyze auth flow" in query_text and "Context from previous reasoning steps" in query_text:
                return QueryResult(
                    answer="Authentication flows through JWT validation",
                    relevant_chunks=[],
                    graph_context=None,
                    metadata={}
                )
            elif "find auth components" in query_text and "Focusing on find auth components" in query_text:
                return QueryResult(
                    answer="Found JWT tokens and OAuth components",
                    relevant_chunks=[],
                    graph_context=None,
                    metadata={}
                )
            else:
                return QueryResult(answer="Default answer", relevant_chunks=[], graph_context=None, metadata={})

        reasoning_engine.graph_rag_engine.query.side_effect = mock_query_side_effect
        
        result = await reasoning_engine.reason(question=question, steps=steps)
        
        # Verify that steps were executed in order
        assert result.reasoning_chain.steps[0].result.answer == "Found JWT tokens and OAuth components"
        assert result.reasoning_chain.steps[1].result.answer == "Authentication flows through JWT validation"
        
        # Verify that the second step's query included context from the first step
        calls = reasoning_engine.graph_rag_engine.query.call_args_list
        assert len(calls) >= 2
        
        # The second call should include context from the first step
        second_call_query = calls[1][0][0]  # First positional argument of second call
        assert "JWT tokens and OAuth components" in second_call_query

    @pytest.mark.asyncio
    async def test_reason_handles_step_failures(self, reasoning_engine):
        """Test that the reasoning engine handles individual step failures gracefully."""
        question = "Test question"
        steps = ["working_step", "failing_step", "final_step"]
        
        def mock_query_side_effect(query_text, config=None):
            # Only fail for the specific failing step, not synthesis
            if ("failing step" in query_text or "failing_step" in query_text) and "comprehensive answer" not in query_text:
                raise Exception("Step failed")
            return QueryResult(
                answer="Success",
                relevant_chunks=[],
                graph_context=None,
                metadata={}
            )

        reasoning_engine.graph_rag_engine.query.side_effect = mock_query_side_effect
        
        result = await reasoning_engine.reason(question=question, steps=steps)
        
        # Verify that failure was handled gracefully
        assert result.reasoning_chain.steps[0].status == "completed"
        assert result.reasoning_chain.steps[1].status == "failed"
        assert result.reasoning_chain.steps[2].status == "completed"
        
        # Should still provide a final answer
        assert result.final_answer is not None

    @pytest.mark.asyncio
    async def test_reason_provides_reasoning_transparency(self, reasoning_engine):
        """Test that the reasoning process is transparent and traceable."""
        question = "How does data flow through the system?"
        steps = ["identify_data_sources", "trace_data_flow"]
        
        result = await reasoning_engine.reason(question=question, steps=steps)
        
        # Verify reasoning transparency
        assert result.reasoning_chain is not None
        for step in result.reasoning_chain.steps:
            assert step.query is not None
            assert step.result is not None or step.status == "failed"
            assert step.reasoning is not None
        
        # Verify final synthesis
        assert result.final_answer != ""
        assert result.synthesis_reasoning is not None

    @pytest.mark.asyncio
    async def test_step_generation_from_question(self, reasoning_engine):
        """Test automatic step generation when no steps are provided."""
        question = "What are the main components of the system architecture?"
        
        # This should automatically generate appropriate reasoning steps
        result = await reasoning_engine.reason(question=question)
        
        assert result.reasoning_chain is not None
        assert len(result.reasoning_chain.steps) > 0
        assert result.final_answer is not None

    def test_reasoning_result_structure(self, reasoning_engine):
        """Test the structure of the reasoning result."""
        # Create a sample reasoning result manually to test structure
        from graph_rag.core.reasoning_chain import ReasoningChain
        from graph_rag.core.reasoning_engine import ReasoningResult
        
        chain = ReasoningChain("Test question", ["step1", "step2"])
        result = ReasoningResult(
            question="Test question",
            reasoning_chain=chain,
            final_answer="Test answer",
            synthesis_reasoning="Synthesized from steps",
            metadata={"test": "data"}
        )
        
        assert result.question == "Test question"
        assert result.reasoning_chain == chain
        assert result.final_answer == "Test answer"
        assert result.synthesis_reasoning == "Synthesized from steps"
        assert result.metadata["test"] == "data"


class TestGraphRAGEngineIntegration:
    """Test integration of reasoning engine with GraphRAGEngine."""

    @pytest.fixture
    def graph_rag_engine(self) -> SimpleGraphRAGEngine:
        """Create a SimpleGraphRAGEngine for integration testing."""
        mock_graph_store = MagicMock(spec=GraphRepository)
        mock_vector_store = MagicMock(spec=VectorStore)
        mock_entity_extractor = MagicMock()
        
        engine = SimpleGraphRAGEngine(
            graph_store=mock_graph_store,
            vector_store=mock_vector_store,
            entity_extractor=mock_entity_extractor
        )
        
        # Mock the query method to return consistent results
        engine.query = AsyncMock(return_value=QueryResult(
            answer="Integration test answer",
            relevant_chunks=[],
            graph_context=None,
            metadata={}
        ))
        
        return engine

    @pytest.mark.asyncio
    async def test_graph_rag_engine_reason_method(self, graph_rag_engine):
        """Test that GraphRAGEngine.reason method works correctly."""
        question = "How does the authentication system work?"
        steps = ["analyze_auth_flow", "identify_security_patterns"]
        
        result = await graph_rag_engine.reason(question=question, steps=steps)
        
        # Verify the reasoning result structure
        assert hasattr(result, 'question')
        assert hasattr(result, 'reasoning_chain')
        assert hasattr(result, 'final_answer')
        assert result.question == question
        assert len(result.reasoning_chain.steps) == 2

    @pytest.mark.asyncio
    async def test_graph_rag_engine_reason_auto_steps(self, graph_rag_engine):
        """Test that GraphRAGEngine.reason method works with auto-generated steps."""
        question = "What are the security implications of our API design?"
        
        result = await graph_rag_engine.reason(question=question)
        
        # Should auto-generate security-related steps
        assert result.question == question
        assert len(result.reasoning_chain.steps) > 0
        # Should contain security-related steps for this question
        step_names = [step.name for step in result.reasoning_chain.steps]
        assert any("security" in name for name in step_names)