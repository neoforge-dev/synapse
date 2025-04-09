"""LLM loader module for dependency injection."""

from typing import Optional
from graph_rag.llm.llm_service import LLMService, MockLLMService
from graph_rag.config import settings

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