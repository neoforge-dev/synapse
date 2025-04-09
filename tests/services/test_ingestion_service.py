import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import numpy as np

from graph_rag.domain.models import Document, Chunk, Edge
from graph_rag.services.ingestion import IngestionService, IngestionResult
from graph_rag.services.embedding import EmbeddingService

# Mock Embedding dimensions
EMBEDDING_DIM = 384 

@pytest.fixture
def mock_graph_repository():
    repo = AsyncMock()
    repo.save_document.return_value = "doc1"
    repo.save_chunk.return_value = "chunk1"
    repo.create_relationship.return_value = "rel1"
    return repo

@pytest.fixture(autouse=True)
def mock_embedding_service():
    """Mock the EmbeddingService class methods globally for service tests."""
    with patch('graph_rag.services.ingestion.EmbeddingService', autospec=True) as mock_emb_service_cls:
        mock_instance = mock_emb_service_cls.return_value
        # Mock the encode method
        def mock_encode(texts):
            if isinstance(texts, str):
                return np.random.rand(EMBEDDING_DIM).tolist()
            else:
                return [np.random.rand(EMBEDDING_DIM).tolist() for _ in texts]
        
        mock_instance.encode.side_effect = mock_encode
        mock_instance.get_embedding_dim.return_value = EMBEDDING_DIM
        yield mock_instance

@pytest.fixture
def sample_text():
    return """This is a test document with multiple paragraphs.
    
    This is the second paragraph with different content.
    
    And this is the third paragraph for testing chunk creation."""

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_ingest_document_creates_document(mock_graph_repository, sample_text):
    """Test that ingestion creates a document node with the right content."""
    service = IngestionService(mock_graph_repository)
    
    result = await service.ingest_document(
        content=sample_text,
        metadata={"source": "test", "author": "tester"}
    )
    
    # Assert document was saved
    mock_graph_repository.save_document.assert_called_once()
    # Extract the Document object from the call
    doc_arg = mock_graph_repository.save_document.call_args[0][0]
    assert isinstance(doc_arg, Document)
    assert doc_arg.content == sample_text
    assert doc_arg.metadata == {"source": "test", "author": "tester"}


@pytest.mark.asyncio
async def test_ingest_document_creates_chunks_with_embeddings(mock_graph_repository, mock_embedding_service, sample_text):
    """Test that ingestion creates chunks with embeddings by default."""
    service = IngestionService(mock_graph_repository)
    
    result = await service.ingest_document(
        content=sample_text,
        metadata={"source": "test"}
    )
    
    # Assert chunks saved and embeddings generated
    assert mock_graph_repository.save_chunk.call_count == 3
    mock_embedding_service.encode.assert_called_once()
    
    document_ids = set()
    for call in mock_graph_repository.save_chunk.call_args_list:
        chunk_arg = call[0][0]
        assert isinstance(chunk_arg, Chunk)
        # Check embedding exists and has correct dimension
        assert chunk_arg.embedding is not None
        assert isinstance(chunk_arg.embedding, list)
        assert len(chunk_arg.embedding) == EMBEDDING_DIM
        document_ids.add(chunk_arg.document_id)
    
    assert len(document_ids) == 1

@pytest.mark.asyncio
async def test_ingest_document_skips_embeddings(mock_graph_repository, mock_embedding_service, sample_text):
    """Test that ingestion skips embedding generation when flag is False."""
    service = IngestionService(mock_graph_repository)
    
    result = await service.ingest_document(
        content=sample_text,
        metadata={"source": "test"},
        generate_embeddings=False # Explicitly disable
    )
    
    assert mock_graph_repository.save_chunk.call_count == 3
    mock_embedding_service.encode.assert_not_called()
    
    for call in mock_graph_repository.save_chunk.call_args_list:
        chunk_arg = call[0][0]
        assert chunk_arg.embedding is None


@pytest.mark.asyncio
async def test_ingest_document_creates_relationships(mock_graph_repository, sample_text):
    """Test that ingestion creates relationships between the document and its chunks."""
    service = IngestionService(mock_graph_repository)
    
    result = await service.ingest_document(
        content=sample_text,
        metadata={"source": "test"}
    )
    
    # Should create 3 relationships (one for each chunk)
    assert mock_graph_repository.create_relationship.call_count == 3
    
    # Check if edges are correctly constructed
    for call in mock_graph_repository.create_relationship.call_args_list:
        edge_arg = call[0][0]
        assert isinstance(edge_arg, Edge)
        assert edge_arg.type == "CONTAINS"
        # The source should be the document, target the chunk
        assert edge_arg.source_id == "doc1"  # From mock return value


@pytest.mark.asyncio
async def test_ingest_document_returns_ingestion_result(mock_graph_repository):
    """Test that the service returns a proper IngestionResult with counts."""
    service = IngestionService(mock_graph_repository)
    
    result = await service.ingest_document(
        content="Short test content",
        metadata={}
    )
    
    assert isinstance(result, IngestionResult)
    assert result.document_id == "doc1"  # From mock return value
    assert len(result.chunk_ids) > 0
    assert result.num_chunks == len(result.chunk_ids)


@pytest.mark.asyncio
async def test_ingest_handles_custom_chunk_size(mock_graph_repository):
    """Test that ingestion respects custom chunk size parameter."""
    long_text = "word " * 100  # 100 words
    service = IngestionService(mock_graph_repository)
    
    # With default settings (paragraph splitting)
    result1 = await service.ingest_document(content=long_text, metadata={}, generate_embeddings=False)
    
    # Reset the mock to clear call counts
    mock_graph_repository.save_chunk.reset_mock()
    
    # With custom max token setting (10 words per chunk)
    result2 = await service.ingest_document(
        content=long_text, 
        metadata={},
        max_tokens_per_chunk=10,
        generate_embeddings=False
    )
    
    # Should create more chunks with smaller token size
    assert result2.num_chunks > result1.num_chunks 