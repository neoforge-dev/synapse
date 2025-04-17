from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pydantic import SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Look for a .env file in the parent directory (project root)
        env_file=os.path.join(os.path.dirname(__file__), '..', '..', '.env'), 
        env_file_encoding='utf-8', 
        extra='ignore' # Ignore extra fields from env vars
    )

    # Application settings
    APP_NAME: str = "graph-rag-mcp"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API settings
    api_host: str = "localhost"
    api_port: int = 8000
    api_log_level: str = "info"

    # Memgraph settings
    MEMGRAPH_HOST: str = "localhost"
    MEMGRAPH_PORT: int = 7687
    MEMGRAPH_URI: Optional[str] = None # Allow override
    MEMGRAPH_USERNAME: str = ""
    MEMGRAPH_PASSWORD: SecretStr = SecretStr("")
    MEMGRAPH_MAX_POOL_SIZE: int = 50
    MEMGRAPH_CONNECTION_TIMEOUT: float = 10.0 # seconds
    MEMGRAPH_MAX_RETRIES: int = 3
    MEMGRAPH_RETRY_WAIT_SECONDS: float = 1.0
    MEMGRAPH_USE_SSL: bool = False

    # Embedding settings
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    EMBEDDING_DIMENSION: int = 1536

    # Search settings
    SEARCH_TOP_K: int = 5
    VECTOR_SEARCH_SIMILARITY_THRESHOLD: float = 0.7 # Default similarity threshold

    # Entity Extractor settings
    entity_extractor_type: str = "spacy"
    entity_extractor_model: str = "en_core_web_sm"
    
    # Vector Store settings
    vector_store_type: str = "simple"
    vector_store_embedding_model: str = "all-MiniLM-L6-v2"

    # Cache settings
    cache_type: str = "memory"

    def get_memgraph_uri(self) -> str:
        if self.MEMGRAPH_URI:
            return self.MEMGRAPH_URI
        # Construct default bolt URI (add +ssc for encrypted connections if needed)
        return f"bolt://{self.MEMGRAPH_HOST}:{self.MEMGRAPH_PORT}"

# Define the factory function here
def get_settings() -> Settings:
    """Loads and returns the application settings."""
    try:
        # This will load from .env and environment variables based on model_config
        loaded_settings = Settings()
        # Optional: Add logging here if desired
        # logger.info("Application settings loaded successfully.")
        return loaded_settings
    except Exception as e:
        # import logging here if needed, or ensure logger is available
        # logger = logging.getLogger(__name__)
        # logger.error(f"CRITICAL: Failed to load application settings: {e}", exc_info=True)
        # For now, re-raise to make the failure explicit during startup/use
        print(f"CRITICAL ERROR: Failed to load application settings: {e}") # Simple print for now
        raise RuntimeError(f"Failed to initialize application settings: {e}") from e 