"""LLM loader module for dependency injection."""

from typing import Optional
from graph_rag.llm.llm_service import LLMService, MockLLMService
from graph_rag.config import get_settings
from openai import OpenAI

settings = get_settings()

def load_llm(use_mock: Optional[bool] = None) -> LLMService:
    """
    Loads the appropriate LLM service based on configuration.
    
    Args:
        use_mock: Optional override for using mock service. If None, uses settings.
        
    Returns:
        An instance of LLMService or MockLLMService.
    """
    if use_mock is None:
        use_mock = settings.USE_MOCK_LLM
    
    if use_mock:
        return MockLLMService()
    return LLMService()

def get_llm_client(model_name: str = settings.EMBEDDING_MODEL):
    """Initializes and returns an LLM client (e.g., OpenAI)."""
    # Simplified: assumes OpenAI for now, adjust as needed
    # You would fetch API keys from settings or environment variables here
    # api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else os.getenv("OPENAI_API_KEY")
    # if not api_key:
    #     raise ValueError("OpenAI API key not found in settings or environment.")
    
    # Example using OpenAI client (replace with your actual LLM client init)
    try:
        client = OpenAI(api_key="YOUR_API_KEY_HERE") # Replace with actual key retrieval
        # You might want to test connectivity here if possible
        # client.models.list() # Example call to check connectivity
        return client
    except Exception as e:
        # Log the error appropriately
        print(f"Error initializing LLM client: {e}")
        raise # Re-raise the exception or handle as appropriate 