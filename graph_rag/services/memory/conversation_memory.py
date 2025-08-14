"""Conversation memory management for maintaining context across interactions."""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

from graph_rag.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class Interaction:
    """Represents a single question-answer interaction in a conversation."""

    question: str
    answer: str
    timestamp: datetime
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class ConversationSession:
    """Represents a conversation session with history and metadata."""

    conversation_id: str
    user_id: str
    interactions: list[Interaction] = field(default_factory=list)
    summary: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, any] = field(default_factory=dict)

    def add_interaction(self, interaction: Interaction) -> None:
        """Add an interaction to this conversation session."""
        self.interactions.append(interaction)
        self.updated_at = datetime.now()


class ConversationMemoryBackend(Protocol):
    """Protocol for conversation memory storage backends."""

    async def save_session(self, session: ConversationSession) -> None:
        """Save a conversation session."""
        ...

    async def load_session(self, conversation_id: str) -> ConversationSession | None:
        """Load a conversation session by ID."""
        ...

    async def delete_session(self, conversation_id: str) -> bool:
        """Delete a conversation session."""
        ...

    async def list_user_conversations(self, user_id: str) -> list[str]:
        """List conversation IDs for a user."""
        ...


class InMemoryConversationBackend:
    """In-memory conversation storage backend."""

    def __init__(self):
        self._sessions: dict[str, ConversationSession] = {}
        self._user_conversations: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def save_session(self, session: ConversationSession) -> None:
        """Save a conversation session to memory."""
        async with self._lock:
            self._sessions[session.conversation_id] = session

            # Track conversation for user
            user_convs = self._user_conversations.setdefault(session.user_id, [])
            if session.conversation_id not in user_convs:
                user_convs.append(session.conversation_id)

    async def load_session(self, conversation_id: str) -> ConversationSession | None:
        """Load a conversation session from memory."""
        async with self._lock:
            return self._sessions.get(conversation_id)

    async def delete_session(self, conversation_id: str) -> bool:
        """Delete a conversation session from memory."""
        async with self._lock:
            session = self._sessions.pop(conversation_id, None)
            if session:
                # Remove from user conversations
                user_convs = self._user_conversations.get(session.user_id, [])
                if conversation_id in user_convs:
                    user_convs.remove(conversation_id)
                return True
            return False

    async def list_user_conversations(self, user_id: str) -> list[str]:
        """List conversation IDs for a user."""
        async with self._lock:
            return self._user_conversations.get(user_id, []).copy()


class FileConversationBackend:
    """File-based conversation storage backend."""

    def __init__(self, storage_path: str | None = None):
        self.storage_path = Path(storage_path) if storage_path else Path("./conversation_memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _get_session_file(self, conversation_id: str) -> Path:
        """Get file path for a conversation session."""
        return self.storage_path / f"{conversation_id}.json"

    def _get_user_index_file(self, user_id: str) -> Path:
        """Get file path for user's conversation index."""
        return self.storage_path / f"user_{user_id}.json"

    def _serialize_session(self, session: ConversationSession) -> dict:
        """Convert session to JSON-serializable dict."""
        return {
            "conversation_id": session.conversation_id,
            "user_id": session.user_id,
            "interactions": [
                {
                    "question": interaction.question,
                    "answer": interaction.answer,
                    "timestamp": interaction.timestamp.isoformat(),
                    "metadata": interaction.metadata
                }
                for interaction in session.interactions
            ],
            "summary": session.summary,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata
        }

    def _deserialize_session(self, data: dict) -> ConversationSession:
        """Convert dict to ConversationSession."""
        interactions = [
            Interaction(
                question=i["question"],
                answer=i["answer"],
                timestamp=datetime.fromisoformat(i["timestamp"]),
                metadata=i.get("metadata", {})
            )
            for i in data["interactions"]
        ]

        return ConversationSession(
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            interactions=interactions,
            summary=data.get("summary"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {})
        )

    async def save_session(self, session: ConversationSession) -> None:
        """Save a conversation session to file."""
        async with self._lock:
            try:
                session_file = self._get_session_file(session.conversation_id)
                session_data = self._serialize_session(session)

                # Write session data
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)

                # Update user index
                user_index_file = self._get_user_index_file(session.user_id)
                user_conversations = []

                if user_index_file.exists():
                    try:
                        with open(user_index_file, encoding='utf-8') as f:
                            user_conversations = json.load(f)
                    except (OSError, json.JSONDecodeError):
                        user_conversations = []

                if session.conversation_id not in user_conversations:
                    user_conversations.append(session.conversation_id)

                with open(user_index_file, 'w', encoding='utf-8') as f:
                    json.dump(user_conversations, f)

            except Exception as e:
                logger.error(f"Error saving conversation session {session.conversation_id}: {e}")
                raise

    async def load_session(self, conversation_id: str) -> ConversationSession | None:
        """Load a conversation session from file."""
        async with self._lock:
            try:
                session_file = self._get_session_file(conversation_id)
                if not session_file.exists():
                    return None

                with open(session_file, encoding='utf-8') as f:
                    session_data = json.load(f)

                return self._deserialize_session(session_data)

            except Exception as e:
                logger.error(f"Error loading conversation session {conversation_id}: {e}")
                return None

    async def delete_session(self, conversation_id: str) -> bool:
        """Delete a conversation session file."""
        async with self._lock:
            try:
                session_file = self._get_session_file(conversation_id)
                if not session_file.exists():
                    return False

                # Load session to get user_id for index cleanup
                session = await self.load_session(conversation_id)
                if session:
                    # Remove from user index
                    user_index_file = self._get_user_index_file(session.user_id)
                    if user_index_file.exists():
                        try:
                            with open(user_index_file, encoding='utf-8') as f:
                                user_conversations = json.load(f)

                            if conversation_id in user_conversations:
                                user_conversations.remove(conversation_id)

                            with open(user_index_file, 'w', encoding='utf-8') as f:
                                json.dump(user_conversations, f)
                        except (OSError, json.JSONDecodeError):
                            pass

                # Delete session file
                session_file.unlink()
                return True

            except Exception as e:
                logger.error(f"Error deleting conversation session {conversation_id}: {e}")
                return False

    async def list_user_conversations(self, user_id: str) -> list[str]:
        """List conversation IDs for a user."""
        async with self._lock:
            try:
                user_index_file = self._get_user_index_file(user_id)
                if not user_index_file.exists():
                    return []

                with open(user_index_file, encoding='utf-8') as f:
                    return json.load(f)

            except Exception as e:
                logger.error(f"Error listing conversations for user {user_id}: {e}")
                return []


