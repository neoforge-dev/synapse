import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

# Core Components
from graph_rag.core.interfaces import (
    ChunkData,  # Correct interface import
    DocumentProcessor,
    EmbeddingService,
    EntityExtractor,
    GraphRepository,
    VectorStore,
)

# Domain Models
from graph_rag.domain.models import Chunk, Document, Edge, Entity, Relationship

# Correct implementation import
from graph_rag.infrastructure.document_processor.simple_processor import ChunkSplitter

# Service Under Test
from graph_rag.services.ingestion import IngestionResult, IngestionService

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
def mock_embedding_service() -> AsyncMock:
    "Mock EmbeddingService."
    mock = AsyncMock(spec=EmbeddingService)

    async def mock_encode_side_effect(texts: list[str]) -> list[list[float]]:
        # Simple mock: return dummy embeddings
        return [[0.1 * len(text)] * 5 for text in texts]

    # Assign an AsyncMock to the encode attribute and set its side_effect
    mock.encode = AsyncMock(side_effect=mock_encode_side_effect)
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
    mock = AsyncMock(spec=DocumentProcessor)
    # Example setup: return specific chunks when called
    mock.chunk_document.return_value = [
        ChunkData(
            id=str(uuid.uuid4()),
            text="Chunk 1 text.",
            document_id="doc1",
            embedding=None,
        ),
        ChunkData(
            id=str(uuid.uuid4()),
            text="Chunk 2 text.",
            document_id="doc1",
            embedding=None,
        ),
    ]
    return mock


@pytest.fixture
def mock_entity_extractor() -> MagicMock:
    "Mock EntityExtractor."
    mock = MagicMock(spec=EntityExtractor)
    # Configure the mock object to have an 'extract' method (matching the abstract method)
    extract_mock = MagicMock()
    # Simple mock: return empty lists for entities/relationships within a ProcessedDocument
    extract_mock.side_effect = lambda doc: ProcessedDocument(
        id=doc.id,
        content=doc.content,
        metadata=doc.metadata,
        chunks=doc.chunks,
        entities=[],
        relationships=[],
    )
    mock.extract = extract_mock  # Assign the configured mock method
    # mock.extract_entities.side_effect = lambda text: [Entity(text=text.split()[0], label="MOCK")] # Remove incorrect old mock setup
    return mock


@pytest.fixture
def sample_text() -> str:
    return "Alice lives in Wonderland. Bob works at OpenAI."


@pytest.fixture
def mock_vector_store(mocker: MockerFixture):
    """Fixture for a mocked VectorStore."""
    # Use AsyncMock directly or configure mocker.Mock properly for async methods
    # mock = mocker.Mock(spec=VectorStore)
    mock = mocker.AsyncMock(spec=VectorStore)
    # Add any necessary default mock behaviors here if needed, e.g.:
    # mock.add_chunks = mocker.AsyncMock() # Explicitly mock async methods if not using AsyncMock for the base
    mock.add_chunks = mocker.AsyncMock()  # Ensure add_chunks is an AsyncMock
    mock.search = mocker.AsyncMock(return_value=[])
    # Mock other methods used by the service if any
    return mock


# -- Tests --


