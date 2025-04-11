import pytest
import uuid

from graph_rag.core.interfaces import DocumentData, ChunkData
from graph_rag.core.document_processor import SimpleDocumentProcessor

# Apply asyncio marker to the whole module
# pytestmark = pytest.mark.asyncio # Removed module-level marker

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

# Add a minimal async test
@pytest.mark.asyncio
async def test_minimal_async():
    assert True

@pytest.mark.asyncio
async def test_simple_chunking_by_paragraph(sample_doc_data):
    """Test chunking by paragraph with SimpleDocumentProcessor."""
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
    """Test chunking by fixed token count with SimpleDocumentProcessor."""
    processor = SimpleDocumentProcessor(chunk_strategy="token", tokens_per_chunk=5)
    chunks = await processor.chunk_document(sample_doc_data)
    
    assert len(chunks) == 2
    assert chunks[0].text == "First paragraph."
    assert chunks[1].text == "Second paragraph, slightly longer."
    for chunk in chunks:
        assert chunk.document_id == "doc-123"

@pytest.mark.asyncio
async def test_simple_chunking_invalid_strategy():
    """Test error handling for invalid chunking strategy."""
    with pytest.raises(ValueError, match="Invalid chunk_strategy"):
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