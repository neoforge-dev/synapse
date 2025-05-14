import uuid
from typing import Any, Optional

import pytest

from graph_rag.core.interfaces import DocumentData
from graph_rag.infrastructure.document_processor.simple_processor import (
    SentenceSplitter,
    SimpleDocumentProcessor,
)
from graph_rag.models import Chunk, Document


@pytest.fixture
def simple_document() -> Document:
    """Provides a simple document for testing."""
    return Document(
        id="doc1",
        content="This is the first sentence. This is the second.",
        metadata={"source": "test"},
    )


@pytest.fixture
def empty_document() -> Document:
    """Provides an empty document."""
    return Document(id="doc_empty", content="", metadata={"source": "test"})


@pytest.fixture
def single_sentence_document() -> Document:
    """Provides a document with only one sentence."""
    return Document(
        id="doc_single",
        content="This is a single sentence.",
        metadata={"source": "test"},
    )


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
    assert len(chunks) > 0  # Assuming simple_document has content
    for chunk in chunks:
        assert "source" in chunk.metadata
        assert chunk.metadata["source"] == "test"
        assert "sentence_index" in chunk.metadata  # Ensure splitter adds its own meta


# Sample data for testing
TEST_DOC_ID = str(uuid.uuid4())
SIMPLE_CONTENT = (
    "This is the first paragraph.\n\nThis is the second.\n   \nThis is the third one."
)
EXPECTED_PARA_CHUNKS = [
    "This is the first paragraph.",
    "This is the second.",
    "This is the third one.",
]

TOKEN_CONTENT = "Word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
EXPECTED_TOKEN_CHUNKS_5 = [
    "Word1 word2 word3 word4 word5",
    "word6 word7 word8 word9 word10",
]

EMPTY_CONTENT = "  \n  \t \n "


@pytest.fixture
def sample_document() -> DocumentData:
    """Provides a sample DocumentData object."""
    return DocumentData(
        id=TEST_DOC_ID, content=SIMPLE_CONTENT, metadata={"source": "test"}
    )


@pytest.fixture
def token_document() -> DocumentData:
    """Provides a sample DocumentData object for token testing."""
    return DocumentData(
        id=TEST_DOC_ID, content=TOKEN_CONTENT, metadata={"source": "test_token"}
    )


@pytest.fixture
def empty_document_data() -> DocumentData:
    """Provides a sample DocumentData object with empty content."""
    return DocumentData(
        id=TEST_DOC_ID, content=EMPTY_CONTENT, metadata={"source": "test_empty"}
    )


@pytest.mark.asyncio
async def test_simple_processor_paragraph_chunking(sample_document: DocumentData):
    """Tests paragraph chunking with SimpleDocumentProcessor."""
    processor = SimpleDocumentProcessor(chunk_strategy="paragraph")
    chunks: list[Chunk] = await processor.chunk_document(
        content=sample_document.content,
        document_id=sample_document.id,
        metadata=sample_document.metadata,
    )
    assert len(chunks) == 3
    assert chunks[0].text == "This is the first paragraph."
    assert chunks[1].text == "This is the second."
    assert chunks[2].text == "This is the third one."
    # Check metadata propagation (assuming SimpleDocumentProcessor adds it)
    assert chunks[0].metadata["source"] == "test"
    assert "paragraph_index" in chunks[0].metadata  # Check for processor-added meta


@pytest.mark.asyncio
async def test_simple_processor_token_chunking(token_document: DocumentData):
    """Tests token chunking with SimpleDocumentProcessor."""
    processor = SimpleDocumentProcessor(chunk_strategy="token", tokens_per_chunk=5)
    chunks: list[Chunk] = await processor.chunk_document(
        content=token_document.content,
        document_id=token_document.id,
        metadata=token_document.metadata,
        max_tokens_per_chunk=5,  # Pass override if needed by test
    )
    assert len(chunks) == 2
    assert chunks[0].text == "Word1 word2 word3 word4 word5"
    assert chunks[1].text == "word6 word7 word8 word9 word10"
    # Check metadata propagation
    assert chunks[0].metadata["source"] == "test_token"
    assert "token_chunk_index" in chunks[0].metadata  # Check for processor-added meta


@pytest.mark.asyncio
async def test_simple_processor_empty_content(empty_document_data: DocumentData):
    """Tests chunking with empty or whitespace-only content."""
    processor_para = SimpleDocumentProcessor(chunk_strategy="paragraph")
    chunks_para: list[Chunk] = await processor_para.chunk_document(
        content=empty_document_data.content,
        document_id=empty_document_data.id,
        metadata=empty_document_data.metadata,
    )
    assert len(chunks_para) == 0

    processor_token = SimpleDocumentProcessor(
        chunk_strategy="token", tokens_per_chunk=10
    )
    chunks_token: list[Chunk] = await processor_token.chunk_document(
        content=empty_document_data.content,
        document_id=empty_document_data.id,
        metadata=empty_document_data.metadata,
    )
    assert len(chunks_token) == 0


def test_invalid_chunk_strategy():
    """Tests that an invalid chunk strategy raises ValueError."""
    with pytest.raises(ValueError, match="Invalid chunk_strategy"):
        SimpleDocumentProcessor(chunk_strategy="invalid_strategy")  # type: ignore


def test_invalid_token_chunk_size():
    """Tests that a non-positive token chunk size raises ValueError."""
    with pytest.raises(ValueError, match="tokens_per_chunk must be positive"):
        SimpleDocumentProcessor(chunk_strategy="token", tokens_per_chunk=0)
    with pytest.raises(ValueError, match="tokens_per_chunk must be positive"):
        SimpleDocumentProcessor(chunk_strategy="token", tokens_per_chunk=-5)


# Add more tests for edge cases:
# - Content with only newlines
# - Very large documents (might need mocking/different setup)
# - Different tokens_per_chunk values


# Mock DocumentData if needed for tests
class MockDocumentData:
    def __init__(self, content: str, metadata: Optional[dict[str, Any]] = None):
        self.content = content
        self.metadata = metadata or {}


@pytest.fixture
def document_processor():
    """Provides an instance of SimpleDocumentProcessor for testing."""
    return SimpleDocumentProcessor()
