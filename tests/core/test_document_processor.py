import pytest
import uuid

from graph_rag.models import Document, Chunk
from graph_rag.core.document_processor import SentenceSplitter
from unittest.mock import MagicMock

@pytest.fixture
def simple_document() -> Document:
    """Provides a simple document for testing."""
    return Document(id="doc1", content="This is the first sentence. This is the second.", metadata={"source": "test"})

@pytest.fixture
def empty_document() -> Document:
    """Provides an empty document."""
    return Document(id="doc_empty", content="", metadata={"source": "test"})

@pytest.fixture
def single_sentence_document() -> Document:
    """Provides a document with only one sentence."""
    return Document(id="doc_single", content="This is a single sentence.", metadata={"source": "test"})

def test_sentence_splitter_basic(simple_document):
    """Tests basic sentence splitting."""
    splitter = SentenceSplitter()
    chunks = splitter.split(simple_document)

    assert len(chunks) == 2
    assert chunks[0].text == "This is the first sentence."
    assert chunks[0].document_id == "doc1"
    assert chunks[0].metadata == {"source": "test", "sentence_index": 0}
    assert isinstance(chunks[0].id, str)

    assert chunks[1].text == "This is the second."
    assert chunks[1].document_id == "doc1"
    assert chunks[1].metadata == {"source": "test", "sentence_index": 1}
    assert isinstance(chunks[1].id, str)

def test_sentence_splitter_empty_doc(empty_document):
    """Tests splitting an empty document."""
    splitter = SentenceSplitter()
    chunks = splitter.split(empty_document)
    assert len(chunks) == 0

def test_sentence_splitter_single_sentence(single_sentence_document):
    """Tests splitting a document with a single sentence."""
    splitter = SentenceSplitter()
    chunks = splitter.split(single_sentence_document)

    assert len(chunks) == 1
    assert chunks[0].text == "This is a single sentence."
    assert chunks[0].document_id == "doc_single"
    assert chunks[0].metadata == {"source": "test", "sentence_index": 0}

def test_sentence_splitter_empty_doc_preserves_metadata(empty_document):
    """Tests that the splitter handles empty docs and preserves metadata structure (if any)."""
    splitter = SentenceSplitter()
    chunks = splitter.split(empty_document)
    assert len(chunks) == 0
    # Optionally, check if the original document metadata is accessible if needed, 
    # but the splitter doesn't modify the input document.
    assert empty_document.metadata == {"source": "test"}

def test_sentence_splitter_preserves_metadata(simple_document):
    """Tests that chunk metadata includes original document metadata."""
    splitter = SentenceSplitter()
    chunks = splitter.split(simple_document)
    assert len(chunks) > 0 # Assuming simple_document has content
    for chunk in chunks:
        assert "source" in chunk.metadata
        assert chunk.metadata["source"] == "test"
        assert "sentence_index" in chunk.metadata # Ensure splitter adds its own meta 