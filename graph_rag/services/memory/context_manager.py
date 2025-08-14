"""Context management for conversation-aware responses."""

import logging
from typing import Optional

from graph_rag.services.memory.conversation_memory import ConversationMemoryManager

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversation context for GraphRAG queries."""
    
    def __init__(self, memory_manager: ConversationMemoryManager):
        """Initialize context manager with memory manager.
        
        Args:
            memory_manager: ConversationMemoryManager instance
        """
        self.memory_manager = memory_manager
        logger.info("ContextManager initialized")
    
    async def start_conversation(self, user_id: str) -> str:
        """Start a new conversation.
        
        Args:
            user_id: User identifier
            
        Returns:
            conversation_id: New conversation ID
        """
        return await self.memory_manager.start_conversation(user_id)
    
    async def add_interaction(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        metadata: Optional[dict] = None
    ) -> None:
        """Add an interaction to the conversation.
        
        Args:
            conversation_id: Conversation identifier
            question: User question
            answer: Assistant answer
            metadata: Optional interaction metadata
        """
        await self.memory_manager.add_interaction(
            conversation_id, question, answer, metadata
        )
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        max_context_length: int = 2000
    ) -> str:
        """Get formatted conversation context for LLM consumption.
        
        Args:
            conversation_id: Conversation identifier
            max_context_length: Maximum context length in characters
            
        Returns:
            Formatted context string for LLM
        """
        session = await self.memory_manager.get_conversation_session(conversation_id)
        if not session:
            return ""
        
        context_parts = []
        
        # Add summary if available
        if session.summary:
            context_parts.append(f"Previous conversation summary: {session.summary}")
        
        # Add recent interactions
        if session.interactions:
            context_parts.append("Previous conversation:")
            
            # Add interactions in reverse order (most recent first) until we hit length limit
            total_length = sum(len(part) for part in context_parts)
            
            for interaction in reversed(session.interactions):
                interaction_text = (
                    f"User: {interaction.question}\n"
                    f"Assistant: {interaction.answer}"
                )
                
                if total_length + len(interaction_text) > max_context_length:
                    break
                
                context_parts.insert(-1 if len(context_parts) > 1 else 0, interaction_text)
                total_length += len(interaction_text)
        
        context = "\n\n".join(context_parts) if context_parts else ""
        
        logger.debug(f"Generated context for conversation {conversation_id}: {len(context)} characters")
        return context
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """Get conversation summary if available.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Conversation summary or None
        """
        session = await self.memory_manager.get_conversation_session(conversation_id)
        return session.summary if session else None
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            True if deleted, False if not found
        """
        return await self.memory_manager.delete_conversation(conversation_id)
    
    async def list_user_conversations(self, user_id: str) -> list[str]:
        """List all conversations for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of conversation IDs
        """
        return await self.memory_manager.list_user_conversations(user_id)