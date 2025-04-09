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
    MEMGRAPH_RETRY_ATTEMPTS: int = 3
    MEMGRAPH_RETRY_WAIT_SECONDS: float = 1.0

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

    def get_memgraph_uri(self) -> str:
        if self.MEMGRAPH_URI:
            return self.MEMGRAPH_URI
        # Construct default bolt URI (add +ssc for encrypted connections if needed)
        return f"bolt://{self.MEMGRAPH_HOST}:{self.MEMGRAPH_PORT}"

# Singleton instance to be imported
settings = Settings() 