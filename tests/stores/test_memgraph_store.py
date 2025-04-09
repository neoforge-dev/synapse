import pytest
import time
import os
import mgclient

from graph_rag.stores.memgraph_store import MemgraphStore
from graph_rag.models import Entity, Relationship

# --- Test Configuration --- 
# Get Memgraph connection details from environment variables or use defaults
MEMGRAPH_HOST = os.getenv("MEMGRAPH_HOST", "127.0.0.1")
MEMGRAPH_PORT = int(os.getenv("MEMGRAPH_PORT", 7687))

# Marker to skip tests if Memgraph is not running
requires_memgraph = pytest.mark.skipif(
    not os.getenv("RUN_MEMGRAPH_TESTS", False),
    reason="Set RUN_MEMGRAPH_TESTS=true environment variable to run Memgraph integration tests"
)

# --- Helper Functions --- 

def clear_memgraph(store: MemgraphStore):
    """Clears all data from the Memgraph instance for test isolation."""
    try:
        store._execute_query("MATCH (n) DETACH DELETE n")
        print("\nCleared Memgraph database.")
    except Exception as e:
        pytest.skip(f"Could not clear Memgraph DB, skipping test: {e}")

def check_memgraph_connection(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT) -> bool:
    """Checks if a connection to Memgraph can be established."""
    try:
        conn = mgclient.connect(host=host, port=port)
        conn.close()
        return True
    except Exception:
        return False

# Global skip if connection cannot be made initially
if not check_memgraph_connection():
    pytest.skip("Cannot connect to Memgraph, skipping all Memgraph tests.", allow_module_level=True)

# --- Fixtures --- 

@pytest.fixture(scope="module") # Use module scope for connection efficiency
def memgraph_store() -> MemgraphStore:
    """Provides a MemgraphStore instance connected to the test DB."""
    try:
        store = MemgraphStore(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)
        yield store
        store.close()
    except Exception as e:
        pytest.skip(f"Failed to initialize MemgraphStore: {e}")

@pytest.fixture(autouse=True) # Automatically run before each test in this module
def clear_db_before_test(memgraph_store):
    """Ensures the database is clean before each test function runs."""
    clear_memgraph(memgraph_store)

@pytest.fixture
def sample_entity_alice() -> Entity:
    return Entity(id="ent-alice-mg", name="Alice", type="PERSON", metadata={"age": 30})

@pytest.fixture
def sample_entity_bob() -> Entity:
    return Entity(id="ent-bob-mg", name="Bob", type="PERSON", metadata={"city": "New York"})

@pytest.fixture
def sample_entity_corp() -> Entity:
    return Entity(id="ent-corp-mg", name="CorpX", type="ORGANIZATION", metadata={"industry": "Tech"})

@pytest.fixture
def sample_relationship_knows(sample_entity_alice, sample_entity_bob) -> Relationship:
    return Relationship(source=sample_entity_alice, target=sample_entity_bob, type="KNOWS", metadata={"since": 2020})

@pytest.fixture
def sample_relationship_works_at(sample_entity_alice, sample_entity_corp) -> Relationship:
    return Relationship(source=sample_entity_alice, target=sample_entity_corp, type="WORKS_AT", metadata={"role": "Engineer"})


# --- Test Cases --- 

@requires_memgraph
def test_memgraph_connection(memgraph_store):
    """Tests basic connection and execution of a simple query."""
    assert memgraph_store._conn is not None
    assert not memgraph_store._conn.closed
    result = memgraph_store._execute_query("RETURN 1 AS result")
    assert result == [(1,)]

@requires_memgraph
def test_add_single_entity(memgraph_store, sample_entity_alice):
    """Test adding a single entity."""
    memgraph_store.add_entity(sample_entity_alice)

    # Verify by reading back
    result = memgraph_store._execute_query(
        f"MATCH (n:{sample_entity_alice.type} {{id: $id}}) RETURN n.id, n.name, n.age, labels(n)",
        params={'id': sample_entity_alice.id}
    )
    assert len(result) == 1
    node_id, name, age, labels = result[0]
    assert node_id == sample_entity_alice.id
    assert name == sample_entity_alice.name
    assert age == sample_entity_alice.metadata["age"]
    assert sample_entity_alice.type in labels
    assert "Entity" not in labels # Ensure specific type was used

