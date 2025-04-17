import pytest
from unittest.mock import patch, MagicMock
import spacy
from typing import Dict

from graph_rag.core.interfaces import ExtractionResult, ExtractedEntity, ExtractedRelationship
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.models import Document, Chunk, Entity, Relationship, ProcessedDocument
from graph_rag.core.entity_extractor import EntityExtractor, MockEntityExtractor

# --- Mock spaCy --- 

@pytest.fixture
def mock_spacy_entity():
    entity = MagicMock()
    entity.text = "Apple Inc."
    entity.label_ = "ORG"
    return entity

@pytest.fixture
def mock_spacy_doc(mock_spacy_entity):
    doc = MagicMock()
    doc.ents = [mock_spacy_entity]
    return doc

@pytest.fixture
def mock_spacy_nlp(mock_spacy_doc):
    nlp = MagicMock()
    nlp.return_value = mock_spacy_doc
    return nlp

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_spacy_extracts_entities(mock_spacy_nlp):
    """Test that entities are extracted correctly using mocked spaCy."""
    # Configure the mock nlp object passed via fixture for *this specific test*
    # Create mock entities
    mock_ent_apple = MagicMock()
    mock_ent_apple.text = "Apple Inc."
    mock_ent_apple.label_ = "ORG"

    mock_ent_cupertino = MagicMock()
    mock_ent_cupertino.text = "Cupertino"
    mock_ent_cupertino.label_ = "GPE" # Geo-Political Entity

    mock_ent_cook = MagicMock()
    mock_ent_cook.text = "Tim Cook"
    mock_ent_cook.label_ = "PERSON"

    # Create a mock Doc object containing these entities
    mock_doc_for_test = MagicMock()
    mock_doc_for_test.ents = [mock_ent_apple, mock_ent_cupertino, mock_ent_cook]

    # Set the return value of the mock nlp *instance* for this test
    mock_spacy_nlp.return_value = mock_doc_for_test

    # Patch spacy.load directly, as import is local in __init__
    with patch("spacy.load") as mock_spacy_load:
        mock_spacy_load.return_value = mock_spacy_nlp

        extractor = SpacyEntityExtractor()
        # The extractor now uses the mocked nlp object during initialization

        # Define test text and create a Document object
        test_text = "Some text mentioning Apple Inc. in Cupertino with Tim Cook."
        test_doc = Document(id="test-doc-1", content=test_text, chunks=[Chunk(id="c1", text=test_text, document_id="test-doc-1")])

        # Call extract method with Document object - handle async if the method is async
        extraction_result = extractor.extract(test_doc)
        if hasattr(extraction_result, "__await__"):
            extraction_result = await extraction_result

        # Assertions
        assert len(extraction_result.entities) == 3
        # Use name for assertion as ID generation might vary
        entity_names = {e.name for e in extraction_result.entities}
        assert "Apple Inc." in entity_names
        assert "Cupertino" in entity_names
        assert "Tim Cook" in entity_names

        # Check if relationships are empty as expected for this mock
        assert len(extraction_result.relationships) == 0

        # Verify spaCy was called correctly
        mock_spacy_nlp.assert_called_once_with(test_text)

@pytest.mark.asyncio
async def test_spacy_extract_no_entities(mock_spacy_nlp):
    """Test extraction when spaCy finds no entities."""
    # Configure the mocked Doc to have no entities
    mock_spacy_doc_no_ents = MagicMock()
    mock_spacy_doc_no_ents.ents = []
    mock_spacy_nlp.return_value = mock_spacy_doc_no_ents

    with patch("spacy.load") as mock_spacy_load: # Corrected patch target
        mock_spacy_load.return_value = mock_spacy_nlp

        extractor = SpacyEntityExtractor()
        test_text = "Just some plain text without named entities."
        test_doc = Document(id="test-doc-2", content=test_text, chunks=[Chunk(id="c2", text=test_text, document_id="test-doc-2")])

        # Handle async extraction if needed
        extraction_result = extractor.extract(test_doc)
        if hasattr(extraction_result, "__await__"):
            extraction_result = await extraction_result

        assert len(extraction_result.entities) == 0
        assert len(extraction_result.relationships) == 0 # Assuming relationships are empty too

        # Verify spaCy was called
        mock_spacy_nlp.assert_called_once_with(test_text) # Check if nlp() was called with text

@pytest.mark.asyncio
async def test_spacy_extract_empty_text(mock_spacy_nlp):
    """Test extraction with empty input text."""
    # Configure mock for empty text if needed (spaCy might handle it gracefully)
    mock_spacy_doc_empty = MagicMock()
    mock_spacy_doc_empty.ents = []
    mock_spacy_nlp.return_value = mock_spacy_doc_empty

    with patch("spacy.load") as mock_spacy_load:
        mock_spacy_load.return_value = mock_spacy_nlp

        extractor = SpacyEntityExtractor()
        test_doc = Document(id="test-doc-empty", content="", chunks=[]) # Empty doc

        extraction_result = await extractor.extract(test_doc)

        assert len(extraction_result.entities) == 0
        assert len(extraction_result.relationships) == 0

        # Verify spaCy was NOT called because there were no chunks
        mock_spacy_nlp.assert_not_called() # Correct assertion

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

@pytest.mark.asyncio
async def test_mock_extractor_finds_entities(doc_with_entities):
    """Test that the mock extractor returns expected entities and relationships."""
    extractor = MockEntityExtractor()
    processed_doc = await extractor.extract(doc_with_entities)

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

@pytest.mark.asyncio
async def test_mock_extractor_no_entities(doc_without_entities):
    """Test extraction when no entities are found by the mock."""
    extractor = MockEntityExtractor()
    processed_doc = await extractor.extract(doc_without_entities)
    
    assert isinstance(processed_doc, ProcessedDocument)
    assert processed_doc.id == doc_without_entities.id
    assert processed_doc.content == doc_without_entities.content
    assert len(processed_doc.entities) == 0
    assert len(processed_doc.relationships) == 0

@pytest.mark.asyncio
async def test_mock_extractor_empty_document(empty_doc_for_extraction):
    """Test extraction on a document with no chunks."""
    extractor = MockEntityExtractor()
    processed_doc = await extractor.extract(empty_doc_for_extraction)
    
    assert isinstance(processed_doc, ProcessedDocument)
    assert processed_doc.id == empty_doc_for_extraction.id
    assert len(processed_doc.entities) == 0
    assert len(processed_doc.relationships) == 0 