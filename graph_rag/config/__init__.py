"""Configuration settings for the Graph RAG application."""

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl, SecretStr
from typing import Optional

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings loaded from environment variables and/or .env file."""
    
    model_config = SettingsConfigDict(
        # Load .env file if present
        env_file='.env',
        env_file_encoding='utf-8',
        # Environment variables are case-insensitive by default with Pydantic v2
        case_sensitive=False, 
        # Prefix for environment variables (optional but good practice)
        env_prefix='SYNAPSE_'
    )

    # --- API Settings --- 
    api_host: str = Field("0.0.0.0", description="Host address for the FastAPI server.")
    api_port: int = Field(8000, description="Port number for the FastAPI server.")
    api_log_level: str = Field("INFO", description="Logging level for the API server.")
    # Example: api_key: Optional[SecretStr] = Field(None, description="Optional API key for securing endpoints.")

    # --- Memgraph Settings --- 
    memgraph_host: str = Field("127.0.0.1", description="Hostname or IP address of the Memgraph instance.")
    memgraph_port: int = Field(7687, description="Port number for the Memgraph instance.")
    memgraph_user: Optional[str] = Field(None, description="Username for Memgraph connection (if required).")
    memgraph_password: Optional[SecretStr] = Field(None, description="Password for Memgraph connection (if required).")
    memgraph_use_ssl: bool = Field(False, description="Whether to use SSL for Memgraph connection.")
    memgraph_max_retries: int = Field(3, ge=0, description="Maximum connection/query retries for Memgraph.")
    memgraph_retry_delay: int = Field(2, ge=1, description="Delay in seconds between Memgraph retries.")

    # --- Vector Store Settings --- 
    vector_store_type: str = Field("simple", description="Type of vector store to use ('simple', 'qdrant', 'mock'). Default: simple")
    vector_store_embedding_model: str = Field("all-MiniLM-L6-v2", description="Sentence-transformer model for the vector store. Default: all-MiniLM-L6-v2")
    # vector_store_host: Optional[str] = Field(None, description="Hostname for the vector store (if applicable).") # Example for Qdrant
    # vector_store_port: Optional[int] = Field(None, description="Port for the vector store (if applicable).") # Example for Qdrant
    # vector_store_api_key: Optional[SecretStr] = Field(None, ...) 
    # vector_store_collection_name: str = Field("graph_rag_chunks", ...)

    # --- NLP Model Settings --- 
    entity_extractor_type: str = Field("spacy", description="Type of entity extractor to use ('mock', 'spacy'). Default: spacy")
    entity_extractor_model: str = Field("en_core_web_sm", description="Identifier for the entity extraction model (e.g., spaCy model name). Default: en_core_web_sm")
    # embedding_model: str = Field("mock", description="Identifier for the text embedding model/service.") # This might be redundant now
    # relationship_extractor_model: Optional[str] = Field(None, ...)
    
    # --- Embedding Provider --- 
    embedding_provider: str = Field("sentencetransformers", description="Provider for embedding models ('mock', 'sentencetransformers', 'openai', 'ollama'). Default: sentencetransformers")
    
    # --- Document Processor Settings --- 
    chunk_splitter_type: str = Field("sentence", description="Type of chunk splitter to use (e.g., 'sentence', 'token').")
    ingestion_chunk_size: int = Field(200, ge=50, description="Target chunk size (e.g., in tokens or sentences depending on splitter) for ingestion.")
    ingestion_chunk_overlap: int = Field(20, ge=0, description="Number of tokens to overlap between chunks during ingestion.")

    # --- Retrieval/RAG Settings ---
    graph_context_max_tokens: int = Field(1500, ge=100, description="Maximum number of tokens for the context retrieved from the graph.")

    # Add other settings as needed...

# Define a factory function instead
def get_settings() -> Settings:
    """Loads and returns the application settings."""
    try:
        # This will load from .env and environment variables based on model_config
        loaded_settings = Settings()
        # Optional: Add logging here if desired
        # logger.info("Application settings loaded successfully.")
        return loaded_settings
    except Exception as e:
        logger.error(f"CRITICAL: Failed to load application settings: {e}", exc_info=True)
        # Depending on the application's needs, you might:
        # 1. Re-raise the exception to halt startup
        # 2. Return a default Settings() instance (potentially risky)
        # 3. Exit the application
        # For now, let's re-raise to make the failure explicit during startup/use
        raise RuntimeError(f"Failed to initialize application settings: {e}") from e

# Make these easily importable from the package
__all__ = ["Settings", "get_settings"] 