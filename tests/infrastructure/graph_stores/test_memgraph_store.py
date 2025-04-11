"""Integration tests for MemgraphGraphRepository."""

import pytest
import uuid
from datetime import datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable

from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.domain.models import Document, Chunk, Node, Relationship, Edge, Entity
from graph_rag.config import get_settings
from graph_rag.services.embedding import EmbeddingService

pytestmark = pytest.mark.asyncio

# Mock Embedding dimensions
EMBEDDING_DIM = 384

settings = get_settings() # Get settings instance

@pytest.fixture
def mock_neo4j_driver():
    """Fixture to mock the Neo4j driver."""
    driver = AsyncMock(spec=AsyncDriver) # Add spec for better mocking
    session = AsyncMock() # Session mock

    # Configure session context management
    # __aenter__ should return the session mock itself to be used in the 'with' block
    session.__aenter__.return_value = session
    # __aexit__ needs to be an awaitable that returns None (or handles exceptions)
    session.__aexit__ = AsyncMock(return_value=None)

    # Configure session.run to return an awaitable mock result
    # This result should be suitable for 'async for record in result' if used
    mock_result = AsyncMock()
    # Example: Make it async iterable (returning an empty list for simplicity)
    async def mock_aiter():
        for i in []: # Empty async iterator
            yield i
    mock_result.__aiter__ = mock_aiter # Assign the async generator function
    # You might need to configure other methods on mock_result depending on usage (e.g., .single(), .data())
    mock_result.data.return_value = {} # Example: mock data() if called
    mock_result.single.return_value = None # Example: mock single() if called

    session.run = AsyncMock(return_value=mock_result) # session.run returns the configured mock_result
    driver.session.return_value = session # driver.session() returns the configured session mock

    return driver

@pytest.fixture
def mock_embedding_service():
    """Mock the EmbeddingService class methods globally for service tests."""
    with patch('graph_rag.services.embedding.EmbeddingService') as mock_emb_service_cls:
        mock_instance = mock_emb_service_cls.return_value
        
        # Manually add the encode attribute as a MagicMock
        mock_instance.encode = MagicMock()

        # Define the side effect for the encode mock
        def mock_encode(texts):
            if isinstance(texts, str):
                return np.random.rand(EMBEDDING_DIM).tolist()
            else:
                return [np.random.rand(EMBEDDING_DIM).tolist() for _ in texts]

        mock_instance.encode.side_effect = mock_encode # Configure the instance
        mock_instance._get_model.return_value = MagicMock() # Mock the internal model loading
        mock_instance.get_embedding_dim.return_value = EMBEDDING_DIM
        yield mock_instance # Yield the configured instance

@pytest.fixture
def graph_repository(mock_neo4j_driver, mock_embedding_service):
    """Create a MemgraphGraphRepository instance with mocked dependencies."""
    # Pass only the driver to the constructor
    # Note: mock_embedding_service is still a dependency to ensure it's patched
    return MemgraphGraphRepository(driver=mock_neo4j_driver)

@pytest.fixture
async def memgraph_repo() -> AsyncGenerator[MemgraphGraphRepository, None]:
    """Fixture providing a MemgraphGraphRepository instance."""
    repo = MemgraphGraphRepository()
    try:
        await repo.connect()
        yield repo
    finally:
        await repo.close()

@pytest.fixture
async def clean_db(memgraph_repo: MemgraphGraphRepository) -> None:
    """Fixture to clean the database before each test."""
    await memgraph_repo.clear_all_data()

@pytest.mark.integration
async def test_connection_management(memgraph_repo: MemgraphGraphRepository):
    """Test connection management functionality."""
    # Test initial connection
    assert memgraph_repo._is_connected
    
    # Test reconnection
    await memgraph_repo.close()
    assert not memgraph_repo._is_connected
    await memgraph_repo.connect()
    assert memgraph_repo._is_connected

