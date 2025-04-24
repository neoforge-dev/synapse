import pytest
import uuid
from typing import List, Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch, call
from pytest_mock import MockerFixture

# Domain Models
from graph_rag.domain.models import Document, Chunk, Relationship, Entity, Edge

# Core Components
from graph_rag.core.document_processor import DocumentProcessor, ChunkSplitter
from graph_rag.core.entity_extractor import EntityExtractor
from graph_rag.core.interfaces import EmbeddingService, VectorStore, GraphRepository
from graph_rag.core.document_processor import SimpleDocumentProcessor

# Service Under Test
from graph_rag.services.ingestion import IngestionService, IngestionResult

# -- Fixtures --

@pytest.fixture
def mock_graph_repository() -> AsyncMock:
    """Mock GraphRepository."""
    mock = AsyncMock(spec=GraphRepository)
    
    # Configure add_document to return an awaitable None
    async def mock_add_document(document: Document) -> None:
        return None
    mock.add_document.side_effect = mock_add_document
    
    # Configure add_chunk to return an awaitable None
    async def mock_add_chunk(chunk: Chunk) -> None:
        return None
    mock.add_chunk.side_effect = mock_add_chunk
    
    # Configure add_relationship to return an awaitable None
    async def mock_add_relationship(edge: Edge) -> None:
        return None
    mock.add_relationship.side_effect = mock_add_relationship
    
    # Legacy mock for backward compatibility
    async def mock_add_entity(entity: Entity) -> str:
        # Return the ID of the entity being added
        return entity.id 
    mock.add_entity.side_effect = mock_add_entity
    
    return mock

@pytest.fixture
def mock_embedding_service() -> MagicMock:
    "Mock EmbeddingService."
    # mock = MagicMock(spec=EmbeddingService)
    # Configure the mock object to have an 'encode' method
    # encode_mock = MagicMock()
    # Simulate returning embeddings based on input text length for simplicity
    # encode_mock.side_effect = lambda texts: [[0.1 * len(text)] * 5 for text in texts]
    # mock.encode = encode_mock # Assign the configured mock method
    # Use AsyncMock for the encode method as it's awaited
    mock = AsyncMock(spec=EmbeddingService)
    async def mock_encode(texts: List[str]) -> List[List[float]]:
        # Simple mock: return dummy embeddings
        return [[0.1 * len(text)] * 5 for text in texts]
    mock.encode = mock_encode
    return mock

@pytest.fixture
def mock_chunk_splitter() -> MagicMock:
    "Mock ChunkSplitter."
    mock = MagicMock(spec=ChunkSplitter)
    # Simple split: Create 3 chunks regardless of content for predictability
    mock.split.side_effect = lambda doc: [
        Chunk(id="chunk_0", text="Chunk 0 content.", document_id=doc.id),
        Chunk(id="chunk_1", text="Chunk 1 content.", document_id=doc.id),
        Chunk(id="chunk_2", text="Chunk 2 content.", document_id=doc.id),
    ]
    return mock

@pytest.fixture
def mock_document_processor() -> MagicMock:
    # """Mock DocumentProcessor (optional, if complex logic needs mocking)."""
    "Mock DocumentProcessor (optional, if complex logic needs mocking)."
    # For now, assume IngestionService uses ChunkSplitter directly
    return MagicMock(spec=DocumentProcessor)

@pytest.fixture
def mock_entity_extractor() -> MagicMock:
    "Mock EntityExtractor."
    mock = MagicMock(spec=EntityExtractor)
    # Configure the mock object to have an 'extract' method (matching the abstract method)
    extract_mock = MagicMock()
    # Simple mock: return empty lists for entities/relationships within a ProcessedDocument
    extract_mock.side_effect = lambda doc: ProcessedDocument(
        id=doc.id, content=doc.content, metadata=doc.metadata, chunks=doc.chunks, 
        entities=[], relationships=[]
    )
    mock.extract = extract_mock # Assign the configured mock method
    # mock.extract_entities.side_effect = lambda text: [Entity(text=text.split()[0], label="MOCK")] # Remove incorrect old mock setup
    return mock


@pytest.fixture
def sample_text() -> str:
    return "Alice lives in Wonderland. Bob works at OpenAI."

@pytest.fixture
def mock_vector_store(mocker: MockerFixture):
    """Fixture for a mocked VectorStore."""
    mock = mocker.Mock(spec=VectorStore)
    # Add any necessary default mock behaviors here if needed, e.g.:
    # mock.add_chunks = mocker.AsyncMock()
    # mock.search = mocker.AsyncMock(return_value=[]) 
    return mock

# -- Tests --

