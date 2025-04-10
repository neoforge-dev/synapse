import pytest
import os
# import subprocess # Removed
# import time # Removed
import logging
from typing import AsyncGenerator, Any, Optional, Generator
import nltk # Add nltk import
import spacy # Add spacy import
import subprocess # Keep subprocess for spaCy download check
import sys # Add sys import

import asyncio
from httpx import AsyncClient, ASGITransport # Import ASGITransport
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock # Add AsyncMock

# Imports for Memgraph setup
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, Neo4jError
# from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type # Removed

from graph_rag.config import settings
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.core.entity_extractor import EntityExtractor, MockEntityExtractor
from graph_rag.api.dependencies import get_entity_extractor, get_graph_repository
from graph_rag.api.main import create_app
from graph_rag.core.debug_tools import GraphDebugger

logger = logging.getLogger(__name__)

# --- NLTK Downloader Fixture ---

@pytest.fixture(scope="session", autouse=True)
def nltk_punkt_downloader():
    """Downloads the NLTK 'punkt' tokenizer models once per session if not already present."""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        logger.info("NLTK 'punkt' resource not found. Downloading...")
        nltk.download('punkt', quiet=True)
        logger.info("NLTK 'punkt' resource downloaded.")

# --- SpaCy Model Downloader Fixture ---

@pytest.fixture(scope="session", autouse=True)
def spacy_model_downloader():
    """Downloads the spaCy 'en_core_web_sm' model once per session if not already present."""
    model_name = "en_core_web_sm"
    try:
        spacy.load(model_name)
        logger.info(f"spaCy model '{model_name}' already available.")
    except OSError:
        logger.info(f"spaCy model '{model_name}' not found. Downloading...")
        # Use subprocess to run the download command directly with the current interpreter
        try:
            # Use sys.executable to ensure we use the same python as pytest
            command = [sys.executable, "-m", "spacy", "download", model_name]
            subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info(f"spaCy model '{model_name}' downloaded successfully.")
            # Verify download by trying to load again
            spacy.load(model_name)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to download spaCy model '{model_name}': {e}")
            # Check if stderr is available and decode if bytes
            stderr_msg = ""
            if hasattr(e, 'stderr') and e.stderr:
                if isinstance(e.stderr, bytes):
                    try:
                        stderr_msg = e.stderr.decode('utf-8')
                    except UnicodeDecodeError:
                        stderr_msg = str(e.stderr) # Fallback if decoding fails
                else:
                     stderr_msg = str(e.stderr)
            pytest.fail(f"Failed to download required spaCy model '{model_name}'. Error: {e}. Stderr: {stderr_msg}")
        except OSError as load_err:
             logger.error(f"Failed to load spaCy model '{model_name}' even after download attempt: {load_err}")
             pytest.fail(f"Failed to load required spaCy model '{model_name}' after download. Error: {load_err}")

# --- Application Fixture ---

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Returns a FastAPI app instance for testing."""
    # Ensure the factory creates the app with the lifespan manager
    test_app = create_app() 
    return test_app

# --- Mock Dependency Functions & Overrides ---

def get_mock_entity_extractor() -> EntityExtractor:
    """Returns a MockEntityExtractor for testing purposes."""
    return MockEntityExtractor()

# --- Test Client Fixtures ---

@pytest.fixture(scope="session")
def mock_graph_repo() -> AsyncMock:
    """Provides a reusable AsyncMock for the Graph Repository."""
    return AsyncMock()

@pytest.fixture(scope="session")
async def test_client(app: FastAPI, mock_graph_repo: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Provides an async test client for the FastAPI app with dependency overrides."""
    # Store original overrides
    original_overrides = app.dependency_overrides.copy()
    
    # Apply overrides for testing
    app.dependency_overrides[get_entity_extractor] = get_mock_entity_extractor
    app.dependency_overrides[get_graph_repository] = lambda: mock_graph_repo # Override graph repo
    
    # Correctly initialize AsyncClient using ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
        
    # Restore original overrides after tests
    app.dependency_overrides = original_overrides

@pytest.fixture(scope="function")
def sync_test_client(app: FastAPI) -> TestClient:
    """Create a synchronous test client for the FastAPI app."""
    client = TestClient(app)
    return client

# --- Event Loop Fixture ---

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    os.environ["MEMGRAPH_URI"] = "bolt://localhost:7687"
    os.environ["MEMGRAPH_USERNAME"] = "neo4j"
    os.environ["MEMGRAPH_PASSWORD"] = "test"
    os.environ["MEMGRAPH_RETRY_ATTEMPTS"] = "3"
    os.environ["MEMGRAPH_RETRY_WAIT_SECONDS"] = "1"
    os.environ["MEMGRAPH_MAX_POOL_SIZE"] = "10"
    os.environ["MEMGRAPH_CONNECTION_TIMEOUT"] = "5"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def memgraph_connection() -> AsyncGenerator[AsyncGraphDatabase.driver, None]:
    """Create a Memgraph connection for testing."""
    uri = settings.get_memgraph_uri()
    auth = (settings.MEMGRAPH_USERNAME, settings.MEMGRAPH_PASSWORD)
    
    driver = None
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            driver = AsyncGraphDatabase.driver(
                uri,
                auth=auth,
                max_connection_pool_size=settings.MEMGRAPH_MAX_POOL_SIZE,
                connection_timeout=settings.MEMGRAPH_CONNECTION_TIMEOUT
            )
            await driver.verify_connectivity()
            break
        except ServiceUnavailable:
            retry_count += 1
            if retry_count == max_retries:
                raise
            await asyncio.sleep(1)
    
    yield driver
    
    if driver:
        await driver.close()

@pytest.fixture(scope="function")
async def clean_memgraph(memgraph_connection: AsyncGraphDatabase.driver) -> None:
    """Clean Memgraph database before each test."""
    async with memgraph_connection.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

@pytest.fixture(scope="function")
async def memgraph_repo(memgraph_connection: AsyncGraphDatabase.driver) -> AsyncGenerator[MemgraphGraphRepository, None]:
    """Create a MemgraphGraphRepository instance for testing."""
    repo = MemgraphGraphRepository(memgraph_connection)
    try:
        await repo.connect()
        yield repo
    finally:
        await repo.close()

# --- Sample Data Fixtures ---

@pytest.fixture
def sample_document() -> dict[str, Any]:
    """Fixture providing a sample document dictionary (adjust if model objects preferred)."""
    return {
        "id": "doc1",
        "content": "This is a test document",
        "metadata": {"source": "test", "author": "tester"}
    }

@pytest.fixture
def sample_chunk() -> dict[str, Any]:
    """Fixture providing a sample chunk dictionary (adjust if model objects preferred)."""
    return {
        "id": "chunk1",
        "content": "This is a test chunk",
        "document_id": "doc1",
        "embedding": [0.1, 0.2, 0.3]
    }

# --- Debugging Fixtures ---

@pytest.fixture(scope="function")
async def graph_debugger(memgraph_repo: MemgraphGraphRepository) -> GraphDebugger:
    """Fixture for GraphDebugger instance using the shared MemgraphGraphRepository."""
    # Assuming GraphDebugger needs the driver, accessed via the repo
    if not memgraph_repo._driver or not memgraph_repo._is_connected:
        await memgraph_repo.connect() # Ensure connection if needed
    if not memgraph_repo._driver:
         raise ValueError("Memgraph repository driver is not initialized after connect()")
    return GraphDebugger(memgraph_repo._driver) 