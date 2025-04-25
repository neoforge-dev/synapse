import pytest
import os
# import subprocess # Removed
# import time # Removed
import logging
from typing import AsyncGenerator, Any, Optional, Generator, Dict
import nltk # Add nltk import
import spacy # Add spacy import
import subprocess # Keep subprocess for spaCy download check
import sys # Add sys import
import time # Add time import for sleep
import pytest_asyncio # Add import
import uuid # <-- Added import
import importlib # <-- Added import
import shutil
from typer.testing import CliRunner # <--- Add CliRunner import

import asyncio
from httpx import AsyncClient, ASGITransport # Import ASGITransport
from fastapi import FastAPI, Request, HTTPException, status, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch # Add AsyncMock, MagicMock, patch

# Imports for Memgraph setup
from neo4j import AsyncGraphDatabase, AsyncDriver # Corrected: Use neo4j directly
from neo4j.exceptions import ServiceUnavailable, Neo4jError, AuthError
# from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type # Removed

from graph_rag.config import get_settings as get_settings_original, Settings # Import Settings explicitly
# from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.core.entity_extractor import EntityExtractor, MockEntityExtractor
# Use standardized getter for graph repository
from graph_rag.api.dependencies import (
    get_entity_extractor, get_graph_repository, get_ingestion_service, 
    get_graph_rag_engine, # get_neo4j_driver, # Removed Neo4j driver getter
    get_document_processor, get_knowledge_graph_builder, # Corrected: get_document_processor
    get_vector_store, # Added import
    get_llm, # Corrected import name: get_llm_service -> get_llm
    get_embedding_service,
    # get_cache_service, # Removed CacheService getter
)
from graph_rag.api.main import create_app
from graph_rag.core.debug_tools import GraphDebugger
import mgclient # Add correct import
import neo4j
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.core.graph_rag_engine import QueryResult # <- Corrected import
# Add necessary imports for GraphRAGEngine and its dependencies
# Import the concrete implementation, not the abstract base class
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine 
from graph_rag.llm import load_llm # Import LLM loader
from graph_rag.api import dependencies as deps # Import the module
from graph_rag.core.interfaces import EmbeddingService, VectorStore # Corrected import
from graph_rag.domain.models import Chunk, Document # Updated module path
from graph_rag.core.interfaces import ( # Core interfaces
    EntityExtractor, EmbeddingService, VectorStore,
    GraphRepository, DocumentProcessor, KnowledgeGraphBuilder # Removed LLMService
)
from graph_rag.core.graph_rag_engine import GraphRAGEngine, SimpleGraphRAGEngine, QueryResult # Core Engine
# from graph_rag.core.graph_store import KnowledgeGraphStore # Removed - Class not defined here
# from graph_rag.core.vector_store import FaissVectorStore # Removed - Class not defined here or infrastructure
from graph_rag.core.entity_extractor import MockEntityExtractor # Mock implementation for tests
from graph_rag.llm import load_llm # LLM loading utility
from graph_rag.core.debug_tools import GraphDebugger # Debug tools
from graph_rag.cli.main import app as main_cli_app  # Updated import path

logger = logging.getLogger(__name__)

# Define BASE_URL here so fixtures can use it
BASE_URL = os.getenv("INTEGRATION_TEST_BASE_URL", "http://localhost:8000")

# Cache for singleton fixtures across test sessions if needed, though typically pytest handles fixture scopes.
_fixture_singletons = {}

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
    max_load_attempts = 3
    load_attempt_delay = 2 # seconds

    try:
        spacy.load(model_name)
        logger.info(f"spaCy model '{model_name}' already available.")
    except OSError:
        logger.info(f"spaCy model '{model_name}' not found. Downloading...")
        # Use subprocess to run the download command directly with the current interpreter
        try:
            # Use sys.executable to ensure we use the same python as pytest
            command = [sys.executable, "-m", "spacy", "download", model_name]
            process = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info(f"spaCy model '{model_name}' download command executed. Output:\n{process.stdout}")
            # Add a small delay before attempting to load
            time.sleep(load_attempt_delay) 

            # Verify download by trying to load again, with retries
            for attempt in range(max_load_attempts):
                try:
                    spacy.load(model_name)
                    logger.info(f"spaCy model '{model_name}' loaded successfully after download (attempt {attempt+1}).")
                    return # Success, exit fixture
                except OSError as load_err:
                    logger.warning(f"Attempt {attempt+1}/{max_load_attempts} to load spaCy model '{model_name}' failed after download: {load_err}")
                    if attempt < max_load_attempts - 1:
                        time.sleep(load_attempt_delay) # Wait before retrying
                    else:
                        # Raise the last error if all attempts fail
                        raise load_err 
                        
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
        except OSError as final_load_err:
             logger.error(f"Failed to load spaCy model '{model_name}' even after download and retries: {final_load_err}")
             pytest.fail(f"Failed to load required spaCy model '{model_name}' after download and retries. Error: {final_load_err}")