@requires_memgraph
def test_update_single_entity(memgraph_store, sample_entity_alice):
    """Test that adding an entity with the same ID updates its properties."""
    # Add initial entity
    memgraph_store.add_entity(sample_entity_alice)

    # Create updated entity
    updated_alice = Entity(
        id=sample_entity_alice.id, 
        name="Alice Updated", 
        type=sample_entity_alice.type, 
        metadata={"age": 31, "status": "active"} # New age, new property
    )
    
    # Add again (should update)
    memgraph_store.add_entity(updated_alice)

    # Verify updated data
    result = memgraph_store._execute_query(
        f"MATCH (n:{updated_alice.type} {{id: $id}}) RETURN n.id, n.name, n.age, n.status, n.updated_at",
        params={'id': updated_alice.id}
    )
    assert len(result) == 1
    node_id, name, age, status, updated_at = result[0]
    assert node_id == updated_alice.id
    assert name == "Alice Updated"
    assert age == 31
    assert status == "active"
    assert updated_at is not None # Check timestamp was set

@requires_memgraph
def test_add_single_relationship(memgraph_store, sample_entity_alice, sample_entity_bob, sample_relationship_knows):
    """Test adding a single relationship between existing entities."""
    # Add entities first
    memgraph_store.add_entity(sample_entity_alice)
    memgraph_store.add_entity(sample_entity_bob)
    
    # Add relationship
    memgraph_store.add_relationship(sample_relationship_knows)

    # Verify by reading back
    result = memgraph_store._execute_query(
        f"MATCH (a:{sample_entity_alice.type} {{id: $a_id}})-[r:{sample_relationship_knows.type}]->(b:{sample_entity_bob.type} {{id: $b_id}}) "
        f"RETURN type(r), r.since",
        params={'a_id': sample_entity_alice.id, 'b_id': sample_entity_bob.id}
    )
    assert len(result) == 1
    rel_type, since = result[0]
    assert rel_type == sample_relationship_knows.type
    assert since == sample_relationship_knows.metadata["since"]

@requires_memgraph
def test_update_single_relationship(memgraph_store, sample_entity_alice, sample_entity_bob, sample_relationship_knows):
    """Test that adding a relationship again updates its properties."""
    memgraph_store.add_entity(sample_entity_alice)
    memgraph_store.add_entity(sample_entity_bob)
    memgraph_store.add_relationship(sample_relationship_knows)

    # Create updated relationship
    updated_knows = Relationship(
        source=sample_entity_alice, 
        target=sample_entity_bob, 
        type=sample_relationship_knows.type,
        metadata={"since": 2021, "strength": "high"} # Updated since, new property
    )

    # Add again (should update)
    memgraph_store.add_relationship(updated_knows)
    
    # Verify updated data
    result = memgraph_store._execute_query(
        f"MATCH (a)-[r:{updated_knows.type}]->(b) WHERE a.id = $a_id AND b.id = $b_id "
        f"RETURN r.since, r.strength, r.updated_at",
        params={'a_id': sample_entity_alice.id, 'b_id': sample_entity_bob.id}
    )
    assert len(result) == 1
    since, strength, updated_at = result[0]
    assert since == 2021
    assert strength == "high"
    assert updated_at is not None

@requires_memgraph
def test_add_relationship_fails_if_nodes_missing(memgraph_store, sample_relationship_knows):
    """Test that adding a relationship might fail or not match if nodes don't exist."""
    # Do NOT add entities first
    # The current `add_relationship` uses MATCH, so it won't create the relationship if nodes are missing.
    # We expect no error, but also no relationship created.
    try:
        memgraph_store.add_relationship(sample_relationship_knows)
    except Exception as e:
        pytest.fail(f"add_relationship raised an unexpected exception: {e}")

    # Verify no relationship was created
    result = memgraph_store._execute_query(
        f"MATCH ()-[r:{sample_relationship_knows.type}]->() RETURN count(r)"
    )
    assert result == [(0,)]

