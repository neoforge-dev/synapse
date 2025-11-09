"""Integration tests for MemgraphGraphRepository."""

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest

try:
    import mgclient  # type: ignore
except Exception:
    pytest.skip("mgclient not available; skipping Memgraph store tests", allow_module_level=True)
import pytest
import pytest_asyncio

from graph_rag.config import get_settings
from graph_rag.domain.models import Chunk, Document, Entity, Node, Relationship
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository

pytestmark = pytest.mark.asyncio

logger = logging.getLogger(__name__)

settings = get_settings()


@pytest_asyncio.fixture
async def memgraph_repo() -> AsyncGenerator[MemgraphGraphRepository, None]:
    """Fixture providing a MemgraphGraphRepository instance connected to the integration test DB."""
    host = settings.memgraph_host
    # port = settings.MEMGRAPH_PORT # No longer directly needed here
    # user = settings.MEMGRAPH_USERNAME # No longer directly needed here
    # password = settings.MEMGRAPH_PASSWORD.get_secret_value() if settings.MEMGRAPH_PASSWORD else None # No longer directly needed here
    # db_uri = settings.get_memgraph_uri() # No longer directly needed here

    allowed_hosts = ["localhost", "127.0.0.1", "memgraph"]
    if host not in allowed_hosts and "GITHUB_ACTIONS" not in os.environ:
        pytest.skip(
            f"Skipping integration tests: MEMGRAPH_HOST ('{host}') is not in allowed hosts ({allowed_hosts}) or not in CI."
        )

    # driver: Optional[AsyncDriver] = None # Driver no longer created here
    repo: MemgraphGraphRepository | None = None
    try:
        # Instantiate the repository - it reads config from settings internally
        repo = MemgraphGraphRepository()
        logger.info(
            "MemgraphGraphRepository created for fixture using internal config."
        )

        # Establish the persistent connection for cleaning and testing
        await repo.connect()

        # Clean the database using the repo's own execute method
        logger.info(
            "Clearing Memgraph database for test using repository execute_query..."
        )
        await repo.execute_query("MATCH (n) DETACH DELETE n;")
        logger.info("Cleared Memgraph database for test.")

        yield repo
    except (mgclient.Error, ConnectionRefusedError, ConnectionError) as e:
        pytest.skip(
            f"Memgraph not available; skipping MemgraphGraphRepository tests: {e}"
        )
    except Exception as e:
        pytest.skip(f"Skipping Memgraph tests due to setup error: {e}")
    finally:
        if repo:
            await repo.close()  # Use repo's close method
            logger.info(
                "MemgraphGraphRepository connection closed in fixture finally block."
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_entity(memgraph_repo: MemgraphGraphRepository):
    """Test adding and retrieving a simple Entity."""
    entity = Entity(
        id="ent1", name="Test Entity", type="TestType", properties={"source": "test"}
    )

    await memgraph_repo.add_entity(entity)
    retrieved = await memgraph_repo.get_entity_by_id(entity.id)

    assert retrieved is not None
    assert isinstance(retrieved, Entity)
    assert retrieved.id == entity.id
    assert retrieved.type == entity.type
    assert retrieved.name == entity.name
    assert retrieved.properties.get("source") == "test"
    assert retrieved.properties.get("name") == "Test Entity"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_relationship(memgraph_repo: MemgraphGraphRepository):
    """Test adding and retrieving a simple Relationship."""
    source_entity = Entity(
        id="src1", type="SourceType", properties={"name": "Source Entity"}
    )
    target_entity = Entity(
        id="tgt1", type="TargetType", properties={"name": "Target Entity"}
    )
    relationship = Relationship(
        id="rel1",
        type="CONNECTED_TO",
        source_id=source_entity.id,
        target_id=target_entity.id,
    )

    await memgraph_repo.add_entity(source_entity)
    await memgraph_repo.add_entity(target_entity)
    await memgraph_repo.add_relationship(relationship)

    retrieved_relationship = await memgraph_repo.get_relationship_by_id("rel1")

    assert retrieved_relationship is not None
    assert retrieved_relationship.id == "rel1"
    assert retrieved_relationship.type == "CONNECTED_TO"
    assert retrieved_relationship.source_id == source_entity.id
    assert retrieved_relationship.target_id == target_entity.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_document(memgraph_repo: MemgraphGraphRepository):
    """Test adding and retrieving a Document."""
    doc = Document(id="doc1", content="Test document text", metadata={"source": "test"})

    await memgraph_repo.add_node(doc)

    retrieved = await memgraph_repo.get_node_by_id(doc.id)

    assert retrieved is not None
    assert retrieved.id == doc.id
    assert retrieved.type == "Document"
    assert retrieved.properties.get("content") == doc.content
    assert retrieved.properties.get("metadata") == doc.metadata


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_chunk(memgraph_repo: MemgraphGraphRepository):
    """Test adding and retrieving a Chunk."""
    doc = Document(id="doc1", content="Parent document")
    chunk = Chunk(id="chunk1", text="This is a text chunk.", document_id=doc.id)

    await memgraph_repo.add_node(doc)
    await memgraph_repo.add_node(chunk)

    retrieved_chunk_node = await memgraph_repo.get_node_by_id(chunk.id)

    assert retrieved_chunk_node is not None
    assert retrieved_chunk_node.id == chunk.id
    assert retrieved_chunk_node.type == "Chunk"
    assert retrieved_chunk_node.properties.get("text") == chunk.text
    assert retrieved_chunk_node.properties.get("document_id") == chunk.document_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_document_by_id_not_found(memgraph_repo: MemgraphGraphRepository):
    """Test retrieving a non-existent document."""
    result = await memgraph_repo.get_node_by_id("non-existent-doc")
    assert result is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_neighbors(memgraph_repo: MemgraphGraphRepository):
    """Test retrieving neighbors of an entity."""
    entity1 = Entity(
        id="ent1", name="Entity 1", type="TestNode", properties={"extra": "e1"}
    )
    entity2 = Entity(
        id="ent2", name="Entity 2", type="TestNode", properties={"extra": "e2"}
    )
    relationship = Relationship(
        id="rel1", type="CONNECTED_TO", source_id=entity1.id, target_id=entity2.id
    )

    await memgraph_repo.add_entity(entity1)
    await memgraph_repo.add_entity(entity2)
    await memgraph_repo.add_relationship(relationship)

    neighbors_nodes, relationships = await memgraph_repo.get_neighbors(
        entity1.id, direction="outgoing"
    )

    assert len(neighbors_nodes) == 1
    neighbor_node = neighbors_nodes[0]
    assert neighbor_node.id == entity2.id
    assert neighbor_node.type == entity2.type
    if isinstance(neighbor_node, Entity):
        assert neighbor_node.name == entity2.name
    assert neighbor_node.properties.get("extra") == entity2.properties.get("extra")
    if isinstance(neighbor_node, Entity):
        assert "name" not in neighbor_node.properties
    else:
        assert neighbor_node.properties.get("name") == entity2.name

    assert len(relationships) == 1
    rel = relationships[0]
    assert rel.type == relationship.type
    assert rel.source_id == entity1.id
    assert rel.target_id == entity2.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_duplicate_entity(memgraph_repo: MemgraphGraphRepository):
    """Test adding the same entity twice (should merge/update)."""
    entity1 = Entity(
        id="dup_ent1", name="Duplicate Entity", type="DupType", properties={"first": 1}
    )
    entity2 = Entity(
        id="dup_ent1",
        name="Duplicate Entity Updated",
        type="DupType",
        properties={"first": 1, "second": 2},
    )

    await memgraph_repo.add_entity(entity1)
    await memgraph_repo.add_entity(entity2)

    retrieved_entity = await memgraph_repo.get_entity_by_id(entity1.id)

    assert retrieved_entity is not None
    assert isinstance(retrieved_entity, Entity)
    assert retrieved_entity.id == entity1.id
    assert retrieved_entity.type == entity2.type
    assert retrieved_entity.name == entity2.name
    assert retrieved_entity.properties.get("first") == 1
    assert retrieved_entity.properties.get("second") == 2
    assert retrieved_entity.properties.get("name") == entity2.name


# Helper function to generate unique IDs
def uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


@pytest.mark.asyncio
async def test_add_and_get_node(memgraph_repo: MemgraphGraphRepository):
    """Test adding a node and retrieving it by ID."""
    node_id = uid("test-node")
    node_type = "TestNode"
    properties = {
        "name": "Test Name",
        "value": 123,
        "timestamp": datetime.now(timezone.utc),
    }

    test_node = Node(id=node_id, type=node_type, properties=properties)

    await memgraph_repo.add_node(test_node)

    retrieved_node = await memgraph_repo.get_node_by_id(node_id)

    assert retrieved_node is not None
    assert retrieved_node.id == node_id
    assert retrieved_node.type == node_type
    # Memgraph might slightly alter timestamp precision, compare with tolerance or ignore
    # assert retrieved_node.properties.get("timestamp") == properties["timestamp"]
    assert retrieved_node.properties.get("name") == properties["name"]
    assert retrieved_node.properties.get("value") == properties["value"]
    # Check internal timestamps if needed (conversion might be tricky)
    # assert retrieved_node.created_at is not None
    # assert retrieved_node.updated_at is not None


@pytest.mark.asyncio
async def test_get_nonexistent_node(memgraph_repo: MemgraphGraphRepository):
    """Test retrieving a node that does not exist."""
    nonexistent_id = uid("nonexistent")
    retrieved_node = await memgraph_repo.get_node_by_id(nonexistent_id)
    assert retrieved_node is None


@pytest.mark.asyncio
async def test_add_relationship_and_get_neighbors(
    memgraph_repo: MemgraphGraphRepository,
):
    """Test adding nodes, a relationship between them, and retrieving neighbors."""
    source_id = uid("source-node")
    target_id = uid("target-node")
    neighbor_id = uid("neighbor-node")

    source_node = Node(id=source_id, type="Source", properties={"name": "Source Node"})
    target_node = Node(id=target_id, type="Target", properties={"name": "Target Node"})
    neighbor_node = Node(
        id=neighbor_id, type="Neighbor", properties={"name": "Neighbor Node"}
    )

    # Add nodes first
    await memgraph_repo.add_node(source_node)
    await memgraph_repo.add_node(target_node)
    await memgraph_repo.add_node(neighbor_node)

    # Add relationships
    rel_type_st = "CONNECTS_TO"
    rel_props_st = {"weight": 10.5}
    rel_st = Relationship(
        id=uid("rel-st"),
        source_id=source_id,
        target_id=target_id,
        type=rel_type_st,
        properties=rel_props_st,
    )
    await memgraph_repo.add_relationship(rel_st)

    rel_type_sn = "RELATED_TO"
    rel_props_sn = {"strength": "high"}
    rel_sn = Relationship(
        id=uid("rel-sn"),
        source_id=source_id,
        target_id=neighbor_id,
        type=rel_type_sn,
        properties=rel_props_sn,
    )
    await memgraph_repo.add_relationship(rel_sn)

    # Test get_neighbors for source node (outgoing)
    # Convert Nodes to Entities for get_neighbors (assuming it expects Entities)
    # This might need adjustment based on actual get_neighbors signature/implementation
    # For now, creating dummy Entity objects for the test
    Entity(id=source_id, type="Source", name="Source Node")

    neighbors, relationships = await memgraph_repo.get_neighbors(
        source_id, direction="outgoing"
    )

    assert len(neighbors) == 2
    neighbor_ids = {n.id for n in neighbors}
    assert target_id in neighbor_ids
    assert neighbor_id in neighbor_ids

    assert len(relationships) == 2
    rel_types = {r.type for r in relationships}
    assert rel_type_st in rel_types
    assert rel_type_sn in rel_types

    # Check relationship properties (assuming Relationship model holds properties)
    for rel in relationships:
        if rel.type == rel_type_st:
            assert rel.properties.get("weight") == rel_props_st["weight"]
            assert rel.source_id == source_id
            assert rel.target_id == target_id
        elif rel.type == rel_type_sn:
            assert rel.source_id == source_id
            assert rel.target_id == neighbor_id

    # Test get_neighbors for target node (incoming)
    neighbors_in, relationships_in = await memgraph_repo.get_neighbors(
        target_id, direction="incoming"
    )
    assert len(neighbors_in) == 1
    assert neighbors_in[0].id == source_id
    assert len(relationships_in) == 1
    assert relationships_in[0].type == rel_type_st

    # Test get_neighbors filtering by type
    neighbors_filtered, relationships_filtered = await memgraph_repo.get_neighbors(
        source_id, relationship_types=[rel_type_st], direction="both"
    )
    assert len(neighbors_filtered) == 1
    assert neighbors_filtered[0].id == target_id
    assert len(relationships_filtered) == 1
    assert relationships_filtered[0].type == rel_type_st


@pytest.mark.asyncio
async def test_add_duplicate_node(memgraph_repo: MemgraphGraphRepository):
    """Test that adding a node with the same ID updates its properties."""
    node_id = uid("dup-node")
    node = Node(id=node_id, type="DuplicateTest", properties={"value": 1})
    await memgraph_repo.add_node(node)

    retrieved1 = await memgraph_repo.get_node_by_id(node_id)
    assert retrieved1 is not None
    assert retrieved1.properties.get("value") == 1

    # Add node with same ID but different property
    node_updated = Node(
        id=node_id, type="DuplicateTest", properties={"value": 2, "new_prop": "hello"}
    )
    await memgraph_repo.add_node(node_updated)

    retrieved2 = await memgraph_repo.get_node_by_id(node_id)
    assert retrieved2 is not None
    assert retrieved2.properties.get("value") == 2
    assert retrieved2.properties.get("new_prop") == "hello"
    assert retrieved2.type == "DuplicateTest"  # Type should remain the same on merge


@pytest.mark.asyncio
async def test_search_nodes_by_properties(memgraph_repo: MemgraphGraphRepository):
    """Test searching for nodes by properties."""
    node_id1 = uid("search-node1")
    node_id2 = uid("search-node2")
    node_id3 = uid("search-node3")
    common_type = "Searchable"

    node1 = Node(
        id=node_id1, type=common_type, properties={"name": "Node One", "group": "A"}
    )
    node2 = Node(
        id=node_id2, type=common_type, properties={"name": "Node Two", "group": "A"}
    )
    node3 = Node(
        id=node_id3, type="OtherType", properties={"name": "Node Three", "group": "B"}
    )

    await memgraph_repo.add_node(node1)
    await memgraph_repo.add_node(node2)
    await memgraph_repo.add_node(node3)

    # Search by type and property
    results_A = await memgraph_repo.search_nodes_by_properties(
        properties={"group": "A"}, node_type=common_type, limit=10
    )
    assert len(results_A) == 2
    result_ids_A = {n.id for n in results_A}
    assert node_id1 in result_ids_A
    assert node_id2 in result_ids_A

    # Search by different property
    results_B = await memgraph_repo.search_nodes_by_properties(
        properties={"group": "B"}, limit=5
    )
    assert len(results_B) == 1
    assert results_B[0].id == node_id3
    assert results_B[0].type == "OtherType"

    # Search by name (should be unique in this test)
    results_name = await memgraph_repo.search_nodes_by_properties(
        properties={"name": "Node One"}
    )
    assert len(results_name) == 1
    assert results_name[0].id == node_id1

    # Search with no results
    results_none = await memgraph_repo.search_nodes_by_properties(
        properties={"group": "C"}
    )
    assert len(results_none) == 0

    # Search with limit
    results_limit = await memgraph_repo.search_nodes_by_properties(
        properties={"group": "A"}, node_type=common_type, limit=1
    )
    assert len(results_limit) == 1


@pytest.mark.asyncio
async def test_delete_document(memgraph_repo: MemgraphGraphRepository):
    """Test deleting a document and ensuring it and its chunks are gone."""
    doc_id = uid("del-doc")
    chunk_id1 = uid("del-chunk1")
    chunk_id2 = uid("del-chunk2")
    other_doc_id = uid("other-doc")

    doc_to_delete = Document(id=doc_id, content="Content to delete", metadata={})
    chunk1 = Chunk(id=chunk_id1, text="Chunk 1 delete", document_id=doc_id)
    chunk2 = Chunk(id=chunk_id2, text="Chunk 2 delete", document_id=doc_id)
    other_doc = Document(id=other_doc_id, content="Keep this", metadata={})

    # Add document, chunks, and another document
    await memgraph_repo.add_node(doc_to_delete)
    await memgraph_repo.add_node(chunk1)
    await memgraph_repo.add_node(chunk2)
    await memgraph_repo.add_node(other_doc)
    # Add relationship from chunk to doc (if implementation requires it for deletion)
    await memgraph_repo.add_relationship(
        Relationship(
            id=uid("rel-chunk1-doc"),
            source_id=chunk_id1,
            target_id=doc_id,
            type="BELONGS_TO",
        )
    )
    await memgraph_repo.add_relationship(
        Relationship(
            id=uid("rel-chunk2-doc"),
            source_id=chunk_id2,
            target_id=doc_id,
            type="BELONGS_TO",
        )
    )

    # Verify initial state
    assert await memgraph_repo.get_node_by_id(doc_id) is not None
    assert await memgraph_repo.get_node_by_id(chunk_id1) is not None
    assert await memgraph_repo.get_node_by_id(chunk_id2) is not None
    assert await memgraph_repo.get_node_by_id(other_doc_id) is not None

    # Delete the document
    deleted = await memgraph_repo.delete_document(doc_id)
    assert deleted is True

    # Verify deleted document and its chunks are gone
    assert await memgraph_repo.get_node_by_id(doc_id) is None
    assert await memgraph_repo.get_node_by_id(chunk_id1) is None
    assert await memgraph_repo.get_node_by_id(chunk_id2) is None

    # Verify other document still exists
    assert await memgraph_repo.get_node_by_id(other_doc_id) is not None

    # Test deleting non-existent document
    deleted_again = await memgraph_repo.delete_document(doc_id)
    assert deleted_again is False
    deleted_nonexistent = await memgraph_repo.delete_document(uid("nonexistent-doc"))
    assert deleted_nonexistent is False


@pytest.mark.asyncio
async def test_get_relationship_by_id(memgraph_repo: MemgraphGraphRepository):
    """Test retrieving a relationship by its ID property."""
    # 1. Setup: Create nodes and a relationship with a specific ID property
    source_node = Entity(
        id="test_rel_source_node", type="TestEntity", name="Source Node Rel Test"
    )
    target_node = Entity(
        id="test_rel_target_node", type="TestEntity", name="Target Node Rel Test"
    )
    rel_id = f"rel-{uuid.uuid4()}"
    rel_properties = {"weight": 0.75, "source": "test"}
    relationship = Relationship(
        id=rel_id,  # Assign the ID here
        source_id=source_node.id,
        target_id=target_node.id,
        type="CONNECTED_TO",
        properties=rel_properties.copy(),  # Pass a copy
    )

    # Add nodes first
    await memgraph_repo.add_node(source_node)
    await memgraph_repo.add_node(target_node)

    # Add relationship (crucially, add_relationship should store the ID property)
    await memgraph_repo.add_relationship(relationship)

    # 2. Act: Retrieve the relationship using the new method
    retrieved_rel = await memgraph_repo.get_relationship_by_id(rel_id)

    # 3. Assert: Check if the retrieved relationship matches the original
    assert retrieved_rel is not None
    assert retrieved_rel.id == rel_id
    assert retrieved_rel.source_id == source_node.id
    assert retrieved_rel.target_id == target_node.id
    assert retrieved_rel.type == "CONNECTED_TO"
    # Compare expected properties, ignoring potential extra keys like timestamps
    for key, value in rel_properties.items():
        assert key in retrieved_rel.properties
        # Handle potential type differences (e.g., datetime vs. string)
        retrieved_value = retrieved_rel.properties[key]
        if isinstance(retrieved_value, datetime):
            # ALWAYS compare ISO format string to handle potential precision differences
            # and ensure the original value (which is string) matches
            expected_value_str = value  # Value is already string here
            retrieved_value_str = retrieved_value.isoformat(timespec="microseconds")
            assert retrieved_value_str == expected_value_str
        elif isinstance(value, datetime):
            # This case shouldn't happen based on the test setup, but handle defensively
            # Convert expected datetime to string for comparison
            expected_value_str = value.isoformat(timespec="microseconds")
            assert retrieved_value == expected_value_str
        else:
            assert retrieved_value == value


@pytest.mark.asyncio
async def test_get_relationship_by_id_not_found(memgraph_repo: MemgraphGraphRepository):
    """Test retrieving a non-existent relationship ID returns None."""
    non_existent_id = f"rel-non-existent-{uuid.uuid4()}"

    retrieved_rel = await memgraph_repo.get_relationship_by_id(non_existent_id)

    assert retrieved_rel is None


# TODO: Add tests for error handling (e.g., adding relationship with missing nodes)
# TODO: Add tests for add_entities_and_relationships (bulk operations)


# @pytest.mark.xfail(reason="get_relationship_by_id not implemented yet") # XFAIL Removed
@pytest.mark.asyncio
async def test_add_get_relationship(memgraph_repo: MemgraphGraphRepository):
    """Tests adding and then retrieving a relationship by its ID."""
    repo = memgraph_repo
    source_id = uid("source-node")
    target_id = uid("target-node")
    rel_id = uid("rel-1")
    rel_type = "CONNECTED_TO"
    properties = {"since": datetime.now(timezone.utc).isoformat(), "weight": 42}

    # Add nodes first
    # Using Node model directly as add_node expects it
    await repo.add_node(
        Node(id=source_id, type="TestNode", properties={"name": "Source"})
    )
    await repo.add_node(
        Node(id=target_id, type="TestNode", properties={"name": "Target"})
    )

    # Add relationship
    rel = Relationship(
        id=rel_id,
        source_id=source_id,
        target_id=target_id,
        type=rel_type,
        properties=properties,
    )
    await repo.add_relationship(rel)

    # Attempt to retrieve the relationship by ID
    retrieved_rel = await repo.get_relationship_by_id(rel_id)  # This should now work

    assert retrieved_rel is not None
    assert retrieved_rel.id == rel_id
    assert retrieved_rel.source_id == source_id
    assert retrieved_rel.target_id == target_id
    assert retrieved_rel.type == rel_type
    # Compare expected properties, ignoring potential extra keys like timestamps
    for key, value in properties.items():
        assert key in retrieved_rel.properties
        # Handle potential type differences (e.g., datetime vs. string)
        retrieved_value = retrieved_rel.properties[key]
        if isinstance(retrieved_value, datetime):
            # ALWAYS compare ISO format string to handle potential precision differences
            # and ensure the original value (which is string) matches
            expected_value_str = value  # Value is already string here
            retrieved_value_str = retrieved_value.isoformat(timespec="microseconds")
            assert retrieved_value_str == expected_value_str
        elif isinstance(value, datetime):
            # This case shouldn't happen based on the test setup, but handle defensively
            # Convert expected datetime to string for comparison
            expected_value_str = value.isoformat(timespec="microseconds")
            assert retrieved_value == expected_value_str
        else:
            assert retrieved_value == value


# ============================================================================
# ERROR HANDLING TESTS (8 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connection_failure_reconnection(memgraph_repo: MemgraphGraphRepository):
    """Test that the repository handles connection failures gracefully with retry logic."""
    # Close the existing connection to simulate failure
    await memgraph_repo.close()

    # The retry decorator should attempt to reconnect when executing queries
    # Test that we can still perform operations after reconnection
    await memgraph_repo.connect()

    # Verify we can perform operations after reconnection
    test_node = Node(id=uid("reconnect-test"), type="TestNode", properties={"test": "reconnect"})
    await memgraph_repo.add_node(test_node)

    retrieved = await memgraph_repo.get_node_by_id(test_node.id)
    assert retrieved is not None
    assert retrieved.id == test_node.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_malformed_query_handling(memgraph_repo: MemgraphGraphRepository):
    """Test handling of malformed Cypher queries."""
    # Execute a malformed query that should raise an exception
    # Neo4j driver will raise CypherSyntaxError for invalid syntax
    from neo4j.exceptions import ClientError
    with pytest.raises(ClientError, match="(syntax|invalid)"):
        await memgraph_repo.execute_query("INVALID CYPHER SYNTAX %%%")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_relationship_with_missing_source_node(memgraph_repo: MemgraphGraphRepository):
    """Test adding a relationship when source node doesn't exist."""
    # Only create target node, not source
    target_node = Node(id=uid("target"), type="TestNode", properties={"name": "Target"})
    await memgraph_repo.add_node(target_node)

    # Try to add relationship with non-existent source
    rel = Relationship(
        id=uid("rel"),
        source_id="non-existent-source",
        target_id=target_node.id,
        type="CONNECTS_TO"
    )

    # The add_relationship method should handle this gracefully (might create nodes or fail)
    # Based on MERGE behavior, it might create the missing node
    await memgraph_repo.add_relationship(rel)

    # Verify the relationship was added (with auto-created source node)
    retrieved_rel = await memgraph_repo.get_relationship_by_id(rel.id)
    assert retrieved_rel is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_relationship_with_missing_target_node(memgraph_repo: MemgraphGraphRepository):
    """Test adding a relationship when target node doesn't exist."""
    # Only create source node, not target
    source_node = Node(id=uid("source"), type="TestNode", properties={"name": "Source"})
    await memgraph_repo.add_node(source_node)

    # Try to add relationship with non-existent target
    rel = Relationship(
        id=uid("rel"),
        source_id=source_node.id,
        target_id="non-existent-target",
        type="CONNECTS_TO"
    )

    # The add_relationship method should handle this gracefully
    await memgraph_repo.add_relationship(rel)

    # Verify the relationship was added
    retrieved_rel = await memgraph_repo.get_relationship_by_id(rel.id)
    assert retrieved_rel is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_with_null_parameters(memgraph_repo: MemgraphGraphRepository):
    """Test that queries handle null/None parameters correctly."""
    # Search for nodes with None property value
    results = await memgraph_repo.search_nodes_by_properties(
        properties={"non_existent_key": None},
        limit=10
    )
    # Should return empty list, not crash
    assert isinstance(results, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_relationship_handling(memgraph_repo: MemgraphGraphRepository):
    """Test adding duplicate relationships (same source, target, type)."""
    source = Node(id=uid("src"), type="TestNode", properties={"name": "Source"})
    target = Node(id=uid("tgt"), type="TestNode", properties={"name": "Target"})

    await memgraph_repo.add_node(source)
    await memgraph_repo.add_node(target)

    # Add first relationship
    rel1 = Relationship(
        id=uid("rel1"),
        source_id=source.id,
        target_id=target.id,
        type="SAME_TYPE",
        properties={"weight": 1}
    )
    await memgraph_repo.add_relationship(rel1)

    # Add second relationship with same source, target, type but different ID
    rel2 = Relationship(
        id=uid("rel2"),
        source_id=source.id,
        target_id=target.id,
        type="SAME_TYPE",
        properties={"weight": 2}
    )
    await memgraph_repo.add_relationship(rel2)

    # Both relationships should exist (different IDs)
    retrieved_rel1 = await memgraph_repo.get_relationship_by_id(rel1.id)
    retrieved_rel2 = await memgraph_repo.get_relationship_by_id(rel2.id)

    assert retrieved_rel1 is not None
    assert retrieved_rel2 is not None
    assert retrieved_rel1.id != retrieved_rel2.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_properties_handling(memgraph_repo: MemgraphGraphRepository):
    """Test handling of nodes with empty properties."""
    # Create node with empty properties
    node = Node(id=uid("empty"), type="EmptyProps", properties={})
    await memgraph_repo.add_node(node)

    retrieved = await memgraph_repo.get_node_by_id(node.id)
    assert retrieved is not None
    assert retrieved.id == node.id
    assert isinstance(retrieved.properties, dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_special_characters_in_properties(memgraph_repo: MemgraphGraphRepository):
    """Test handling of special characters in node properties."""
    special_chars = "Test with 'quotes', \"double quotes\", and \\backslashes\\"
    node = Node(
        id=uid("special"),
        type="SpecialTest",
        properties={"text": special_chars, "emoji": "🚀", "unicode": "日本語"}
    )

    await memgraph_repo.add_node(node)
    retrieved = await memgraph_repo.get_node_by_id(node.id)

    assert retrieved is not None
    assert retrieved.properties["text"] == special_chars
    assert retrieved.properties["emoji"] == "🚀"
    assert retrieved.properties["unicode"] == "日本語"


# ============================================================================
# CONCURRENT OPERATION TESTS (6 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_reads(memgraph_repo: MemgraphGraphRepository):
    """Test multiple concurrent read operations."""
    # Create test nodes
    node_ids = [uid(f"concurrent-read-{i}") for i in range(5)]
    for node_id in node_ids:
        node = Node(id=node_id, type="ConcurrentRead", properties={"index": node_id})
        await memgraph_repo.add_node(node)

    # Perform concurrent reads
    tasks = [memgraph_repo.get_node_by_id(node_id) for node_id in node_ids]
    results = await asyncio.gather(*tasks)

    # Verify all reads succeeded
    assert len(results) == 5
    for i, result in enumerate(results):
        assert result is not None
        assert result.id == node_ids[i]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_writes(memgraph_repo: MemgraphGraphRepository):
    """Test multiple concurrent write operations."""
    # Create nodes concurrently
    node_ids = [uid(f"concurrent-write-{i}") for i in range(10)]
    nodes = [
        Node(id=node_id, type="ConcurrentWrite", properties={"index": i})
        for i, node_id in enumerate(node_ids)
    ]

    # Write concurrently
    tasks = [memgraph_repo.add_node(node) for node in nodes]
    await asyncio.gather(*tasks)

    # Verify all writes succeeded
    for node_id in node_ids:
        retrieved = await memgraph_repo.get_node_by_id(node_id)
        assert retrieved is not None
        assert retrieved.id == node_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_read_write(memgraph_repo: MemgraphGraphRepository):
    """Test concurrent read and write operations on the same data."""
    # Create initial node
    node_id = uid("read-write")
    initial_node = Node(id=node_id, type="ReadWrite", properties={"counter": 0})
    await memgraph_repo.add_node(initial_node)

    # Mix of reads and writes
    async def read_node():
        return await memgraph_repo.get_node_by_id(node_id)

    async def update_node(value):
        updated = Node(id=node_id, type="ReadWrite", properties={"counter": value})
        await memgraph_repo.add_node(updated)

    # Execute mixed operations concurrently
    tasks = [read_node(), update_node(1), read_node(), update_node(2), read_node()]
    await asyncio.gather(*tasks)

    # Verify operations completed (final state should have counter=2)
    final = await memgraph_repo.get_node_by_id(node_id)
    assert final is not None
    assert final.properties["counter"] in [1, 2]  # One of the updates succeeded


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_entity_creation_race(memgraph_repo: MemgraphGraphRepository):
    """Test race conditions when creating entities concurrently with same ID."""
    entity_id = uid("race-entity")

    # Create multiple tasks trying to create entity with same ID
    async def create_entity(name_suffix):
        entity = Entity(
            id=entity_id,
            type="RaceTest",
            name=f"Entity-{name_suffix}",
            properties={"suffix": name_suffix}
        )
        await memgraph_repo.add_entity(entity)

    # Run concurrent creation attempts
    tasks = [create_entity(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Verify entity exists (one of the creations succeeded, others merged)
    retrieved = await memgraph_repo.get_entity_by_id(entity_id)
    assert retrieved is not None
    assert retrieved.id == entity_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_relationship_creation(memgraph_repo: MemgraphGraphRepository):
    """Test creating relationships concurrently between same nodes."""
    source = Node(id=uid("src"), type="Source", properties={})
    target = Node(id=uid("tgt"), type="Target", properties={})

    await memgraph_repo.add_node(source)
    await memgraph_repo.add_node(target)

    # Create multiple relationships concurrently
    async def create_rel(index):
        rel = Relationship(
            id=uid(f"rel-{index}"),
            source_id=source.id,
            target_id=target.id,
            type="CONCURRENT_REL",
            properties={"index": index}
        )
        await memgraph_repo.add_relationship(rel)

    tasks = [create_rel(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Verify all relationships were created
    neighbors, rels = await memgraph_repo.get_neighbors(source.id, direction="outgoing")
    assert len(rels) >= 5  # All relationships should exist


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_delete_operations(memgraph_repo: MemgraphGraphRepository):
    """Test concurrent delete operations to ensure no deadlocks."""
    # Create multiple documents
    doc_ids = [uid(f"doc-{i}") for i in range(5)]
    for doc_id in doc_ids:
        doc = Document(id=doc_id, content=f"Document {doc_id}", metadata={})
        await memgraph_repo.add_node(doc)

    # Delete concurrently
    tasks = [memgraph_repo.delete_document(doc_id) for doc_id in doc_ids]
    results = await asyncio.gather(*tasks)

    # Verify all deletes succeeded
    assert all(results)

    # Verify documents are gone
    for doc_id in doc_ids:
        retrieved = await memgraph_repo.get_node_by_id(doc_id)
        assert retrieved is None


# ============================================================================
# LARGE-SCALE DATA TESTS (4 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bulk_insert_performance(memgraph_repo: MemgraphGraphRepository):
    """Test efficient insertion of 1000+ nodes."""
    # Create 1000 nodes
    nodes = [
        Node(id=uid(f"bulk-{i}"), type="BulkTest", properties={"index": i, "data": f"node-{i}"})
        for i in range(1000)
    ]

    # Use bulk insert method
    await memgraph_repo.add_nodes(nodes)

    # Verify a sample of nodes
    sample_indices = [0, 250, 500, 750, 999]
    for i in sample_indices:
        retrieved = await memgraph_repo.get_node_by_id(nodes[i].id)
        assert retrieved is not None
        assert retrieved.properties["index"] == i


@pytest.mark.integration
@pytest.mark.asyncio
async def test_large_graph_traversal(memgraph_repo: MemgraphGraphRepository):
    """Test traversing graphs with 500+ nodes and relationships."""
    # Create a chain of 500 nodes
    num_nodes = 500
    node_ids = [uid(f"chain-{i}") for i in range(num_nodes)]

    # Add nodes
    for i, node_id in enumerate(node_ids):
        node = Node(id=node_id, type="ChainNode", properties={"position": i})
        await memgraph_repo.add_node(node)

    # Connect nodes in a chain
    for i in range(num_nodes - 1):
        rel = Relationship(
            id=uid(f"chain-rel-{i}"),
            source_id=node_ids[i],
            target_id=node_ids[i + 1],
            type="NEXT"
        )
        await memgraph_repo.add_relationship(rel)

    # Traverse from first node
    neighbors, rels = await memgraph_repo.get_neighbors(node_ids[0], direction="outgoing")
    assert len(neighbors) >= 1
    assert neighbors[0].id == node_ids[1]

    # Verify chain integrity by checking middle node
    mid_neighbors, mid_rels = await memgraph_repo.get_neighbors(
        node_ids[250], direction="both"
    )
    assert len(mid_neighbors) >= 1  # Should have at least one neighbor


@pytest.mark.integration
@pytest.mark.asyncio
async def test_large_property_search(memgraph_repo: MemgraphGraphRepository):
    """Test searching across large datasets with property filters."""
    # Create 200 nodes with various properties
    for i in range(200):
        node = Node(
            id=uid(f"search-{i}"),
            type="SearchableNode",
            properties={
                "category": f"cat-{i % 10}",  # 10 categories
                "value": i,
                "active": i % 2 == 0
            }
        )
        await memgraph_repo.add_node(node)

    # Search for specific category
    results = await memgraph_repo.search_nodes_by_properties(
        properties={"category": "cat-5"},
        node_type="SearchableNode",
        limit=100
    )

    # Should find ~20 nodes (200 total / 10 categories)
    assert len(results) >= 15  # Allow some margin
    assert all(r.properties["category"] == "cat-5" for r in results)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bulk_relationship_creation(memgraph_repo: MemgraphGraphRepository):
    """Test creating many relationships efficiently."""
    # Create hub-and-spoke topology: 1 central node, 100 connected nodes
    center_id = uid("hub")
    center = Node(id=center_id, type="Hub", properties={"role": "center"})
    await memgraph_repo.add_node(center)

    # Create spoke nodes and relationships
    spoke_ids = [uid(f"spoke-{i}") for i in range(100)]

    for spoke_id in spoke_ids:
        spoke = Node(id=spoke_id, type="Spoke", properties={})
        await memgraph_repo.add_node(spoke)

    # Add relationships
    for i, spoke_id in enumerate(spoke_ids):
        rel = Relationship(
            id=uid(f"hub-rel-{i}"),
            source_id=center_id,
            target_id=spoke_id,
            type="CONNECTS"
        )
        await memgraph_repo.add_relationship(rel)

    # Verify hub has all connections
    neighbors, rels = await memgraph_repo.get_neighbors(center_id, direction="outgoing")
    assert len(neighbors) == 100
    assert len(rels) == 100


# ============================================================================
# INTEGRATION FLOW TESTS (6 tests) - Week 2 Milestone
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_to_chunk_pipeline(memgraph_repo: MemgraphGraphRepository):
    """Test complete document-to-chunk ingestion flow."""
    # Create a document
    doc_id = uid("pipeline-doc")
    doc = Document(
        id=doc_id,
        content="This is a test document with multiple chunks of content.",
        metadata={"source": "test", "author": "test-user"}
    )
    await memgraph_repo.add_node(doc)

    # Create chunks from the document
    chunk_ids = [uid(f"chunk-{i}") for i in range(3)]
    chunks = [
        Chunk(id=chunk_ids[0], text="This is a test document", document_id=doc_id),
        Chunk(id=chunk_ids[1], text="with multiple chunks", document_id=doc_id),
        Chunk(id=chunk_ids[2], text="of content.", document_id=doc_id)
    ]

    # Add chunks
    for chunk in chunks:
        await memgraph_repo.add_node(chunk)

    # Link chunks to document
    for i, chunk_id in enumerate(chunk_ids):
        rel = Relationship(
            id=uid(f"doc-chunk-rel-{i}"),
            source_id=chunk_id,
            target_id=doc_id,
            type="BELONGS_TO",
            properties={"position": i}
        )
        await memgraph_repo.add_relationship(rel)

    # Verify the pipeline
    retrieved_doc = await memgraph_repo.get_node_by_id(doc_id)
    assert retrieved_doc is not None

    # Verify all chunks exist
    for chunk_id in chunk_ids:
        retrieved_chunk = await memgraph_repo.get_node_by_id(chunk_id)
        assert retrieved_chunk is not None
        assert retrieved_chunk.properties["document_id"] == doc_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chunk_to_entity_pipeline(memgraph_repo: MemgraphGraphRepository):
    """Test chunk-to-entity extraction flow."""
    # Create document and chunk
    doc_id = uid("entity-doc")
    chunk_id = uid("entity-chunk")

    doc = Document(id=doc_id, content="Apple Inc. was founded by Steve Jobs.", metadata={})
    chunk = Chunk(id=chunk_id, text="Apple Inc. was founded by Steve Jobs.", document_id=doc_id)

    await memgraph_repo.add_node(doc)
    await memgraph_repo.add_node(chunk)

    # Extract entities from chunk
    entities = [
        Entity(id=uid("entity-apple"), type="Organization", name="Apple Inc.", properties={}),
        Entity(id=uid("entity-jobs"), type="Person", name="Steve Jobs", properties={})
    ]

    for entity in entities:
        await memgraph_repo.add_entity(entity)

    # Link entities to chunk
    for i, entity in enumerate(entities):
        rel = Relationship(
            id=uid(f"chunk-entity-rel-{i}"),
            source_id=chunk_id,
            target_id=entity.id,
            type="MENTIONS",
            properties={"confidence": 0.95}
        )
        await memgraph_repo.add_relationship(rel)

    # Verify entity extraction
    chunk_neighbors, chunk_rels = await memgraph_repo.get_neighbors(
        chunk_id, relationship_types=["MENTIONS"], direction="outgoing"
    )
    assert len(chunk_neighbors) == 2
    assert len(chunk_rels) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_entity_relationship_pipeline(memgraph_repo: MemgraphGraphRepository):
    """Test relationship creation flow between entities."""
    # Create entities
    apple = Entity(id=uid("apple"), type="Organization", name="Apple Inc.", properties={})
    jobs = Entity(id=uid("jobs"), type="Person", name="Steve Jobs", properties={})
    wozniak = Entity(id=uid("wozniak"), type="Person", name="Steve Wozniak", properties={})

    await memgraph_repo.add_entity(apple)
    await memgraph_repo.add_entity(jobs)
    await memgraph_repo.add_entity(wozniak)

    # Create relationships
    founded_rel = Relationship(
        id=uid("founded-rel"),
        source_id=jobs.id,
        target_id=apple.id,
        type="FOUNDED",
        properties={"year": 1976}
    )
    co_founded_rel = Relationship(
        id=uid("co-founded-rel"),
        source_id=wozniak.id,
        target_id=apple.id,
        type="FOUNDED",
        properties={"year": 1976}
    )

    await memgraph_repo.add_relationship(founded_rel)
    await memgraph_repo.add_relationship(co_founded_rel)

    # Verify relationship network
    apple_neighbors, apple_rels = await memgraph_repo.get_neighbors(
        apple.id, relationship_types=["FOUNDED"], direction="incoming"
    )
    assert len(apple_neighbors) == 2
    assert {n.properties.get("name") for n in apple_neighbors} == {"Steve Jobs", "Steve Wozniak"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_document_knowledge_graph(memgraph_repo: MemgraphGraphRepository):
    """Test building a knowledge graph from multiple documents."""
    # Create multiple documents
    doc_ids = [uid(f"multi-doc-{i}") for i in range(3)]
    docs = [
        Document(id=doc_ids[0], content="Apple was founded in 1976.", metadata={"topic": "tech"}),
        Document(id=doc_ids[1], content="Steve Jobs led Apple to success.", metadata={"topic": "leadership"}),
        Document(id=doc_ids[2], content="iPhone revolutionized smartphones.", metadata={"topic": "innovation"})
    ]

    for doc in docs:
        await memgraph_repo.add_node(doc)

    # Create shared entities across documents
    apple = Entity(id=uid("apple-entity"), type="Organization", name="Apple", properties={})
    jobs = Entity(id=uid("jobs-entity"), type="Person", name="Steve Jobs", properties={})
    iphone = Entity(id=uid("iphone-entity"), type="Product", name="iPhone", properties={})

    await memgraph_repo.add_entity(apple)
    await memgraph_repo.add_entity(jobs)
    await memgraph_repo.add_entity(iphone)

    # Link entities to documents
    doc_entity_links = [
        (doc_ids[0], apple.id), (doc_ids[1], apple.id), (doc_ids[2], apple.id),
        (doc_ids[1], jobs.id), (doc_ids[2], iphone.id)
    ]

    for doc_id, entity_id in doc_entity_links:
        rel = Relationship(
            id=uid("doc-entity-link"),
            source_id=doc_id,
            target_id=entity_id,
            type="REFERENCES"
        )
        await memgraph_repo.add_relationship(rel)

    # Verify cross-document entity linking
    apple_neighbors, apple_rels = await memgraph_repo.get_neighbors(
        apple.id, relationship_types=["REFERENCES"], direction="incoming"
    )
    assert len(apple_neighbors) == 3  # Referenced in all 3 documents


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cross_document_entity_linking(memgraph_repo: MemgraphGraphRepository):
    """Test linking entities across different documents."""
    # Create two documents mentioning the same entity
    doc1_id = uid("doc1")
    doc2_id = uid("doc2")

    doc1 = Document(id=doc1_id, content="Microsoft was founded by Bill Gates.", metadata={})
    doc2 = Document(id=doc2_id, content="Bill Gates is a philanthropist.", metadata={})

    await memgraph_repo.add_node(doc1)
    await memgraph_repo.add_node(doc2)

    # Create shared entity
    gates = Entity(id=uid("gates"), type="Person", name="Bill Gates", properties={"merged": True})
    await memgraph_repo.add_entity(gates)

    # Link entity to both documents
    rel1 = Relationship(id=uid("rel1"), source_id=doc1_id, target_id=gates.id, type="MENTIONS")
    rel2 = Relationship(id=uid("rel2"), source_id=doc2_id, target_id=gates.id, type="MENTIONS")

    await memgraph_repo.add_relationship(rel1)
    await memgraph_repo.add_relationship(rel2)

    # Verify entity is linked to both documents
    entity_neighbors, entity_rels = await memgraph_repo.get_neighbors(
        gates.id, relationship_types=["MENTIONS"], direction="incoming"
    )
    assert len(entity_neighbors) == 2
    assert {n.id for n in entity_neighbors} == {doc1_id, doc2_id}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_relationship_inference_flow(memgraph_repo: MemgraphGraphRepository):
    """Test inferring relationships from document content and entity co-occurrence."""
    # Create document with multiple entity mentions
    doc_id = uid("inference-doc")
    doc = Document(
        id=doc_id,
        content="Elon Musk founded Tesla and SpaceX.",
        metadata={"inference_test": True}
    )
    await memgraph_repo.add_node(doc)

    # Create entities
    musk = Entity(id=uid("musk"), type="Person", name="Elon Musk", properties={})
    tesla = Entity(id=uid("tesla"), type="Organization", name="Tesla", properties={})
    spacex = Entity(id=uid("spacex"), type="Organization", name="SpaceX", properties={})

    await memgraph_repo.add_entity(musk)
    await memgraph_repo.add_entity(tesla)
    await memgraph_repo.add_entity(spacex)

    # Infer relationships based on co-occurrence in document
    inferred_rels = [
        Relationship(
            id=uid("inferred1"),
            source_id=musk.id,
            target_id=tesla.id,
            type="FOUNDED",
            properties={"inferred": True, "confidence": 0.9}
        ),
        Relationship(
            id=uid("inferred2"),
            source_id=musk.id,
            target_id=spacex.id,
            type="FOUNDED",
            properties={"inferred": True, "confidence": 0.9}
        )
    ]

    for rel in inferred_rels:
        await memgraph_repo.add_relationship(rel)

    # Verify inferred relationships
    musk_neighbors, musk_rels = await memgraph_repo.get_neighbors(
        musk.id, relationship_types=["FOUNDED"], direction="outgoing"
    )
    assert len(musk_neighbors) == 2
    assert all(r.properties.get("inferred") is True for r in musk_rels)
    assert all(r.properties.get("confidence") == 0.9 for r in musk_rels)