# --- Application Fixture ---

@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Returns a FastAPI app instance for testing."""
    # Ensure the factory creates the app with the lifespan manager
    test_app = create_app() 
    return test_app

# --- CLI Runner Fixture ---

@pytest.fixture(scope="function")
def cli_runner() -> CliRunner:
    """Provides a Typer CliRunner instance for testing CLI commands."""
    return CliRunner()

# --- Mock Dependency Functions & Overrides ---

# Use the concrete mock implementation defined below
@pytest.fixture(scope="function")
def mock_entity_extractor() -> MockEntityExtractor:
    """Returns a MockEntityExtractor instance for testing purposes."""
    # Ensure this fixture provides the concrete mock, not an AsyncMock
    return MockEntityExtractor()

# --- Test Client Fixtures ---

@pytest.fixture(scope="session")
def mock_graph_repo() -> AsyncMock:
    """Provides a reusable AsyncMock for the GraphRepository."""
    mock_repo = AsyncMock(spec=GraphRepository)

    # Mock get_document_by_id to return an actual Document object
    from graph_rag.domain.models import Document # Import inside fixture
    mock_doc_instance = Document(
        id="mock_doc_id",
        content="Mock document content",
        metadata={"source": "mock"}
        # created_at and updated_at will default to None/Pydantic defaults
    )
    # Side effect to return different docs based on ID if needed, or just return the instance
    async def get_doc_side_effect(doc_id):
        if doc_id == "doc_key1":
            return Document(id="doc_key1", content="Keyword Doc", metadata={"topic": "keyword"})
        elif doc_id == "doc_vec1":
            return Document(id="doc_vec1", content="Vector Doc", metadata={"topic": "vector"})
        # Fallback to a default mock doc or None
        elif doc_id == "mock_doc_id": 
             return mock_doc_instance
        else:
             return None # Simulate document not found
             
    # mock_repo.get_document_by_id.return_value = mock_doc_instance # Old way
    mock_repo.get_document_by_id.side_effect = get_doc_side_effect # Use side effect

    # Keep other mock method setups
    mock_repo.add_entity = AsyncMock(return_value=None)
    mock_repo.add_relationship = AsyncMock(return_value=None)
    mock_repo.delete_document = AsyncMock(return_value=True) # Mock successful deletion
    mock_repo.get_chunks_for_document = AsyncMock(return_value=[]) # Return empty list by default

    return mock_repo

@pytest.fixture(scope="session")
def mock_neo4j_driver() -> AsyncMock:
    """Provides a reusable AsyncMock for the Neo4j Driver."""
    mock_driver = AsyncMock(spec=AsyncDriver)
    mock_driver.verify_connectivity.return_value = None # Mock successful connectivity check
    return mock_driver

@pytest.fixture(scope="session")
def mock_ingestion_service() -> AsyncMock:
    """Provides a reusable AsyncMock for the IngestionService."""
    mock = AsyncMock()
    mock.ingest_document.side_effect = lambda **kwargs: {"document_id": "test-id", "chunk_ids": ["chunk-1"]}
    mock.ingest_document_background.return_value = ("doc_id_123", "task_id_456")
    return mock

@pytest.fixture(scope="function")
def mock_graph_rag_engine() -> AsyncMock:
    """Provides a reusable AsyncMock for the GraphRAGEngine."""
    mock_engine = AsyncMock(spec=GraphRAGEngine) # Use spec for better type checking

    # Define the mock query method with the expected signature
    async def mock_query(query_text: str, k=None, config: Optional[Dict[str, Any]] = None) -> QueryResult: # Correct type hint
        # Handle k parameter, default to 3 if not provided
        actual_k = k if k is not None else (config.get("k", 3) if config else 3)

        # Special handling for unified search endpoint tests
        if query_text == "test keyword query":
            return QueryResult(
                relevant_chunks=[Chunk(id="key_chunk1", text="Keyword result", document_id="doc_key1", metadata={}, embedding=[])], # Use Chunk
                llm_response="Mock keyword response",
                graph_context="Mock keyword context"
            )
        elif query_text == "test vector query":
            return QueryResult(
                relevant_chunks=[Chunk(id="vec_chunk1", text="Vector result", document_id="doc_vec1", metadata={}, embedding=[])], # Use Chunk
                llm_response="Mock vector response",
                graph_context="Mock vector context"
            )
        # Handle batch search endpoint tests with exact parameters 
        elif query_text == "query1 for batch" and config and config.get("k") == 2 and config.get("search_type") == "keyword":
            return QueryResult(
                relevant_chunks=[Chunk(id="b_chunk1", text="Batch result 1", document_id="b_doc1", score=0.9, metadata={}, embedding=[])], # Use Chunk, add score, metadata, embedding
                llm_response="Mock LLM response 1",
                graph_context="Mock graph context 1"
            )
        elif query_text == "query2 for batch" and config and config.get("k") == 4 and config.get("search_type") == "vector":
            return QueryResult(
                relevant_chunks=[Chunk(id="b_chunk2", text="Batch result 2", document_id="b_doc2", score=0.8, metadata={}, embedding=[])], # Use Chunk, add score, metadata, embedding
                llm_response="Mock LLM response 2",
                graph_context="Mock graph context 2"
            )
        # Add handler for partial failure test
        elif query_text == "successful query":
            return QueryResult(
                relevant_chunks=[Chunk(id="pb_chunk1", text="Partial batch result 1", document_id="pb_doc1", score=0.7, metadata={}, embedding=[])], # Use Chunk, add score, metadata, embedding
                llm_response="Mock LLM response 1",
                graph_context="Mock graph context 1"
            )
        elif query_text == "failing query":
            raise Exception("Simulated engine failure for batch")
        # Default mock response
        else:
            # Define a default result structure matching QueryResult
            default_result = QueryResult(
                answer=f"Mock answer for '{query_text}' (k={actual_k})",
                relevant_chunks=[
                    Chunk(id="mock-chunk-1", text="Mock relevant chunk 1", document_id="mock-doc")
                ],
                graph_context=None,
                metadata={"k_used": actual_k, "config_received": config}
            )
            return default_result

    mock_engine.query = AsyncMock(side_effect=mock_query)
    mock_engine.ingest_document = AsyncMock(return_value=("doc-mock-id", "task-mock-id"))
    # Add other necessary methods/attributes with AsyncMock
    mock_engine.retrieve_context = AsyncMock(return_value=[]) # Default empty context
    
    # Add streaming search mock
    async def mock_stream_context(*args, **kwargs):
        # Return a single chunk with known ID for stream test
        yield Chunk(id="chunk_0", text="Content 0 Text", document_id="doc_0", score=0.9, metadata={}, embedding=[]) # Use Chunk, add score, metadata, embedding
    
    mock_engine.stream_context = mock_stream_context
    
    # Add mock for delete_document if it exists on the engine
    if hasattr(mock_engine, 'delete_document'):
        mock_engine.delete_document = AsyncMock(return_value=True) # Assume success

    return mock_engine

@pytest.fixture(scope="session")
def mock_doc_processor() -> AsyncMock:
    """Provides a reusable AsyncMock for the DocumentProcessor."""
    return AsyncMock()

@pytest.fixture(scope="session")
def mock_kg_builder() -> AsyncMock:
    """Provides a reusable AsyncMock for the KnowledgeGraphBuilder."""
    return AsyncMock()

@pytest.fixture(scope="function") # Changed from @pytest.fixture
def mock_vector_store() -> AsyncMock: # Changed MagicMock to AsyncMock
    """Provides a function-scoped AsyncMock for the VectorStore."""
    mock_vs = AsyncMock(spec=VectorStore)

    # Mock the async add_document method
    async def mock_add_document(doc: Document):
        # Simulate adding a document, perhaps return a mock ID or status
        print(f"MockVectorStore: Adding document {doc.id}")
        await asyncio.sleep(0) # Simulate async operation
        return True
    mock_vs.add_document = AsyncMock(side_effect=mock_add_document)

    # Mock the async add_chunks method
    async def mock_add_chunks(chunks: list[Chunk]):
         print(f"MockVectorStore: Adding {len(chunks)} chunks.")
         await asyncio.sleep(0) # Simulate async operation
         return [c.id for c in chunks] # Return mock chunk IDs
    mock_vs.add_chunks = AsyncMock(side_effect=mock_add_chunks)

    # Mock the async search method
    async def mock_search(query_text: str, k: int, **kwargs) -> list[tuple[Chunk, float]]:
        # Simulate finding relevant chunks
        print(f"MockVectorStore: Searching for '{query_text}' with k={k}")
        await asyncio.sleep(0) # Simulate async operation
        # Return mock chunks with decreasing scores
        mock_results = [
            (Chunk(id=f"mock-chunk-{i}", text=f"Mock relevant chunk {i} for '{query_text}'", document_id="mock-doc"), 1.0 - (i * 0.1))
            for i in range(1, k + 1)
        ]
        return mock_results[:k] # Ensure we return at most k results
    mock_vs.search = AsyncMock(side_effect=mock_search)
    
    # Mock the async delete_document method
    async def mock_delete_document(document_id: str):
        print(f"MockVectorStore: Deleting document {document_id}")
        await asyncio.sleep(0) # Simulate async operation
        return True # Assume success
    mock_vs.delete_document = AsyncMock(side_effect=mock_delete_document)

    # Add other necessary async methods if they exist on the VectorStore interface
    # e.g., mock_vs.delete_chunks = AsyncMock(...)

    return mock_vs

@pytest.fixture(scope="function")
def mock_background_tasks():
    """Provides a function-scoped MagicMock for BackgroundTasks."""
    mock = MagicMock(spec=BackgroundTasks)
    mock.add_task = MagicMock() # Mock the add_task method
    return mock

@pytest_asyncio.fixture(scope="function")
async def test_client(
    app: FastAPI,
    mock_graph_repo: AsyncMock,
    mock_ingestion_service: AsyncMock,
    mock_graph_rag_engine: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_doc_processor: AsyncMock,
    mock_kg_builder: AsyncMock,
    mock_entity_extractor: MockEntityExtractor,
    mock_background_tasks: MagicMock # <--- Add mock_background_tasks
) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an asynchronous test client for the FastAPI application with mocked dependencies.
    This fixture ensures that specific dependencies are replaced with mocks for isolated testing.
    """
    
    # Set the mock engine on the app state *before* creating the client
    # This ensures the lifespan event or dependencies pick up the mock
    app.state.graph_rag_engine = mock_graph_rag_engine
    
    dependency_overrides = {
        deps.get_graph_repository: lambda: mock_graph_repo,
        # deps.get_ingestion_service: lambda: mock_ingestion_service, # Use real service for integration
        deps.get_graph_rag_engine: lambda: mock_graph_rag_engine,
        deps.get_vector_store: lambda: mock_vector_store,
        deps.get_document_processor: lambda: mock_doc_processor,
        deps.get_knowledge_graph_builder: lambda: mock_kg_builder,
        deps.get_entity_extractor: lambda: mock_entity_extractor,
        BackgroundTasks: lambda: mock_background_tasks # <--- Add BackgroundTasks override
    }
    
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.update(dependency_overrides)

    # Use httpx.AsyncClient with ASGITransport for testing async FastAPI applications
    # The base_url is set to a dummy value as requests are handled in-memory via the transport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    # Restore original dependencies after the test completes
    app.dependency_overrides = original_overrides
    # Optionally clear the state if needed, though app lifespan should handle setup/teardown
    if hasattr(app.state, 'graph_rag_engine'):
         del app.state.graph_rag_engine
         
    # --- Reset mocks after test --- # <--- Add reset for background tasks
    mock_graph_repo.reset_mock()
    mock_ingestion_service.reset_mock()
    mock_graph_rag_engine.reset_mock()
    mock_vector_store.reset_mock()
    mock_doc_processor.reset_mock()
    mock_kg_builder.reset_mock()
    mock_background_tasks.reset_mock()
    # mock_entity_extractor doesn't need reset if it's stateless
    # app.dependency_overrides = {} # Clearing overrides might be better done by restoring original_overrides

