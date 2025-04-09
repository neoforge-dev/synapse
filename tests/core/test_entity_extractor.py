import pytest
from unittest.mock import patch, MagicMock

from graph_rag.core.interfaces import ExtractionResult, ExtractedEntity, ExtractedRelationship
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.models import Document, Chunk, Entity, Relationship, ProcessedDocument
from graph_rag.core.entity_extractor import EntityExtractor, MockEntityExtractor

# --- Mock spaCy --- 

@pytest.fixture
def mock_spacy_doc():
    """Mocks a spaCy Doc object with entities."""
    # Mock individual entities (Span objects)
    ent1 = MagicMock()
    ent1.text = "Apple"
    ent1.label_ = "ORG"
    ent1.start_char = 10
    ent1.end_char = 15
    
    ent2 = MagicMock()
    ent2.text = "Cupertino"
    ent2.label_ = "GPE" # Geopolitical Entity
    ent2.start_char = 25
    ent2.end_char = 34
    
    ent3 = MagicMock()
    ent3.text = "Tim Cook"
    ent3.label_ = "PERSON"
    ent3.start_char = 40
    ent3.end_char = 48

    # Mock the Doc object's `ents` property
    doc = MagicMock()
    doc.ents = [ent1, ent2, ent3]
    return doc

@pytest.fixture
def mock_spacy_nlp(mock_spacy_doc):
    """Mocks the spaCy nlp object."""
    nlp = MagicMock()
    # Configure the nlp object to return the mocked Doc when called
    nlp.return_value = mock_spacy_doc
    return nlp

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_spacy_extracts_entities(mock_spacy_nlp):
    """Test that entities are extracted correctly using mocked spaCy."""
    # Patch spacy.load directly, as import is local in __init__
    with patch("spacy.load") as mock_spacy_load:
        mock_spacy_load.return_value = mock_spacy_nlp
        
        extractor = SpacyEntityExtractor()
        # The extractor now uses the mocked nlp object during initialization

        # Need to adapt the test method signature as SpacyEntityExtractor.extract 
        # expects a Document object, not just text.
        doc = Document(
            id="test-doc-spacy", 
            content="Some text mentioning Apple Inc. in Cupertino with Tim Cook.",
            chunks=[Chunk(id="c1", content="Some text mentioning Apple Inc. in Cupertino with Tim Cook.", document_id="test-doc-spacy")] # Use content
        )
        processed_doc = extractor.extract(doc)
        
        # Assertions
        assert isinstance(processed_doc, ProcessedDocument)
        assert len(processed_doc.entities) == 3
        
        # Check entity details
        entity_map = {e.name: e for e in processed_doc.entities}
        assert "Apple" in entity_map
        assert entity_map["Apple"].type == "ORG"
        # ID generation depends on _normalize_entity_text, adjust assertion if needed
        assert entity_map["Apple"].id == "ORG:apple"

        assert "Cupertino" in entity_map
        assert entity_map["Cupertino"].type == "GPE"
        assert entity_map["Cupertino"].id == "GPE:cupertino"
        
        assert "Tim Cook" in entity_map
        assert entity_map["Tim Cook"].type == "PERSON"
        assert entity_map["Tim Cook"].id == "PERSON:tim_cook"
        
        # Check relationships (still 0 for this extractor)
        assert len(processed_doc.relationships) == 0
        
        # Ensure nlp object was called via chunk processing
        mock_spacy_nlp.assert_called_once_with(doc.chunks[0].content)

@pytest.mark.asyncio
async def test_spacy_extract_no_entities(mock_spacy_nlp):
    """Test extraction when spaCy finds no entities."""
    # Configure the mocked Doc to have no entities
    mock_spacy_nlp.return_value.ents = []
    
    with patch("spacy.load") as mock_spacy_load: # Corrected patch target
        mock_spacy_load.return_value = mock_spacy_nlp
        
        extractor = SpacyEntityExtractor()
        doc = Document(
            id="test-doc-no-ent", 
            content="Just some plain text without named entities.",
            chunks=[Chunk(id="c1", content="Just some plain text without named entities.", document_id="test-doc-no-ent")]
        )
        processed_doc = extractor.extract(doc)
        
        assert len(processed_doc.entities) == 0
        assert len(processed_doc.relationships) == 0
        mock_spacy_nlp.assert_called_once_with(doc.chunks[0].content)

