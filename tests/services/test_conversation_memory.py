"""Tests for conversation memory system."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from graph_rag.services.memory.context_manager import ContextManager
from graph_rag.services.memory.conversation_memory import (
    ConversationMemoryManager,
    ConversationSession,
    Interaction,
)


class TestConversationMemoryManager:
    """Test conversation memory management capabilities."""

    @pytest.fixture
    def memory_manager(self):
        """Create a ConversationMemoryManager for testing."""
        return ConversationMemoryManager()

    @pytest.mark.asyncio
    async def test_start_conversation(self, memory_manager):
        """Test starting a new conversation."""
        user_id = "user123"
        conversation_id = await memory_manager.start_conversation(user_id)

        # Should return a valid conversation ID
        assert conversation_id is not None
        assert isinstance(conversation_id, str)
        assert len(conversation_id) > 0

        # Should create a conversation session
        session = await memory_manager.get_conversation_session(conversation_id)
        assert session is not None
        assert session.conversation_id == conversation_id
        assert session.user_id == user_id
        assert len(session.interactions) == 0

    @pytest.mark.asyncio
    async def test_add_interaction(self, memory_manager):
        """Test adding interactions to a conversation."""
        user_id = "user123"
        conversation_id = await memory_manager.start_conversation(user_id)

        question = "What is GraphRAG?"
        answer = "GraphRAG combines knowledge graphs with retrieval augmented generation..."

        await memory_manager.add_interaction(conversation_id, question, answer)

        session = await memory_manager.get_conversation_session(conversation_id)
        assert len(session.interactions) == 1

        interaction = session.interactions[0]
        assert interaction.question == question
        assert interaction.answer == answer
        assert interaction.timestamp is not None

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, memory_manager):
        """Test retrieving conversation history."""
        user_id = "user123"
        conversation_id = await memory_manager.start_conversation(user_id)

        # Add multiple interactions
        interactions = [
            ("What is GraphRAG?", "GraphRAG combines knowledge graphs..."),
            ("How does it work?", "It works by first extracting entities..."),
            ("What are the benefits?", "Benefits include better context awareness...")
        ]

        for question, answer in interactions:
            await memory_manager.add_interaction(conversation_id, question, answer)

        history = await memory_manager.get_conversation_history(conversation_id)
        assert len(history) == 3

        # Should be in chronological order
        for i, (expected_question, expected_answer) in enumerate(interactions):
            assert history[i].question == expected_question
            assert history[i].answer == expected_answer

    @pytest.mark.asyncio
    async def test_conversation_not_found(self, memory_manager):
        """Test handling of non-existent conversation."""
        non_existent_id = str(uuid.uuid4())

        session = await memory_manager.get_conversation_session(non_existent_id)
        assert session is None

        history = await memory_manager.get_conversation_history(non_existent_id)
        assert history == []

    @pytest.mark.asyncio
    async def test_memory_limit_truncation(self, memory_manager):
        """Test that memory is truncated when limit is reached."""
        # Set small memory limit for testing
        memory_manager.max_interactions_per_conversation = 3

        user_id = "user123"
        conversation_id = await memory_manager.start_conversation(user_id)

        # Add more interactions than the limit
        for i in range(5):
            await memory_manager.add_interaction(
                conversation_id,
                f"Question {i}",
                f"Answer {i}"
            )

        history = await memory_manager.get_conversation_history(conversation_id)
        # Should only keep the most recent interactions
        assert len(history) == 3
        # Should keep the last 3 interactions
        assert history[0].question == "Question 2"
        assert history[1].question == "Question 3"
        assert history[2].question == "Question 4"

    @pytest.mark.asyncio
    async def test_conversation_summarization(self, memory_manager):
        """Test conversation summarization when memory limit is reached."""
        # Configure memory manager for summarization
        memory_manager.max_interactions_per_conversation = 2
        memory_manager.enable_summarization = True

        user_id = "user123"
        conversation_id = await memory_manager.start_conversation(user_id)

        # Add interactions beyond limit
        interactions = [
            ("What is AI?", "AI stands for Artificial Intelligence..."),
            ("What is ML?", "ML stands for Machine Learning..."),
            ("What is DL?", "DL stands for Deep Learning...")
        ]

        for question, answer in interactions:
            await memory_manager.add_interaction(conversation_id, question, answer)

        session = await memory_manager.get_conversation_session(conversation_id)

        # Should have summary and recent interactions
        assert session.summary is not None
        assert len(session.interactions) == 1  # Most recent interactions (keep_recent = max(2//2, 1) = 1)

        # Should contain information about the conversation
        assert "AI" in session.summary or "Artificial Intelligence" in session.summary


class TestContextManager:
    """Test context management capabilities."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create a mock ConversationMemoryManager."""
        memory_manager = AsyncMock(spec=ConversationMemoryManager)
        return memory_manager

    @pytest.fixture
    def context_manager(self, mock_memory_manager):
        """Create a ContextManager for testing."""
        return ContextManager(mock_memory_manager)

    @pytest.mark.asyncio
    async def test_start_conversation(self, context_manager, mock_memory_manager):
        """Test starting a conversation through context manager."""
        user_id = "user123"
        mock_memory_manager.start_conversation.return_value = "conv_123"

        conversation_id = await context_manager.start_conversation(user_id)

        assert conversation_id == "conv_123"
        mock_memory_manager.start_conversation.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_add_interaction(self, context_manager, mock_memory_manager):
        """Test adding interaction through context manager."""
        conversation_id = "conv_123"
        question = "What is GraphRAG?"
        answer = "GraphRAG combines..."

        await context_manager.add_interaction(conversation_id, question, answer)

        mock_memory_manager.add_interaction.assert_called_once_with(
            conversation_id, question, answer, None
        )

    @pytest.mark.asyncio
    async def test_get_conversation_context(self, context_manager, mock_memory_manager):
        """Test getting conversation context."""
        conversation_id = "conv_123"

        # Mock interaction history
        mock_interactions = [
            Interaction(
                question="What is GraphRAG?",
                answer="GraphRAG combines knowledge graphs...",
                timestamp=datetime.now()
            ),
            Interaction(
                question="How does it work?",
                answer="It extracts entities and relationships...",
                timestamp=datetime.now()
            )
        ]

        mock_session = ConversationSession(
            conversation_id=conversation_id,
            user_id="user123",
            interactions=mock_interactions,
            summary="Previous discussion about GraphRAG basics"
        )

        mock_memory_manager.get_conversation_session.return_value = mock_session

        context = await context_manager.get_conversation_context(conversation_id)

        assert context is not None
        assert "GraphRAG combines knowledge graphs" in context
        assert "It extracts entities and relationships" in context
        assert "Previous discussion about GraphRAG basics" in context

    @pytest.mark.asyncio
    async def test_get_conversation_context_no_session(self, context_manager, mock_memory_manager):
        """Test getting context for non-existent conversation."""
        conversation_id = "non_existent"
        mock_memory_manager.get_conversation_session.return_value = None

        context = await context_manager.get_conversation_context(conversation_id)

        assert context == ""

    @pytest.mark.asyncio
    async def test_context_formatting(self, context_manager, mock_memory_manager):
        """Test that context is properly formatted for LLM consumption."""
        conversation_id = "conv_123"

        mock_interactions = [
            Interaction(
                question="What is the capital of France?",
                answer="The capital of France is Paris.",
                timestamp=datetime.now()
            )
        ]

        mock_session = ConversationSession(
            conversation_id=conversation_id,
            user_id="user123",
            interactions=mock_interactions,
            summary=None
        )

        mock_memory_manager.get_conversation_session.return_value = mock_session

        context = await context_manager.get_conversation_context(conversation_id)

        # Context should be formatted for LLM consumption
        assert "Previous conversation:" in context
        assert "User: What is the capital of France?" in context
        assert "Assistant: The capital of France is Paris." in context


