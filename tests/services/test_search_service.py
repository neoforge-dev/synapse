from unittest.mock import AsyncMock

import numpy as np
import pytest

from graph_rag.domain.models import Chunk
from graph_rag.services.search import SearchResult, SearchService

# Sample chunk data for mocking repository response
SAMPLE_CHUNK_1 = Chunk(
    id="chunk1", text="Apples are red.", document_id="doc1", embedding=[0.1] * 384
)
SAMPLE_CHUNK_2 = Chunk(
    id="chunk2", text="Oranges are orange.", document_id="doc1", embedding=[0.2] * 384
)
SAMPLE_CHUNK_3 = Chunk(
    id="chunk3",
    text="Another chunk mentioning red Apple.",
    document_id="doc2",
    embedding=[0.3] * 384,
)

SAMPLE_CHUNKS_CONTENT = [SAMPLE_CHUNK_1, SAMPLE_CHUNK_3]
SAMPLE_CHUNKS_SIMILARITY = [
    (SAMPLE_CHUNK_1, 0.95),
    (SAMPLE_CHUNK_3, 0.85),
]

EMBEDDING_DIM = 384
QUERY_VECTOR = np.random.rand(EMBEDDING_DIM).tolist()


@pytest.fixture
def mock_graph_repository_with_search():
    repo = AsyncMock()
    repo.search_chunks_by_content.return_value = SAMPLE_CHUNKS_CONTENT
    repo.search_chunks_by_similarity.return_value = SAMPLE_CHUNKS_SIMILARITY
    return repo


@pytest.fixture
def mock_embedding_service_for_search():
    """Mock the EmbeddingService used within SearchService."""
    mock_instance = AsyncMock()
    mock_instance.generate_embedding.return_value = (
        QUERY_VECTOR  # Return a fixed vector for the query
    )
    mock_instance.get_embedding_dimension.return_value = (
        EMBEDDING_DIM  # Ensure dim is mocked
    )
    return mock_instance


# --- Keyword Search Tests ---


@pytest.mark.asyncio
async def test_search_chunks_calls_repository(
    mock_graph_repository_with_search, mock_embedding_service_for_search
):
    service = SearchService(
        mock_graph_repository_with_search, mock_embedding_service_for_search
    )
    query = "apple"
    await service.search_chunks(query)
    mock_graph_repository_with_search.search_chunks_by_content.assert_called_once_with(
        query, 10
    )  # Default limit


@pytest.mark.asyncio
async def test_search_chunks_returns_search_results(
    mock_graph_repository_with_search, mock_embedding_service_for_search
):
    service = SearchService(
        mock_graph_repository_with_search, mock_embedding_service_for_search
    )
    query = "apple"
    results = await service.search_chunks(query)
    assert len(results) == len(SAMPLE_CHUNKS_CONTENT)
    for i, result in enumerate(results):
        assert result.chunk_id == SAMPLE_CHUNKS_CONTENT[i].id
        assert result.score == 1.0  # Default score for keyword match


@pytest.mark.asyncio
async def test_search_chunks_handles_no_results(
    mock_graph_repository_with_search, mock_embedding_service_for_search
):
    mock_graph_repository_with_search.search_chunks_by_content.return_value = []
    service = SearchService(
        mock_graph_repository_with_search, mock_embedding_service_for_search
    )
    results = await service.search_chunks("nonexistent")
    assert results == []


# --- Similarity Search Tests ---


@pytest.mark.asyncio
async def test_search_chunks_similarity_calls_embedding_and_repo(
    mock_graph_repository_with_search, mock_embedding_service_for_search
):
    """Test similarity search calls embedding service and repo method."""
    service = SearchService(
        mock_graph_repository_with_search, mock_embedding_service_for_search
    )
    query = "find similar apples"
    limit = 5

    await service.search_chunks_by_similarity(query, limit)

    mock_embedding_service_for_search.generate_embedding.assert_called_once_with(query)
    mock_graph_repository_with_search.search_chunks_by_similarity.assert_called_once_with(
        query_vector=QUERY_VECTOR, limit=limit
    )


@pytest.mark.asyncio
async def test_search_chunks_similarity_returns_results(
    mock_graph_repository_with_search, mock_embedding_service_for_search
):
    """Test similarity search returns correctly mapped results with scores."""
    service = SearchService(
        mock_graph_repository_with_search, mock_embedding_service_for_search
    )
    query = "find similar apples"

    results = await service.search_chunks_by_similarity(query)

    assert len(results) == len(SAMPLE_CHUNKS_SIMILARITY)
    for i, result in enumerate(results):
        assert isinstance(result, SearchResult)
        expected_chunk, expected_score = SAMPLE_CHUNKS_SIMILARITY[i]
        assert result.chunk_id == expected_chunk.id
        assert result.document_id == expected_chunk.document_id
        assert result.content == expected_chunk.text
        assert result.score == expected_score  # Score comes from repo


@pytest.mark.asyncio
async def test_search_chunks_similarity_handles_no_results(
    mock_graph_repository_with_search, mock_embedding_service_for_search
):
    """Test similarity search returns empty list when repo finds nothing."""
    mock_graph_repository_with_search.search_chunks_by_similarity.return_value = []
    service = SearchService(
        mock_graph_repository_with_search, mock_embedding_service_for_search
    )

    results = await service.search_chunks_by_similarity("nonexistent")
    assert results == []
