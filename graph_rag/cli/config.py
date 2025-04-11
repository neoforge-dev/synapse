"""CLI configuration module for GraphRAG."""
from typing import Optional
from pathlib import Path
import os
import typer
import httpx
import logging
from graph_rag.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

class CLIConfig:
    """Configuration for CLI commands."""
    
    def __init__(self):
        # Default API base URL from settings
        self._api_base_url = f"http://{settings.api_host}:{settings.api_port}/api/v1"
        
        # Override from environment if set
        if "GRAPH_RAG_API_URL" in os.environ:
            self._api_base_url = os.environ["GRAPH_RAG_API_URL"].rstrip("/")
    
    @property
    def api_base_url(self) -> str:
        """Get the base URL for API endpoints."""
        return self._api_base_url
    
    @api_base_url.setter
    def api_base_url(self, value: str) -> None:
        """Set the base URL for API endpoints."""
        self._api_base_url = value.rstrip("/")
    
    @property
    def ingestion_url(self) -> str:
        """Get the URL for the ingestion endpoint."""
        return f"{self.api_base_url}/ingestion/documents"
    
    @property
    def query_url(self) -> str:
        """Get the URL for the query endpoint."""
        return f"{self.api_base_url}/query"
    
    @property
    def search_url(self) -> str:
        """Get the URL for the search endpoint."""
        return f"{self.api_base_url}/search/query"
    
    @property
    def health_url(self) -> str:
        """Get the URL for the health check endpoint."""
        return f"{self.api_base_url}/health"

# Create a singleton instance
cli_config = CLIConfig() 