@pytest.mark.asyncio
async def test_spacy_extract_empty_text(mock_spacy_nlp):
    """Test extraction with empty input text."""
    with patch("spacy.load") as mock_spacy_load: # Corrected patch target
        mock_spacy_load.return_value = mock_spacy_nlp
        
        extractor = SpacyEntityExtractor()
        doc = Document(id="test-doc-empty", content="", chunks=[]) # No chunks for empty doc
        processed_doc = extractor.extract(doc)
        
        assert len(processed_doc.entities) == 0
        assert len(processed_doc.relationships) == 0
        # spaCy shouldn't be called if there are no chunks with text
        mock_spacy_nlp.assert_not_called()

# TODO: Add tests for relationship extraction if a different model/library is used 

@pytest.fixture
def doc_with_entities() -> Document:
    """Document designed to trigger mock extraction."""
    return Document(
        id="doc-entities",
        content="Alice knows Bob. This system is GraphRAG.",
        metadata={"source": "entity-test"},
        # Assume chunks have been created by DocumentProcessor
        chunks=[
            Chunk(id="c1", text="Alice knows Bob.", document_id="doc-entities", metadata={"sentence_index": 0}),
            Chunk(id="c2", text="This system is GraphRAG.", document_id="doc-entities", metadata={"sentence_index": 1})
        ]
    )

@pytest.fixture
def doc_without_entities() -> Document:
    """Document with no entities the mock extractor recognizes."""
    return Document(
        id="doc-no-entities",
        content="Just some plain text here.",
        metadata={"source": "no-entity-test"},
        chunks=[
            Chunk(id="c3", text="Just some plain text here.", document_id="doc-no-entities", metadata={"sentence_index": 0})
        ]
    )

@pytest.fixture
def empty_doc_for_extraction() -> Document:
    """An empty document (no content, no chunks)."""
    return Document(id="doc-empty-extract", content="", metadata={}, chunks=[])

def test_mock_extractor_finds_entities(doc_with_entities):
    """Test that the mock extractor returns expected entities and relationships."""
    extractor = MockEntityExtractor()
    processed_doc = extractor.extract(doc_with_entities)

    assert isinstance(processed_doc, ProcessedDocument)
    
    # Check preserved fields
    assert processed_doc.id == doc_with_entities.id
    assert processed_doc.content == doc_with_entities.content
    assert processed_doc.metadata == doc_with_entities.metadata
    assert processed_doc.chunks == doc_with_entities.chunks

    # Check extracted entities
    assert len(processed_doc.entities) == 3
    entity_names = {e.name for e in processed_doc.entities}
    assert entity_names == {"Alice", "Bob", "GraphRAG"}

    # Check extracted relationships
    assert len(processed_doc.relationships) == 1
    rel = processed_doc.relationships[0]
    assert rel.type == "KNOWS"
    assert rel.source.name == "Alice"
    assert rel.target.name == "Bob"

def test_mock_extractor_no_entities(doc_without_entities):
    """Test extraction when no entities are found by the mock."""
    extractor = MockEntityExtractor()
    processed_doc = extractor.extract(doc_without_entities)
    
    assert isinstance(processed_doc, ProcessedDocument)
    assert processed_doc.id == doc_without_entities.id
    assert processed_doc.content == doc_without_entities.content
    assert len(processed_doc.entities) == 0
    assert len(processed_doc.relationships) == 0

def test_mock_extractor_empty_document(empty_doc_for_extraction):
    """Test extraction on a document with no chunks."""
    extractor = MockEntityExtractor()
    processed_doc = extractor.extract(empty_doc_for_extraction)
    
    assert isinstance(processed_doc, ProcessedDocument)
    assert processed_doc.id == empty_doc_for_extraction.id
    assert len(processed_doc.entities) == 0
    assert len(processed_doc.relationships) == 0 