@pytest.mark.asyncio
async def test_ingest_document_creates_document(
    mock_graph_repository: AsyncMock,
    mock_embedding_service: MagicMock,
    mock_document_processor: MagicMock,  # Add necessary mocks
    mock_entity_extractor: MagicMock,  # Add necessary mocks
    mock_vector_store: MagicMock,  # Add vector store mock
    sample_text: str,
):
    # """Test that ingestion creates a document node with the right content."""
    "Test that ingestion creates a document node with the right content."
    # Correct instantiation with all required mocks
    service = IngestionService(
        document_processor=mock_document_processor,  # Pass the mock
        entity_extractor=mock_entity_extractor,  # Pass the mock
        graph_store=mock_graph_repository,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,  # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_doc"}

    # Need to mock document_processor.chunk_document as it's now used internally
    mock_document_processor.chunk_document.return_value = [
        Chunk(id="chunk_0", text="Chunk 0 content.", document_id=document_id),
        Chunk(id="chunk_1", text="Chunk 1 content.", document_id=document_id),
    ]

    result = await service.ingest_document(
        document_id, sample_text, metadata, generate_embeddings=False
    )

    # Verify graph_store.add_document was called
    mock_graph_repository.add_document.assert_called_once()

    # Verify the Document object passed to add_document
    document_call = mock_graph_repository.add_document.call_args
    assert document_call is not None, "add_document was not called"

    added_doc = document_call.args[0]
    assert isinstance(added_doc, Document), (
        "add_document was not called with a Document object"
    )
    assert added_doc.id == result.document_id  # Use result.document_id for consistency
    assert added_doc.content == sample_text
    assert added_doc.metadata == metadata


@pytest.mark.asyncio
async def test_ingest_document_creates_chunks_with_embeddings(
    mock_graph_repository: AsyncMock,
    mock_embedding_service: MagicMock,
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock,  # Add vector store mock
    sample_text: str,
):
    # """Test that ingestion creates chunks with embeddings by default."""
    "Test that ingestion creates chunks with embeddings by default."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,  # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_chunks_embed"}

    # Mock document_processor.chunk_document
    mock_chunks = [
        Chunk(
            id="chunk_embed_0",
            text="Chunk 0 for embedding.",
            document_id=document_id,
            metadata={},
        ),
        Chunk(
            id="chunk_embed_1",
            text="Chunk 1 for embedding.",
            document_id=document_id,
            metadata={},
        ),
    ]
    mock_document_processor.chunk_document.return_value = mock_chunks

    result = await service.ingest_document(
        document_id, sample_text, metadata, generate_embeddings=True
    )

    mock_embedding_service.encode.assert_called_once()
    # Check that the texts passed to encode match the mock chunk texts
    encode_call_args = mock_embedding_service.encode.call_args[0][0]
    assert encode_call_args == [c.text for c in mock_chunks]

    mock_vector_store.add_chunks.assert_called_once()
    # Check chunks added to vector store have embeddings
    vs_call_args = mock_vector_store.add_chunks.call_args[0][0]
    assert len(vs_call_args) == len(mock_chunks)
    for chunk in vs_call_args:
        assert hasattr(chunk, "embedding")
        assert chunk.embedding is not None

    assert mock_graph_repository.add_chunk.call_count == result.num_chunks
    assert mock_graph_repository.add_chunk.call_count == len(mock_chunks)

    # Check that each chunk saved to graph has an embedding
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert added_chunk.id in result.chunk_ids
        assert hasattr(added_chunk, "embedding")
        assert added_chunk.embedding is not None
        assert isinstance(added_chunk.embedding, list)
        # Dimension check depends on mock_embedding_service mock
        # assert len(added_chunk.embedding) == 5 # Assuming mock returns dim 5


@pytest.mark.asyncio
async def test_ingest_document_skips_embeddings(
    mock_graph_repository: AsyncMock,
    mock_embedding_service: MagicMock,
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock,  # Add vector store mock
    sample_text: str,
):
    # """Test that ingestion skips embedding generation when flag is False."""
    "Test that ingestion skips embedding generation when flag is False."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,  # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_skip_embed"}

    # Mock document_processor.chunk_document
    mock_chunks = [
        Chunk(
            id="chunk_skip_0",
            text="Chunk 0 skipping embedding.",
            document_id=document_id,
        ),
        Chunk(
            id="chunk_skip_1",
            text="Chunk 1 skipping embedding.",
            document_id=document_id,
        ),
    ]
    mock_document_processor.chunk_document.return_value = mock_chunks

    result = await service.ingest_document(
        document_id, sample_text, metadata, generate_embeddings=False
    )

    mock_embedding_service.encode.assert_not_called()
    mock_vector_store.add_chunks.assert_not_called()  # Chunks shouldn't be added if no embeddings generated
    assert mock_graph_repository.add_chunk.call_count == result.num_chunks
    assert mock_graph_repository.add_chunk.call_count == len(mock_chunks)

    # Check that each chunk saved has embedding set to None or missing
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert added_chunk.id in result.chunk_ids
        assert hasattr(added_chunk, "embedding")  # Field should exist
        assert added_chunk.embedding is None  # Value should be None


@pytest.mark.asyncio
async def test_ingest_document_creates_relationships(
    mock_graph_repository: AsyncMock,
    mock_embedding_service: MagicMock,
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock,  # Add vector store mock
    sample_text: str,
):
    # """Test that ingestion creates relationships between the document and its chunks."""
    "Test that ingestion creates relationships between the document and its chunks."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,  # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    metadata = {"source": "test_rels"}

    # Mock document_processor.chunk_document
    mock_chunks = [
        Chunk(
            id="chunk_rel_0",
            text="Chunk 0 for relationship test.",
            document_id=document_id,
        ),
        Chunk(
            id="chunk_rel_1",
            text="Chunk 1 for relationship test.",
            document_id=document_id,
        ),
    ]
    mock_document_processor.chunk_document.return_value = mock_chunks

    await service.ingest_document(
        document_id, sample_text, metadata, generate_embeddings=False
    )

    # Verify add_relationship was called for each chunk
    assert mock_graph_repository.add_relationship.call_count == len(mock_chunks)

    # Verify the relationships created
    for i, call_item in enumerate(
        mock_graph_repository.add_relationship.call_args_list
    ):
        added_rel = call_item.args[0]
        assert isinstance(added_rel, Relationship)
        assert added_rel.type == "CONTAINS"
        assert added_rel.source_id == document_id
        assert (
            added_rel.target_id == mock_chunks[i].id
        )  # Check against corresponding mock chunk


@pytest.mark.asyncio
async def test_ingest_document_returns_ingestion_result(
    mock_graph_repository: AsyncMock,
    mock_embedding_service: MagicMock,
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock,  # Add vector store mock
):
    # """Test that the service returns a proper IngestionResult with counts."""
    "Test that the service returns a proper IngestionResult with counts."
    # Correct instantiation
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,  # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    content = "Test content for result."
    metadata = {"source": "test_result"}

    # Mock document_processor.chunk_document to return a predictable number of chunks
    mock_chunks = [
        Chunk(
            id="chunk_res_0", text="Chunk 0 for result test.", document_id=document_id
        ),
        Chunk(
            id="chunk_res_1", text="Chunk 1 for result test.", document_id=document_id
        ),
        Chunk(
            id="chunk_res_2", text="Chunk 2 for result test.", document_id=document_id
        ),
    ]
    mock_document_processor.chunk_document.return_value = mock_chunks

    result = await service.ingest_document(document_id, content, metadata)

    assert isinstance(result, IngestionResult)
    assert isinstance(result.document_id, str)
    assert isinstance(result.chunk_ids, list)
    assert len(result.chunk_ids) == len(mock_chunks)  # Check against mock chunks
    assert result.num_chunks == len(mock_chunks)

    # Check document handling
    mock_graph_repository.add_document.assert_called_once()
    doc_call = mock_graph_repository.add_document.call_args
    # Verify the ID matches the one used in the call, or the one returned in the result
    assert result.document_id == doc_call.args[0].id

    # Check chunk processing
    chunk_ids_saved = [
        call.args[0].id for call in mock_graph_repository.add_chunk.call_args_list
    ]
    assert set(result.chunk_ids) == set(chunk_ids_saved)
    assert set(result.chunk_ids) == set(c.id for c in mock_chunks)


@pytest.mark.asyncio
async def test_ingest_handles_custom_chunk_size(
    mock_graph_repository: AsyncMock,
    mock_embedding_service: MagicMock,
    mock_document_processor: MagicMock,
    mock_entity_extractor: MagicMock,
    mock_vector_store: MagicMock,  # Add vector store mock
):
    # """Test that ingestion respects custom chunk size parameter ( conceptual - needs better splitter mock )."""
    "Test that ingestion respects custom chunk size parameter ( conceptual - needs better splitter mock )."
    # Use a real splitter for this test, or enhance the mock splitter
    # real_splitter = SimpleDocumentProcessor().chunk_splitter # Get the default splitter

    # Correct instantiation - remove chunk_splitter
    service = IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,  # Pass vector store mock
    )
    document_id = str(uuid.uuid4())
    long_text = "word " * 100  # 100 words
    metadata = {"source": "test_custom_chunk"}

    # Mock document_processor.chunk_document
    mock_chunks = [
        Chunk(id="chunk_custom_0", text="word " * 20, document_id=document_id),
        Chunk(id="chunk_custom_1", text="word " * 20, document_id=document_id),
        Chunk(id="chunk_custom_2", text="word " * 20, document_id=document_id),
        Chunk(id="chunk_custom_3", text="word " * 20, document_id=document_id),
        Chunk(id="chunk_custom_4", text="word " * 20, document_id=document_id),
    ]
    mock_document_processor.chunk_document.return_value = mock_chunks

    # This test currently only verifies the service runs without error
    # when using a real splitter. It doesn't verify the chunk size logic yet.
    # TODO: Enhance this test with a configurable mock_chunk_splitter or by
    #       inspecting the chunks produced by the real splitter.
    try:
        # The max_tokens_per_chunk argument is used by the document_processor, not the IngestionService directly.
        # We need to assert that the document_processor was called correctly if we want to test this.
        # For now, we just call ingest_document.
        await service.ingest_document(document_id, long_text, metadata)
    except Exception as e:
        pytest.fail(f"Ingestion with custom chunk size failed: {e}")

    # Assert that the document processor's chunking method was called.
    # The arguments check would depend on how SimpleDocumentProcessor handles max_tokens.
    mock_document_processor.chunk_document.assert_called_once()
    # For now, just check that the call didn't crash and chunks were added.
    assert mock_graph_repository.add_chunk.call_count == len(mock_chunks)


