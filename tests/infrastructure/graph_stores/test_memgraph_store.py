"""Integration tests for MemgraphGraphRepository."""

import pytest
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Dict, Any, Optional, Tuple
import os
import logging
import pytest_asyncio
from neo4j import AsyncGraphDatabase, AsyncDriver
import mgclient

from graph_rag.config import get_settings
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.domain.models import Document, Chunk, Entity, Relationship, Node

pytestmark = pytest.mark.asyncio

logger = logging.getLogger(__name__)

settings = get_settings()

@pytest_asyncio.fixture
async def memgraph_repo() -> AsyncGenerator[MemgraphGraphRepository, None]:
    """Fixture providing a MemgraphGraphRepository instance connected to the integration test DB."""
    host = settings.MEMGRAPH_HOST
    # port = settings.MEMGRAPH_PORT # No longer directly needed here
    # user = settings.MEMGRAPH_USERNAME # No longer directly needed here
    # password = settings.MEMGRAPH_PASSWORD.get_secret_value() if settings.MEMGRAPH_PASSWORD else None # No longer directly needed here
    # db_uri = settings.get_memgraph_uri() # No longer directly needed here

    allowed_hosts = ["localhost", "127.0.0.1", "memgraph"]
    if host not in allowed_hosts and "GITHUB_ACTIONS" not in os.environ:
        pytest.skip(f"Skipping integration tests: MEMGRAPH_HOST ('{host}') is not in allowed hosts ({allowed_hosts}) or not in CI.")

    # driver: Optional[AsyncDriver] = None # Driver no longer created here
    repo: Optional[MemgraphGraphRepository] = None
    try:
        # Instantiate the repository - it reads config from settings internally
        repo = MemgraphGraphRepository() 
        logger.info(f"MemgraphGraphRepository created for fixture using internal config.")
        
        # Establish the persistent connection for cleaning and testing
        await repo.connect() 

        # Clean the database using the repo's own execute method
        logger.info("Clearing Memgraph database for test using repository execute_query...")
        await repo.execute_query("MATCH (n) DETACH DELETE n;")
        logger.info("Cleared Memgraph database for test.")
        
        yield repo
    except (mgclient.Error, ConnectionRefusedError, ConnectionError) as e:
        pytest.fail(f"Failed to connect to Memgraph or setup repository: {e}")
    except Exception as e:
        pytest.fail(f"Error during Memgraph fixture setup: {e}")
    finally:
        if repo:
            await repo.close() # Use repo's close method
            logger.info("MemgraphGraphRepository connection closed in fixture finally block.")