@pytest.mark.integration
async def test_document_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test document CRUD operations."""
    # Create document
    doc_id = str(uuid.uuid4())
    document = Document(
        id=doc_id,
        content="Test document content",
        metadata={"author": "Test Author"}
    )
    await memgraph_repo.add_document(document)
    
    # Retrieve document
    retrieved = await memgraph_repo.get_document_by_id(doc_id)
    assert retrieved is not None
    assert retrieved.id == doc_id
    assert retrieved.content == document.content
    assert retrieved.metadata == document.metadata
    
    # Update document
    document.content = "Updated content"
    await memgraph_repo.add_document(document)
    updated = await memgraph_repo.get_document_by_id(doc_id)
    assert updated.content == "Updated content"

@pytest.mark.integration
async def test_chunk_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test chunk operations with document relationships."""
    # Create document
    doc_id = str(uuid.uuid4())
    document = Document(id=doc_id, content="Test document")
    await memgraph_repo.add_document(document)
    
    # Create chunk
    chunk_id = str(uuid.uuid4())
    chunk = Chunk(
        id=chunk_id,
        document_id=doc_id,
        content="Test chunk content",
        metadata={"position": 1}
    )
    await memgraph_repo.add_chunk(chunk)
    
    # Verify chunk exists and is linked to document
    query = """
    MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk {id: $chunk_id})
    RETURN c
    """
    results = await memgraph_repo._execute_read_query(
        query,
        {"doc_id": doc_id, "chunk_id": chunk_id}
    )
    assert len(results) == 1
    assert results[0]["c"]["content"] == chunk.content

@pytest.mark.integration
async def test_entity_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test entity operations using the GraphStore interface methods."""
    # Use the Entity model from domain.models
    entity_id = str(uuid.uuid4())
    entity = Entity(
        id=entity_id,
        name="John Doe", # Use 'name' as per Entity model
        type="Person",
        metadata={"age": 30} # Use 'metadata' as per Entity model
    )
    
    # Use the interface method add_entity
    await memgraph_repo.add_entity(entity)

    # Verify entity exists using get_entity_by_id
    retrieved_entity = await memgraph_repo.get_entity_by_id(entity_id)
    assert retrieved_entity is not None
    assert isinstance(retrieved_entity, Entity) # Check type
    assert retrieved_entity.id == entity_id
    assert retrieved_entity.name == "John Doe"
    assert retrieved_entity.type == "Person"
    assert retrieved_entity.metadata == {"age": 30}

@pytest.mark.integration
async def test_entity_interface_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test GraphStore interface methods using Entity model."""
    # 1. Add Entity using add_entity
    entity1_id = str(uuid.uuid4())
    entity1 = Entity(
        id=entity1_id,
        name="Alice Entity",
        type="Person",
        metadata={"skill": "Python", "city": "Testville"}
    )
    await memgraph_repo.add_entity(entity1)

    # 2. Retrieve using get_entity_by_id
    retrieved_entity1 = await memgraph_repo.get_entity_by_id(entity1_id)
    assert retrieved_entity1 is not None
    assert isinstance(retrieved_entity1, Entity)
    assert retrieved_entity1.id == entity1_id
    assert retrieved_entity1.name == "Alice Entity"
    assert retrieved_entity1.type == "Person"
    assert retrieved_entity1.metadata == {"skill": "Python", "city": "Testville"}

    # 3. Add related entities and relationships
    entity2_id = str(uuid.uuid4())
    entity2 = Entity(
        id=entity2_id,
        name="Bob Entity",
        type="Person",
        metadata={"skill": "Java"}
    )
    await memgraph_repo.add_entity(entity2)

    relationship1 = Relationship(
        id=str(uuid.uuid4()),
        source_id=entity1.id,
        target_id=entity2.id,
        type="FRIENDS_WITH",
        properties={"since": "2022"}
    )
    await memgraph_repo.add_relationship(relationship1)

    # 4. Call get_neighbors
    neighbors, relationships = await memgraph_repo.get_neighbors(entity1_id)

    # 5. Verify neighbors are Entity objects
    assert len(neighbors) == 1
    assert len(relationships) == 1

    neighbor_entity = neighbors[0]
    assert isinstance(neighbor_entity, Entity)
    assert neighbor_entity.id == entity2_id
    assert neighbor_entity.name == "Bob Entity"
    assert neighbor_entity.type == "Person"
    assert neighbor_entity.metadata == {"skill": "Java"}
    
    neighbor_rel = relationships[0]
    assert isinstance(neighbor_rel, Relationship)
    assert neighbor_rel.source_id == entity1_id
    assert neighbor_rel.target_id == entity2_id
    assert neighbor_rel.type == "FRIENDS_WITH"

