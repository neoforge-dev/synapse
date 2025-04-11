import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
import numpy as np
from graph_rag.domain.models import Document, Chunk
from graph_rag.services.ingestion import IngestionService
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository
from graph_rag.services.embedding import EmbeddingService
from graph_rag.core.document_processor import ChunkSplitter, SentenceSplitter

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
    with patch('graph_rag.services.ingestion.EmbeddingService') as mock_emb_service_cls:
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

# Sample text for testing
sample_text = "Sentence one. Sentence two. Sentence three."
# Adjust expected chunks based on SentenceSplitter (assuming it splits by sentence)
sample_chunks_content = ["Sentence one.", "Sentence two.", "Sentence three."]
# Create mock Chunk objects (assuming Chunk has a 'content' attribute)
sample_chunks = [Chunk(id=f"chunk_{i}", content=content, document_id="doc_1") for i, content in enumerate(sample_chunks_content)]
sample_embeddings = [np.array([0.1, 0.2]), np.array([0.3, 0.4]), np.array([0.5, 0.6])]

@pytest.fixture
def mock_graph_repo():
    """Fixture for a mocked GraphRepository."""
    repo = MagicMock(spec=GraphRepository)
    repo.save_document = AsyncMock()
    repo.save_chunk = AsyncMock()
    repo.save_edge = AsyncMock()
    return repo

@pytest.fixture
def mock_embedding_service():
    """Fixture for a mocked EmbeddingService."""
    service = MagicMock(spec=EmbeddingService)
    # Define the side effect for encode
    def mock_encode(texts):
        if not isinstance(texts, list):
            raise TypeError("Input must be a list of strings")
        # Return embeddings based on the number of input texts, matching sample_embeddings length
        num_texts = len(texts)
        if num_texts == len(sample_chunks_content):
            return sample_embeddings
        else:
            # Generate generic embeddings if the count doesn't match
            return [np.random.rand(2).astype(np.float32) for _ in range(num_texts)]
    
    service.encode = MagicMock(side_effect=mock_encode)
    # service.encode = MagicMock(return_value=sample_embeddings)
    return service

@pytest.fixture
def mock_chunk_splitter():
    """Fixture for a mocked ChunkSplitter."""
    splitter = MagicMock(spec=ChunkSplitter)
    splitter.split.return_value = sample_chunks # Return mock Chunk objects
    return splitter

@pytest.fixture
def ingestion_service(mock_graph_repo, mock_embedding_service, mock_chunk_splitter):
    """Fixture to create an IngestionService instance with mocked dependencies."""
    return IngestionService(
        graph_repo=mock_graph_repo, 
        embedding_service=mock_embedding_service,
        chunk_splitter=mock_chunk_splitter
    )

@pytest.mark.asyncio
async def test_ingest_document_no_embeddings(
    ingestion_service, 
    mock_graph_repo, 
    mock_chunk_splitter, 
    mock_embedding_service
):
    """Test document ingestion without generating embeddings."""
    document = Document(id="doc_1", content=sample_text)
    
    result = await ingestion_service.ingest_document(document, generate_embeddings=False)
    
    # Assert document was saved
    mock_graph_repo.save_document.assert_awaited_once_with(document)
    
    # Assert splitter was called
    mock_chunk_splitter.split.assert_called_once_with(document)
    
    # Assert chunks were saved
    expected_chunk_calls = [call(chunk) for chunk in sample_chunks]
    mock_graph_repo.save_chunk.assert_has_awaits(expected_chunk_calls, any_order=False) # Order matters if edges depend on it
    assert mock_graph_repo.save_chunk.await_count == len(sample_chunks)

    # Assert embeddings were NOT generated
    mock_embedding_service.encode.assert_not_called()
    
    # Assert edges were saved (assuming sequential chunks create edges)
    # Adjust edge creation logic if necessary
    expected_edge_calls = []
    if len(sample_chunks) > 1:
        for i in range(len(sample_chunks) - 1):
            edge = call(sample_chunks[i].id, sample_chunks[i+1].id, {"relationship": "sequential"})
            expected_edge_calls.append(edge)
        mock_graph_repo.save_edge.assert_has_awaits(expected_edge_calls, any_order=False)
        assert mock_graph_repo.save_edge.await_count == len(sample_chunks) - 1
    else:
        mock_graph_repo.save_edge.assert_not_called()

    # Check result object
    assert result.document_id == "doc_1"
    assert result.chunks_processed == len(sample_chunks)
    assert result.embeddings_generated == 0
    assert result.edges_created == (len(sample_chunks) - 1) if len(sample_chunks) > 1 else 0