@pytest.mark.asyncio
async def test_ingest_document_creates_document(
    mock_graph_repository: AsyncMock, 
    mock_embedding_service: MagicMock, 
    mock_chunk_splitter: MagicMock,
    mock_document_processor: MagicMock, # Add necessary mocks
    mock_entity_extractor: MagicMock, # Add necessary mocks
    mock_vector_store: MagicMock, # Add vector store mock
    sample_text: str
):
    # """Test that ingestion creates a document node with the right content."""
    "Test that ingestion creates a document node with the right content."
    # Correct instantiation with all required mocks
    service = IngestionService(
        document_processor=mock_document_processor, # Pass the mock
        entity_extractor=mock_entity_extractor, # Pass the mock
        graph_store=mock_graph_repository, 
        embedding_service=mock_embedding_service, 
        chunk_splitter=mock_chunk_splitter,
        vector_store=mock_vector_store # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_doc"}
    
    result = await service.ingest_document(document_id, sample_text, metadata, generate_embeddings=False)
    
    # Verify graph_store.add_document was called
    mock_graph_repository.add_document.assert_called_once()
    
    # Verify the Document object passed to add_document
    document_call = mock_graph_repository.add_document.call_args
    assert document_call is not None, "add_document was not called"
    
    added_doc = document_call.args[0]
    assert isinstance(added_doc, Document), "add_document was not called with a Document object"
    assert added_doc.id == result.document_id
    assert added_doc.content == sample_text
    assert added_doc.metadata == metadata

@pytest.mark.asyncio
async def test_ingest_document_creates_chunks_with_embeddings(
    mock_graph_repository: AsyncMock, 
    mock_embedding_service: MagicMock, 
    mock_chunk_splitter: MagicMock, 
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock, # Add vector store mock
    sample_text: str
):
    # """Test that ingestion creates chunks with embeddings by default."""
    "Test that ingestion creates chunks with embeddings by default."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository, 
        embedding_service=mock_embedding_service, 
        chunk_splitter=mock_chunk_splitter,
        vector_store=mock_vector_store # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_chunks_embed"}
    
    result = await service.ingest_document(document_id, sample_text, metadata, generate_embeddings=True)
    
    mock_embedding_service.encode.assert_called_once()
    assert mock_graph_repository.add_chunk.call_count == result.num_chunks
    assert mock_graph_repository.add_chunk.call_count == 3 # Based on mock_chunk_splitter behavior

    # Check that each chunk saved has an embedding
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert added_chunk.id in result.chunk_ids
        assert hasattr(added_chunk, 'embedding')
        assert added_chunk.embedding is not None
        assert isinstance(added_chunk.embedding, list)
        assert len(added_chunk.embedding) == 5 # Based on mock_embedding_service behavior

@pytest.mark.asyncio
async def test_ingest_document_skips_embeddings(
    mock_graph_repository: AsyncMock, 
    mock_embedding_service: MagicMock, 
    mock_chunk_splitter: MagicMock, 
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock, # Add vector store mock
    sample_text: str
):
    # """Test that ingestion skips embedding generation when flag is False."""
    "Test that ingestion skips embedding generation when flag is False."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository, 
        embedding_service=mock_embedding_service, 
        chunk_splitter=mock_chunk_splitter,
        vector_store=mock_vector_store # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_skip_embed"}
    
    result = await service.ingest_document(document_id, sample_text, metadata, generate_embeddings=False)
    
    mock_embedding_service.encode.assert_not_called()
    assert mock_graph_repository.add_chunk.call_count == result.num_chunks
    assert mock_graph_repository.add_chunk.call_count == 3
    
    # Check that each chunk saved has embedding set to None or missing
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert added_chunk.id in result.chunk_ids
        assert hasattr(added_chunk, 'embedding') # Field should exist
        assert added_chunk.embedding is None # Value should be None

@pytest.mark.asyncio
async def test_ingest_document_creates_relationships(
    mock_graph_repository: AsyncMock, 
    mock_embedding_service: MagicMock, 
    mock_chunk_splitter: MagicMock, 
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock, # Add vector store mock
    sample_text: str
):
    # """Test that ingestion creates relationships between the document and its chunks."""
    "Test that ingestion creates relationships between the document and its chunks."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository, 
        embedding_service=mock_embedding_service, 
        chunk_splitter=mock_chunk_splitter,
        vector_store=mock_vector_store # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_rels"}
    
    result = await service.ingest_document(document_id, sample_text, metadata, generate_embeddings=False)
    
    # Verify add_relationship was called for each chunk
    assert mock_graph_repository.add_relationship.call_count == result.num_chunks
    assert mock_graph_repository.add_relationship.call_count == 3
    
    for call_item in mock_graph_repository.add_relationship.call_args_list:
        added_edge = call_item.args[0]
        assert isinstance(added_edge, Edge)
        assert added_edge.type == "CONTAINS"
        assert added_edge.source_id == result.document_id
        assert added_edge.target_id in result.chunk_ids

@pytest.mark.asyncio
async def test_ingest_document_returns_ingestion_result(
    mock_graph_repository: AsyncMock, 
    mock_embedding_service: MagicMock, 
    mock_chunk_splitter: MagicMock,
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock # Add vector store mock
):
    # """Test that the service returns a proper IngestionResult with counts."""
    "Test that the service returns a proper IngestionResult with counts."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository, 
        embedding_service=mock_embedding_service, 
        chunk_splitter=mock_chunk_splitter,
        vector_store=mock_vector_store # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    content = "Test content for result."
    metadata = {"source": "test_result"}
    
    result = await service.ingest_document(document_id, content, metadata)
    
    assert isinstance(result, IngestionResult)
    assert isinstance(result.document_id, str)
    assert isinstance(result.chunk_ids, list)
    assert len(result.chunk_ids) == 3 # Based on mock splitter
    assert result.num_chunks == 3
    
    # Check document handling
    mock_graph_repository.add_document.assert_called_once()
    doc_call = mock_graph_repository.add_document.call_args
    assert result.document_id == doc_call.args[0].id
    
    # Check chunk processing
    chunk_ids = [call.args[0].id for call in mock_graph_repository.add_chunk.call_args_list]
    assert set(result.chunk_ids) == set(chunk_ids)


@pytest.mark.asyncio
async def test_ingest_handles_custom_chunk_size(
    mock_graph_repository: AsyncMock, 
    mock_embedding_service: MagicMock,
    # We need a real splitter or a better mock to test this properly
    # mock_chunk_splitter: MagicMock, 
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock # Add vector store mock
):
    # """Test that ingestion respects custom chunk size parameter ( conceptual - needs better splitter mock )."""
    "Test that ingestion respects custom chunk size parameter ( conceptual - needs better splitter mock )."
    # Use a real splitter for this test, or enhance the mock splitter
    real_splitter = SimpleDocumentProcessor().chunk_splitter # Get the default splitter
    
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository, 
        embedding_service=mock_embedding_service, 
        chunk_splitter=real_splitter, # Use the real splitter
        vector_store=mock_vector_store # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    long_text = "word " * 100  # 100 words
    metadata = {"source": "test_custom_chunk"}
    
    # This test currently only verifies the service runs without error
    # when using a real splitter. It doesn't verify the chunk size logic yet.
    # TODO: Enhance this test with a configurable mock_chunk_splitter or by
    #       inspecting the chunks produced by the real splitter.
    try:
        await service.ingest_document(document_id, long_text, metadata, max_tokens_per_chunk=20)
    except Exception as e:
        pytest.fail(f"Ingestion with custom chunk size failed: {e}")
    
    # Assertions would ideally check mock_chunk_splitter.split was called with appropriate args
    # or check the number/content of chunks if using a real splitter and mocking add_entity.
    # For now, just check that the call didn't crash.
    assert True # Placeholder assertion

# Test fixture for IngestionService instance (optional, can use mocks directly)
@pytest.fixture
def ingestion_service(
    mock_document_processor,
    mock_entity_extractor,
    mock_graph_repository, # Use repo mock
    mock_embedding_service,
    mock_chunk_splitter,
    mock_vector_store
):
    """Fixture to create an IngestionService instance with mock dependencies."""
    return IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository, # Use repo mock
        embedding_service=mock_embedding_service,
        chunk_splitter=mock_chunk_splitter,
        vector_store=mock_vector_store
    )