# Test fixture for IngestionService instance (optional, can use mocks directly)
@pytest.fixture
def ingestion_service(
    mock_document_processor,
    mock_entity_extractor,
    mock_graph_repository,  # Use repo mock
    mock_embedding_service,
    mock_vector_store,
):
    """Fixture to create an IngestionService instance with mock dependencies."""
    return IngestionService(
        document_processor=mock_document_processor,
        entity_extractor=mock_entity_extractor,
        graph_store=mock_graph_repository,  # Use repo mock
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )


# Tests using the ingestion_service fixture


@pytest.mark.asyncio
async def test_ingest_document_no_embeddings(
    ingestion_service: IngestionService,
    mock_graph_repository: AsyncMock,  # Still need repo mock for assertions
    mock_embedding_service: MagicMock,  # Still need embedding mock for assertions
    mock_document_processor: MagicMock,  # Added missing dependency used in the test
):
    # """Test ingestion without embedding generation using the service fixture."""
    "Test ingestion without embedding generation using the service fixture."
    document_id = str(uuid.uuid4())
    content = "Test document content."
    metadata = {"source": "no-embed-test"}

    # Mock the chunking call that happens inside ingest_document
    mock_chunks = [
        Chunk(
            id="chunk_fixture_noemb_0",
            text="Fixture chunk 0 no embedding.",
            document_id=document_id,
        ),
        Chunk(
            id="chunk_fixture_noemb_1",
            text="Fixture chunk 1 no embedding.",
            document_id=document_id,
        ),
    ]
    mock_document_processor.chunk_document.return_value = mock_chunks

    await ingestion_service.ingest_document(
        document_id=document_id,
        content=content,
        metadata=metadata,
        generate_embeddings=False,
    )

    # Verify embedding service was not called
    mock_embedding_service.encode.assert_not_called()

    # Verify chunks were added without embeddings
    assert mock_graph_repository.add_chunk.call_count == len(
        mock_chunks
    )  # Check against actual mock chunks

    # Check that each chunk saved has embedding set to None or missing
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert hasattr(added_chunk, "embedding")  # Field should exist
        assert added_chunk.embedding is None  # Value should be None


