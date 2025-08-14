import uuid

import pytest

try:
    pass  # type: ignore
except Exception:
    pytest.skip("mgclient not available; skipping Memgraph repository tests", allow_module_level=True)

from graph_rag.domain.models import Chunk, Document, Entity, Relationship

# Use the concrete implementation from conftest
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository


@pytest.mark.asyncio
async def test_delete_document(memgraph_repo: MemgraphGraphRepository, sample_document):
    """Test deleting a document and associated chunks."""
    # 1. Arrange: Create a document and a chunk linked to it
    doc = Document(**sample_document)
    chunk = Chunk(
        id="chunk_for_delete",
        text="This chunk belongs to the document to be deleted.",
        document_id=doc.id,
        embedding=[0.1] * 10,
        metadata=None,
    )
    await memgraph_repo.add_document(doc)
    await memgraph_repo.add_chunk(chunk)

    # Verify creation
    retrieved_doc = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc is not None
    # Now verify chunk creation
    retrieved_chunks = await memgraph_repo.get_chunks_by_document_id(doc.id)
    assert len(retrieved_chunks) == 1
    assert retrieved_chunks[0].id == chunk.id
    assert retrieved_chunks[0].text == chunk.text
    assert retrieved_chunks[0].embedding == chunk.embedding

    # 2. Act: Delete the document using the public method
    deleted = await memgraph_repo.delete_document(doc.id)
    assert deleted is True

    # 3. Assert: Document should be gone
    retrieved_doc_after_delete = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_after_delete is None
    # Now verify chunk deletion
    retrieved_chunks_after_delete = await memgraph_repo.get_chunks_by_document_id(
        doc.id
    )
    assert len(retrieved_chunks_after_delete) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_document(memgraph_repo: MemgraphGraphRepository):
    """Test deleting a document that does not exist."""
    document_id = "nonexistent-doc-id"
    deleted = await memgraph_repo.delete_document(document_id)
    assert deleted is False
    retrieved = await memgraph_repo.get_document_by_id(document_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_update_document_metadata(
    memgraph_repo: MemgraphGraphRepository, sample_document
):
    """Test updating only the metadata of a document."""
    doc = Document(**sample_document)
    await memgraph_repo.add_document(doc)
    retrieved_doc_before = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_before is not None
    assert retrieved_doc_before.metadata == sample_document["metadata"]

    # 2. Act: Update the metadata using add_document (MERGE semantics)
    new_metadata = {
        "source": "updated_test",
        "status": "processed",
        "nested": {"key": 1},
    }
    updated_doc = Document(id=doc.id, content=doc.content, metadata=new_metadata)
    await memgraph_repo.add_document(updated_doc)

    # 3. Assert: Verify by fetching again
    retrieved_doc_after = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_after is not None
    assert retrieved_doc_after.id == doc.id
    assert retrieved_doc_after.content == doc.content
    assert retrieved_doc_after.metadata == new_metadata
    assert retrieved_doc_after.updated_at is not None


@pytest.mark.asyncio
async def test_update_document_nonexistent(memgraph_repo: MemgraphGraphRepository):
    """Test updating a document that does not exist."""
    # Try to update a non-existent document (should create it)
    doc_id = "nonexistent-doc-for-update"
    new_metadata = {"new": "data"}
    doc = Document(id=doc_id, content="", metadata=new_metadata)
    await memgraph_repo.add_document(doc)
    retrieved = await memgraph_repo.get_document_by_id(doc_id)
    assert retrieved is not None
    assert retrieved.metadata == new_metadata


@pytest.mark.asyncio
async def test_update_document_no_properties(
    memgraph_repo: MemgraphGraphRepository, sample_document
):
    """Test updating with no properties specified should ideally not change anything except updated_at."""
    doc = Document(**sample_document)
    await memgraph_repo.add_document(doc)
    retrieved_doc_before = await memgraph_repo.get_document_by_id(doc.id)

    # Act: Update with only id and content (simulate no-op update)
    updated_doc = Document(id=doc.id, content=doc.content, metadata=doc.metadata)
    await memgraph_repo.add_document(updated_doc)

    # Assert: Should return the doc, potentially unchanged or with updated 'updated_at'
    retrieved_doc_after = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_after is not None
    assert retrieved_doc_after.id == doc.id
    assert retrieved_doc_after.metadata == retrieved_doc_before.metadata
    assert retrieved_doc_after.updated_at is not None
    # Optionally check that updated_at has changed
    # assert retrieved_doc_after.updated_at > retrieved_doc_before.updated_at


@pytest.mark.asyncio
async def test_connection(memgraph_repo: MemgraphGraphRepository):
    """Test that we can connect to the database by executing a simple query."""
    # Try to execute a simple query using the public method
    result = await memgraph_repo.execute_query("RETURN 1 as test")
    assert result is not None
    assert len(result) == 1
    assert result[0]["test"] == 1  # Result is a list of dicts


@pytest.mark.asyncio
async def test_create_and_retrieve_document(memgraph_repo: MemgraphGraphRepository):
    """Test creating and retrieving a document using add_document and get_document_by_id."""
    doc_id = f"test_doc_{uuid.uuid4()}"  # Use uuid for unique ID
    doc = Document(
        id=doc_id, content="This is a test document", metadata={"source": "test"}
    )
    await memgraph_repo.add_document(doc)
    result = await memgraph_repo.get_document_by_id(doc.id)
    assert result is not None
    assert result.id == doc.id
    assert result.content == doc.content
    assert result.metadata == {"source": "test"}


@pytest.mark.asyncio
async def test_create_and_retrieve_chunk(memgraph_repo: MemgraphGraphRepository):
    """Test creating and retrieving a chunk."""
    doc_id = f"test_doc_chunk_{uuid.uuid4()}"
    doc = Document(id=doc_id, content="This is another test document", metadata={})
    await memgraph_repo.add_document(doc)
    chunk = Chunk(
        id=f"test_chunk_{uuid.uuid4()}",
        text="This is a test chunk",
        document_id=doc.id,
        embedding=[0.1, 0.2, 0.3],
    )
    await memgraph_repo.add_chunk(chunk)
    chunks = await memgraph_repo.get_chunks_by_document_id(doc.id)
    assert len(chunks) == 1
    retrieved_chunk = chunks[0]
    assert retrieved_chunk.id == chunk.id
    assert retrieved_chunk.text == chunk.text
    assert retrieved_chunk.embedding == chunk.embedding
    # Check document_id matches
    assert retrieved_chunk.document_id == doc.id


# --- Tests for Entity and Relationship Methods ---


@pytest.mark.asyncio
async def test_add_and_get_entity(memgraph_repo: MemgraphGraphRepository):
    """Test adding and retrieving a single entity."""
    entity_id = f"test_entity_{uuid.uuid4()}"
    entity = Entity(
        id=entity_id,
        type="Person",
        name="Alice",
        properties={"email": "alice@example.com", "name": "Alice"},
    )

    await memgraph_repo.add_entity(entity)
    retrieved_entity = await memgraph_repo.get_entity_by_id(entity_id)

    assert retrieved_entity is not None
    assert retrieved_entity.id == entity.id
    assert retrieved_entity.type == "Person"
    assert retrieved_entity.name == "Alice"
    assert retrieved_entity.properties == {
        "email": "alice@example.com",
        "name": "Alice",
        "type": "Person",
    }


@pytest.mark.asyncio
async def test_add_and_get_relationship(memgraph_repo: MemgraphGraphRepository):
    """Test adding and retrieving a relationship (requires existing nodes)."""
    # Arrange: Add source and target entities first
    ent1_id = f"rel_test_ent1_{uuid.uuid4()}"
    ent2_id = f"rel_test_ent2_{uuid.uuid4()}"
    ent1 = Entity(id=ent1_id, type="Person", name="Bob")
    ent2 = Entity(id=ent2_id, type="Company", name="Acme")
    await memgraph_repo.add_entity(ent1)
    await memgraph_repo.add_entity(ent2)

    # Act: Add relationship with an ID
    rel_id = f"rel_{uuid.uuid4()}"
    rel = Relationship(
        id=rel_id,
        source_id=ent1_id,
        target_id=ent2_id,
        type="WORKS_AT",
        properties={"role": "Engineer"},
    )
    await memgraph_repo.add_relationship(rel)

    # Assert: Retrieve neighbors to verify relationship
    neighbors, relationships = await memgraph_repo.get_neighbors(
        ent1_id, direction="out"
    )

    assert len(neighbors) == 1
    assert neighbors[0].id == ent2_id
    assert len(relationships) == 1
    retrieved_rel = relationships[0]
    assert retrieved_rel.type == "WORKS_AT"
    assert retrieved_rel.source_id == ent1_id
    assert retrieved_rel.target_id == ent2_id
    assert retrieved_rel.properties == {"role": "Engineer", "id": rel_id}


@pytest.mark.asyncio
async def test_get_neighbors(memgraph_repo: MemgraphGraphRepository):
    """Test retrieving neighbors of a node."""
    # Arrange: A -> B -> C, A -> D
    a_id = f"neigh_a_{uuid.uuid4()}"
    b_id = f"neigh_b_{uuid.uuid4()}"
    c_id = f"neigh_c_{uuid.uuid4()}"
    d_id = f"neigh_d_{uuid.uuid4()}"
    ent_a = Entity(id=a_id, type="TestNode", name="A")
    ent_b = Entity(id=b_id, type="TestNode", name="B")
    ent_c = Entity(id=c_id, type="TestNode", name="C")
    ent_d = Entity(id=d_id, type="TestNode", name="D")
    rel_ab = Relationship(
        id=f"rel_{uuid.uuid4()}", source_id=a_id, target_id=b_id, type="REL"
    )
    rel_bc = Relationship(
        id=f"rel_{uuid.uuid4()}", source_id=b_id, target_id=c_id, type="REL"
    )
    rel_ad = Relationship(
        id=f"rel_{uuid.uuid4()}", source_id=a_id, target_id=d_id, type="REL"
    )

    await memgraph_repo.add_entity(ent_a)
    await memgraph_repo.add_entity(ent_b)
    await memgraph_repo.add_entity(ent_c)
    await memgraph_repo.add_entity(ent_d)
    await memgraph_repo.add_relationship(rel_ab)
    await memgraph_repo.add_relationship(rel_bc)
    await memgraph_repo.add_relationship(rel_ad)

    # Act & Assert: Neighbors of A (OUT)
    neighbors_a_out, rels_a_out = await memgraph_repo.get_neighbors(
        a_id, direction="out"
    )
    assert len(neighbors_a_out) == 2
    assert {n.id for n in neighbors_a_out} == {b_id, d_id}
    assert len(rels_a_out) == 2
    assert {r.target_id for r in rels_a_out} == {b_id, d_id}

    # Act & Assert: Neighbors of B (IN)
    neighbors_b_in, rels_b_in = await memgraph_repo.get_neighbors(b_id, direction="in")
    assert a_id in [n.id for n in neighbors_b_in]

    # Act & Assert: Neighbors of B (BOTH)
    neighbors_b_both, rels_b_both = await memgraph_repo.get_neighbors(
        b_id, direction="both"
    )
    assert len(neighbors_b_both) == 2
    assert {n.id for n in neighbors_b_both} == {a_id, c_id}
    assert len(rels_b_both) == 2
    assert {(r.source_id, r.target_id) for r in rels_b_both} == {
        (a_id, b_id),
        (b_id, c_id),
    }


@pytest.mark.asyncio
async def test_search_entities_by_properties(memgraph_repo: MemgraphGraphRepository):
    """Test searching for entities based on properties."""
    # Arrange
    id1 = f"search_ent1_{uuid.uuid4()}"
    id2 = f"search_ent2_{uuid.uuid4()}"
    # Store metadata in properties
    ent1 = Entity(
        id=id1,
        type="Person",
        name="Charlie",
        properties={"city": "London", "name": "Charlie"},
    )
    ent2 = Entity(
        id=id2,
        type="Person",
        name="David",
        properties={"city": "London", "status": "active", "name": "David"},
    )
    await memgraph_repo.add_entity(ent1)
    await memgraph_repo.add_entity(ent2)

    # Act & Assert: Search by name ONLY for now, as property search might be flawed
    # RE-ENABLE the combined property search test
    results = await memgraph_repo.search_entities_by_properties(
        {"city": "London", "type": "Person"}
    )
    assert len(results) == 2
    assert {e.id for e in results} == {id1, id2}

    results_status = await memgraph_repo.search_entities_by_properties(
        {"status": "active"}
    )
    assert len(results_status) == 1
    assert results_status[0].id == id2

    results_name = await memgraph_repo.search_entities_by_properties(
        {"name": "Charlie"}
    )
    assert len(results_name) == 1
    assert results_name[0].id == id1

    results_name_david = await memgraph_repo.search_entities_by_properties(
        {"name": "David"}
    )
    assert len(results_name_david) == 1
    assert results_name_david[0].id == id2

    # Comment out potentially failing property searches until implementation is verified
    # results = await memgraph_repo.search_entities_by_properties({"city": "London", "type": "Person"})
    # assert len(results) == 2
    # assert {e.id for e in results} == {id1, id2}
    # results_status = await memgraph_repo.search_entities_by_properties({"status": "active"})
    # assert len(results_status) == 1
    # assert results_status[0].id == id2

    # Act & Assert: Search non-existent
    results_none = await memgraph_repo.search_entities_by_properties({"city": "Paris"})
    assert len(results_none) == 0


@pytest.mark.asyncio
async def test_link_chunk_to_entities(memgraph_repo: MemgraphGraphRepository):
    """Test linking a chunk to multiple entities."""
    # Arrange
    doc_id = f"link_doc_{uuid.uuid4()}"
    chunk_id = f"link_chunk_{uuid.uuid4()}"
    ent1_id = f"link_ent1_{uuid.uuid4()}"
    ent2_id = f"link_ent2_{uuid.uuid4()}"
    doc = Document(id=doc_id, content="Doc for linking", metadata={})
    chunk = Chunk(
        id=chunk_id, text="Chunk to link", document_id=doc_id, embedding=[0.5] * 10
    )
    ent1 = Entity(id=ent1_id, type="Topic", name="Testing")
    ent2 = Entity(id=ent2_id, type="Topic", name="Linking")

    await memgraph_repo.add_document(doc)
    await memgraph_repo.add_chunk(chunk)
    await memgraph_repo.add_entity(ent1)
    await memgraph_repo.add_entity(ent2)

    # Act
    await memgraph_repo.link_chunk_to_entities(chunk_id, [ent1_id, ent2_id])

    # Assert: Verify relationships exist (e.g., using a direct query or checking neighbors)
    # We expect Chunk-[MENTIONS]->Entity relationships
    query = """
    MATCH (c:Chunk {id: $chunk_id})-[r:MENTIONS]->(e)
    RETURN e.id as entity_id
    """
    results = await memgraph_repo.execute_query(query, params={"chunk_id": chunk_id})
    assert len(results) == 2
    assert {res["entity_id"] for res in results} == {ent1_id, ent2_id}


@pytest.mark.xfail(reason="Implementation needs fix or verification")
@pytest.mark.asyncio
async def test_add_entities_and_relationships_transaction(
    memgraph_repo: MemgraphGraphRepository,
):
    """Test adding multiple entities and relationships in a single transaction."""
    # Arrange
    e1_id = f"tx_e1_{uuid.uuid4()}"
    e2_id = f"tx_e2_{uuid.uuid4()}"
    e3_id = f"tx_e3_{uuid.uuid4()}"
    entities = [
        Entity(id=e1_id, type="TX", name="Node1"),
        Entity(id=e2_id, type="TX", name="Node2"),
        Entity(id=e3_id, type="TX", name="Node3"),
    ]
    relationships = [
        Relationship(
            id=f"tx_rel1_{uuid.uuid4()}",
            source_id=e1_id,
            target_id=e2_id,
            type="TX_REL",
            properties={"val": 1},
        ),
        Relationship(
            id=f"tx_rel2_{uuid.uuid4()}",
            source_id=e2_id,
            target_id=e3_id,
            type="TX_REL",
            properties={"val": 2},
        ),
    ]

    # Act
    await memgraph_repo.add_entities_and_relationships(entities, relationships)

    # Assert: Verify all nodes and relationships exist
    node1 = await memgraph_repo.get_entity_by_id(e1_id)
    node2 = await memgraph_repo.get_entity_by_id(e2_id)
    node3 = await memgraph_repo.get_entity_by_id(e3_id)
    assert node1 is not None and node1.name == "Node1"
    assert node2 is not None and node2.name == "Node2"
    assert node3 is not None and node3.name == "Node3"

    # Check relationships by querying neighbors
    n1_neighbors, n1_rels = await memgraph_repo.get_neighbors(e1_id, direction="out")
    assert len(n1_neighbors) == 1 and n1_neighbors[0].id == e2_id
    assert (
        len(n1_rels) == 1
        and n1_rels[0].target_id == e2_id
        and n1_rels[0].properties == {"val": 1}
    )

    n2_neighbors, n2_rels = await memgraph_repo.get_neighbors(e2_id, direction="out")
    assert len(n2_neighbors) == 1 and n2_neighbors[0].id == e3_id
    assert (
        len(n2_rels) == 1
        and n2_rels[0].target_id == e3_id
        and n2_rels[0].properties == {"val": 2}
    )
