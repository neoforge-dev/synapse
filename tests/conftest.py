import pytest
import os
from typing import AsyncGenerator, Any
# from neo4j import GraphDatabase # Keep if other tests use it, comment out if not
from httpx import AsyncClient
from fastapi import FastAPI
import asyncio
from fastapi.testclient import TestClient
from graph_rag.main import app
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository
from tests.setup_test_db import setup_test_database, cleanup_test_database

# Comment out or remove the gqlalchemy/repository import as it's unused now
# from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository 
from graph_rag.api.main import app, create_app # Use create_app factory
from graph_rag.config import settings

app = create_app() # Create app instance for client

@pytest.fixture(scope="session", autouse=True)
async def setup_test_environment():
    """Set up test environment before running tests."""
    await setup_test_database()
    yield
    await cleanup_test_database()

@pytest.fixture(scope="session")
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(scope="session")
async def graph_repository() -> AsyncGenerator[GraphRepository, None]:
    """Provides a test graph repository instance."""
    repo = GraphRepository(
        uri=os.environ["MEMGRAPH_URI"],
        username=os.environ["MEMGRAPH_USERNAME"],
        password=os.environ["MEMGRAPH_PASSWORD"]
    )
    yield repo
    await repo.close()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Comment out fixtures related to old driver/repository if no longer needed
# @pytest.fixture(scope="session")
# async def driver() -> AsyncGenerator[GraphDatabase.driver, None]:
#     """Fixture providing a Neo4j driver instance for testing."""
#     driver = GraphDatabase.driver("bolt://localhost:7687")
#     try:
#         await asyncio.sleep(2) 
#         yield driver
#     finally:
#         driver.close()
# 
# @pytest.fixture
# async def graph_repository(driver: GraphDatabase.driver) -> AsyncGenerator[MemgraphRepository, None]:
#     """Fixture providing a MemgraphRepository instance for testing."""
#     repository = MemgraphRepository(host="localhost", port=7687)
#     yield repository
#     # Clean up after each test (handled by E2E test fixture now)
#     # with driver.session() as session:
#     #     session.run("MATCH (n) DETACH DELETE n")

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

# Comment out autouse clean_database if module-scoped fixture in E2E test handles it
# @pytest.fixture(autouse=True)
# async def clean_database(driver: GraphDatabase.driver) -> None:
#     """Clean the database before each test."""
#     with driver.session() as session:
#         session.run("MATCH (n) DETACH DELETE n") 

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app) 