@pytest.mark.integration
async def test_relationship_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test relationship operations between entities using interface methods."""
    # Create entities using Entity model
    entity1_id = str(uuid.uuid4())
    entity1 = Entity(id=entity1_id, name="Entity 1", type="TestNode")
    entity2_id = str(uuid.uuid4())
    entity2 = Entity(id=entity2_id, name="Entity 2", type="TestNode")

    await memgraph_repo.add_entity(entity1)
    await memgraph_repo.add_entity(entity2)

    # Create relationship using Relationship model
    rel_id = str(uuid.uuid4())
    relationship = Relationship(
        id=rel_id,
        source_id=entity1.id,
        target_id=entity2.id,
        type="CONNECTS_TO",
        properties={"weight": 0.5}
    )
    await memgraph_repo.add_relationship(relationship)

    # Verify relationship exists using get_neighbors
    neighbors, relationships = await memgraph_repo.get_neighbors(entity1_id, direction="outgoing")
    assert len(neighbors) == 1
    assert neighbors[0].id == entity2_id
    assert len(relationships) == 1
    retrieved_rel = relationships[0]
    assert retrieved_rel.id == rel_id # Check if ID is stored/retrieved if needed
    assert retrieved_rel.source_id == entity1_id
    assert retrieved_rel.target_id == entity2_id
    assert retrieved_rel.type == "CONNECTS_TO"
    assert retrieved_rel.properties == {"weight": 0.5}

@pytest.mark.integration
async def test_bulk_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test bulk adding entities and relationships using add_entities_and_relationships."""
    # Create entities and relationships
    entity1 = Entity(id=str(uuid.uuid4()), name="Bulk Entity 1", type="BulkNode")
    entity2 = Entity(id=str(uuid.uuid4()), name="Bulk Entity 2", type="BulkNode")
    entity3 = Entity(id=str(uuid.uuid4()), name="Bulk Entity 3", type="BulkNode")
    
    entities = [entity1, entity2, entity3]
    
    relationships = [
        Relationship(id=str(uuid.uuid4()), source_id=entity1.id, target_id=entity2.id, type="LINKED"),
        Relationship(id=str(uuid.uuid4()), source_id=entity2.id, target_id=entity3.id, type="LINKED", properties={"strength": 10})
    ]

    # Use the bulk operation method
    await memgraph_repo.add_entities_and_relationships(entities, relationships)

    # Verify entities exist
    retrieved1 = await memgraph_repo.get_entity_by_id(entity1.id)
    retrieved2 = await memgraph_repo.get_entity_by_id(entity2.id)
    retrieved3 = await memgraph_repo.get_entity_by_id(entity3.id)
    assert retrieved1 is not None and retrieved1.name == "Bulk Entity 1"
    assert retrieved2 is not None and retrieved2.name == "Bulk Entity 2"
    assert retrieved3 is not None and retrieved3.name == "Bulk Entity 3"

    # Verify relationships exist using get_neighbors
    neighbors1, rels1 = await memgraph_repo.get_neighbors(entity1.id, direction="outgoing")
    assert len(neighbors1) == 1 and neighbors1[0].id == entity2.id
    assert len(rels1) == 1 and rels1[0].type == "LINKED"

    neighbors2, rels2 = await memgraph_repo.get_neighbors(entity2.id, direction="outgoing")
    assert len(neighbors2) == 1 and neighbors2[0].id == entity3.id
    assert len(rels2) == 1 and rels2[0].type == "LINKED" and rels2[0].properties == {"strength": 10}
    
    neighbors3, rels3 = await memgraph_repo.get_neighbors(entity3.id, direction="incoming")
    assert len(neighbors3) == 1 and neighbors3[0].id == entity2.id
    assert len(rels3) == 1 and rels3[0].type == "LINKED"