class ConversationMemoryManager:
    """Manages conversation memory with configurable storage backends."""

    def __init__(
        self,
        backend: ConversationMemoryBackend | None = None,
        max_interactions_per_conversation: int = 20,
        enable_summarization: bool = False
    ):
        """Initialize conversation memory manager.
        
        Args:
            backend: Storage backend for conversations
            max_interactions_per_conversation: Maximum interactions to keep in memory
            enable_summarization: Whether to enable conversation summarization
        """
        self.backend = backend or InMemoryConversationBackend()
        self.max_interactions_per_conversation = max_interactions_per_conversation
        self.enable_summarization = enable_summarization
        logger.info(f"ConversationMemoryManager initialized with backend: {type(self.backend).__name__}")

    async def start_conversation(self, user_id: str) -> str:
        """Start a new conversation session.
        
        Args:
            user_id: User identifier
            
        Returns:
            conversation_id: Unique conversation identifier
        """
        conversation_id = str(uuid.uuid4())

        session = ConversationSession(
            conversation_id=conversation_id,
            user_id=user_id
        )

        await self.backend.save_session(session)

        logger.info(f"Started new conversation {conversation_id} for user {user_id}")
        return conversation_id

    async def add_interaction(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        metadata: dict[str, any] | None = None
    ) -> None:
        """Add an interaction to a conversation.
        
        Args:
            conversation_id: Conversation identifier
            question: User question
            answer: Assistant answer
            metadata: Optional interaction metadata
        """
        session = await self.backend.load_session(conversation_id)
        if not session:
            raise ValueError(f"Conversation {conversation_id} not found")

        interaction = Interaction(
            question=question,
            answer=answer,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        session.add_interaction(interaction)

        # Handle memory limits
        await self._handle_memory_limits(session)

        await self.backend.save_session(session)

        logger.debug(f"Added interaction to conversation {conversation_id}")

    async def get_conversation_session(self, conversation_id: str) -> ConversationSession | None:
        """Get a conversation session by ID.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            ConversationSession or None if not found
        """
        return await self.backend.load_session(conversation_id)

    async def get_conversation_history(self, conversation_id: str) -> list[Interaction]:
        """Get conversation history.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            List of interactions in chronological order
        """
        session = await self.backend.load_session(conversation_id)
        if not session:
            return []

        return session.interactions

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            True if deleted, False if not found
        """
        return await self.backend.delete_session(conversation_id)

    async def list_user_conversations(self, user_id: str) -> list[str]:
        """List all conversations for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of conversation IDs
        """
        return await self.backend.list_user_conversations(user_id)

    async def _handle_memory_limits(self, session: ConversationSession) -> None:
        """Handle memory limits by truncating or summarizing conversations."""
        if len(session.interactions) <= self.max_interactions_per_conversation:
            return

        if self.enable_summarization:
            # Summarize older interactions and keep recent ones
            await self._summarize_conversation(session)
        else:
            # Simple truncation - keep most recent interactions
            session.interactions = session.interactions[-self.max_interactions_per_conversation:]

    async def _summarize_conversation(self, session: ConversationSession) -> None:
        """Summarize older interactions in a conversation."""
        if len(session.interactions) <= self.max_interactions_per_conversation:
            return

        # Keep half of max_interactions as recent interactions
        keep_recent = max(self.max_interactions_per_conversation // 2, 1)
        interactions_to_summarize = session.interactions[:-keep_recent]

        # Simple summarization - in a real implementation, you'd use an LLM
        summary_points = []
        for interaction in interactions_to_summarize:
            # Extract key topics from questions
            if "AI" in interaction.question or "Artificial Intelligence" in interaction.answer:
                summary_points.append("Discussion about AI and Artificial Intelligence")
            elif "ML" in interaction.question or "Machine Learning" in interaction.answer:
                summary_points.append("Discussion about Machine Learning")
            elif "GraphRAG" in interaction.question or "GraphRAG" in interaction.answer:
                summary_points.append("Discussion about GraphRAG technology")
            else:
                summary_points.append(f"Q&A about {interaction.question[:50]}...")

        if summary_points:
            existing_summary = session.summary or ""
            new_summary = "; ".join(set(summary_points))
            if existing_summary:
                session.summary = f"{existing_summary}; {new_summary}"
            else:
                session.summary = new_summary

        # Keep only recent interactions
        session.interactions = session.interactions[-keep_recent:]
