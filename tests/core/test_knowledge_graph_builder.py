import pytest
import uuid
from typing import Dict, List, Set
from unittest.mock import MagicMock, AsyncMock, call

from graph_rag.core.interfaces import (
    DocumentData, ChunkData, ExtractedEntity, ExtractedRelationship
)
from graph_rag.core.knowledge_graph_builder import InMemoryKnowledgeGraphBuilder
from graph_rag.models import ProcessedDocument, Entity, Relationship
from graph_rag.core.knowledge_graph_builder import SimpleKnowledgeGraphBuilder
from graph_rag.core.graph_store import MockGraphStore, GraphStore
from graph_rag.domain.models import Document, Chunk

@pytest.fixture
def memory_kg() -> InMemoryKnowledgeGraphBuilder:
    """Provides an empty in-memory knowledge graph."""
    return InMemoryKnowledgeGraphBuilder()

@pytest.fixture
def mock_graph_store() -> AsyncMock:
    """Provides a mock GraphStore object."""
    # Use AsyncMock for async methods
    mock = AsyncMock(spec=GraphStore)
    mock.add_entities_and_relationships = AsyncMock(return_value=None)
    return mock

# --- Helper Data --- 

DOC_ID_1 = "doc-kg-1"
CHUNK_ID_1 = "chunk-kg-1"
ENTITY_ID_APPLE = "apple"
ENTITY_ID_STEVE = "steve_jobs"

@pytest.fixture
def sample_doc_kg() -> DocumentData:
    return DocumentData(id=DOC_ID_1, content="Apple was founded by Steve Jobs.", metadata={"year": 1976})

@pytest.fixture
def sample_chunk_kg() -> ChunkData:
    return ChunkData(id=CHUNK_ID_1, text="Apple was founded by Steve Jobs.", document_id=DOC_ID_1)

@pytest.fixture
def sample_entity_apple() -> ExtractedEntity:
    return ExtractedEntity(id=ENTITY_ID_APPLE, label="ORG", text="Apple")

@pytest.fixture
def sample_entity_steve() -> ExtractedEntity:
    return ExtractedEntity(id=ENTITY_ID_STEVE, label="PERSON", text="Steve Jobs")

@pytest.fixture
def sample_relationship_founded() -> ExtractedRelationship:
    return ExtractedRelationship(source_entity_id=ENTITY_ID_STEVE, target_entity_id=ENTITY_ID_APPLE, label="FOUNDED")

@pytest.fixture
def sample_processed_doc() -> ProcessedDocument:
    """Provides a sample ProcessedDocument with entities and relationships."""
    entity1 = Entity(id="ent-1", type="PERSON", name="Alice")
    entity2 = Entity(id="ent-2", type="PERSON", name="Bob")
    entity3 = Entity(id="ent-3", type="ORG", name="Acme Corp")
    
    rel1 = Relationship(type="WORKS_AT", source=entity1, target=entity3)
    rel2 = Relationship(type="KNOWS", source=entity1, target=entity2)
    
    chunk1 = Chunk(id="c1", text="Alice works at Acme Corp. Alice knows Bob.", document_id="doc-1")
    chunk2 = Chunk(id="c2", text="Alice knows Bob.", document_id="doc-1")
    
    return ProcessedDocument(
        id="doc-1",
        content="Alice works at Acme Corp. Alice knows Bob.",
        metadata={"source": "test"},
        chunks=[chunk1, chunk2],
        entities=[entity1, entity2, entity3],
        relationships=[rel1, rel2]
    )

@pytest.fixture
def empty_processed_doc() -> ProcessedDocument:
    """Provides a sample ProcessedDocument with no entities or relationships."""
    chunk1 = Chunk(id="c3", text="Just some text.", document_id="doc-empty")
    return ProcessedDocument(
        id="doc-empty",
        content="Just some text.",
        metadata={"source": "empty"},
        chunks=[chunk1],
        entities=[],
        relationships=[]
    )

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_add_document(memory_kg: InMemoryKnowledgeGraphBuilder, sample_doc_kg):
    await memory_kg.add_document(sample_doc_kg)
    assert DOC_ID_1 in memory_kg.documents
    assert memory_kg.documents[DOC_ID_1] == sample_doc_kg

