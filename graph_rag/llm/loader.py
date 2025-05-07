"""LLM loader module for dependency injection."""

import logging
from typing import Dict, Optional, Type, Union

# Use the protocol directly and the concrete mock implementation
from graph_rag.llm.protocols import LLMService
from graph_rag.llm.mock_llm import MockLLMService 
# from graph_rag.llm.llm_service import BaseLLM, MockLLMService # OLD import

from graph_rag.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# LLM registry mapping type names to LLMService implementations
LLM_REGISTRY: Dict[str, Type[LLMService]] = {
    "mock": MockLLMService,
    # Add other implementations here (e.g., "openai", "ollama")
    # "openai": OpenAILLMService,
    # "ollama": OllamaLLMService, # Assuming these implement LLMService protocol
}

# Define the path for the mock LLM if needed globally
MOCK_LLM_PATH = "graph_rag.llm.mock_llm.MockLLMService"

def load_llm(llm_type: Optional[str] = None) -> LLMService: # Return type is the protocol
    """Loads and initializes an LLM service based on configuration."""
    # Use LLM_TYPE setting from config
    config_llm_type = getattr(settings, 'LLM_TYPE', 'mock') # Safely get LLM_TYPE, default to mock
    llm_type_to_load = llm_type or config_llm_type 
    logger.info(f"Attempting to load LLM of type: {llm_type_to_load}")

    llm_class = LLM_REGISTRY.get(llm_type_to_load.lower())

    if llm_class:
        try:
            # Instantiate the LLM class - add necessary config args if needed
            # Example: if llm_type_to_load == 'openai': 
            #     api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
            #     if not api_key: raise ValueError("OpenAI API key required but not found.")
            #     return llm_class(api_key=api_key)
            
            # For MockLLMService, or others without required args in __init__:
            return llm_class()
        except Exception as e:
            logger.error(f"Failed to initialize LLM service '{llm_type_to_load}': {e}", exc_info=True)
            raise ValueError(f"Failed to initialize LLM service '{llm_type_to_load}'.") from e
    else:
        logger.error(f"Unsupported LLM type specified: '{llm_type_to_load}'. Available: {list(LLM_REGISTRY.keys())}")
        raise ValueError(f"Unsupported LLM type: '{llm_type_to_load}'")

# This function seems outdated or incorrectly placed, as it refers to EMBEDDING_MODEL
# Let's comment it out for now, as LLM client loading is handled by load_llm
# def get_llm_client(model_name: str = settings.EMBEDDING_MODEL):
#     logger.info(f"Getting LLM client for model: {model_name}")
#     # Placeholder for actual client retrieval based on model name/config
#     # This might involve checking settings.LLM_TYPE and returning the appropriate client
#     # For now, just return a mock or raise NotImplementedError
#     if settings.LLM_TYPE == "mock":
#         return MockLLMService() # Or whatever mock client is appropriate
#     else:
#         logger.warning(f"LLM client retrieval not fully implemented for type: {settings.LLM_TYPE}")
#         raise NotImplementedError("LLM client retrieval not implemented for this type.") 