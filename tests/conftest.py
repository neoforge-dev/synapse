import pytest
import asyncio
from typing import AsyncGenerator, Any
from neo4j import GraphDatabase
from httpx import AsyncClient

from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.api.main import app


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def driver() -> AsyncGenerator[GraphDatabase.driver, None]:
    """Fixture providing a Neo4j driver instance for testing."""
    driver = GraphDatabase.driver("bolt://localhost:7687")
    try:
        # Wait for Memgraph to be ready
        await asyncio.sleep(2)  # Give Memgraph time to start
        yield driver
    finally:
        driver.close()


@pytest.fixture
async def graph_repository(driver: GraphDatabase.driver) -> AsyncGenerator[MemgraphRepository, None]:
    """Fixture providing a MemgraphRepository instance for testing."""
    repository = MemgraphRepository(host="localhost", port=7687)
    yield repository
    # Clean up after each test
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_document() -> dict[str, Any]:
    """Fixture providing a sample document for testing."""
    return {
        "id": "doc1",
        "type": "Document",
        "content": "This is a test document",
        "metadata": {"source": "test", "author": "tester"}
    }


@pytest.fixture
def sample_chunk() -> dict[str, Any]:
    """Fixture providing a sample chunk for testing."""
    return {
        "id": "chunk1",
        "type": "Chunk",
        "content": "This is a test chunk",
        "document_id": "doc1",
        "embedding": [0.1, 0.2, 0.3]
    }


@pytest.fixture(autouse=True)
async def clean_database(driver: GraphDatabase.driver) -> None:
    """Clean the database before each test."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n") 