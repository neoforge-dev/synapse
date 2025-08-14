"""Tests for batch operations functionality."""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import List

from graph_rag.services.batch_operations import (
    BatchOperationsService,
    BatchOperationType,
    BatchStatus,
    BatchIngestionRequest,
    BatchSearchRequest,
    BatchOperationResult,
    BatchResult
)
from graph_rag.services.ingestion import IngestionService
from graph_rag.services.search import AdvancedSearchService, HybridSearchResult, SearchStrategy
from graph_rag.core.interfaces import SearchResultData, ChunkData, VectorStore, GraphRepository


@pytest.fixture
def mock_ingestion_service():
    """Mock ingestion service for testing."""
    mock = AsyncMock(spec=IngestionService)
    mock.ingest_document.return_value = None
    return mock


@pytest.fixture
def mock_search_service():
    """Mock search service for testing."""
    mock = AsyncMock(spec=AdvancedSearchService)
    
    # Mock search result
    search_result = HybridSearchResult(
        results=[
            SearchResultData(
                chunk=ChunkData(
                    id="chunk1",
                    document_id="doc1",
                    text="Sample search result",
                    embedding=[0.1, 0.2, 0.3]
                ),
                score=0.9
            )
        ],
        strategy=SearchStrategy.HYBRID,
        query="test query",
        total_vector_results=1,
        total_keyword_results=0,
        execution_time_ms=100.0
    )
    
    mock.search.return_value = search_result
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock = AsyncMock(spec=VectorStore)
    mock.delete_chunks.return_value = None
    return mock


@pytest.fixture
def mock_graph_repository():
    """Mock graph repository for testing."""
    mock = AsyncMock(spec=GraphRepository)
    mock.delete_document.return_value = True
    mock.get_chunks_by_document_id.return_value = []
    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    mock = AsyncMock()
    mock.generate_embeddings.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    return mock


@pytest.fixture
def batch_service(
    mock_ingestion_service,
    mock_search_service,
    mock_vector_store,
    mock_graph_repository,
    mock_embedding_service
):
    """Create batch operations service with mocked dependencies."""
    return BatchOperationsService(
        ingestion_service=mock_ingestion_service,
        search_service=mock_search_service,
        vector_store=mock_vector_store,
        graph_repository=mock_graph_repository,
        embedding_service=mock_embedding_service,
        max_workers=2,
        batch_size=5
    )


@pytest.mark.asyncio
async def test_batch_ingest_documents(batch_service, mock_ingestion_service):
    """Test batch document ingestion."""
    documents = [
        {
            "path": "doc1.txt",
            "content": "Sample document 1 content",
            "metadata": {"title": "Document 1"}
        },
        {
            "path": "doc2.txt", 
            "content": "Sample document 2 content",
            "metadata": {"title": "Document 2"}
        },
        {
            "content": "Document without path",
            "metadata": {"title": "Document 3"}
        }
    ]
    
    request = BatchIngestionRequest(
        documents=documents,
        generate_embeddings=True,
        replace_existing=True
    )
    
    result = await batch_service.batch_ingest_documents(request)
    
    assert isinstance(result, BatchOperationResult)
    assert result.operation_type == BatchOperationType.INGEST
    assert result.total_items == 3
    assert result.successful_items == 3
    assert result.failed_items == 0
    assert result.success_rate == 1.0
    assert len(result.results) == 3
    
    # Verify ingestion service was called for each document
    assert mock_ingestion_service.ingest_document.call_count == 3
    
    # Check individual results
    for batch_result in result.results:
        assert batch_result.status == BatchStatus.COMPLETED
        assert batch_result.error is None
        assert batch_result.data is not None
        assert "document_id" in batch_result.data


@pytest.mark.asyncio
async def test_batch_ingest_with_failures(batch_service, mock_ingestion_service):
    """Test batch ingestion with some failures."""
    # Configure mock to fail on second document
    async def mock_ingest(document_id, content, metadata, **kwargs):
        if "fail" in content:
            raise ValueError("Simulated ingestion failure")
    
    mock_ingestion_service.ingest_document.side_effect = mock_ingest
    
    documents = [
        {"content": "Good document", "metadata": {}},
        {"content": "Document that will fail", "metadata": {}},
        {"content": "Another good document", "metadata": {}}
    ]
    
    request = BatchIngestionRequest(documents=documents)
    result = await batch_service.batch_ingest_documents(request)
    
    assert result.total_items == 3
    assert result.successful_items == 2
    assert result.failed_items == 1
    assert result.success_rate == 2/3
    
    # Check that one result failed
    failed_results = [r for r in result.results if r.status == BatchStatus.FAILED]
    assert len(failed_results) == 1
    assert "Simulated ingestion failure" in failed_results[0].error