@pytest.mark.asyncio
async def test_add_chunk(memory_kg: InMemoryKnowledgeGraphBuilder, sample_chunk_kg, sample_doc_kg):
    # Add document first for context
    await memory_kg.add_document(sample_doc_kg)
    await memory_kg.add_chunk(sample_chunk_kg)
    
    assert CHUNK_ID_1 in memory_kg.chunks
    assert memory_kg.chunks[CHUNK_ID_1] == sample_chunk_kg
    # Check relationship (internal detail, but useful for testing)
    assert memory_kg.doc_chunk_links.get(DOC_ID_1) == {CHUNK_ID_1}
    assert memory_kg.chunk_doc_links.get(CHUNK_ID_1) == DOC_ID_1

@pytest.mark.asyncio
async def test_add_entity(memory_kg: InMemoryKnowledgeGraphBuilder, sample_entity_apple):
    await memory_kg.add_entity(sample_entity_apple)
    assert ENTITY_ID_APPLE in memory_kg.entities
    assert memory_kg.entities[ENTITY_ID_APPLE] == sample_entity_apple

@pytest.mark.asyncio
async def test_add_relationship(memory_kg: InMemoryKnowledgeGraphBuilder, sample_entity_apple, sample_entity_steve, sample_relationship_founded):
    # Add entities first
    await memory_kg.add_entity(sample_entity_apple)
    await memory_kg.add_entity(sample_entity_steve)
    await memory_kg.add_relationship(sample_relationship_founded)
    
    # Check relationship stored (internal detail)
    rel_key = (ENTITY_ID_STEVE, ENTITY_ID_APPLE, "FOUNDED")
    assert rel_key in memory_kg.relationships
    assert memory_kg.relationships[rel_key] == sample_relationship_founded

@pytest.mark.asyncio
async def test_link_chunk_to_entities(memory_kg: InMemoryKnowledgeGraphBuilder, sample_chunk_kg, sample_entity_apple, sample_entity_steve):
    # Add chunk and entities first
    await memory_kg.add_chunk(sample_chunk_kg) # Assumes add_chunk handles adding to its dict
    await memory_kg.add_entity(sample_entity_apple)
    await memory_kg.add_entity(sample_entity_steve)
    
    entity_ids = [ENTITY_ID_APPLE, ENTITY_ID_STEVE]
    await memory_kg.link_chunk_to_entities(CHUNK_ID_1, entity_ids)
    
    # Check links (internal detail)
    assert memory_kg.chunk_entity_links.get(CHUNK_ID_1) == set(entity_ids)
    assert memory_kg.entity_chunk_links.get(ENTITY_ID_APPLE) == {CHUNK_ID_1}
    assert memory_kg.entity_chunk_links.get(ENTITY_ID_STEVE) == {CHUNK_ID_1}

@pytest.mark.asyncio
async def test_add_duplicate_document(memory_kg: InMemoryKnowledgeGraphBuilder, sample_doc_kg):
    """Test adding the same document twice (should overwrite or ignore)."""
    await memory_kg.add_document(sample_doc_kg)
    # Modify slightly for overwrite check
    doc_copy = sample_doc_kg.model_copy(update={"metadata": {"new": "data"}})
    await memory_kg.add_document(doc_copy)
    
    assert len(memory_kg.documents) == 1
    assert memory_kg.documents[DOC_ID_1].metadata == {"new": "data"}

@pytest.mark.asyncio
async def test_simple_builder_build(mock_graph_store: AsyncMock, sample_processed_doc: ProcessedDocument):
    """Tests that SimpleKnowledgeGraphBuilder calls add_entities_and_relationships."""
    builder = SimpleKnowledgeGraphBuilder(graph_store=mock_graph_store)
    # The build method is now async
    await builder.build(sample_processed_doc) 
    
    mock_graph_store.add_entities_and_relationships.assert_awaited_once_with(
        sample_processed_doc.entities,
        sample_processed_doc.relationships
    )

@pytest.mark.asyncio
async def test_simple_builder_build_empty(mock_graph_store: AsyncMock, empty_processed_doc: ProcessedDocument):
    """Tests that SimpleKnowledgeGraphBuilder does not call repo if no entities/rels."""
    builder = SimpleKnowledgeGraphBuilder(graph_store=mock_graph_store)
    # The build method is now async
    await builder.build(empty_processed_doc)
    
    mock_graph_store.add_entities_and_relationships.assert_not_awaited()

def test_simple_builder_init_invalid_store():
    """Tests that initializing with an invalid store raises TypeError."""
    with pytest.raises(TypeError):
        SimpleKnowledgeGraphBuilder(graph_store=MagicMock()) # Not a GraphStore