# Tests using the ingestion_service fixture

@pytest.mark.asyncio
async def test_ingest_document_no_embeddings(
    ingestion_service: IngestionService,
    mock_graph_repository: AsyncMock, # Still need repo mock for assertions
    mock_embedding_service: MagicMock # Still need embedding mock for assertions
):
    # """Test ingestion without embedding generation using the service fixture."""
    "Test ingestion without embedding generation using the service fixture."
    document_id = str(uuid.uuid4())
    content = "Test document content."
    metadata = {"source": "no-embed-test"}

    await ingestion_service.ingest_document(
        document_id=document_id,
        content=content,
        metadata=metadata,
        generate_embeddings=False
    )

    # Verify embedding service was not called
    mock_embedding_service.encode.assert_not_called()

    # Verify chunks were added without embeddings
    assert mock_graph_repository.add_chunk.call_count == 3 # Based on mock splitter
    
    # Check that each chunk saved has embedding set to None or missing
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert hasattr(added_chunk, 'embedding') # Field should exist
        assert added_chunk.embedding is None # Value should be None

@pytest.mark.asyncio
async def test_ingest_document_with_embeddings(
    ingestion_service: IngestionService,
    mock_graph_repository: AsyncMock, # Still need repo mock for assertions
    mock_embedding_service: MagicMock # Still need embedding mock for assertions
):
    # """Test ingestion with embedding generation using the service fixture."""
    "Test ingestion with embedding generation using the service fixture."
    document_id = str(uuid.uuid4())
    content = "Another test document."
    metadata = {"source": "embed-test"}

    await ingestion_service.ingest_document(
        document_id=document_id,
        content=content,
        metadata=metadata,
        generate_embeddings=True
    )

    # Verify embedding service was called
    mock_embedding_service.encode.assert_called_once()

    # Verify chunks were added with embeddings
    assert mock_graph_repository.add_chunk.call_count == 3 # Based on mock splitter
    
    # Check that each chunk has embeddings
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert hasattr(added_chunk, 'embedding')
        assert added_chunk.embedding is not None
        assert isinstance(added_chunk.embedding, list)
        assert len(added_chunk.embedding) > 0