@pytest.mark.integration
async def test_error_handling(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test error handling for invalid operations (e.g., adding relationship with missing entity)."""
    # Add one entity
    entity1 = Entity(id=str(uuid.uuid4()), name="Error Entity 1", type="ErrorNode")
    await memgraph_repo.add_entity(entity1)

    # Attempt to add relationship with a non-existent target ID
    non_existent_id = str(uuid.uuid4())
    invalid_relationship = Relationship(
        id=str(uuid.uuid4()),
        source_id=entity1.id,
        target_id=non_existent_id, 
        type="INVALID_LINK"
    )

    # Depending on Memgraph behavior and constraints, this might:
    # 1. Succeed (creating the relationship hanging)
    # 2. Fail (if constraints prevent it - less likely without explicit constraints)
    # 3. The repository logic might add checks (currently it doesn't seem to)
    # For now, assume it might succeed but the target node won't be retrievable.
    # We are not explicitly testing for Neo4jError here as constraints aren't set up.
    await memgraph_repo.add_relationship(invalid_relationship)

    # Verify the relationship might exist, but the neighbor entity doesn't
    neighbors, relationships = await memgraph_repo.get_neighbors(entity1.id, direction="outgoing")
    # The target entity `non_existent_id` should not be in the neighbors list
    assert len(neighbors) == 0 
    # The relationship itself might still be returned by the query if Memgraph stores it
    # Check the relationship details if it is returned
    if relationships:
        assert len(relationships) == 1
        assert relationships[0].target_id == non_existent_id
    
    # Test getting non-existent entity
    non_existent_retrieved = await memgraph_repo.get_entity_by_id(non_existent_id)
    assert non_existent_retrieved is None

@pytest.mark.integration
async def test_neighbor_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test retrieving neighbors with different directions and types."""
    # Setup: Ent1 -> Ent2 (TYPE_A), Ent3 -> Ent1 (TYPE_B)
    ent1 = Entity(id=str(uuid.uuid4()), name="Center", type="NeighborNode")
    ent2 = Entity(id=str(uuid.uuid4()), name="Outgoing", type="NeighborNode")
    ent3 = Entity(id=str(uuid.uuid4()), name="Incoming", type="NeighborNode")
    await memgraph_repo.add_entities_and_relationships(
        [ent1, ent2, ent3],
        [
            Relationship(id=str(uuid.uuid4()), source_id=ent1.id, target_id=ent2.id, type="TYPE_A"),
            Relationship(id=str(uuid.uuid4()), source_id=ent3.id, target_id=ent1.id, type="TYPE_B")
        ]
    )

    # Test outgoing
    neighbors_out, rels_out = await memgraph_repo.get_neighbors(ent1.id, direction="outgoing")
    assert len(neighbors_out) == 1 and neighbors_out[0].id == ent2.id
    assert len(rels_out) == 1 and rels_out[0].type == "TYPE_A"

    # Test incoming
    neighbors_in, rels_in = await memgraph_repo.get_neighbors(ent1.id, direction="incoming")
    assert len(neighbors_in) == 1 and neighbors_in[0].id == ent3.id
    assert len(rels_in) == 1 and rels_in[0].type == "TYPE_B"

    # Test both
    neighbors_both, rels_both = await memgraph_repo.get_neighbors(ent1.id, direction="both")
    assert len(neighbors_both) == 2
    assert {n.id for n in neighbors_both} == {ent2.id, ent3.id}
    assert len(rels_both) == 2
    assert {r.type for r in rels_both} == {"TYPE_A", "TYPE_B"}

    # Test filtering by outgoing type
    neighbors_type_a, rels_type_a = await memgraph_repo.get_neighbors(ent1.id, relationship_types=["TYPE_A"], direction="outgoing")
    assert len(neighbors_type_a) == 1 and neighbors_type_a[0].id == ent2.id
    assert len(rels_type_a) == 1 and rels_type_a[0].type == "TYPE_A"

    # Test filtering by incoming type
    neighbors_type_b, rels_type_b = await memgraph_repo.get_neighbors(ent1.id, relationship_types=["TYPE_B"], direction="incoming")
    assert len(neighbors_type_b) == 1 and neighbors_type_b[0].id == ent3.id
    assert len(rels_type_b) == 1 and rels_type_b[0].type == "TYPE_B"

    # Test filtering by non-matching type
    neighbors_none, rels_none = await memgraph_repo.get_neighbors(ent1.id, relationship_types=["TYPE_C"], direction="both")
    assert len(neighbors_none) == 0
    assert len(rels_none) == 0

@pytest.mark.integration
async def test_property_search(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test searching entities by properties using search_entities_by_properties."""
    # Add entities with different properties
    ent1 = Entity(id=str(uuid.uuid4()), name="Searchable Alice", type="Person", metadata={"city": "Zurich", "status": "active"})
    ent2 = Entity(id=str(uuid.uuid4()), name="Searchable Bob", type="Person", metadata={"city": "London", "status": "active"})
    ent3 = Entity(id=str(uuid.uuid4()), name="Inactive Charlie", type="Person", metadata={"city": "Zurich", "status": "inactive"})
    ent4 = Entity(id=str(uuid.uuid4()), name="Searchable Corp", type="Organization", metadata={"city": "Zurich"})
    await memgraph_repo.add_entities_and_relationships([ent1, ent2, ent3, ent4], [])

    # Search by type
    persons = await memgraph_repo.search_entities_by_properties({"type": "Person"})
    assert len(persons) == 3
    assert {p.name for p in persons} == {"Searchable Alice", "Searchable Bob", "Inactive Charlie"}

    # Search by metadata property (city)
    zurich_entities = await memgraph_repo.search_entities_by_properties({"city": "Zurich"})
    assert len(zurich_entities) == 3 # Alice, Charlie, Corp
    assert {e.name for e in zurich_entities} == {"Searchable Alice", "Inactive Charlie", "Searchable Corp"}

    # Search by multiple metadata properties (city and status)
    active_zurich = await memgraph_repo.search_entities_by_properties({"city": "Zurich", "status": "active"})
    assert len(active_zurich) == 1
    assert active_zurich[0].id == ent1.id

    # Search by name (exact match)
    bob_search = await memgraph_repo.search_entities_by_properties({"name": "Searchable Bob"})
    assert len(bob_search) == 1
    assert bob_search[0].id == ent2.id

    # Search with limit
    limited_persons = await memgraph_repo.search_entities_by_properties({"type": "Person"}, limit=2)
    assert len(limited_persons) == 2

    # Search for non-existent property value
    no_match = await memgraph_repo.search_entities_by_properties({"city": "Paris"})
    assert len(no_match) == 0

@pytest.mark.asyncio
async def test_add_document_creates_document(graph_repository):
    """Test that adding a document creates a document node with the correct content."""
    # Arrange
    doc_id = str(uuid.uuid4())
    content = "Test document content"
    
    # Act
    await graph_repository.add_document(doc_id, content)
    
    # Assert
    graph_repository.driver.session.return_value.run.assert_called_once()
    query = graph_repository.driver.session.return_value.run.call_args[0][0]
    assert "CREATE (d:Document" in query
    assert f"id: '{doc_id}'" in query
    assert f"content: '{content}'" in query

@pytest.mark.asyncio
async def test_add_chunk_creates_chunk_with_embedding(graph_repository):
    """Test that adding a chunk creates a chunk node with embedding."""
    # Arrange
    chunk_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    content = "Test chunk content"
    embedding = np.random.rand(EMBEDDING_DIM).tolist()
    
    # Act
    await graph_repository.add_chunk(chunk_id, doc_id, content, embedding)
    
    # Assert
    graph_repository.driver.session.return_value.run.assert_called_once()
    query = graph_repository.driver.session.return_value.run.call_args[0][0]
    assert "CREATE (c:Chunk" in query
    assert f"id: '{chunk_id}'" in query
    assert f"content: '{content}'" in query
    assert f"document_id: '{doc_id}'" in query
    assert "embedding: " in query

@pytest.mark.asyncio
async def test_link_chunk_to_document_creates_relationship(graph_repository):
    """Test that linking a chunk to a document creates a relationship."""
    # Arrange
    chunk_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    
    # Act
    await graph_repository.link_chunk_to_document(chunk_id, doc_id)
    
    # Assert
    graph_repository.driver.session.return_value.run.assert_called_once()
    query = graph_repository.driver.session.return_value.run.call_args[0][0]
    assert "MATCH (c:Chunk" in query
    assert "MATCH (d:Document" in query
    assert "CREATE (c)-[:BELONGS_TO]->(d)" in query

@pytest.mark.asyncio
async def test_get_document_by_id_returns_document(graph_repository):
    """Test that retrieving a document by ID returns the correct document."""
    # Arrange
    doc_id = str(uuid.uuid4())
    content = "Test document content"
    mock_result = AsyncMock()
    mock_result.data.return_value = [{"d": {"id": doc_id, "content": content}}]
    graph_repository.driver.session.return_value.run.return_value = mock_result
    
    # Act
    result = await graph_repository.get_document_by_id(doc_id)
    
    # Assert
    assert result["id"] == doc_id
    assert result["content"] == content
    graph_repository.driver.session.return_value.run.assert_called_once()
    query = graph_repository.driver.session.return_value.run.call_args[0][0]
    assert f"MATCH (d:Document {{id: '{doc_id}'}})" in query

@pytest.mark.asyncio
async def test_get_chunks_by_document_id_returns_chunks(graph_repository):
    """Test that retrieving chunks by document ID returns the correct chunks."""
    # Arrange
    doc_id = str(uuid.uuid4())
    chunk1 = {"id": str(uuid.uuid4()), "content": "Chunk 1"}
    chunk2 = {"id": str(uuid.uuid4()), "content": "Chunk 2"}
    mock_result = AsyncMock()
    mock_result.data.return_value = [
        {"c": chunk1},
        {"c": chunk2}
    ]
    graph_repository.driver.session.return_value.run.return_value = mock_result
    
    # Act
    result = await graph_repository.get_chunks_by_document_id(doc_id)
    
    # Assert
    assert len(result) == 2
    assert result[0]["id"] == chunk1["id"]
    assert result[0]["content"] == chunk1["content"]
    assert result[1]["id"] == chunk2["id"]
    assert result[1]["content"] == chunk2["content"]
    graph_repository.driver.session.return_value.run.assert_called_once()
    query = graph_repository.driver.session.return_value.run.call_args[0][0]
    assert f"MATCH (d:Document {{id: '{doc_id}'}})" in query
    assert "MATCH (c:Chunk)-[:BELONGS_TO]->(d)" in query