@pytest.mark.asyncio
async def test_inmemory_add_document():
    builder = InMemoryKnowledgeGraphBuilder()
    doc_data = DocumentData(id="doc1", content="Test content", metadata={"a": 1})
    await builder.add_document(doc_data)
    assert "doc1" in builder.documents
    assert builder.documents["doc1"] == doc_data

@pytest.mark.asyncio
async def test_inmemory_add_chunk():
    builder = InMemoryKnowledgeGraphBuilder()
    doc_data = DocumentData(id="doc1", content="Test content", metadata={"a": 1})
    await builder.add_document(doc_data) # Add parent doc first
    chunk_data = ChunkData(id="chunk1", text="Test chunk", document_id="doc1")
    await builder.add_chunk(chunk_data)
    assert "chunk1" in builder.chunks
    assert builder.chunks["chunk1"] == chunk_data
    assert "doc1" in builder.doc_chunk_links
    assert "chunk1" in builder.doc_chunk_links["doc1"]
    assert builder.chunk_doc_links["chunk1"] == "doc1"

@pytest.mark.asyncio
async def test_inmemory_add_entity():
    builder = InMemoryKnowledgeGraphBuilder()
    entity_data = ExtractedEntity(id="ent1", label="PERSON", text="Alice", name="Alice")
    await builder.add_entity(entity_data)
    assert "ent1" in builder.entities
    assert builder.entities["ent1"] == entity_data

@pytest.mark.asyncio
async def test_inmemory_add_relationship():
    builder = InMemoryKnowledgeGraphBuilder()
    # Add entities first for relationship to be added (current warning behavior)
    ent1 = ExtractedEntity(id="ent1", label="PERSON", text="Alice", name="Alice")
    ent2 = ExtractedEntity(id="ent2", label="PERSON", text="Bob", name="Bob")
    await builder.add_entity(ent1)
    await builder.add_entity(ent2)
    
    rel_data = ExtractedRelationship(source_entity_id="ent1", target_entity_id="ent2", label="KNOWS")
    rel_key = ("ent1", "ent2", "KNOWS")
    await builder.add_relationship(rel_data)
    assert rel_key in builder.relationships
    assert builder.relationships[rel_key] == rel_data

@pytest.mark.asyncio
async def test_inmemory_link_chunk_to_entities():
    builder = InMemoryKnowledgeGraphBuilder()
    # Add chunk and entities
    await builder.add_chunk(ChunkData(id="chunk1", text="Text", document_id="doc1"))
    await builder.add_entity(ExtractedEntity(id="ent1", label="PERSON", text="Alice"))
    await builder.add_entity(ExtractedEntity(id="ent2", label="ORG", text="Acme"))

    await builder.link_chunk_to_entities("chunk1", ["ent1", "ent2", "ent-nonexistent"])
    
    assert "chunk1" in builder.chunk_entity_links
    assert builder.chunk_entity_links["chunk1"] == {"ent1", "ent2"}
    assert "ent1" in builder.entity_chunk_links
    assert builder.entity_chunk_links["ent1"] == {"chunk1"}
    assert "ent2" in builder.entity_chunk_links
    assert builder.entity_chunk_links["ent2"] == {"chunk1"}
    assert "ent-nonexistent" not in builder.entity_chunk_links

@pytest.mark.asyncio
async def test_inmemory_build(sample_processed_doc: ProcessedDocument):
    """Tests the build method of InMemoryKnowledgeGraphBuilder."""
    builder = InMemoryKnowledgeGraphBuilder()
    await builder.build(sample_processed_doc)

    # Check entities were added
    assert len(builder.entities) == len(sample_processed_doc.entities)
    for entity in sample_processed_doc.entities:
        assert entity.id in builder.entities
        stored_entity = builder.entities[entity.id]
        # Check key attributes (assuming conversion in build)
        assert stored_entity.label == entity.type
        assert stored_entity.text == entity.name

    # Check relationships were added
    assert len(builder.relationships) == len(sample_processed_doc.relationships)
    for rel in sample_processed_doc.relationships:
        rel_key = (rel.source.id, rel.target.id, rel.type)
        assert rel_key in builder.relationships

@pytest.mark.asyncio
async def test_inmemory_build_empty(empty_processed_doc: ProcessedDocument):
    """Tests the build method with no entities/relationships."""
    builder = InMemoryKnowledgeGraphBuilder()
    await builder.build(empty_processed_doc)
    assert len(builder.entities) == 0
    assert len(builder.relationships) == 0 