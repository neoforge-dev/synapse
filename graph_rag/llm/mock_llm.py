from .protocols import LLMService
from typing import List, Dict, Any

class MockLLMService(LLMService):
    """A mock LLM service for testing or default use."""

    async def generate_response(
        self, 
        prompt: str, 
        context: str = "", 
        system_prompt: str = None, 
        history: List[Dict[str, str]] = None,
        config: Dict[str, Any] = None
    ) -> str:
        """Returns a predefined mock response."""
        return f"Mock response for prompt: '{prompt[:50]}...'"

    async def generate_stream_response(
        self, 
        prompt: str, 
        context: str = "", 
        system_prompt: str = None, 
        history: List[Dict[str, str]] = None,
        config: Dict[str, Any] = None
    ):
        """Yields a predefined mock streaming response."""
        response = f"Mock stream response for prompt: '{prompt[:50]}...'"
        yield response

    async def extract_entities_relationships(
        self, 
        text: str, 
        config: Dict[str, Any] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Returns predefined mock entities and relationships."""
        return {"entities": [], "relationships": []} 