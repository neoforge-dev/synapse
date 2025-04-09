import pytest
import uuid

from graph_rag.core.interfaces import DocumentData, ChunkData
from graph_rag.core.document_processor import SimpleDocumentProcessor
from graph_rag.models import Document, Chunk
from graph_rag.core.document_processor import DocumentProcessor, SentenceSplitter
from unittest.mock import MagicMock

@pytest.fixture
def sample_doc_data() -> DocumentData:
    return DocumentData(
        id="doc-123",
        content="""First paragraph.

Second paragraph, slightly longer.

Third paragraph.

Fourth.
""",
        metadata={"source": "test"}
    )

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

@pytest.mark.asyncio
async def test_simple_chunking_by_paragraph(sample_doc_data):
    """Test basic paragraph splitting."""
    processor = SimpleDocumentProcessor(chunk_strategy="paragraph")
    chunks = await processor.chunk_document(sample_doc_data)
    
    assert len(chunks) == 4
    assert chunks[0].text == "First paragraph."
    assert chunks[1].text == "Second paragraph, slightly longer."
    assert chunks[2].text == "Third paragraph."
    assert chunks[3].text == "Fourth."
    for chunk in chunks:
        assert chunk.document_id == "doc-123"
        assert isinstance(chunk.id, str)
        assert chunk.embedding is None # Embeddings not handled here

@pytest.mark.asyncio
async def test_simple_chunking_fixed_tokens(sample_doc_data):
    """Test chunking by fixed token (word) count."""
    # Recalculate expected chunks based on word count of sample_doc_data
    # Content: "First paragraph. Second paragraph, slightly longer. Third paragraph. Fourth."
    # Words: 3 + 4 + 2 + 1 = 10 words
    processor = SimpleDocumentProcessor(chunk_strategy="token", tokens_per_chunk=5)
    chunks = await processor.chunk_document(sample_doc_data)
    
    assert len(chunks) == 2
    assert chunks[0].text == "First paragraph. Second paragraph, slightly"
    assert chunks[1].text == "longer. Third paragraph. Fourth."
    for chunk in chunks:
        assert chunk.document_id == "doc-123"

@pytest.mark.asyncio
async def test_simple_chunking_invalid_strategy(sample_doc_data):
    """Test error handling for invalid chunking strategy."""
    with pytest.raises(ValueError):
        SimpleDocumentProcessor(chunk_strategy="invalid_strategy")

@pytest.mark.asyncio
async def test_simple_chunking_empty_doc():
    """Test chunking an empty document."""
    doc = DocumentData(id="empty-doc", content="", metadata={})
    processor = SimpleDocumentProcessor()
    chunks = await processor.chunk_document(doc)
    assert len(chunks) == 0

@pytest.mark.asyncio
async def test_simple_chunking_whitespace_doc():
    """Test chunking a document with only whitespace."""
    doc = DocumentData(id="ws-doc", content="  \n\n   \t ", metadata={})
    processor = SimpleDocumentProcessor()
    chunks = await processor.chunk_document(doc)
    assert len(chunks) == 0

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

def test_document_processor_uses_splitter(simple_document):
    """Tests that DocumentProcessor uses the provided splitter."""
    mock_splitter = MagicMock()
    mock_splitter.split.return_value = [
        Chunk(id="chunk1", text="Sentence 1.", document_id=simple_document.id),
        Chunk(id="chunk2", text="Sentence 2.", document_id=simple_document.id)
    ]

    processor = DocumentProcessor(splitter=mock_splitter)
    processed_doc = processor.process(simple_document)

    mock_splitter.split.assert_called_once_with(simple_document)
    assert processed_doc == simple_document # The processor modifies the doc in place
    assert len(processed_doc.chunks) == 2
    assert processed_doc.chunks[0].id == "chunk1"
    assert processed_doc.chunks[1].id == "chunk2"

def test_document_processor_empty_doc(empty_document):
    """Tests processing an empty document."""
    processor = DocumentProcessor(splitter=SentenceSplitter())
    processed_doc = processor.process(empty_document)
    assert processed_doc.id == "doc_empty"
    assert len(processed_doc.chunks) == 0

def test_document_processor_preserves_metadata(simple_document):
    """Tests that original document metadata is preserved."""
    processor = DocumentProcessor(splitter=SentenceSplitter())
    processed_doc = processor.process(simple_document)
    assert processed_doc.metadata == {"source": "test"} 