@pytest.fixture(scope="function")
def sync_test_client(app: FastAPI) -> TestClient:
    """Provides a synchronous TestClient for basic app checks (if needed)."""
    # Note: This client won't easily work with async dependencies unless mocked carefully.
    # Prefer async_test_client for most API tests.
    return TestClient(app)

# --- Environment Setup & Integration Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Sets up the test environment once per session."""
    logger.info("Setting up test environment...")

    # Set environment variables for testing if not already set
    # Example: Use a separate test database or configuration
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG" # Increase log level for tests
    os.environ["GRAPH_DB_URI"] = os.getenv("TEST_MEMGRAPH_URI", "bolt://localhost:7687")
    os.environ["NEO4J_URI"] = os.getenv("TEST_NEO4J_URI", "bolt://localhost:7687") # Keep consistent for now
    os.environ["NEO4J_USERNAME"] = os.getenv("TEST_NEO4J_USER", "neo4j")
    os.environ["NEO4J_PASSWORD"] = os.getenv("TEST_NEO4J_PASSWORD", "password")
    os.environ["VECTOR_STORE_PATH"] = os.getenv("TEST_VECTOR_STORE_PATH", "/tmp/test_vector_store")
    os.environ["CACHE_TYPE"] = "redis" # Example: Use Redis for testing cache if applicable
    os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1") # Use different DB for tests

    # Create test directories if they don't exist
    vector_store_path = os.environ["VECTOR_STORE_PATH"]
    if not os.path.exists(vector_store_path):
        os.makedirs(vector_store_path)
        logger.info(f"Created test vector store directory: {vector_store_path}")

    yield # Allow tests to run

    # Teardown: Clean up test environment after all tests in the session are done
    logger.info("Tearing down test environment...")
    try:
        if os.path.exists(vector_store_path):
            shutil.rmtree(vector_store_path)
            logger.info(f"Removed test vector store directory: {vector_store_path}")
    except Exception as e:
        logger.error(f"Error during test environment cleanup: {e}")
        
    # Potentially clear test database, Redis keys, etc.
    # Example: Clear Redis test database
    # try:
    #     import redis
    #     r = redis.from_url(os.environ["REDIS_URL"])
    #     r.flushdb()
    #     logger.info("Flushed Redis test database.")
    # except ImportError:
    #     logger.warning("redis-py not installed, skipping Redis cleanup.")
    # except Exception as e:
    #     logger.error(f"Error cleaning up Redis: {e}")