@pytest.mark.asyncio
async def test_batch_search(batch_service, mock_search_service):
    """Test batch search operations."""
    queries = [
        "machine learning",
        "artificial intelligence", 
        "data science",
        "neural networks"
    ]
    
    request = BatchSearchRequest(
        queries=queries,
        search_strategy="hybrid",
        limit_per_query=5,
        rerank=True
    )
    
    result = await batch_service.batch_search(request)
    
    assert isinstance(result, BatchOperationResult)
    assert result.operation_type == BatchOperationType.SEARCH
    assert result.total_items == 4
    assert result.successful_items == 4
    assert result.failed_items == 0
    assert len(result.results) == 4
    
    # Verify search service was called for each query
    assert mock_search_service.search.call_count == 4
    
    # Check individual results
    for batch_result in result.results:
        assert batch_result.status == BatchStatus.COMPLETED
        assert batch_result.data is not None
        assert isinstance(batch_result.data, HybridSearchResult)


@pytest.mark.asyncio
async def test_batch_generate_embeddings(batch_service, mock_embedding_service):
    """Test batch embedding generation."""
    texts = [
        "First text to embed",
        "Second text to embed"
    ]
    
    result = await batch_service.batch_generate_embeddings(texts)
    
    assert isinstance(result, BatchOperationResult)
    assert result.operation_type == BatchOperationType.EMBED
    assert result.total_items == 2
    assert result.successful_items == 2
    assert result.failed_items == 0
    assert len(result.results) == 2
    
    # Verify embedding service was called
    mock_embedding_service.generate_embeddings.assert_called_once_with(texts)
    
    # Check individual results
    for batch_result in result.results:
        assert batch_result.status == BatchStatus.COMPLETED
        assert batch_result.data is not None
        assert isinstance(batch_result.data, list)  # Embedding vector


@pytest.mark.asyncio
async def test_batch_delete_documents(batch_service, mock_graph_repository, mock_vector_store):
    """Test batch document deletion."""
    document_ids = ["doc1", "doc2", "doc3"]
    
    result = await batch_service.batch_delete_documents(document_ids)
    
    assert isinstance(result, BatchOperationResult)
    assert result.operation_type == BatchOperationType.DELETE
    assert result.total_items == 3
    assert result.successful_items == 3
    assert result.failed_items == 0
    assert len(result.results) == 3
    
    # Verify deletion methods were called
    assert mock_graph_repository.delete_document.call_count == 3
    assert mock_graph_repository.get_chunks_by_document_id.call_count == 3
    
    # Check individual results
    for batch_result in result.results:
        assert batch_result.status == BatchStatus.COMPLETED
        assert batch_result.data is not None
        assert "document_id" in batch_result.data


@pytest.mark.asyncio
async def test_batch_operations_with_progress_callback():
    """Test batch operations with progress callback."""
    progress_calls = []
    
    def progress_callback(current, total):
        progress_calls.append((current, total))
    
    # Create service with small batch size for testing
    service = BatchOperationsService(
        batch_size=2,
        enable_progress_callback=True
    )
    
    documents = [{"content": f"doc {i}", "metadata": {}} for i in range(5)]
    request = BatchIngestionRequest(documents=documents)
    
    # Mock ingestion service
    mock_ingestion = AsyncMock()
    service.ingestion_service = mock_ingestion
    
    await service.batch_ingest_documents(request, progress_callback)
    
    # Should have received progress updates
    assert len(progress_calls) > 0
    # Final call should be (5, 5)
    assert progress_calls[-1] == (5, 5)


@pytest.mark.asyncio
async def test_batch_operations_without_services():
    """Test batch operations when required services are not available."""
    service = BatchOperationsService()  # No services provided
    
    # Test ingestion without service
    request = BatchIngestionRequest(documents=[{"content": "test", "metadata": {}}])
    result = await service.batch_ingest_documents(request)
    
    assert result.successful_items == 0
    assert result.failed_items == 1
    assert result.results[0].status == BatchStatus.FAILED
    assert "not available" in result.results[0].error
    
    # Test search without service
    search_request = BatchSearchRequest(queries=["test"])
    search_result = await service.batch_search(search_request)
    
    assert search_result.successful_items == 0
    assert search_result.failed_items == 1
    assert search_result.results[0].status == BatchStatus.FAILED
    
    # Test embeddings without service
    embed_result = await service.batch_generate_embeddings(["test"])
    
    assert embed_result.successful_items == 0
    assert embed_result.failed_items == 1


