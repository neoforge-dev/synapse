import pytest
import uuid
from typing import Dict, List, Set
from unittest.mock import MagicMock

from graph_rag.core.interfaces import (
    DocumentData, ChunkData, ExtractedEntity, ExtractedRelationship
)
from graph_rag.core.knowledge_graph_builder import InMemoryKnowledgeGraphBuilder
from graph_rag.models import ProcessedDocument, Entity, Relationship
from graph_rag.core.knowledge_graph_builder import SimpleKnowledgeGraphBuilder
from graph_rag.core.graph_store import MockGraphStore

@pytest.fixture
def memory_kg() -> InMemoryKnowledgeGraphBuilder:
    """Provides an empty in-memory knowledge graph."""
    return InMemoryKnowledgeGraphBuilder()

@pytest.fixture
def mock_graph_store() -> MockGraphStore:
    """Provides a fresh MockGraphStore for each test."""
    return MockGraphStore()

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
def processed_doc_with_data() -> ProcessedDocument:
    """A sample ProcessedDocument with entities and relationships."""
    alice = Entity(id="ent-alice", name="Alice", type="PERSON")
    bob = Entity(id="ent-bob", name="Bob", type="PERSON")
    graphrag_sys = Entity(id="ent-graphrag", name="GraphRAG", type="SYSTEM")
    rel1 = Relationship(source=alice, target=bob, type="KNOWS")
    
    return ProcessedDocument(
        id="proc-doc-1",
        content="Alice knows Bob. GraphRAG is cool.",
        metadata={"source": "builder-test"},
        chunks=[], # Chunks not directly used by builder, but part of model
        entities=[alice, bob, graphrag_sys],
        relationships=[rel1]
    )

@pytest.fixture
def processed_doc_no_data() -> ProcessedDocument:
    """A ProcessedDocument with no entities or relationships."""
    return ProcessedDocument(
        id="proc-doc-2",
        content="Nothing to see here.",
        metadata={"source": "builder-test-empty"},
        chunks=[],
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

def test_builder_adds_entities_and_relationships(mock_graph_store, processed_doc_with_data):
    """Test that the builder calls the graph store's bulk add method."""
    builder = SimpleKnowledgeGraphBuilder(graph_store=mock_graph_store)
    
    # Wrap the target method with MagicMock for assertion
    mock_graph_store.add_entities_and_relationships = MagicMock(
        wraps=mock_graph_store.add_entities_and_relationships # Optional: retain original behavior
    )
    
    builder.build(processed_doc_with_data)

    # Verify the bulk add method was called once with the correct data
    mock_graph_store.add_entities_and_relationships.assert_called_once_with(
        processed_doc_with_data.entities, 
        processed_doc_with_data.relationships
    )
    
    # Verify the state of the mock store itself (though checking calls is often sufficient)
    assert len(mock_graph_store.entities) == 3
    assert "ent-alice" in mock_graph_store.entities
    assert "ent-bob" in mock_graph_store.entities
    assert "ent-graphrag" in mock_graph_store.entities
    assert len(mock_graph_store.relationships) == 1
    assert mock_graph_store.relationships[0].type == "KNOWS"

def test_builder_no_data_does_nothing(mock_graph_store, processed_doc_no_data):
    """Test that the builder does not call the store if there's no data."""
    builder = SimpleKnowledgeGraphBuilder(graph_store=mock_graph_store)

    # Wrap methods with MagicMock for assertion
    mock_graph_store.add_entities_and_relationships = MagicMock()
    mock_graph_store.add_entity = MagicMock() # Also check individual adds just in case
    mock_graph_store.add_relationship = MagicMock()

    builder.build(processed_doc_no_data)

    # Verify no add methods were called
    mock_graph_store.add_entities_and_relationships.assert_not_called()
    mock_graph_store.add_entity.assert_not_called()
    mock_graph_store.add_relationship.assert_not_called()
    
    # Verify store is empty
    assert not mock_graph_store.entities
    assert not mock_graph_store.relationships

def test_builder_requires_graph_store():
    """Test that the builder raises TypeError if graph_store is invalid."""
    with pytest.raises(TypeError, match="graph_store must be an instance of GraphStore"):
        SimpleKnowledgeGraphBuilder(graph_store=None) # type: ignore
    with pytest.raises(TypeError, match="graph_store must be an instance of GraphStore"):
        SimpleKnowledgeGraphBuilder(graph_store={"not": "a store"}) # type: ignore 