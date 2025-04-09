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
from graph_rag.models import Document, Chunk, Entity, Relationship
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
    with patch('graph_rag.services.embedding.EmbeddingService', autospec=True) as mock_emb_service:
        # Mock the encode method
        def mock_encode(texts):
            if isinstance(texts, str):
                return np.random.rand(EMBEDDING_DIM).tolist()
            else:
                return [np.random.rand(EMBEDDING_DIM).tolist() for _ in texts]
        
        mock_emb_service.encode.side_effect = mock_encode
        mock_emb_service._get_model.return_value = MagicMock() # Mock the internal model loading
        mock_emb_service.get_embedding_dim.return_value = EMBEDDING_DIM
        yield mock_emb_service

@pytest.fixture
def graph_repository(mock_neo4j_driver, mock_embedding_service):
    """Create a MemgraphGraphRepository instance with mocked dependencies."""
    return MemgraphGraphRepository(mock_neo4j_driver, mock_embedding_service)

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

async def test_connection_management(memgraph_repo: MemgraphGraphRepository):
    """Test connection management functionality."""
    # Test initial connection
    assert memgraph_repo._is_connected
    
    # Test reconnection
    await memgraph_repo.close()
    assert not memgraph_repo._is_connected
    await memgraph_repo.connect()
    assert memgraph_repo._is_connected

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

async def test_entity_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test entity operations."""
    # Create entity
    entity_id = str(uuid.uuid4())
    entity = Entity(
        id=entity_id,
        type="Person",
        properties={"name": "John Doe", "age": 30}
    )
    await memgraph_repo.add_entity(entity)
    
    # Retrieve entity
    retrieved = await memgraph_repo.get_entity_by_id(entity_id)
    assert retrieved is not None
    assert retrieved.id == entity_id
    assert retrieved.type == "Person"
    assert retrieved.properties == entity.properties

async def test_relationship_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test relationship operations between entities."""
    # Create entities
    person1 = Entity(
        id=str(uuid.uuid4()),
        type="Person",
        properties={"name": "Alice"}
    )
    person2 = Entity(
        id=str(uuid.uuid4()),
        type="Person",
        properties={"name": "Bob"}
    )
    await memgraph_repo.add_entity(person1)
    await memgraph_repo.add_entity(person2)
    
    # Create relationship
    relationship = Relationship(
        source=person1,
        target=person2,
        type="KNOWS",
        properties={"since": datetime.now().isoformat()}
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

async def test_bulk_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test bulk operations for entities and relationships."""
    # Create entities
    entities = [
        Entity(
            id=str(uuid.uuid4()),
            type="Person",
            properties={"name": f"Person {i}"}
        )
        for i in range(3)
    ]
    
    # Create relationships
    relationships = [
        Relationship(
            source=entities[i],
            target=entities[i + 1],
            type="KNOWS",
            properties={"since": datetime.now().isoformat()}
        )
        for i in range(2)
    ]
    
    # Add in bulk
    await memgraph_repo.add_entities_and_relationships(entities, relationships)
    
    # Verify all entities exist
    for entity in entities:
        retrieved = await memgraph_repo.get_entity_by_id(entity.id)
        assert retrieved is not None
        assert retrieved.properties == entity.properties
    
    # Verify all relationships exist
    for rel in relationships:
        query = """
        MATCH (source {id: $source_id})-[r:KNOWS]->(target {id: $target_id})
        RETURN r
        """
        results = await memgraph_repo._execute_read_query(
            query,
            {"source_id": rel.source.id, "target_id": rel.target.id}
        )
        assert len(results) == 1

async def test_error_handling(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test error handling in various scenarios."""
    # Test invalid connection
    await memgraph_repo.close()
    with pytest.raises(ConnectionError):
        await memgraph_repo.add_document(Document(id="test", content="test"))
    
    # Reconnect for remaining tests
    await memgraph_repo.connect()
    
    # Test invalid entity ID
    with pytest.raises(Exception):
        await memgraph_repo.get_entity_by_id("nonexistent")
    
    # Test invalid relationship
    with pytest.raises(Exception):
        await memgraph_repo.add_relationship(
            Relationship(
                source=Entity(id="nonexistent1", type="Person"),
                target=Entity(id="nonexistent2", type="Person"),
                type="KNOWS"
            )
        )

async def test_neighbor_operations(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test neighbor retrieval operations."""
    # Create entities and relationships
    center = Entity(
        id=str(uuid.uuid4()),
        type="Person",
        properties={"name": "Center"}
    )
    neighbors = [
        Entity(
            id=str(uuid.uuid4()),
            type="Person",
            properties={"name": f"Neighbor {i}"}
        )
        for i in range(3)
    ]
    
    await memgraph_repo.add_entity(center)
    for neighbor in neighbors:
        await memgraph_repo.add_entity(neighbor)
        await memgraph_repo.add_relationship(
            Relationship(
                source=center,
                target=neighbor,
                type="KNOWS"
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

async def test_property_search(memgraph_repo: MemgraphGraphRepository, clean_db: None):
    """Test property-based entity search."""
    # Create entities with specific properties
    entities = [
        Entity(
            id=str(uuid.uuid4()),
            type="Person",
            properties={"name": f"Person {i}", "age": 20 + i}
        )
        for i in range(5)
    ]
    
    for entity in entities:
        await memgraph_repo.add_entity(entity)
    
    # Search by properties
    results = await memgraph_repo.search_entities_by_properties(
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