@pytest.mark.asyncio
async def test_get_batch_statistics():
    """Test batch statistics generation."""
    service = BatchOperationsService()
    
    # Create sample results
    results = [
        BatchOperationResult(
            operation_type=BatchOperationType.INGEST,
            total_items=10,
            successful_items=8,
            failed_items=2,
            execution_time_ms=1000.0,
            results=[]
        ),
        BatchOperationResult(
            operation_type=BatchOperationType.SEARCH,
            total_items=5,
            successful_items=5,
            failed_items=0,
            execution_time_ms=500.0,
            results=[]
        ),
        BatchOperationResult(
            operation_type=BatchOperationType.INGEST,
            total_items=5,
            successful_items=4,
            failed_items=1,
            execution_time_ms=750.0,
            results=[]
        )
    ]
    
    stats = await service.get_batch_statistics(results)
    
    assert stats["total_operations"] == 3
    assert stats["total_items"] == 20
    assert stats["total_successful"] == 17
    assert stats["total_failed"] == 3
    assert stats["overall_success_rate"] == 17/20
    assert stats["operations_by_type"]["ingest"] == 2
    assert stats["operations_by_type"]["search"] == 1
    
    # Check performance by type
    ingest_perf = stats["performance_by_type"]["ingest"]
    assert ingest_perf["operations"] == 2
    assert ingest_perf["items"] == 15
    assert ingest_perf["success_rate"] == 12/15  # 8+4 successful out of 10+5


@pytest.mark.asyncio
async def test_batch_size_handling(mock_ingestion_service):
    """Test that large batches are properly split."""
    service = BatchOperationsService(
        ingestion_service=mock_ingestion_service,
        batch_size=3  # Small batch size for testing
    )
    
    # Create 7 documents (should be split into 3, 3, 1)
    documents = [{"content": f"doc {i}", "metadata": {}} for i in range(7)]
    request = BatchIngestionRequest(documents=documents)
    
    result = await service.batch_ingest_documents(request)
    
    assert result.total_items == 7
    assert result.successful_items == 7
    assert len(result.results) == 7
    
    # Verify all documents were processed
    assert mock_ingestion_service.ingest_document.call_count == 7


def test_batch_result_properties():
    """Test BatchOperationResult properties."""
    result = BatchOperationResult(
        operation_type=BatchOperationType.SEARCH,
        total_items=10,
        successful_items=8,
        failed_items=2,
        execution_time_ms=1000.0,
        results=[]
    )
    
    assert result.success_rate == 0.8
    assert result.average_item_time_ms == 100.0
    
    # Test with zero items
    empty_result = BatchOperationResult(
        operation_type=BatchOperationType.SEARCH,
        total_items=0,
        successful_items=0,
        failed_items=0,
        execution_time_ms=0.0,
        results=[]
    )
    
    assert empty_result.success_rate == 1.0
    assert empty_result.average_item_time_ms == 0.0


def test_batch_service_cleanup():
    """Test cleanup of batch service resources."""
    service = BatchOperationsService()
    
    # Should not raise any exceptions
    service.close()
    
    # Calling close multiple times should be safe
    service.close()


@pytest.mark.asyncio
async def test_embedding_batch_failure(mock_embedding_service):
    """Test handling of embedding generation failures."""
    # Configure mock to fail
    mock_embedding_service.generate_embeddings.side_effect = RuntimeError("Embedding failed")
    
    service = BatchOperationsService(
        embedding_service=mock_embedding_service,
        batch_size=2
    )
    
    texts = ["text1", "text2"]
    result = await service.batch_generate_embeddings(texts)
    
    assert result.successful_items == 0
    assert result.failed_items == 2
    assert all(r.status == BatchStatus.FAILED for r in result.results)
    assert all("Embedding failed" in r.error for r in result.results)


@pytest.mark.asyncio 
async def test_search_strategy_mapping(batch_service, mock_search_service):
    """Test that search strategy strings are properly mapped to enums."""
    queries = ["test query"]
    
    # Test different strategy strings
    strategies = ["vector_only", "keyword_only", "hybrid", "graph_enhanced", "invalid"]
    
    for strategy in strategies:
        request = BatchSearchRequest(
            queries=queries,
            search_strategy=strategy
        )
        
        result = await batch_service.batch_search(request)
        
        # Should succeed even with invalid strategy (falls back to hybrid)
        assert result.successful_items == 1
        assert result.failed_items == 0
        
        # Verify search was called
        mock_search_service.search.assert_called()
        
        # Reset mock for next iteration
        mock_search_service.reset_mock()


@pytest.mark.asyncio
async def test_deletion_with_vector_store_fallback(
    batch_service, 
    mock_graph_repository, 
    mock_vector_store
):
    """Test document deletion with vector store fallback method."""
    # Remove the delete_by_document_id method to test fallback
    if hasattr(mock_vector_store, 'delete_by_document_id'):
        delattr(mock_vector_store, 'delete_by_document_id')
    
    # Mock chunks to be deleted
    from graph_rag.domain.models import Chunk
    chunks = [
        Chunk(id="chunk1", document_id="doc1", text="chunk1"),
        Chunk(id="chunk2", document_id="doc1", text="chunk2")
    ]
    mock_graph_repository.get_chunks_by_document_id.return_value = chunks
    
    document_ids = ["doc1"]
    result = await batch_service.batch_delete_documents(document_ids)
    
    assert result.successful_items == 1
    assert result.failed_items == 0
    
    # Verify fallback deletion was used
    mock_graph_repository.get_chunks_by_document_id.assert_called_with("doc1")
    mock_vector_store.delete_chunks.assert_called_with(["chunk1", "chunk2"])