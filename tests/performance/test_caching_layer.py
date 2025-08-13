"""Test performance improvements from caching layer using TDD approach."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_graph_query_caching_improves_performance():
    """Test that repeated graph queries are significantly faster with caching."""
    from graph_rag.infrastructure.cache.query_cache import QueryCache
    
    # Mock expensive graph operation
    call_count = 0
    async def expensive_graph_query(query, params):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate expensive operation
        return {"nodes": [{"id": "test"}], "edges": []}
    
    cache = QueryCache()
    
    # First call should hit the expensive operation
    start_time = time.time()
    result1 = await cache.get_or_compute("graph:test_query", expensive_graph_query, "MATCH (n) RETURN n", {})
    first_call_time = time.time() - start_time
    
    # Second call should be much faster (cached)
    start_time = time.time()
    result2 = await cache.get_or_compute("graph:test_query", expensive_graph_query, "MATCH (n) RETURN n", {})
    second_call_time = time.time() - start_time
    
    # Assertions
    assert result1 == result2
    assert call_count == 1  # Expensive operation called only once
    assert second_call_time < first_call_time / 10  # At least 10x faster
    assert first_call_time >= 0.1  # First call took expected time
    assert second_call_time < 0.01  # Second call was fast


@pytest.mark.asyncio
async def test_embedding_caching_prevents_recomputation():
    """Test that embeddings are cached to prevent expensive recomputation."""
    from graph_rag.infrastructure.cache.embedding_cache import EmbeddingCache
    
    # Mock expensive embedding computation
    compute_count = 0
    async def expensive_embed(text):
        nonlocal compute_count
        compute_count += 1
        await asyncio.sleep(0.05)  # Simulate model inference
        return [0.1, 0.2, 0.3]  # Mock embedding
    
    cache = EmbeddingCache()
    
    # Same text should only be embedded once
    text = "This is a test document for embedding"
    
    start_time = time.time()
    embedding1 = await cache.get_or_compute(text, expensive_embed, text)
    first_time = time.time() - start_time
    
    start_time = time.time()
    embedding2 = await cache.get_or_compute(text, expensive_embed, text)
    second_time = time.time() - start_time
    
    # Assertions
    assert embedding1 == embedding2
    assert compute_count == 1  # Embedding computed only once
    assert second_time < first_time / 5  # Much faster second time
    assert embedding1 == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_vector_search_result_caching():
    """Test that vector search results are cached for performance."""
    from graph_rag.infrastructure.cache.search_cache import SearchCache
    
    # Mock expensive vector search
    search_count = 0
    async def expensive_vector_search(query_vector, top_k):
        nonlocal search_count
        search_count += 1
        await asyncio.sleep(0.08)  # Simulate FAISS search
        return [{"id": "doc1", "score": 0.9}, {"id": "doc2", "score": 0.8}]
    
    cache = SearchCache()
    query_vector = [0.1, 0.2, 0.3, 0.4]
    
    # First search
    start_time = time.time()
    results1 = await cache.get_or_compute(
        f"vector_search:{hash(tuple(query_vector))}:5",
        expensive_vector_search,
        query_vector, 5
    )
    first_time = time.time() - start_time
    
    # Second search with same parameters
    start_time = time.time()
    results2 = await cache.get_or_compute(
        f"vector_search:{hash(tuple(query_vector))}:5",
        expensive_vector_search,
        query_vector, 5
    )
    second_time = time.time() - start_time
    
    # Assertions
    assert results1 == results2
    assert search_count == 1  # Search performed only once
    assert second_time < first_time / 5  # Cached result much faster


@pytest.mark.asyncio
async def test_cache_invalidation_on_data_changes():
    """Test that cache is properly invalidated when underlying data changes."""
    from graph_rag.infrastructure.cache.cache_manager import CacheManager
    
    cache_manager = CacheManager()
    
    # Cache some query result
    await cache_manager.set("graph:node123", {"data": "original"}, ttl=300)
    
    # Verify it's cached
    cached_result = await cache_manager.get("graph:node123")
    assert cached_result == {"data": "original"}
    
    # Simulate data change (document update/delete)
    await cache_manager.invalidate_pattern("graph:node123*")
    
    # Verify cache is cleared
    invalidated_result = await cache_manager.get("graph:node123")
    assert invalidated_result is None


def test_cache_configuration_supports_redis():
    """Test that caching can be configured to use Redis for production."""
    from graph_rag.config import get_settings
    
    # Mock Redis configuration
    with patch.dict('os.environ', {
        'SYNAPSE_CACHE_TYPE': 'redis',
        'SYNAPSE_REDIS_URL': 'redis://localhost:6379/0'
    }):
        settings = get_settings()
        assert hasattr(settings, 'cache_type')
        assert hasattr(settings, 'redis_url')


@pytest.mark.asyncio
async def test_concurrent_cache_access_thread_safe():
    """Test that cache handles concurrent access safely."""
    from graph_rag.infrastructure.cache.query_cache import QueryCache
    
    cache = QueryCache()
    
    # Simulate concurrent access to same cache key
    async def worker(worker_id):
        result = await cache.get_or_compute(
            "concurrent_test",
            lambda: {"worker": worker_id, "timestamp": time.time()},
        )
        return result
    
    # Run multiple workers concurrently
    tasks = [worker(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    # All workers should get the same cached result
    first_result = results[0]
    for result in results[1:]:
        assert result == first_result