@requires_memgraph
def test_add_entities_and_relationships_bulk(memgraph_store, sample_entity_alice, sample_entity_bob, sample_entity_corp, sample_relationship_knows, sample_relationship_works_at):
    """Test the bulk add method."""
    entities = [sample_entity_alice, sample_entity_bob, sample_entity_corp]
    relationships = [sample_relationship_knows, sample_relationship_works_at]

    memgraph_store.add_entities_and_relationships(entities, relationships)

    # Verify entities
    result_nodes = memgraph_store._execute_query("MATCH (n) RETURN n.id, labels(n)")
    assert len(result_nodes) == 3
    node_ids = {n[0] for n in result_nodes}
    assert node_ids == {e.id for e in entities}
    
    # Verify relationships
    result_rels = memgraph_store._execute_query("MATCH ()-[r]->() RETURN type(r)")
    assert len(result_rels) == 2
    rel_types = {r[0] for r in result_rels}
    assert rel_types == {rel.type for rel in relationships}

    # Verify specific relationship property
    result_works = memgraph_store._execute_query(
        f"MATCH (a {{id: $a_id}})-[r:{sample_relationship_works_at.type}]->(c {{id: $c_id}}) RETURN r.role",
        params={'a_id': sample_entity_alice.id, 'c_id': sample_entity_corp.id}
    )
    assert result_works == [("Engineer",)]

@requires_memgraph
def test_bulk_add_with_empty_lists(memgraph_store):
    """Test that bulk add handles empty lists gracefully."""
    try:
        memgraph_store.add_entities_and_relationships([], [])
    except Exception as e:
        pytest.fail(f"Bulk add with empty lists failed: {e}")
    # Verify database is still empty
    result = memgraph_store._execute_query("MATCH (n) RETURN count(n)")
    assert result == [(0,)]

# --- Tests for Query Methods --- 

@requires_memgraph
def test_get_entity_by_id_found(memgraph_store, sample_entity_bob):
    """Test retrieving an existing entity by ID."""
    memgraph_store.add_entity(sample_entity_bob)
    
    retrieved_entity = memgraph_store.get_entity_by_id(sample_entity_bob.id)
    
    assert retrieved_entity is not None
    assert retrieved_entity.id == sample_entity_bob.id
    assert retrieved_entity.name == sample_entity_bob.name
    assert retrieved_entity.type == sample_entity_bob.type
    assert retrieved_entity.metadata == sample_entity_bob.metadata

@requires_memgraph
def test_get_entity_by_id_not_found(memgraph_store):
    """Test retrieving a non-existent entity by ID."""
    retrieved_entity = memgraph_store.get_entity_by_id("non-existent-id")
    assert retrieved_entity is None

@requires_memgraph
def test_get_neighbors_basic(memgraph_store, sample_entity_alice, sample_entity_bob, sample_entity_corp, sample_relationship_knows, sample_relationship_works_at):
    """Test retrieving neighbors and relationships."""
    # Add data
    memgraph_store.add_entity(sample_entity_alice)
    memgraph_store.add_entity(sample_entity_bob)
    memgraph_store.add_entity(sample_entity_corp)
    memgraph_store.add_relationship(sample_relationship_knows) # Alice -> KNOWS -> Bob
    memgraph_store.add_relationship(sample_relationship_works_at) # Alice -> WORKS_AT -> CorpX
    
    # Get neighbors of Alice
    neighbors, relationships = memgraph_store.get_neighbors(sample_entity_alice.id)
    
    # Verify neighbors
    assert len(neighbors) == 2
    neighbor_ids = {n.id for n in neighbors}
    assert neighbor_ids == {sample_entity_bob.id, sample_entity_corp.id}
    
    # Verify relationships
    assert len(relationships) == 2
    rel_types = {(r.source.id, r.type, r.target.id) for r in relationships}
    expected_rels = {
        (sample_entity_alice.id, "KNOWS", sample_entity_bob.id),
        (sample_entity_alice.id, "WORKS_AT", sample_entity_corp.id)
    }
    assert rel_types == expected_rels
    # Check relationship metadata
    for r in relationships:
        if r.type == "KNOWS":
            assert r.metadata == sample_relationship_knows.metadata
        elif r.type == "WORKS_AT":
            assert r.metadata == sample_relationship_works_at.metadata

