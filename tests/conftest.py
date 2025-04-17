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
import time # Add time import for sleep
import pytest_asyncio # Add import
import uuid # <-- Added import

import asyncio
from httpx import AsyncClient, ASGITransport # Import ASGITransport
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch # Add AsyncMock, MagicMock, patch

# Imports for Memgraph setup
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, Neo4jError, AuthError
# from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type # Removed

from graph_rag.config import get_settings
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.core.entity_extractor import EntityExtractor, MockEntityExtractor
# Use standardized getter for graph repository
from graph_rag.api.dependencies import (
    get_entity_extractor, get_graph_repository, get_ingestion_service, 
    get_graph_rag_engine, # get_neo4j_driver, # Removed Neo4j driver getter
    get_document_processor, get_knowledge_graph_builder # Corrected: get_document_processor
)
from graph_rag.api.main import create_app
from graph_rag.core.debug_tools import GraphDebugger
import mgclient # Add correct import
import neo4j
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.core.graph_rag_engine import QueryResult # <- Corrected import

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
            logger.info(f"spaCy model '{model_name}' download command executed. Output:\\n{process.stdout}")
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

@pytest.fixture(scope="session")
def mock_graph_rag_engine() -> AsyncMock:
    """Provides a reusable AsyncMock for the GraphRAGEngine."""
    return AsyncMock()

@pytest.fixture(scope="session")
def mock_doc_processor() -> AsyncMock:
    """Provides a reusable AsyncMock for the DocumentProcessor."""
    return AsyncMock()

@pytest.fixture(scope="session")
def mock_kg_builder() -> AsyncMock:
    """Provides a reusable AsyncMock for the KnowledgeGraphBuilder."""
    return AsyncMock()

@pytest.fixture(scope="session")
def mock_vector_store() -> AsyncMock:
    """Provides a reusable AsyncMock for the VectorStore."""
    return AsyncMock()

@pytest_asyncio.fixture(scope="function")
async def test_client(
    app: FastAPI, 
    mock_graph_repo: AsyncMock, 
    mock_ingestion_service: AsyncMock, 
    mock_graph_rag_engine: AsyncMock, 
    mock_vector_store: AsyncMock,
    mock_doc_processor: AsyncMock,
    mock_kg_builder: AsyncMock,
    mock_entity_extractor: AsyncMock # Added mock entity extractor
) -> AsyncGenerator[AsyncClient, None]:
    """Provides an async test client with dependency overrides and state mocking."""
    # Reset mocks for function scope
    mock_graph_repo.reset_mock()
    mock_ingestion_service.reset_mock()
    mock_graph_rag_engine.reset_mock()
    mock_vector_store.reset_mock()
    mock_doc_processor.reset_mock()
    mock_kg_builder.reset_mock()
    mock_entity_extractor.reset_mock() # Reset entity extractor mock

    # Configure mock_graph_rag_engine.query to return a default QueryResult
    default_query_result = QueryResult(
        answer="Default mock answer",
        relevant_chunks=[],
        graph_context=([], []), # Default empty tuple for entities and relationships
        metadata={"source": "mock_engine"}
    )
    mock_graph_rag_engine.query.return_value = default_query_result

    # Re-apply necessary side effects if they are needed consistently across tests
    # mock_ingestion_service.ingest_document.side_effect = lambda **kwargs: {"document_id": "test-id", "chunk_ids": ["chunk-1"]} # Kept original line commented for reference
    # mock_ingestion_service.ingest_document_background.return_value = ("doc_id_123", "task_id_456") # Kept original line commented for reference

    # --- Configure mock_ingestion_service for background task testing ---
    # Define a side effect that simulates the background processing
    async def mock_ingest_effect(**kwargs):
        # Simulate adding the document to the mocked graph repo if needed for checks
        # Note: This requires access to the mock_graph_repo instance from the outer scope.
        doc_id = kwargs.get("document_id", f"doc-{uuid.uuid4()}")
        content = kwargs.get("content", "")
        metadata = kwargs.get("metadata", {})
        
        # Create a dummy Document object to pass to the mock repo
        # Use the actual Document model if the mock expects it
        # For simplicity, maybe the mock just needs the ID?
        # Let's assume add_document is called on the *mocked* repo
        try:
            # Create a simple object or dict that mock_graph_repo.add_document might expect
            # This depends on how strictly add_document's signature is mocked/checked.
            # Let's assume it can accept a simple object/dict for testing purposes.
            dummy_doc_data = {"id": doc_id, "content": content, "metadata": metadata}
            await mock_graph_repo.add_document(dummy_doc_data) # Call add_document on the MOCK repo
            logger.debug(f"Mock Ingestion Service: Simulated add_document for {doc_id} on mock_graph_repo.")
        except Exception as e:
            logger.error(f"Mock Ingestion Service: Error during mock add_document for {doc_id}: {e}")
            
        # Background task doesn't return directly
        return

    # Make ingest_document awaitable and apply the side effect
    mock_ingestion_service.ingest_document = AsyncMock(side_effect=mock_ingest_effect)

    original_overrides = app.dependency_overrides.copy()
    # --- Apply dependency overrides for direct endpoint injection (Depends) ---
    app.dependency_overrides[get_entity_extractor] = lambda: mock_entity_extractor
    app.dependency_overrides[get_graph_repository] = lambda: mock_graph_repo
    app.dependency_overrides[get_ingestion_service] = lambda: mock_ingestion_service
    app.dependency_overrides[get_graph_rag_engine] = lambda: mock_graph_rag_engine # Override for lifespan/startup
    app.dependency_overrides[get_document_processor] = lambda: mock_doc_processor
    app.dependency_overrides[get_knowledge_graph_builder] = lambda: mock_kg_builder

    # Store original state attributes we plan to mock
    original_state = {}
    state_keys_to_mock = [
        "graph_repository", "ingestion_service", "graph_rag_engine", 
        "vector_store", "doc_processor", "kg_builder", "entity_extractor"
    ]
    for key in state_keys_to_mock:
        if hasattr(app.state, key):
             original_state[key] = getattr(app.state, key)

    # Lifespan runs when the client starts
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Wait briefly for lifespan startup if necessary (though overrides might cover it)
        await asyncio.sleep(0.01)
        
        # --- Explicitly mock state attributes after potential lifespan setup ---
        # Ensure critical state attributes needed by endpoints (like health check) are mocked
        if hasattr(app.state, "graph_rag_engine"):
            app.state.graph_rag_engine = mock_graph_rag_engine
        else:
            # If the state attribute doesn't exist after lifespan, set it directly.
            # This covers cases where lifespan might fail or not set the attribute.
            setattr(app.state, "graph_rag_engine", mock_graph_rag_engine)

        # Optionally mock other state attributes if needed by tests
        # if hasattr(app.state, "graph_repository"): app.state.graph_repository = mock_graph_repo
        # ... etc for other state keys ...

        yield client # Tests run here with overridden dependencies and state mocks
        
    # Restore original overrides
    app.dependency_overrides = original_overrides
    # Restore original state attributes
    for key, value in original_state.items():
        if value is not Ellipsis: # Use Ellipsis or another marker for intentionally skipped keys
             setattr(app.state, key, value)
        elif hasattr(app.state, key):
            # If we didn't store an original value, remove the mocked one if it exists
            delattr(app.state, key)

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

