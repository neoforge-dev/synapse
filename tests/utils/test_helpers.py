"""Test utilities and helper functions for GraphRAG tests."""

import asyncio
import logging
from typing import Any, Optional

from neo4j import AsyncDriver

from graph_rag.domain.models import Chunk, Document, Entity, Node, Relationship

logger = logging.getLogger(__name__)

# --- Test Data Generators ---


def create_test_document(
    doc_id: str = "test_doc_1",
    content: str = "Test document content",
    metadata: Optional[dict[str, Any]] = None,
) -> Document:
    """Creates a test document instance matching the Pydantic model."""
    if metadata is None:
        metadata = {"source": "test"}
    return Document(
        id=doc_id,
        content=content,
        metadata=metadata,
    )


def create_test_chunk(
    chunk_id: str = "test_chunk_1",
    content: str = "Test chunk text",
    doc_id: str = "test_doc_1",
    embedding: Optional[list[float]] = None,
) -> Chunk:
    """Creates a test chunk instance matching the Pydantic model."""
    if embedding is None:
        embedding = [0.1, 0.2, 0.3]
    return Chunk(
        id=chunk_id,
        content=content,
        document_id=doc_id,
        embedding=embedding,
    )


def create_test_entity(
    entity_id: str = "test_entity_1",
    name: str = "Test Entity",
    entity_type: str = "PERSON",
    metadata: Optional[dict[str, Any]] = None,
) -> Entity:
    """Creates a test entity instance matching the Pydantic model."""
    props = {"name": name}
    if metadata:
        props.update(metadata)
    return Entity(id=entity_id, type=entity_type, properties=props)


def create_test_relationship(
    source: Node,
    target: Node,
    rel_type: str = "RELATED_TO",
    rel_id: str = "test_rel_1",
    metadata: Optional[dict[str, Any]] = None,
) -> Relationship:
    """Creates a test relationship (Edge) instance matching the Pydantic model."""
    props = {}
    if metadata:
        props.update(metadata)
    return Relationship(
        id=rel_id,
        source_id=source.id,
        target_id=target.id,
        type=rel_type,
        properties=props,
    )


# --- Graph Database Helpers ---


async def clear_graph_db(driver: AsyncDriver) -> None:
    """Clears all nodes and relationships from the graph database."""
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


async def verify_graph_state(
    driver: AsyncDriver, expected_nodes: int = 0, expected_relationships: int = 0
) -> None:
    """Verifies the current state of the graph database."""
    async with driver.session() as session:
        # Count nodes
        node_result = await session.run("MATCH (n) RETURN count(n) as count")
        record = await node_result.single()
        assert record["count"] == expected_nodes, (
            f"Expected {expected_nodes} nodes, found {record['count']}"
        )

        # Count relationships
        rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
        record = await rel_result.single()
        assert record["count"] == expected_relationships, (
            f"Expected {expected_relationships} relationships, found {record['count']}"
        )


# --- Async Test Helpers ---


async def wait_for_condition(
    condition_func, timeout: float = 5.0, interval: float = 0.1
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
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
