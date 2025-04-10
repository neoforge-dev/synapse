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
from graph_rag.config import settings
from graph_rag.services.embedding import EmbeddingService

pytestmark = pytest.mark.asyncio

# Mock Embedding dimensions
EMBEDDING_DIM = 384

@pytest.fixture
def mock_neo4j_driver():
    """Fixture to mock the Neo4j driver."""
    driver = AsyncMock()
    session = AsyncMock()
    driver.session.return_value = session
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
    """Test entity operations."""
    # Create entity (using Node model)
    entity_id = str(uuid.uuid4())
    entity = Node(
        id=entity_id,
        type="Person", # Set the type for the node
        properties={"name": "John Doe", "age": 30} # Use the properties field
    )
    # await memgraph_repo.add_entity(entity) # Needs add_node or similar
    await memgraph_repo.add_node(entity) # Assuming a generic add_node method

    # Verify entity exists
    # retrieved_entity = await memgraph_repo.get_entity_by_id(entity_id)
    retrieved_node = await memgraph_repo.get_node_by_id(entity_id) # Assuming get_node_by_id
    assert retrieved_node is not None
    assert retrieved_node.id == entity_id
    assert retrieved_node.type == "Person"
    assert retrieved_node.properties == {"name": "John Doe", "age": 30}

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
    """Test relationship operations between entities."""
    # Create entities (using Node model)
    person1_id = str(uuid.uuid4())
    person1 = Node(
        id=person1_id,
        type="Person",
        properties={"name": "Alice"}
    )
    person2_id = str(uuid.uuid4())
    person2 = Node(
        id=person2_id,
        type="Person",
        properties={"name": "Bob"}
    )
    # await memgraph_repo.add_entity(person1)
    # await memgraph_repo.add_entity(person2)
    await memgraph_repo.add_node(person1) # Use add_node
    await memgraph_repo.add_node(person2) # Use add_node

    # Create relationship using domain model (Edge alias)
    relationship = Relationship( # Relationship is Edge
        id=str(uuid.uuid4()), # Reinstate ID
        source_id=person1.id, # Required by Edge
        target_id=person2.id, # Required by Edge
        type="KNOWS",          # Required by Edge
        properties={"since": datetime.now().isoformat()} # Optional
    )
    await memgraph_repo.add_relationship(relationship)
    
    # Verify relationship exists
    query = """
    MATCH (p1:Person {id: $p1_id})-[r:KNOWS]->(p2:Person {id: $p2_id})
    RETURN r
    """
    results = await memgraph_repo._execute_read_query(
        query,
        {"p1_id": person1.id, "p2_id": person2.id}
    )
    assert len(results) == 1