@pytest.mark.asyncio
async def test_ingest_document_with_embeddings(
    ingestion_service, 
    mock_graph_repo, 
    mock_chunk_splitter, 
    mock_embedding_service
):
    """Test document ingestion WITH generating embeddings."""
    document = Document(id="doc_1", content=sample_text)
    
    result = await ingestion_service.ingest_document(document, generate_embeddings=True)
    
    # Assert document saved
    mock_graph_repo.save_document.assert_awaited_once_with(document)
    
    # Assert splitter called
    mock_chunk_splitter.split.assert_called_once_with(document)
    
    # Assert embeddings were generated
    # We expect encode to be called with the CONTENT of the chunks
    mock_embedding_service.encode.assert_called_once_with(sample_chunks_content)
    
    # Assert chunks were saved with embeddings
    expected_chunk_calls = []
    for i, chunk in enumerate(sample_chunks):
        # IMPORTANT: Create a *copy* or new Chunk instance with the embedding
        # Assuming the service modifies the chunk object in place or saves a new one
        # Let's assume the service updates the chunk objects passed from the splitter
        chunk.embedding = sample_embeddings[i] 
        expected_chunk_calls.append(call(chunk))
        
    mock_graph_repo.save_chunk.assert_has_awaits(expected_chunk_calls, any_order=False)
    assert mock_graph_repo.save_chunk.await_count == len(sample_chunks)

    # Assert edges were saved
    expected_edge_calls = []
    if len(sample_chunks) > 1:
        for i in range(len(sample_chunks) - 1):
            edge = call(sample_chunks[i].id, sample_chunks[i+1].id, {"relationship": "sequential"})
            expected_edge_calls.append(edge)
        mock_graph_repo.save_edge.assert_has_awaits(expected_edge_calls, any_order=False)
        assert mock_graph_repo.save_edge.await_count == len(sample_chunks) - 1
    else:
        mock_graph_repo.save_edge.assert_not_called()

    # Check result object
    assert result.document_id == "doc_1"
    assert result.chunks_processed == len(sample_chunks)
    assert result.embeddings_generated == len(sample_embeddings)
    assert result.edges_created == (len(sample_chunks) - 1) if len(sample_chunks) > 1 else 0


@pytest.mark.asyncio
async def test_ingest_document_embedding_error(
    ingestion_service, 
    mock_graph_repo, 
    mock_chunk_splitter, 
    mock_embedding_service
):
    """Test handling when embedding generation returns unexpected number of embeddings."""
    document = Document(id="doc_1", content=sample_text)
    
    # Configure mock encode to return a different number of embeddings
    mock_embedding_service.encode.side_effect = lambda texts: sample_embeddings[:len(texts)-1] # Return one less

    result = await ingestion_service.ingest_document(document, generate_embeddings=True)

    # Verify encode was called
    mock_embedding_service.encode.assert_called_once_with(sample_chunks_content)
    
    # Assert chunks were saved *without* embeddings due to the error
    expected_chunk_calls = []
    for chunk in sample_chunks:
        # Make sure the mock chunk objects don't have embeddings from previous tests
        chunk.embedding = None 
        expected_chunk_calls.append(call(chunk))
        
    mock_graph_repo.save_chunk.assert_has_awaits(expected_chunk_calls, any_order=False)
    assert mock_graph_repo.save_chunk.await_count == len(sample_chunks)
    
    # Check result reflects the error (0 embeddings generated)
    assert result.embeddings_generated == 0
    # Other assertions remain similar
    assert result.document_id == "doc_1"
    assert result.chunks_processed == len(sample_chunks)
    assert result.edges_created == (len(sample_chunks) - 1) if len(sample_chunks) > 1 else 0
    mock_graph_repo.save_document.assert_awaited_once()
    mock_chunk_splitter.split.assert_called_once()

@pytest.mark.asyncio
async def test_ingest_document_single_chunk(
    ingestion_service, 
    mock_graph_repo, 
    mock_chunk_splitter, 
    mock_embedding_service
):
    """Test ingestion when the document results in only one chunk."""
    single_chunk_content = ["Single sentence document."]
    single_chunk = [Chunk(id="chunk_0", content=single_chunk_content[0], document_id="doc_single")]
    single_embedding = [np.array([0.9, 0.8])]

    document = Document(id="doc_single", content=single_chunk_content[0])
    mock_chunk_splitter.split.return_value = single_chunk
    mock_embedding_service.encode.side_effect = lambda texts: single_embedding if len(texts) == 1 else []
    
    result = await ingestion_service.ingest_document(document, generate_embeddings=True)

    # Assertions
    mock_graph_repo.save_document.assert_awaited_once_with(document)
    mock_chunk_splitter.split.assert_called_once_with(document)
    mock_embedding_service.encode.assert_called_once_with(single_chunk_content)
    
    # Assert single chunk saved with embedding
    single_chunk[0].embedding = single_embedding[0]
    mock_graph_repo.save_chunk.assert_awaited_once_with(single_chunk[0])
    
    # Assert NO edges were saved
    mock_graph_repo.save_edge.assert_not_called()
    
    # Check result
    assert result.document_id == "doc_single"
    assert result.chunks_processed == 1
    assert result.embeddings_generated == 1
    assert result.edges_created == 0

# Add more tests as needed, e.g., for empty documents, repository errors, etc. 