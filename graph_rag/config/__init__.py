"""Configuration settings for the Graph RAG application."""

import logging
import os
from typing import Optional
from urllib.parse import urlparse

from pydantic import Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and/or .env file."""

    model_config = SettingsConfigDict(
        # Load .env file if present
        env_file=".env",
        env_file_encoding="utf-8",
        # Environment variables are case-insensitive by default with Pydantic v2
        case_sensitive=False,
        # Prefix for environment variables (optional but good practice)
        env_prefix="SYNAPSE_",
    )

    # --- API Settings ---
    api_host: str = Field("0.0.0.0", description="Host address for the FastAPI server.")
    api_port: int = Field(8000, description="Port number for the FastAPI server.")
    api_log_level: str = Field("INFO", description="Logging level for the API server.")
    api_log_json: bool = Field(
        False, description="Emit structured JSON logs when true."
    )
    # Example: api_key: Optional[SecretStr] = Field(None, description="Optional API key for securing endpoints.")

    # --- Memgraph Settings ---
    memgraph_host: str = Field(
        "127.0.0.1", description="Hostname or IP address of the Memgraph instance."
    )
    memgraph_port: int = Field(
        7687, description="Port number for the Memgraph instance."
    )
    memgraph_user: Optional[str] = Field(
        None, description="Username for Memgraph connection (if required)."
    )
    memgraph_password: Optional[SecretStr] = Field(
        None, description="Password for Memgraph connection (if required)."
    )
    memgraph_use_ssl: bool = Field(
        False, description="Whether to use SSL for Memgraph connection."
    )
    memgraph_max_retries: int = Field(
        3, ge=0, description="Maximum connection/query retries for Memgraph."
    )
    memgraph_retry_delay: int = Field(
        2, ge=1, description="Delay in seconds between Memgraph retries."
    )

    # --- Vector Store Settings ---
    vector_store_type: str = Field(
        "simple",
        description="Type of vector store to use ('simple', 'qdrant', 'mock'). Default: simple",
    )
    vector_store_path: str = Field(
        os.path.expanduser("~/.graph_rag/faiss_store"),
        description="Filesystem path for persistent vector store data (used by 'faiss').",
    )
    vector_store_embedding_model: str = Field(
        "all-MiniLM-L6-v2",
        description="Sentence-transformer model for the vector store. Default: all-MiniLM-L6-v2",
    )
    # vector_store_host: Optional[str] = Field(None, description="Hostname for the vector store (if applicable).") # Example for Qdrant
    # vector_store_port: Optional[int] = Field(None, description="Port for the vector store (if applicable).") # Example for Qdrant
    # vector_store_api_key: Optional[SecretStr] = Field(None, ...)
    # vector_store_collection_name: str = Field("graph_rag_chunks", ...)

    # --- NLP Model Settings ---
    entity_extractor_type: str = Field(
        "spacy",
        description="Type of entity extractor to use ('mock', 'spacy'). Default: spacy",
    )
    entity_extractor_model: str = Field(
        "en_core_web_sm",
        description="Identifier for the entity extraction model (e.g., spaCy model name). Default: en_core_web_sm",
    )
    # embedding_model: str = Field("mock", description="Identifier for the text embedding model/service.") # This might be redundant now
    # relationship_extractor_model: Optional[str] = Field(None, ...)

    # --- Embedding Provider ---
    embedding_provider: str = Field(
        "sentence-transformers",
        description="Provider for embedding models ('mock', 'sentence-transformers', 'openai', 'ollama'). Default: sentence-transformers",
    )

    # --- LLM Settings ---
    llm_type: str = Field(
        "mock",
        description="Type of LLM service to use ('mock', 'openai'). Default: mock",
    )
    openai_api_key: Optional[SecretStr] = Field(
        None, description="OpenAI API key for LLM service (if using OpenAI)."
    )
    llm_model_name: str = Field(
        "gpt-3.5-turbo",
        description="Model name for the LLM service. Default: gpt-3.5-turbo",
    )

    # --- Notion API Settings ---
    notion_api_key: Optional[SecretStr] = Field(
        None, description="Notion API key (internal sync)."
    )
    notion_base_url: str = Field(
        "https://api.notion.com/v1",
        description="Base URL for Notion API.",
    )
    notion_version: str = Field(
        "2022-06-28", description="Notion API version header value."
    )
    notion_max_qps: float = Field(
        3.0,
        ge=0.1,
        description="Maximum Notion API requests per second (client-side throttle).",
    )
    notion_backoff_ceiling: float = Field(
        8.0,
        ge=0.5,
        description="Maximum exponential backoff seconds ceiling for 429 retries.",
    )

    # --- Cache Settings ---
    cache_type: str = Field(
        "memory",
        description="Type of cache to use ('memory'). Default: memory",
    )

    # --- Document Processor Settings ---
    chunk_splitter_type: str = Field(
        "sentence",
        description="Type of chunk splitter to use (e.g., 'sentence', 'token').",
    )
    ingestion_chunk_size: int = Field(
        200,
        ge=50,
        description="Target chunk size (e.g., in tokens or sentences depending on splitter) for ingestion.",
    )
    ingestion_chunk_overlap: int = Field(
        20,
        ge=0,
        description="Number of tokens to overlap between chunks during ingestion.",
    )

    # --- Retrieval/RAG Settings ---
    graph_context_max_tokens: int = Field(
        1500,
        ge=100,
        description="Maximum number of tokens for the context retrieved from the graph.",
    )

    # --- Feature Flags ---
    enable_keyword_streaming: bool = Field(
        False,
        description="Enable streaming of keyword search results (NDJSON).",
    )
    enable_metrics: bool = Field(
        True, description="Expose /metrics Prometheus endpoint."
    )

    # --- LLM-derived relationship persistence ---
    enable_llm_relationships: bool = Field(
        False,
        description=(
            "Enable persisting LLM-inferred relationships into the graph. "
            "Env: SYNAPSE_ENABLE_LLM_RELATIONSHIPS"
        ),
    )
    llm_rel_min_confidence: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum confidence (0..1) required to persist LLM relationships. "
            "Env: SYNAPSE_LLM_REL_MIN_CONFIDENCE"
        ),
    )

    # --- Maintenance Jobs ---
    enable_maintenance_jobs: bool = Field(
        False,
        description=(
            "Enable background maintenance jobs (e.g., FAISS rebuild). Disabled by default."
        ),
    )
    maintenance_interval_seconds: int = Field(
        86400,
        ge=60,
        description="Interval between maintenance runs in seconds (default 1 day).",
    )

    # Add other settings as needed...

    @model_validator(mode="after")
    def _apply_env_aliases(self) -> "Settings":
        """
        Support common env aliases used in tests/integration without changing
        public API:
        - GRAPH_DB_URI: parse into memgraph_host, memgraph_port, memgraph_use_ssl
        - NEO4J_USERNAME/NEO4J_PASSWORD: map to memgraph_user/memgraph_password

        Only apply if corresponding SYNAPSE_ values are not explicitly set.
        """
        graph_db_uri = os.getenv("GRAPH_DB_URI")
        syn_host_set = os.getenv("SYNAPSE_MEMGRAPH_HOST") is not None
        syn_port_set = os.getenv("SYNAPSE_MEMGRAPH_PORT") is not None
        syn_ssl_set = os.getenv("SYNAPSE_MEMGRAPH_USE_SSL") is not None

        # Only allow alias to override defaults if host/port are still at defaults
        DEFAULT_HOST = "127.0.0.1"
        DEFAULT_PORT = 7687

        if (
            graph_db_uri
            and not (syn_host_set and syn_port_set)
            and self.memgraph_host == DEFAULT_HOST
            and self.memgraph_port == DEFAULT_PORT
        ):
            try:
                parsed = urlparse(graph_db_uri)
                # Scheme bolt+s implies SSL
                scheme = (parsed.scheme or "bolt").lower()
                use_ssl = scheme in {"bolt+s", "bolts", "bolt+ssc"}
                host = parsed.hostname or self.memgraph_host
                port = parsed.port or self.memgraph_port
                # Normalize localhost to default IP to keep defaults test stable
                if host == "localhost":
                    host = DEFAULT_HOST
                if not syn_host_set:
                    self.memgraph_host = host
                if not syn_port_set:
                    self.memgraph_port = int(port)
                if not syn_ssl_set:
                    self.memgraph_use_ssl = use_ssl
            except Exception as e:
                logger.warning(f"Failed to parse GRAPH_DB_URI='{graph_db_uri}': {e}")

        # Map credentials if not explicitly set via SYNAPSE_
        if self.memgraph_user is None and os.getenv("NEO4J_USERNAME") is not None:
            self.memgraph_user = os.getenv("NEO4J_USERNAME")
        if self.memgraph_password is None and os.getenv("NEO4J_PASSWORD") is not None:
            self.memgraph_password = SecretStr(os.getenv("NEO4J_PASSWORD") or "")

        # Alias for JSON logging: allow SYNAPSE_JSON_LOGS to set api_log_json
        try:
            if os.getenv("SYNAPSE_JSON_LOGS") is not None and os.getenv("SYNAPSE_API_LOG_JSON") is None:
                val = os.getenv("SYNAPSE_JSON_LOGS", "false").lower() in {"1", "true", "yes", "on"}
                self.api_log_json = val
        except Exception:
            pass

        return self

    def get_memgraph_uri(self) -> str:
        """Constructs the Memgraph connection URI from the individual settings."""
        protocol = "bolt+s" if self.memgraph_use_ssl else "bolt"
        return f"{protocol}://{self.memgraph_host}:{self.memgraph_port}"

    @property
    def MEMGRAPH_USERNAME(self) -> Optional[str]:
        """Alias for memgraph_user to match the expected property name in main.py."""
        return self.memgraph_user

    @property
    def MEMGRAPH_PASSWORD(self) -> Optional[SecretStr]:
        """Alias for memgraph_password to match the expected property name in main.py."""
        return self.memgraph_password


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
        logger.error(
            f"CRITICAL: Failed to load application settings: {e}", exc_info=True
        )
        # Depending on the application's needs, you might:
        # 1. Re-raise the exception to halt startup
        # 2. Return a default Settings() instance (potentially risky)
        # 3. Exit the application
        # For now, let's re-raise to make the failure explicit during startup/use
        raise RuntimeError(f"Failed to initialize application settings: {e}") from e


# Make these easily importable from the package
__all__ = ["Settings", "get_settings"]