@pytest.fixture
async def clean_db(memgraph_repo: MemgraphGraphRepository) -> None:
    """Fixture to ensure the database is clean before each test using this."""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_entity(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding and retrieving a simple Entity."""
    entity = Entity(id="ent1", name="Test Entity", type="TestType", properties={"source": "test"})

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
async def test_add_get_relationship(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding and retrieving a simple Relationship."""
    source_entity = Entity(id="src1", type="SourceType", properties={"name": "Source Entity"})
    target_entity = Entity(id="tgt1", type="TargetType", properties={"name": "Target Entity"})
    relationship = Relationship(id="rel1", type="CONNECTED_TO", source_id=source_entity.id, target_id=target_entity.id)

    await memgraph_repo.add_entity(source_entity)
    await memgraph_repo.add_entity(target_entity)
    await memgraph_repo.add_relationship(relationship)

    pytest.xfail("get_relationship_by_id not yet implemented")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_document(memgraph_repo: MemgraphGraphRepository, clean_db: None):
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
async def test_add_get_chunk(memgraph_repo: MemgraphGraphRepository, clean_db: None):
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
async def test_get_document_by_id_not_found(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test retrieving a non-existent document."""
    result = await memgraph_repo.get_node_by_id("non-existent-doc")
    assert result is None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_neighbors(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test retrieving neighbors of an entity."""
    entity1 = Entity(id="ent1", name="Entity 1", type="TestNode", properties={"extra": "e1"})
    entity2 = Entity(id="ent2", name="Entity 2", type="TestNode", properties={"extra": "e2"})
    relationship = Relationship(id="rel1", type="CONNECTED_TO", source_id=entity1.id, target_id=entity2.id)

    await memgraph_repo.add_entity(entity1)
    await memgraph_repo.add_entity(entity2)
    await memgraph_repo.add_relationship(relationship)

    neighbors_nodes, relationships = await memgraph_repo.get_neighbors(entity1.id, direction="outgoing")

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
async def test_add_duplicate_entity(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding the same entity twice (should merge/update)."""
    entity1 = Entity(id="dup_ent1", name="Duplicate Entity", type="DupType", properties={"first": 1})
    entity2 = Entity(id="dup_ent1", name="Duplicate Entity Updated", type="DupType", properties={"first": 1, "second": 2})

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
    properties = {"name": "Test Name", "value": 123, "timestamp": datetime.now(timezone.utc)}
    
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
async def test_add_relationship_and_get_neighbors(memgraph_repo: MemgraphGraphRepository):
    """Test adding nodes, a relationship between them, and retrieving neighbors."""
    source_id = uid("source-node")
    target_id = uid("target-node")
    neighbor_id = uid("neighbor-node")
    
    source_node = Node(id=source_id, type="Source", properties={"name": "Source Node"})
    target_node = Node(id=target_id, type="Target", properties={"name": "Target Node"})
    neighbor_node = Node(id=neighbor_id, type="Neighbor", properties={"name": "Neighbor Node"})
    
    # Add nodes first
    await memgraph_repo.add_node(source_node)
    await memgraph_repo.add_node(target_node)
    await memgraph_repo.add_node(neighbor_node)
    
    # Add relationships
    rel_type_st = "CONNECTS_TO"
    rel_props_st = {"weight": 10.5}
    rel_st = Relationship(id=uid("rel-st"), source_id=source_id, target_id=target_id, type=rel_type_st, properties=rel_props_st)
    await memgraph_repo.add_relationship(rel_st)
    
    rel_type_sn = "RELATED_TO"
    rel_props_sn = {"strength": "high"}
    rel_sn = Relationship(id=uid("rel-sn"), source_id=source_id, target_id=neighbor_id, type=rel_type_sn, properties=rel_props_sn)
    await memgraph_repo.add_relationship(rel_sn)

    # Test get_neighbors for source node (outgoing)
    # Convert Nodes to Entities for get_neighbors (assuming it expects Entities)
    # This might need adjustment based on actual get_neighbors signature/implementation
    # For now, creating dummy Entity objects for the test
    source_entity = Entity(id=source_id, type="Source", name="Source Node") 
    
    neighbors, relationships = await memgraph_repo.get_neighbors(source_id, direction="outgoing")
    
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
    neighbors_in, relationships_in = await memgraph_repo.get_neighbors(target_id, direction="incoming")
    assert len(neighbors_in) == 1
    assert neighbors_in[0].id == source_id
    assert len(relationships_in) == 1
    assert relationships_in[0].type == rel_type_st

    # Test get_neighbors filtering by type
    neighbors_filtered, relationships_filtered = await memgraph_repo.get_neighbors(source_id, relationship_types=[rel_type_st], direction="both")
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
    node_updated = Node(id=node_id, type="DuplicateTest", properties={"value": 2, "new_prop": "hello"})
    await memgraph_repo.add_node(node_updated)
    
    retrieved2 = await memgraph_repo.get_node_by_id(node_id)
    assert retrieved2 is not None
    assert retrieved2.properties.get("value") == 2
    assert retrieved2.properties.get("new_prop") == "hello"
    assert retrieved2.type == "DuplicateTest" # Type should remain the same on merge

@pytest.mark.asyncio
async def test_search_nodes_by_properties(memgraph_repo: MemgraphGraphRepository):
    """Test searching for nodes by properties."""
    node_id1 = uid("search-node1")
    node_id2 = uid("search-node2")
    node_id3 = uid("search-node3")
    common_type = "Searchable"
    
    node1 = Node(id=node_id1, type=common_type, properties={"name": "Node One", "group": "A"})
    node2 = Node(id=node_id2, type=common_type, properties={"name": "Node Two", "group": "A"})
    node3 = Node(id=node_id3, type="OtherType", properties={"name": "Node Three", "group": "B"})
    
    await memgraph_repo.add_node(node1)
    await memgraph_repo.add_node(node2)
    await memgraph_repo.add_node(node3)
    
    # Search by type and property
    results_A = await memgraph_repo.search_nodes_by_properties(properties={"group": "A"}, node_type=common_type, limit=10)
    assert len(results_A) == 2
    result_ids_A = {n.id for n in results_A}
    assert node_id1 in result_ids_A
    assert node_id2 in result_ids_A
    
    # Search by different property
    results_B = await memgraph_repo.search_nodes_by_properties(properties={"group": "B"}, limit=5)
    assert len(results_B) == 1
    assert results_B[0].id == node_id3
    assert results_B[0].type == "OtherType"

    # Search by name (should be unique in this test)
    results_name = await memgraph_repo.search_nodes_by_properties(properties={"name": "Node One"})
    assert len(results_name) == 1
    assert results_name[0].id == node_id1
    
    # Search with no results
    results_none = await memgraph_repo.search_nodes_by_properties(properties={"group": "C"})
    assert len(results_none) == 0
    
    # Search with limit
    results_limit = await memgraph_repo.search_nodes_by_properties(properties={"group": "A"}, node_type=common_type, limit=1)
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
    await memgraph_repo.add_relationship(Relationship(id=uid("rel-chunk1-doc"), source_id=chunk_id1, target_id=doc_id, type="BELONGS_TO"))
    await memgraph_repo.add_relationship(Relationship(id=uid("rel-chunk2-doc"), source_id=chunk_id2, target_id=doc_id, type="BELONGS_TO"))

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
    source_node = Entity(id="test_rel_source_node", type="TestEntity", name="Source Node Rel Test")
    target_node = Entity(id="test_rel_target_node", type="TestEntity", name="Target Node Rel Test")
    rel_id = f"rel-{uuid.uuid4()}"
    rel_properties = {"weight": 0.75, "source": "test"}
    relationship = Relationship(
        id=rel_id, # Assign the ID here
        source_id=source_node.id,
        target_id=target_node.id,
        type="CONNECTED_TO",
        properties=rel_properties.copy() # Pass a copy
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
    # Assert properties, excluding any automatically added ones like created/updated_at
    assert retrieved_rel.properties == rel_properties 

@pytest.mark.asyncio
async def test_get_relationship_by_id_not_found(memgraph_repo: MemgraphGraphRepository):
    """Test retrieving a non-existent relationship ID returns None."""
    non_existent_id = f"rel-non-existent-{uuid.uuid4()}"
    
    retrieved_rel = await memgraph_repo.get_relationship_by_id(non_existent_id)
    
    assert retrieved_rel is None

# TODO: Add tests for error handling (e.g., adding relationship with missing nodes)
# TODO: Add tests for add_entities_and_relationships (bulk operations)