class TestConversationModels:
    """Test conversation memory data models."""

    def test_interaction_creation(self):
        """Test creating an Interaction."""
        question = "What is AI?"
        answer = "AI stands for Artificial Intelligence"
        timestamp = datetime.now()

        interaction = Interaction(
            question=question,
            answer=answer,
            timestamp=timestamp
        )

        assert interaction.question == question
        assert interaction.answer == answer
        assert interaction.timestamp == timestamp

    def test_conversation_session_creation(self):
        """Test creating a ConversationSession."""
        conversation_id = "conv_123"
        user_id = "user456"

        session = ConversationSession(
            conversation_id=conversation_id,
            user_id=user_id,
            interactions=[],
            summary=None
        )

        assert session.conversation_id == conversation_id
        assert session.user_id == user_id
        assert session.interactions == []
        assert session.summary is None
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_conversation_session_add_interaction(self):
        """Test adding interaction to conversation session."""
        session = ConversationSession(
            conversation_id="conv_123",
            user_id="user456",
            interactions=[],
            summary=None
        )

        interaction = Interaction(
            question="Test question",
            answer="Test answer",
            timestamp=datetime.now()
        )

        session.add_interaction(interaction)

        assert len(session.interactions) == 1
        assert session.interactions[0] == interaction
        # updated_at should be refreshed
        assert session.updated_at >= session.created_at
