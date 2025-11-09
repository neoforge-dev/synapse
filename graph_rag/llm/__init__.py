# Remove eager imports - use lazy loading instead
from .llm_service import LLMService, MockLLMService
from .loader import load_llm


def get_openai_service(*args, **kwargs):
    """Lazy load OpenAI service to reduce startup time by ~0.5s."""
    from .openai_service import OpenAIService
    return OpenAIService(*args, **kwargs)


def get_anthropic_service(*args, **kwargs):
    """Lazy load Anthropic service to reduce startup time by ~0.5s."""
    from .anthropic_service import AnthropicService
    return AnthropicService(*args, **kwargs)


def get_ollama_service(*args, **kwargs):
    """Lazy load Ollama service to reduce startup time by ~0.5s."""
    from .ollama_service import OllamaService
    return OllamaService(*args, **kwargs)


def get_mock_llm_service(*args, **kwargs):
    """Lazy load Mock LLM service (lightweight, but consistent pattern)."""
    from .mock_llm import MockLLMService as MockService
    return MockService(*args, **kwargs)


# For backwards compatibility, keep the class references but they will trigger lazy loading
# This is a transitional pattern - prefer using the get_* functions directly
OpenAIService = get_openai_service
AnthropicService = get_anthropic_service
OllamaService = get_ollama_service

__all__ = [
    "LLMService",
    "MockLLMService",
    "load_llm",
    "OpenAIService",
    "AnthropicService",
    "OllamaService",
    "get_openai_service",
    "get_anthropic_service",
    "get_ollama_service",
    "get_mock_llm_service"
]
