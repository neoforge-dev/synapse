"""Integration tests for MemgraphGraphRepository."""

import pytest
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Dict, Any, Optional
import os
import logging
import pytest_asyncio
from neo4j import AsyncGraphDatabase, AsyncDriver

from graph_rag.config import get_settings
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.domain.models import Document, Chunk, Entity, Relationship

pytestmark = pytest.mark.asyncio

logger = logging.getLogger(__name__)

settings = get_settings()

@pytest_asyncio.fixture
async def memgraph_repo() -> AsyncGenerator[MemgraphGraphRepository, None]:
    """Fixture providing a MemgraphGraphRepository instance connected to the integration test DB."""
    host = settings.MEMGRAPH_HOST
    port = settings.MEMGRAPH_PORT
    user = settings.MEMGRAPH_USERNAME
    password = settings.MEMGRAPH_PASSWORD.get_secret_value() if settings.MEMGRAPH_PASSWORD else None
    db_uri = settings.get_memgraph_uri()

    allowed_hosts = ["localhost", "127.0.0.1", "memgraph"]
    if host not in allowed_hosts and "GITHUB_ACTIONS" not in os.environ:
        pytest.skip(f"Skipping integration tests: MEMGRAPH_HOST ('{host}') is not in allowed hosts ({allowed_hosts}) or not in CI.")

    driver: Optional[AsyncDriver] = None
    repo: Optional[MemgraphGraphRepository] = None
    try:
        driver = AsyncGraphDatabase.driver(db_uri, auth=(user, password) if user else None)
        logger.info(f"Neo4j AsyncDriver created for fixture: {db_uri}")

        repo = MemgraphGraphRepository(driver=driver)

        logger.info("Clearing Memgraph database for test using async driver...")
        await driver.execute_query("MATCH (n) DETACH DELETE n;")
        logger.info("Cleared Memgraph database for test.")
        
        yield repo
    except ConnectionRefusedError as e:
        pytest.fail(f"Failed to connect to Memgraph ({db_uri}) for integration tests: Connection refused. Is Memgraph running? {e}")
    except Exception as e:
        pytest.fail(f"Error during Memgraph fixture setup ({db_uri}): {e}")
    finally:
        if repo:
            await repo.close()
        elif driver:
            await driver.close()
            logger.info("Neo4j AsyncDriver closed directly in fixture finally block.")