@pytest.mark.asyncio
async def test_ingest_document_with_embeddings(
    ingestion_service: IngestionService,
    mock_graph_repository: AsyncMock,  # Still need repo mock for assertions
    mock_embedding_service: MagicMock,  # Still need embedding mock for assertions
    mock_document_processor: MagicMock,  # Added missing dependency used in the test
    mock_vector_store: MagicMock,  # Need vector store from fixture
):
    # """Test ingestion with embedding generation using the service fixture."""
    "Test ingestion with embedding generation using the service fixture."
    document_id = str(uuid.uuid4())
    content = "Another test document."
    metadata = {"source": "embed-test"}

    # Mock the chunking call
    mock_chunks = [
        Chunk(
            id="chunk_fixture_emb_0",
            text="Fixture chunk 0 with embedding.",
            document_id=document_id,
            metadata={},
        ),
        Chunk(
            id="chunk_fixture_emb_1",
            text="Fixture chunk 1 with embedding.",
            document_id=document_id,
            metadata={},
        ),
    ]
    mock_document_processor.chunk_document.return_value = mock_chunks

    await ingestion_service.ingest_document(
        document_id=document_id,
        content=content,
        metadata=metadata,
        generate_embeddings=True,
    )

    # Verify embedding service was called
    mock_embedding_service.encode.assert_called_once()
    # Verify vector store add_chunks was called
    mock_vector_store.add_chunks.assert_called_once()

    # Verify chunks were added with embeddings
    assert mock_graph_repository.add_chunk.call_count == len(mock_chunks)
    for call_item in mock_graph_repository.add_chunk.call_args_list:
        added_chunk = call_item.args[0]
        assert hasattr(added_chunk, "embedding")
        assert added_chunk.embedding is not None
