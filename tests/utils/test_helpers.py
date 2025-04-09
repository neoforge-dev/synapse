"""Test utilities and helper functions for GraphRAG tests."""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from neo4j import AsyncGraphDatabase
from graph_rag.models import Document, Chunk, Entity, Relationship

logger = logging.getLogger(__name__)

# --- Test Data Generators ---

def create_test_document(
    doc_id: str = "test_doc_1",
    content: str = "Test document content",
    metadata: Optional[Dict[str, Any]] = None
) -> Document:
    """Creates a test document with optional metadata."""
    if metadata is None:
        metadata = {"source": "test", "created_at": datetime.utcnow().isoformat()}
    return Document(
        id=doc_id,
        content=content,
        metadata=metadata
    )

def create_test_chunk(
    chunk_id: str = "test_chunk_1",
    text: str = "Test chunk text",
    doc_id: str = "test_doc_1",
    embedding: Optional[List[float]] = None
) -> Chunk:
    """Creates a test chunk with optional embedding."""
    if embedding is None:
        embedding = [0.1, 0.2, 0.3]  # Simple test embedding
    return Chunk(
        id=chunk_id,
        text=text,
        document_id=doc_id,
        embedding=embedding
    )

def create_test_entity(
    entity_id: str = "test_entity_1",
    name: str = "Test Entity",
    entity_type: str = "PERSON",
    metadata: Optional[Dict[str, Any]] = None
) -> Entity:
    """Creates a test entity with optional metadata."""
    if metadata is None:
        metadata = {"confidence": 0.95}
    return Entity(
        id=entity_id,
        name=name,
        type=entity_type,
        metadata=metadata
    )

def create_test_relationship(
    source: Entity,
    target: Entity,
    rel_type: str = "RELATED_TO",
    metadata: Optional[Dict[str, Any]] = None
) -> Relationship:
    """Creates a test relationship between two entities."""
    if metadata is None:
        metadata = {"confidence": 0.85}
    return Relationship(
        source=source,
        target=target,
        type=rel_type,
        metadata=metadata
    )

# --- Graph Database Helpers ---

async def clear_graph_db(driver: AsyncGraphDatabase.driver) -> None:
    """Clears all nodes and relationships from the graph database."""
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

async def verify_graph_state(
    driver: AsyncGraphDatabase.driver,
    expected_nodes: int = 0,
    expected_relationships: int = 0
) -> None:
    """Verifies the current state of the graph database."""
    async with driver.session() as session:
        # Count nodes
        node_result = await session.run("MATCH (n) RETURN count(n) as count")
        node_count = await node_result.single()
        assert node_count["count"] == expected_nodes, f"Expected {expected_nodes} nodes, found {node_count['count']}"

        # Count relationships
        rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = await rel_result.single()
        assert rel_count["count"] == expected_relationships, f"Expected {expected_relationships} relationships, found {rel_count['count']}"

# --- Async Test Helpers ---

async def wait_for_condition(
    condition_func,
    timeout: float = 5.0,
    interval: float = 0.1
) -> bool:
    """Waits for a condition to become true with timeout."""
    start_time = asyncio.get_event_loop().time()
    while True:
        if await condition_func():
            return True
        if asyncio.get_event_loop().time() - start_time > timeout:
            return False
        await asyncio.sleep(interval)

# --- Logging Helpers ---

def setup_test_logging(level: int = logging.DEBUG) -> None:
    """Sets up logging for tests."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ) 