@pytest.fixture
async def clean_db(memgraph_repo: MemgraphGraphRepository) -> None:
    """Fixture to ensure the database is clean before each test using this."""
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_entity(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding and retrieving a simple Entity."""
    entity = Entity(id="ent1", name="Test Entity", type="TestType", metadata={"source": "test"})

    await memgraph_repo.add_entity(entity)
    retrieved = await memgraph_repo.get_entity_by_id(entity.id)

    assert retrieved is not None
    assert isinstance(retrieved, Entity)
    assert retrieved.id == entity.id
    assert retrieved.type == entity.type
    assert retrieved.name == entity.name
    assert retrieved.metadata.get("source") == entity.metadata.get("source")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_relationship(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding and retrieving a simple Relationship."""
    source_entity = Entity(id="src1", name="Source Entity", type="SourceType")
    target_entity = Entity(id="tgt1", name="Target Entity", type="TargetType")
    relationship = Relationship(id="rel1", type="CONNECTED_TO", source_id=source_entity.id, target_id=target_entity.id)

    await memgraph_repo.add_entity(source_entity)
    await memgraph_repo.add_entity(target_entity)
    await memgraph_repo.add_relationship(relationship)

    retrieved_relationship = await memgraph_repo.get_relationship_by_id(relationship.id)

    assert retrieved_relationship is not None
    assert isinstance(retrieved_relationship, Relationship)
    assert retrieved_relationship.id == relationship.id
    assert retrieved_relationship.type == relationship.type
    assert retrieved_relationship.source_id == relationship.source_id
    assert retrieved_relationship.target_id == relationship.target_id

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_document(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding and retrieving a Document."""
    doc = Document(id="doc1", text="Test document text", metadata={"source": "test"})

    await memgraph_repo.add_entity(doc)
    retrieved = await memgraph_repo.get_entity_by_id(doc.id)

    assert retrieved is not None
    assert isinstance(retrieved, Document)
    assert retrieved.id == doc.id
    assert retrieved.text == doc.text
    assert retrieved.metadata == doc.metadata

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_get_chunk(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding and retrieving a Chunk."""
    doc = Document(id="doc1", text="Parent document")
    chunk = Chunk(id="chunk1", text="This is a text chunk.", document_id=doc.id)

    await memgraph_repo.add_entity(doc)
    await memgraph_repo.add_entity(chunk)

    retrieved_chunk = await memgraph_repo.get_entity_by_id(chunk.id)

    assert retrieved_chunk is not None
    assert isinstance(retrieved_chunk, Chunk)
    assert retrieved_chunk.id == chunk.id
    assert retrieved_chunk.text == chunk.text
    assert retrieved_chunk.document_id == chunk.document_id

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_document_by_id_not_found(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test retrieving a non-existent document."""
    result = await memgraph_repo.get_document_by_id("non-existent-doc")

    assert result is None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_neighbors(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test retrieving neighbors of an entity."""
    # Create entities and relationships
    entity1 = Entity(id="ent1", name="Entity 1", type="TestNode")
    entity2 = Entity(id="ent2", name="Entity 2", type="TestNode")
    relationship = Relationship(id="rel1", type="CONNECTED_TO", source_id=entity1.id, target_id=entity2.id)

    await memgraph_repo.add_entity(entity1)
    await memgraph_repo.add_entity(entity2)
    await memgraph_repo.add_relationship(relationship)

    neighbors, relationships = await memgraph_repo.get_neighbors(entity1.id, direction="outgoing")

    assert len(neighbors) == 1
    assert neighbors[0].id == entity2.id
    assert neighbors[0].name == entity2.name

    assert len(relationships) == 1
    rel = relationships[0]
    assert isinstance(rel, Relationship)
    assert rel.id == relationship.id
    assert rel.type == relationship.type
    assert rel.source_id == relationship.source_id
    assert rel.target_id == relationship.target_id

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_duplicate_entity(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test adding the same entity twice (should merge/update)."""
    entity1 = Entity(id="dup_ent1", name="Duplicate Entity", type="DupType", metadata={"first": 1})
    entity2 = Entity(id="dup_ent1", name="Duplicate Entity", type="DupType", metadata={"second": 2})

    await memgraph_repo.add_entity(entity1)
    await memgraph_repo.add_entity(entity2)

    retrieved_entity = await memgraph_repo.get_entity_by_id(entity1.id)

    assert retrieved_entity is not None
    assert isinstance(retrieved_entity, Entity)
    assert retrieved_entity.id == entity1.id
    assert retrieved_entity.name == entity2.name
    assert retrieved_entity.type == entity2.type
    assert retrieved_entity.metadata == entity2.metadata

@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_as_entity(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test adding and retrieving a Document using GraphStore entity methods."""
    doc_id = str(uuid.uuid4())
    doc_content = "This is the document content."
    doc_metadata = {"author": "Test Author", "source": "test.txt"}

    document_entity = Entity(
        id=doc_id,
        type="Document",
        properties={
            "content": doc_content,
            **doc_metadata
        }
    )
    await memgraph_repo.add_entity(document_entity)

    retrieved_entity = await memgraph_repo.get_entity_by_id(doc_id)

    assert retrieved_entity is not None
    assert isinstance(retrieved_entity, Entity)
    assert retrieved_entity.id == doc_id
    assert retrieved_entity.type == "Document"
    assert retrieved_entity.properties.get("content") == doc_content
    assert retrieved_entity.properties.get("author") == doc_metadata["author"]
    assert retrieved_entity.properties.get("source") == doc_metadata["source"]

    updated_content = "Updated document content."
    updated_metadata = {"status": "updated"}
    document_entity_for_update = Entity(
        id=doc_id,
        type="Document",
        properties={
            "content": updated_content,
            "author": doc_metadata["author"],
            **updated_metadata
        }
    )
    await memgraph_repo.add_entity(document_entity_for_update)
    retrieved_updated_entity = await memgraph_repo.get_entity_by_id(doc_id)

    assert retrieved_updated_entity is not None
    assert retrieved_updated_entity.properties.get("content") == updated_content
    assert retrieved_updated_entity.properties.get("author") == doc_metadata["author"]
    assert retrieved_updated_entity.properties.get("source") is None, "Property 'source' should be removed by SET operation."
    assert retrieved_updated_entity.properties.get("status") == updated_metadata["status"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chunk_as_entity(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test adding and retrieving a Chunk using GraphStore entity methods and linking."""
    doc_id = str(uuid.uuid4())
    chunk_id = str(uuid.uuid4())
    chunk_content = "This is a text chunk."
    chunk_embedding = [0.1, 0.2, 0.3]
    chunk_metadata = {"position": 1, "doc_part": "abstract"}

    document_entity = Entity(id=doc_id, type="Document", properties={"content": "Parent doc", "source": "parent.txt"})
    await memgraph_repo.add_entity(document_entity)

    chunk_entity = Entity(
        id=chunk_id,
        type="Chunk",
        properties={
            "content": chunk_content,
            "document_id": doc_id,
            "embedding": chunk_embedding,
            **chunk_metadata
        }
    )
    await memgraph_repo.add_entity(chunk_entity)

    retrieved_chunk = await memgraph_repo.get_entity_by_id(chunk_id)
    assert retrieved_chunk is not None
    assert isinstance(retrieved_chunk, Entity)
    assert retrieved_chunk.id == chunk_id
    assert retrieved_chunk.type == "Chunk"
    assert retrieved_chunk.properties.get("content") == chunk_content
    assert retrieved_chunk.properties.get("document_id") == doc_id
    assert retrieved_chunk.properties.get("embedding") == chunk_embedding
    assert retrieved_chunk.properties.get("position") == chunk_metadata["position"]

    contains_rel_id = str(uuid.uuid4())
    contains_relationship = Relationship(
        id=contains_rel_id,
        type="CONTAINS",
        source_id=doc_id,
        target_id=chunk_id,
        properties={"verified": True}
    )
    await memgraph_repo.add_relationship(contains_relationship)

    neighbors, relationships = await memgraph_repo.get_neighbors(doc_id, relationship_types=["CONTAINS"], direction="outgoing")

    assert len(neighbors) == 1
    assert neighbors[0].id == chunk_id
    assert neighbors[0].type == "Chunk"

    assert len(relationships) == 1
    rel = relationships[0]
    assert isinstance(rel, Relationship)
    assert rel.id == contains_rel_id
    assert rel.type == "CONTAINS"
    assert rel.source_id == doc_id
    assert rel.target_id == chunk_id
    assert rel.properties.get("verified") is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_entity_interface_operations(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test GraphStore interface methods using Entity model."""
    entity1_id = str(uuid.uuid4())
    entity1_props = {"skill": "Python", "city": "Testville", "name": "Alice Entity"}
    entity1 = Entity(
        id=entity1_id,
        type="Person",
        properties=entity1_props
    )
    await memgraph_repo.add_entity(entity1)

    retrieved_entity1 = await memgraph_repo.get_entity_by_id(entity1_id)
    assert retrieved_entity1 is not None
    assert isinstance(retrieved_entity1, Entity)
    assert retrieved_entity1.id == entity1_id
    assert retrieved_entity1.type == "Person"
    retrieved_props = retrieved_entity1.properties.copy()
    retrieved_props.pop("updated_at", None)
    assert retrieved_props == entity1_props

    entity2_id = str(uuid.uuid4())
    entity2_props = {"language": "Cypher", "name": "Bob"}
    entity2 = Entity(
        id=entity2_id,
        type="Developer",
        properties=entity2_props
    )
    await memgraph_repo.add_entity(entity2)

    rel_id = str(uuid.uuid4())
    rel_props = {"since": 2024, "project": "GraphRAG"}
    relationship = Relationship(
        id=rel_id,
        type="WORKS_WITH",
        source_id=entity1_id,
        target_id=entity2_id,
        properties=rel_props
    )
    await memgraph_repo.add_relationship(relationship)

    alice_neighbors, alice_rels = await memgraph_repo.get_neighbors(entity1_id, direction="outgoing")
    assert len(alice_neighbors) == 1
    assert alice_neighbors[0].id == entity2_id
    assert alice_neighbors[0].type == "Developer"
    retrieved_neighbor_props = alice_neighbors[0].properties.copy()
    retrieved_neighbor_props.pop("updated_at", None)
    assert retrieved_neighbor_props == entity2_props

    assert len(alice_rels) == 1
    assert alice_rels[0].id == rel_id
    assert alice_rels[0].type == "WORKS_WITH"
    assert alice_rels[0].source_id == entity1_id
    assert alice_rels[0].target_id == entity2_id
    retrieved_rel_props = alice_rels[0].properties.copy()
    retrieved_rel_props.pop("updated_at", None)
    assert retrieved_rel_props == rel_props

    bob_neighbors, bob_rels = await memgraph_repo.get_neighbors(entity2_id, direction="incoming")
    assert len(bob_neighbors) == 1
    assert bob_neighbors[0].id == entity1_id
    assert len(bob_rels) == 1
    assert bob_rels[0].id == rel_id

    search_props = {"skill": "Python", "type": "Person"}
    found_entities = await memgraph_repo.search_entities_by_properties(search_props, limit=5)
    assert len(found_entities) == 1
    assert found_entities[0].id == entity1_id
    assert found_entities[0].properties.get("name") == "Alice Entity"

    search_just_type = {"type": "Developer"}
    found_devs = await memgraph_repo.search_entities_by_properties(search_just_type)
    assert len(found_devs) == 1
    assert found_devs[0].id == entity2_id

@pytest.mark.integration
@pytest.mark.asyncio
async def test_relationship_operations(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test relationship operations between entities using interface methods."""
    entity1_id = str(uuid.uuid4())
    entity1 = Entity(id=entity1_id, type="TestNode", properties={"name": "Entity 1"})
    entity2_id = str(uuid.uuid4())
    entity2 = Entity(id=entity2_id, type="TestNode", properties={"name": "Entity 2"})

    await memgraph_repo.add_entity(entity1)
    await memgraph_repo.add_entity(entity2)

    rel_id = str(uuid.uuid4())
    rel_props = {"weight": 1.5}
    relationship = Relationship(
        id=rel_id,
        type="CONNECTED_TO",
        source_id=entity1_id,
        target_id=entity2_id,
        properties=rel_props
    )

    await memgraph_repo.add_relationship(relationship)

    neighbors1, rels1 = await memgraph_repo.get_neighbors(entity1_id, direction="outgoing")
    assert len(neighbors1) == 1 and neighbors1[0].id == entity2_id
    assert len(rels1) == 1
    rel1 = rels1[0]
    assert isinstance(rel1, Relationship)
    assert rel1.id == rel_id
    assert rel1.type == "CONNECTED_TO"
    assert rel1.source_id == entity1_id
    assert rel1.target_id == entity2_id
    assert rel1.properties == rel_props

    neighbors2, rels2 = await memgraph_repo.get_neighbors(entity2_id, direction="incoming")
    assert len(neighbors2) == 1 and neighbors2[0].id == entity1_id
    assert len(rels2) == 1 and rels2[0].id == rel_id

    updated_rel_props = {"weight": 2.0, "status": "active"}
    updated_relationship = Relationship(
        id=rel_id,
        type="CONNECTED_TO",
        source_id=entity1_id,
        target_id=entity2_id,
        properties=updated_rel_props
    )
    await memgraph_repo.add_relationship(updated_relationship)

    _, rels_updated = await memgraph_repo.get_neighbors(entity1_id, direction="outgoing")
    assert len(rels_updated) == 1
    assert rels_updated[0].id == rel_id
    assert rels_updated[0].properties == updated_rel_props

@pytest.mark.integration
@pytest.mark.asyncio
async def test_bulk_operations(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test bulk adding entities and relationships using add_entities_and_relationships."""
    entity1_id = str(uuid.uuid4())
    entity2_id = str(uuid.uuid4())
    entity3_id = str(uuid.uuid4())
    entity1 = Entity(id=entity1_id, type="BulkNode", properties={"name": "Bulk Entity 1"})
    entity2 = Entity(id=entity2_id, type="BulkNode", properties={"name": "Bulk Entity 2", "value": 10})
    entity3 = Entity(id=entity3_id, type="AnotherBulkNode", properties={"name": "Bulk Entity 3"})

    entities = [entity1, entity2, entity3]

    rel1_id = str(uuid.uuid4())
    rel2_id = str(uuid.uuid4())
    relationships = [
        Relationship(id=rel1_id, source_id=entity1_id, target_id=entity2_id, type="LINKED"),
        Relationship(id=rel2_id, source_id=entity2_id, target_id=entity3_id, type="REFERENCES", properties={"strength": 10})
    ]

    await memgraph_repo.add_entities_and_relationships(entities, relationships)

    retrieved1 = await memgraph_repo.get_entity_by_id(entity1_id)
    retrieved2 = await memgraph_repo.get_entity_by_id(entity2_id)
    retrieved3 = await memgraph_repo.get_entity_by_id(entity3_id)
    assert retrieved1 is not None and retrieved1.properties.get("name") == "Bulk Entity 1" and retrieved1.type == "BulkNode"
    assert retrieved2 is not None and retrieved2.properties.get("value") == 10 and retrieved2.type == "BulkNode"
    assert retrieved3 is not None and retrieved3.type == "AnotherBulkNode"

    neighbors1, rels1 = await memgraph_repo.get_neighbors(entity1_id, direction="outgoing")
    assert len(neighbors1) == 1 and neighbors1[0].id == entity2_id
    assert len(rels1) == 1 and rels1[0].id == rel1_id and rels1[0].type == "LINKED"
    assert rels1[0].properties == {}

    neighbors2, rels2 = await memgraph_repo.get_neighbors(entity2_id, direction="outgoing", relationship_types=["REFERENCES"])
    assert len(neighbors2) == 1 and neighbors2[0].id == entity3_id
    assert len(rels2) == 1 and rels2[0].id == rel2_id and rels2[0].properties.get("strength") == 10

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test error handling for invalid operations (e.g., adding relationship with missing entity)."""
    entity1_id = str(uuid.uuid4())
    entity1 = Entity(id=entity1_id, type="ErrorNode", properties={"name": "Error Entity 1"})
    await memgraph_repo.add_entity(entity1)

    missing_entity_id = str(uuid.uuid4())
    invalid_relationship = Relationship(
        id=str(uuid.uuid4()),
        source_id=entity1_id,
        target_id=missing_entity_id,
        type="BAD_LINK"
    )

    with pytest.raises(ValueError) as excinfo:
        await memgraph_repo.add_relationship(invalid_relationship)

    assert f"failed to add/update relationship {invalid_relationship.id}" in str(excinfo.value).lower()
    assert "source or target node may not exist" in str(excinfo.value).lower()

    retrieved_entity1 = await memgraph_repo.get_entity_by_id(entity1_id)
    assert retrieved_entity1 is not None
    assert retrieved_entity1.id == entity1_id

@pytest.mark.integration
@pytest.mark.asyncio
async def test_neighbor_operations(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test retrieving neighbors with different directions and types."""
    ent1_id = str(uuid.uuid4())
    ent2_id = str(uuid.uuid4())
    ent3_id = str(uuid.uuid4())
    ent1 = Entity(id=ent1_id, type="NeighborNode", properties={"name": "Center"})
    ent2 = Entity(id=ent2_id, type="NeighborNode", properties={"name": "Outgoing"})
    ent3 = Entity(id=ent3_id, type="AnotherNeighborNode", properties={"name": "Incoming/Outgoing"})

    rel_a_id = str(uuid.uuid4())
    rel_b_id = str(uuid.uuid4())
    rel_c_id = str(uuid.uuid4())

    await memgraph_repo.add_entities_and_relationships(
        [ent1, ent2, ent3],
        [
            Relationship(id=rel_a_id, source_id=ent1_id, target_id=ent2_id, type="TYPE_A"),
            Relationship(id=rel_b_id, source_id=ent3_id, target_id=ent1_id, type="TYPE_B"),
            Relationship(id=rel_c_id, source_id=ent1_id, target_id=ent3_id, type="TYPE_C", properties={"weight": 5})
        ]
    )

    out_neighbors, out_rels = await memgraph_repo.get_neighbors(ent1_id, direction="outgoing")
    assert len(out_neighbors) == 2
    assert {n.id for n in out_neighbors} == {ent2_id, ent3_id}
    assert len(out_rels) == 2
    assert {r.id for r in out_rels} == {rel_a_id, rel_c_id}
    rel_c = next((r for r in out_rels if r.id == rel_c_id), None)
    assert rel_c is not None and rel_c.properties.get("weight") == 5

    in_neighbors, in_rels = await memgraph_repo.get_neighbors(ent1_id, direction="incoming")
    assert len(in_neighbors) == 1
    assert in_neighbors[0].id == ent3_id
    assert in_neighbors[0].type == "AnotherNeighborNode"
    assert len(in_rels) == 1
    assert in_rels[0].id == rel_b_id
    assert in_rels[0].type == "TYPE_B"

    both_neighbors, both_rels = await memgraph_repo.get_neighbors(ent1_id, direction="both")
    assert len(both_neighbors) == 2
    assert {n.id for n in both_neighbors} == {ent2_id, ent3_id}
    assert len(both_rels) == 3
    assert {r.id for r in both_rels} == {rel_a_id, rel_b_id, rel_c_id}

    type_a_neighbors, type_a_rels = await memgraph_repo.get_neighbors(ent1_id, relationship_types=["TYPE_A"], direction="outgoing")
    assert len(type_a_neighbors) == 1
    assert type_a_neighbors[0].id == ent2_id
    assert len(type_a_rels) == 1
    assert type_a_rels[0].id == rel_a_id

    type_bc_neighbors, type_bc_rels = await memgraph_repo.get_neighbors(ent1_id, relationship_types=["TYPE_B", "TYPE_C"], direction="incoming")
    assert len(type_bc_neighbors) == 1
    assert type_bc_neighbors[0].id == ent3_id
    assert len(type_bc_rels) == 1
    assert type_bc_rels[0].id == rel_b_id

    no_type_neighbors, no_type_rels = await memgraph_repo.get_neighbors(ent1_id, relationship_types=["NONEXISTENT"], direction="both")
    assert len(no_type_neighbors) == 0
    assert len(no_type_rels) == 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_property_search(memgraph_repo: MemgraphRepository, clean_db: None):
    """Test searching entities by properties using search_entities_by_properties."""
    ent1_id = str(uuid.uuid4())
    ent2_id = str(uuid.uuid4())
    ent3_id = str(uuid.uuid4())
    ent4_id = str(uuid.uuid4())
    ent1 = Entity(id=ent1_id, type="Person", properties={"name": "Searchable Alice", "city": "Zurich", "status": "active", "age": 30})
    ent2 = Entity(id=ent2_id, type="Person", properties={"name": "Searchable Bob", "city": "London", "status": "active", "age": 35})
    ent3 = Entity(id=ent3_id, type="Person", properties={"name": "Inactive Charlie", "city": "Zurich", "status": "inactive", "age": 40})
    ent4 = Entity(id=ent4_id, type="Organization", properties={"name": "Searchable Corp", "city": "Zurich", "active_projects": 5})

    await memgraph_repo.add_entities_and_relationships([ent1, ent2, ent3, ent4], [])

    zurich_entities = await memgraph_repo.search_entities_by_properties({"city": "Zurich"})
    assert len(zurich_entities) == 3
    assert {e.id for e in zurich_entities} == {ent1_id, ent3_id, ent4_id}
    alice = next((e for e in zurich_entities if e.id == ent1_id), None)
    assert alice is not None and alice.properties.get("age") == 30

    person_entities = await memgraph_repo.search_entities_by_properties({"type": "Person"})
    assert len(person_entities) == 3
    assert {e.id for e in person_entities} == {ent1_id, ent2_id, ent3_id}

    active_zurich_persons = await memgraph_repo.search_entities_by_properties({"type": "Person", "city": "Zurich", "status": "active"})
    assert len(active_zurich_persons) == 1
    assert active_zurich_persons[0].id == ent1_id
    assert active_zurich_persons[0].properties.get("name") == "Searchable Alice"

    two_persons = await memgraph_repo.search_entities_by_properties({"type": "Person"}, limit=2)
    assert len(two_persons) == 2

    no_match = await memgraph_repo.search_entities_by_properties({"city": "Paris"})
    assert len(no_match) == 0

    bob = await memgraph_repo.search_entities_by_properties({"name": "Searchable Bob"})
    assert len(bob) == 1
    assert bob[0].id == ent2_id