# ========================
# Memgraph/Neo4j Fixtures
# ========================

# Use function scope for the driver to avoid sharing across tests, preventing state leakage.
# @pytest.mark.skip(reason="Need to investigate Neo4j/Memgraph driver issues in async")
# @pytest_asyncio.fixture(scope="session")
@pytest_asyncio.fixture(scope="function")
async def memgraph_connection() -> AsyncGenerator[AsyncDriver, None]:
    """
    Provides an asynchronous Neo4j driver instance connected to Memgraph.
    Handles driver creation and closure.
    Uses MEMGRAPH_URI from environment variables or defaults.
    """
    settings = get_settings()
    uri = settings.get_memgraph_uri()
    auth = (
        (settings.MEMGRAPH_USERNAME, settings.MEMGRAPH_PASSWORD.get_secret_value() if settings.MEMGRAPH_PASSWORD else None)
        if settings.MEMGRAPH_USERNAME # Check only for username existence
        else None
    )

    driver = None
    try:
        driver = neo4j.AsyncGraphDatabase.driver(uri, auth=auth)
        # Use the driver's built-in connectivity check
        await driver.verify_connectivity()
        logger.debug("Memgraph connection verified successfully.") # Add log
        # connection_successful = await check_memgraph_connection(driver) # Removed call to undefined function
        # if not connection_successful:
        #     pytest.skip("Cannot connect to Memgraph, skipping integration tests.")
        yield driver
    except ServiceUnavailable as e: # Catch specific connection errors
        logger.error(f"Failed to connect to Memgraph at {uri}: {e}")
        pytest.skip(f"Cannot connect to Memgraph ({uri}): {e}")
    except AuthError as e: # Catch specific auth errors
        logger.error(f"Authentication failed for Memgraph at {uri}: {e}")
        pytest.skip(f"Memgraph authentication failed ({uri}): {e}")
    except Exception as e: # Catch other potential errors
        logger.error(f"Failed to connect to Memgraph: {e}", exc_info=True) # Log full traceback for unexpected errors
        pytest.skip(f"Cannot connect to Memgraph: {e}")
    finally:
        if driver:
            await driver.close()