@pytest.mark.integration
async def test_bulk_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test bulk operations for entities and relationships."""
    # Create entities (using Node model)
    entities = [
        Node(
            id=str(uuid.uuid4()),
            type="Person",
            properties={"name": f"Person {i}"}
        )
        for i in range(3)
    ]
    # await memgraph_repo.add_entities(entities) # Needs add_nodes or similar
    await memgraph_repo.add_nodes(entities) # Use add_nodes
    
    # Create relationships for bulk test using domain model (Edge alias)
    relationships = [
        Relationship(
            id=str(uuid.uuid4()), # Reinstate ID
            source_id=entities[0].id,
            target_id=entities[1].id,
            type="KNOWS",
            properties={"since": "2023"}
        ),
        Relationship(
            id=str(uuid.uuid4()), # Reinstate ID
            source_id=entities[1].id,
            target_id=entities[2].id,
            type="KNOWS",
            properties={"strength": 5}
        )
    ]
    # Add relationships (assuming a bulk add method or individual calls)
    # If no bulk method, add individually:
    for rel in relationships:
        await memgraph_repo.add_relationship(rel)

    # Verify entities exist
    for entity in entities:
        retrieved_node = await memgraph_repo.get_node_by_id(entity.id)
        assert retrieved_node is not None
        assert retrieved_node.properties == entity.properties
    
    # Verify all relationships exist
    for rel in relationships:
        query = """
        MATCH (source {id: $source_id})-[r:KNOWS]->(target {id: $target_id})
        RETURN r
        """
        results = await memgraph_repo._execute_read_query(
            query,
            {"source_id": rel.source_id, "target_id": rel.target_id}
        )
        assert len(results) == 1

@pytest.mark.integration
async def test_error_handling(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test error handling in various scenarios."""
    # Test invalid connection - This is tricky to test reliably with retries
    # We already test close/reconnect in test_connection_management
    # await memgraph_repo.close()
    # with pytest.raises(ConnectionError):
    #     # Document requires content, use domain model
    #     await memgraph_repo.add_document(Document(id="test", content="test content"))
    
    # Reconnect if closed (or ensure connected initially)
    if not memgraph_repo._is_connected:
         await memgraph_repo.connect()
    
    # Test invalid node ID retrieval (should return None)
    # with pytest.raises(Exception): # Or specific exception if known
    #    await memgraph_repo.get_node_by_id("nonexistent")
    assert await memgraph_repo.get_node_by_id("nonexistent") is None
    
    # Test adding invalid relationship (should fail silently or raise specific DB error)
    invalid_rel = Relationship( # Relationship is Edge
            id=str(uuid.uuid4()), # Reinstate ID
            source_id="nonexistent1", # Required by Edge
            target_id="nonexistent2", # Required by Edge
            type="KNOWS"          # Required by Edge
    )
    await memgraph_repo.add_relationship(invalid_rel)
    # Add assertion: Check relationship wasn't created
    query = "MATCH ()-[r:KNOWS {id: $rel_id}]->() RETURN count(r) as count"
    result = await memgraph_repo._execute_read_query(query, {"rel_id": invalid_rel.id})
    assert result[0]["count"] == 0

@pytest.mark.integration
async def test_neighbor_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test neighbor retrieval operations."""
    # Create entities and relationships (using Node model)
    center_id = str(uuid.uuid4())
    center = Node(
        id=center_id,
        type="Person",
        properties={"name": "Center"}
    )
    neighbors = [
        Node(
            id=str(uuid.uuid4()),
            type="Person",
            properties={"name": f"Neighbor {i}"}
        )
        for i in range(3)
    ]

    # await memgraph_repo.add_entity(center)
    # await memgraph_repo.add_entities(neighbors)
    await memgraph_repo.add_node(center) # Use add_node
    await memgraph_repo.add_nodes(neighbors) # Use add_nodes

    # Create relationships using domain model (Edge alias)
    for neighbor in neighbors:
        await memgraph_repo.add_relationship(
            Relationship( # Relationship is Edge
                id=str(uuid.uuid4()), # Reinstate ID
                source_id=center.id, # Required by Edge
                target_id=neighbor.id, # Required by Edge
                type="KNOWS"          # Required by Edge
                # No properties needed for this test case
            )
        )
    
    # Get neighbors
    entities, relationships = await memgraph_repo.get_neighbors(center.id)
    assert len(entities) == 3
    assert len(relationships) == 3
    assert all(rel.type == "KNOWS" for rel in relationships)
    
    # Test direction filtering
    entities, _ = await memgraph_repo.get_neighbors(center.id, direction="outgoing")
    assert len(entities) == 3
    
    entities, _ = await memgraph_repo.get_neighbors(center.id, direction="incoming")
    assert len(entities) == 0

@pytest.mark.integration
async def test_property_search(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test property-based entity search."""
    # Create entities with specific properties (using Node model)
    entities = [
        Node(
            id=str(uuid.uuid4()),
            type="Person",
            properties={"name": f"Person {i}", "age": 20 + i}
        )
        for i in range(5)
    ]
    # await memgraph_repo.add_entities(entities) # Needs add_nodes
    await memgraph_repo.add_nodes(entities) # Use add_nodes
    
    # Search for entities by property
    results = await memgraph_repo.search_nodes_by_properties(
        {"age": 22},
        limit=1
    )
    assert len(results) == 1
    assert results[0].properties["age"] == 22

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