@requires_memgraph
def test_get_neighbors_outgoing(memgraph_store, sample_entity_alice, sample_entity_bob, sample_relationship_knows):
    """Test retrieving only outgoing neighbors."""
    memgraph_store.add_entity(sample_entity_alice)
    memgraph_store.add_entity(sample_entity_bob)
    memgraph_store.add_relationship(sample_relationship_knows) # Alice -> KNOWS -> Bob
    # Add incoming relationship
    rel_bob_knows_alice = Relationship(source=sample_entity_bob, target=sample_entity_alice, type="KNOWS", metadata={})
    memgraph_store.add_relationship(rel_bob_knows_alice) 
    
    neighbors, relationships = memgraph_store.get_neighbors(sample_entity_alice.id, direction="outgoing")
    
    assert len(neighbors) == 1
    assert neighbors[0].id == sample_entity_bob.id
    assert len(relationships) == 1
    assert relationships[0].source.id == sample_entity_alice.id
    assert relationships[0].target.id == sample_entity_bob.id
    assert relationships[0].type == "KNOWS"

@requires_memgraph
def test_get_neighbors_incoming(memgraph_store, sample_entity_alice, sample_entity_bob, sample_relationship_knows):
    """Test retrieving only incoming neighbors."""
    memgraph_store.add_entity(sample_entity_alice)
    memgraph_store.add_entity(sample_entity_bob)
    memgraph_store.add_relationship(sample_relationship_knows) # Alice -> KNOWS -> Bob
    rel_bob_knows_alice = Relationship(source=sample_entity_bob, target=sample_entity_alice, type="KNOWS", metadata={})
    memgraph_store.add_relationship(rel_bob_knows_alice) # Bob -> KNOWS -> Alice
    
    neighbors, relationships = memgraph_store.get_neighbors(sample_entity_alice.id, direction="incoming")
    
    assert len(neighbors) == 1
    assert neighbors[0].id == sample_entity_bob.id # Bob is the neighbor
    assert len(relationships) == 1
    assert relationships[0].source.id == sample_entity_bob.id # Relationship source is Bob
    assert relationships[0].target.id == sample_entity_alice.id
    assert relationships[0].type == "KNOWS"

@requires_memgraph
def test_get_neighbors_with_type_filter(memgraph_store, sample_entity_alice, sample_entity_bob, sample_entity_corp, sample_relationship_knows, sample_relationship_works_at):
    """Test retrieving neighbors filtered by relationship type."""
    memgraph_store.add_entity(sample_entity_alice)
    memgraph_store.add_entity(sample_entity_bob)
    memgraph_store.add_entity(sample_entity_corp)
    memgraph_store.add_relationship(sample_relationship_knows)
    memgraph_store.add_relationship(sample_relationship_works_at)
    
    neighbors, relationships = memgraph_store.get_neighbors(sample_entity_alice.id, relationship_types=["WORKS_AT"])
    
    assert len(neighbors) == 1
    assert neighbors[0].id == sample_entity_corp.id
    assert len(relationships) == 1
    assert relationships[0].type == "WORKS_AT"

@requires_memgraph
def test_get_neighbors_no_neighbors(memgraph_store, sample_entity_alice):
    """Test retrieving neighbors for a node with no connections."""
    memgraph_store.add_entity(sample_entity_alice)
    
    neighbors, relationships = memgraph_store.get_neighbors(sample_entity_alice.id)
    
    assert len(neighbors) == 0
    assert len(relationships) == 0

@requires_memgraph
def test_get_neighbors_node_not_found(memgraph_store):
    """Test retrieving neighbors for a non-existent node ID."""
    neighbors, relationships = memgraph_store.get_neighbors("non-existent-node")
    assert len(neighbors) == 0
    assert len(relationships) == 0

# TODO: Add tests for error handling during connection
# TODO: Add tests for query methods (get_subgraph, community_detection) once implemented 