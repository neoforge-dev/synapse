from typing import Protocol, List, Dict, Any, Optional, AsyncGenerator, Tuple

class LLMService(Protocol):
    """Protocol defining the interface for LLM services."""
    
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a response to the given prompt.
        
        Args:
            prompt: The input prompt to generate a response for.
            context: Optional context to consider when generating the response.
            history: Optional conversation history.
            
        Returns:
            The generated response as a string.
        """
        ...
    
    async def generate_response_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response to the given prompt.
        
        Args:
            prompt: The input prompt to generate a response for.
            context: Optional context to consider when generating the response.
            history: Optional conversation history.
            
        Yields:
            Chunks of the generated response as strings.
        """
        ...
    
    async def extract_entities_relationships(
        self, text: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract entities and relationships from the given text.
        
        Args:
            text: The text to extract entities and relationships from.
            
        Returns:
            A tuple containing:
            - List of extracted entities, each represented as a dictionary
            - List of extracted relationships, each represented as a dictionary
        """
        ...
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text.
        
        Args:
            text: The text to generate an embedding for.
            
        Returns:
            A list of floats representing the embedding vector.
        """
        ...
    
    async def get_token_usage(self) -> Dict[str, int]:
        """Get the current token usage statistics.
        
        Returns:
            A dictionary containing token usage statistics.
        """
        ... 