@pytest_asyncio.fixture(scope="function")
async def memgraph_repo(memgraph_connection: AsyncDriver) -> AsyncGenerator[MemgraphGraphRepository, None]:
    """
    Create a MemgraphGraphRepository instance for testing, ensuring the database is clean before each test.
    Uses the new MemgraphGraphRepository implementation and the session-scoped driver.
    """
    from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
    repo = MemgraphGraphRepository()  # Use default config (connects to Memgraph)
    # Clean the database before the test using the driver from the connection fixture
    logger.debug("Cleaning database before yielding repository using session driver...")
    try:
        await memgraph_connection.execute_query("MATCH (n) DETACH DELETE n")
        logger.debug("Database cleaned for repository fixture.")
    except Exception as e:
         logger.error(f"Failed to clean database in memgraph_repo fixture: {e}", exc_info=True)
         pytest.fail(f"Database cleaning failed: {e}")
    yield repo
    logger.debug("Memgraph repository fixture scope ended.")

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

@pytest.fixture
def sample_text() -> str:
    """Provides a simple sample text for testing."""
    return "Alice lives in Wonderland. Bob works at OpenAI."

# --- Debugging Fixtures ---

@pytest.fixture(scope="function")
async def mock_graph_debugger() -> AsyncMock: # Removed dependency, this is just a mock
    """Provides a MOCKED instance of GraphDebugger."""
    mock_debugger = AsyncMock(spec=GraphDebugger)
    # Add specific mock behaviors if needed for unit tests
    mock_debugger.capture_system_state.return_value = SystemState(node_counts={}, relationship_counts={}, indexes=[], constraints=[])
    mock_debugger.debug_test_failure.return_value = (Investigation(hypotheses=[]), DebugContext())
    yield mock_debugger

# Define graph_debugger as a top-level fixture
# Use the session-scoped memgraph_connection for the driver
@pytest_asyncio.fixture(scope="function")
async def graph_debugger(memgraph_connection: AsyncDriver):
    """Provides a GraphDebugger instance connected via the session's neo4j driver."""
    if os.environ.get("RUNNING_INTEGRATION_TESTS") != "true":
        pytest.skip("Skipping GraphDebugger fixture: Not running integration tests.")
    from graph_rag.core.debug_tools import GraphDebugger
    driver = memgraph_connection
    try:
        logger.debug("GraphDebugger fixture: Clearing DB.")
        await driver.execute_query("MATCH (n) DETACH DELETE n")
        debugger = GraphDebugger(driver)
        return debugger
    except Exception as e:
        pytest.fail(f"Failed to initialize GraphDebugger with provided driver: {e}")

# --- Graph Repository Fixtures ---

# Removed the duplicate memgraph_repo definition previously here

# Use this fixture for tests needing a real (but potentially mocked transport) repository
# @pytest.fixture(scope="function") # This is the first definition, now corrected above
# async def memgraph_repo(memgraph_connection: AsyncDriver) -> MemgraphGraphRepository:

@pytest.fixture(scope="session")
def mock_entity_extractor() -> AsyncMock: # Add mock fixture for entity extractor
    """Provides a reusable AsyncMock for the EntityExtractor."""
    return AsyncMock() 

# --- Integration Test Client Fixture ---

@pytest_asyncio.fixture(scope="function")
async def integration_test_client(
    app: FastAPI, 
    memgraph_repo: MemgraphGraphRepository # Use the real repo fixture
    # Add other real dependencies if needed for integration flow
) -> AsyncGenerator[AsyncClient, None]:
    """Provides an async test client configured for INTEGRATION tests.
    Uses the real Memgraph repository and potentially other real services,
    ensuring that the application instance used by the client interacts
    with the actual database and components under test.
    """
    
    original_overrides = app.dependency_overrides.copy()
    
    # --- Override dependencies specifically needed for integration ---
    # Ensure the app uses the REAL repository provided by the memgraph_repo fixture
    app.dependency_overrides[get_graph_repository] = lambda: memgraph_repo
    
    # Example: If ingestion service needs to be real for these tests:
    # Need to figure out how to construct the real IngestionService here
    # It requires doc_processor, entity_extractor, embedding_service, chunk_splitter
    # This might require creating real instances or dedicated integration fixtures for them.
    # For now, let's comment out overriding the ingestion service, assuming
    # the default dependency injection will pick up the real one if others are real.
    # Or, perhaps the test directly uses the repo, not the service via API?
    # ---> Let's assume for now the test interacts directly or the default DI works.
    
    # --- Mock specific external dependencies IF necessary for integration ---
    # e.g., Mocking an external email service if it's called indirectly
    # app.dependency_overrides[get_email_service] = lambda: AsyncMock()

    # Create the client using ASGITransport against the configured app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Restore original dependency overrides after the test
    app.dependency_overrides = original_overrides

@pytest.fixture(scope="function")
def sync_test_client(app: FastAPI) -> TestClient:
    """Create a synchronous test client for the FastAPI app."""
    client = TestClient(app)
    return client 