@pytest_asyncio.fixture(scope="function")
async def memgraph_connection() -> AsyncGenerator[AsyncDriver, None]:
    """Provides a Memgraph connection for integration tests."""
    uri = os.getenv("GRAPH_DB_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME") # Assuming Memgraph uses same vars for simplicity
    password = os.getenv("NEO4J_PASSWORD")
    
    driver: Optional[AsyncDriver] = None
    max_attempts = 5
    delay = 3 # seconds

    for attempt in range(max_attempts):
        try:
            auth = (username, password) if username or password else None
            driver = AsyncGraphDatabase.driver(uri, auth=auth)
            # Verify connectivity asynchronously
            await driver.verify_connectivity()
            logger.info(f"Successfully connected to Memgraph at {uri} (attempt {attempt + 1}).")
            
            # Clear the database before the test
            try:
                async with driver.session() as session:
                    await session.run("MATCH (n) DETACH DELETE n")
                logger.info("Cleared Memgraph database before test.")
            except Exception as clear_err:
                 logger.error(f"Failed to clear Memgraph database: {clear_err}")
                 # Decide if this should fail the test setup
                 # pytest.fail(f"Failed to clear Memgraph database: {clear_err}")

            yield driver # Provide the driver to the test
            return # Exit after successful yield

        except (ServiceUnavailable, AuthError, Neo4jError) as e:
            logger.warning(f"Memgraph connection attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt == max_attempts - 1:
                logger.error("Max Memgraph connection attempts reached. Failing test.")
                pytest.fail(f"Could not connect to Memgraph at {uri} after {max_attempts} attempts: {e}")
            if driver:
                await driver.close() # Close previous attempt's driver if it exists
            await asyncio.sleep(delay * (attempt + 1)) # Exponential backoff might be better
        except Exception as e: # Catch other potential errors during connection setup
             logger.error(f"An unexpected error occurred during Memgraph connection setup: {e}")
             pytest.fail(f"Unexpected error connecting to Memgraph: {e}")
        finally:
            # This block might not be reached correctly if yield is inside try
            pass 

    # Ensure driver is closed if loop finishes without yielding (e.g., due to failure)
    if driver:
        await driver.close()
        logger.info("Closed Memgraph driver after test or on failure.")


@pytest_asyncio.fixture(scope="function")
async def memgraph_repo() -> AsyncGenerator[MemgraphGraphRepository, None]:
    """Provides an initialized MemgraphGraphRepository for integration tests."""
    from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
    from graph_rag.config import get_settings
    
    # Create a MemgraphGraphRepository with default settings
    repo = MemgraphGraphRepository()
    
    try:
        # Establish connection
        await repo.connect()
        
        # Clear the database for clean test state
        await repo.execute_query("MATCH (n) DETACH DELETE n;")
        logger.info("Cleared Memgraph database for test.")
        
        yield repo
    except Exception as e:
        logger.error(f"Error setting up memgraph_repo fixture: {e}")
        pytest.fail(f"Failed to set up MemgraphGraphRepository: {e}")
    finally:
        if repo:
            await repo.close()
            logger.info("MemgraphGraphRepository connection closed in fixture finally block.")

# --- Sample Data Fixtures ---

@pytest.fixture
def sample_document() -> dict[str, Any]:
    """Provides a sample document dictionary for testing."""
    return {
        "id": "doc-123",
        "content": "This is the first sample document. It contains information about apples and oranges.",
        "metadata": {"source": "test_source", "version": 1}
    }

@pytest.fixture
def sample_chunk() -> dict[str, Any]:
    """Provides a sample chunk dictionary for testing."""
    return {
        "id": "chunk-abc",
        "document_id": "doc-123",
        "text": "Information about apples and oranges.",
        "metadata": {"chunk_num": 0, "embedding": [0.1, 0.2, 0.3]} # Example embedding
    }

@pytest.fixture
def sample_text() -> str:
    """Provides a sample text string."""
    return """
    The quick brown fox jumps over the lazy dog. 
    This text discusses various animals and their actions. 
    Foxes are known for their cunning, while dogs are often loyal companions.
    """

# --- Debugger Fixtures ---

@pytest.fixture(scope="function")
async def mock_graph_debugger() -> AsyncMock: # Removed dependency, this is just a mock
    """Provides a mock GraphDebugger."""
    mock_debugger = AsyncMock(spec=GraphDebugger)
    # Mock specific methods if needed for tests using the mock debugger
    mock_debugger.visualize_graph.return_value = "mock_visualization_data"
    mock_debugger.debug_query.return_value = {"mock": "debug_info"}
    return mock_debugger

@pytest_asyncio.fixture(scope="function")
async def graph_debugger(memgraph_connection: AsyncDriver):
    """Provides an actual GraphDebugger instance connected to Memgraph."""
    if not memgraph_connection:
         pytest.fail("Memgraph connection fixture failed to provide a driver for GraphDebugger.")
         
    # Assuming GraphDebugger is initialized similarly to the repository
    debugger = GraphDebugger(driver=memgraph_connection) 
    
    # Example: Check if connection works for the debugger
    try:
        # Replace with an actual check if the debugger has one
        async with debugger.driver.session() as session: 
            result = await session.run("RETURN 1")
            await result.single()
        logger.info("GraphDebugger connection verified.")
    except Exception as e:
        logger.error(f"GraphDebugger failed connection check: {e}")
        pytest.fail(f"GraphDebugger could not verify connection: {e}")

    yield debugger
    # Driver closure is handled by the memgraph_connection fixture

# --- Integration Test Client ---

@pytest_asyncio.fixture(scope="function")
async def integration_test_client(
    app: FastAPI, 
    setup_environment: None # Depends on environment setup
    # memgraph_connection: AsyncDriver # Inject real dependencies if needed for integration tests
) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an AsyncClient for integration tests, potentially using real dependencies.
    It clears dependency overrides to use the actual implementations.
    """
    # Clear existing overrides to use real dependencies for integration tests
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.clear() 
    
    # Reload settings to ensure integration test env vars are picked up
    # Important: Ensure the app uses the reloaded settings. This might require
    # careful app factory design or patching the settings getter used by the app.
    # For now, assume the app picks up env vars on startup, or use override below.
    
    # Optional: Override settings getter to provide dynamically loaded test settings
    integration_settings = get_reloaded_settings() 
    app.dependency_overrides[get_settings_original] = lambda: integration_settings
    logger.info(f"Integration test client using settings: {integration_settings.model_dump()}")

    # Use ASGITransport for async app testing with httpx
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Optional: Wait for external services like Memgraph if not handled by fixtures
        # await asyncio.sleep(1) # Simple wait, replace with proper health checks
        yield client

    # Restore original overrides after the test finishes
    app.dependency_overrides = original_overrides
    
# --- Settings Reloading Helper ---

def get_reloaded_settings() -> Settings:
    """
    Dynamically reloads the Settings module to pick up environment variables
    set during test setup.
    """
    try:
        # Find the spec for the settings module
        spec = importlib.util.find_spec("graph_rag.config.settings")
        if spec and spec.loader:
            settings_module = importlib.util.module_from_spec(spec)
            # Execute the module definition - this should re-evaluate environment lookups
            spec.loader.exec_module(settings_module) 
            # Access the reloaded Settings class or factory function
            # Assuming Settings is directly available or via a factory
            if hasattr(settings_module, 'Settings'):
                 # Re-instantiate the Settings class
                 reloaded_settings = getattr(settings_module, 'Settings')()
                 logger.debug("Reloaded Settings instance created.")
                 return reloaded_settings
            elif hasattr(settings_module, 'get_settings'):
                 # Call the factory function again
                 reloaded_settings = getattr(settings_module, 'get_settings')()
                 logger.debug("Reloaded Settings via get_settings factory.")
                 return reloaded_settings
            else:
                 logger.error("Could not find Settings class or get_settings function in reloaded module.")
                 raise ImportError("Failed to reload settings correctly.")
        else:
            logger.error("Could not find spec for graph_rag.config.settings.")
            raise ImportError("Could not find spec for settings module.")
    except Exception as e:
        logger.exception(f"Error reloading settings: {e}")
        # Fallback to original settings if reload fails? Or fail the test?
        # For safety, let's try falling back, but log prominently
        logger.error("Falling back to original settings due to reload error.")
        return get_settings_original() # Return original cached settings


# --- Environment Setup Fixture (Function Scoped) ---
@pytest.fixture(scope="function") # Use function scope for isolation
def setup_environment() -> Generator[None, None, None]:
    """
    Sets up environment variables and test directories for a single test function.
    Cleans up afterwards.
    """
    original_env = os.environ.copy() # Store original environment
    logger.debug("Setting up function-scoped test environment...")

    # Define test-specific environment variables
    test_vector_store_path = f"/tmp/test_vector_store_{uuid.uuid4()}"
    test_env_vars = {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "DEBUG",
        "GRAPH_DB_URI": os.getenv("TEST_MEMGRAPH_URI", "bolt://localhost:7687"),
        "NEO4J_URI": os.getenv("TEST_NEO4J_URI", "bolt://localhost:7687"),
        "NEO4J_USERNAME": os.getenv("TEST_NEO4J_USER", "neo4j"),
        "NEO4J_PASSWORD": os.getenv("TEST_NEO4J_PASSWORD", "password"),
        "VECTOR_STORE_PATH": test_vector_store_path,
        "CACHE_TYPE": "memory", # Use memory cache for function scope unless Redis needed
        # "REDIS_URL": os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1") 
    }
    
    # Apply test environment variables
    for key, value in test_env_vars.items():
        os.environ[key] = value
        logger.debug(f"Set env var: {key}={value}")

    # Create test directories
    if not os.path.exists(test_vector_store_path):
        os.makedirs(test_vector_store_path)
        logger.debug(f"Created test vector store directory: {test_vector_store_path}")
        
    # --- Crucial Step: Reload Settings Module ---
    # This ensures that the Settings object used within the test function
    # reflects the environment variables set *in this fixture*.
    # We need to make this reloaded settings available, perhaps via another fixture.
    # See `reloaded_settings` fixture below.

    yield # Test function runs here

    logger.debug("Tearing down function-scoped test environment...")
    # Clean up test directories
    try:
        if os.path.exists(test_vector_store_path):
            shutil.rmtree(test_vector_store_path)
            logger.debug(f"Removed test vector store directory: {test_vector_store_path}")
    except Exception as e:
        logger.error(f"Error during function environment cleanup: {e}")

    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)
    logger.debug("Restored original environment variables.")


# --- Reloaded Settings Fixture ---
@pytest.fixture(scope="function")
def reloaded_settings(setup_environment: None) -> Settings:
    """
    Provides a Settings instance that reflects the environment variables
    set by the `setup_environment` fixture for the current test function.
    Depends on `setup_environment` to ensure variables are set first.
    """
    logger.debug("Reloading settings for function scope...")
    # Call the helper function to perform the actual reload
    settings = get_reloaded_settings()
    logger.debug(f"Function-scoped settings reloaded: {settings.model_dump(exclude={'neo4j_password'})}") # Avoid logging password
    return settings
    
# --- Settings Override Fixture ---

# This fixture provides a function that overrides the settings getter.
# It uses the `reloaded_settings` fixture to get the correct settings
# for the current test scope.
@pytest.fixture(scope="function")
def override_get_settings(reloaded_settings: Settings):
    """
    Provides a function that, when used as a dependency override,
    returns the correctly reloaded Settings for the current test function.
    """
    # Define the override function locally
    def _override() -> Settings:
        return reloaded_settings # Return the settings loaded for this test function
    
    return _override # Return the function itself


# Example Usage in a test:
# def test_something_with_reloaded_settings(test_client, override_get_settings, app):
#     app.dependency_overrides[get_settings_original] = override_get_settings
#     # ... rest of the test ...
#     # Cleanup of override happens automatically if test_client handles it,
#     # or manually if needed: del app.dependency_overrides[get_settings_original]


# --- ChromaDB Cleanup Fixture (Session Scoped) ---

# Example fixture assuming ChromaDB is used and needs cleanup
@pytest.fixture(scope="session", autouse=True)
def cleanup_chromadb(request):
    """Cleans up ChromaDB persistent storage directory after the test session."""
    
    # Default path, adjust if your configuration differs or uses env vars
    # Ideally, read this from the test configuration/settings
    chroma_persist_dir = os.getenv("TEST_VECTOR_STORE_PATH", "/tmp/test_vector_store") 
                                  
    def finalizer():
        logger.info("Running session finalizer for ChromaDB cleanup...")
        if os.path.exists(chroma_persist_dir) and os.path.isdir(chroma_persist_dir):
            try:
                # Check if the directory looks like a ChromaDB store before deleting
                # (e.g., contains specific files like 'chroma.sqlite3')
                if os.path.exists(os.path.join(chroma_persist_dir, "chroma.sqlite3")):
                    logger.info(f"Removing ChromaDB persistence directory: {chroma_persist_dir}")
                    shutil.rmtree(chroma_persist_dir)
                else:
                     logger.warning(f"Directory {chroma_persist_dir} exists but doesn't look like ChromaDB, skipping removal.")
            except Exception as e:
                logger.error(f"Error removing ChromaDB directory {chroma_persist_dir}: {e}")
        else:
            logger.info(f"ChromaDB persistence directory {chroma_persist_dir} not found, skipping cleanup.")

    # Register the finalizer to run at the end of the session
    request.addfinalizer(finalizer) 