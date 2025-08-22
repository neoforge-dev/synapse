#!/usr/bin/env python3
"""Debug script to test the API's vector store search directly."""

import asyncio
import logging

import requests

from graph_rag.api.dependencies import create_vector_store
from graph_rag.config import get_settings

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_api_vector_store_state():
    """Test the exact vector store instance used by the API."""
    print("=" * 50)
    print("DEBUGGING API VECTOR STORE SEARCH")
    print("=" * 50)

    # First trigger loading by making an API call
    print("1. Triggering vector store loading via API...")
    try:
        response = requests.post(
            "http://localhost:8004/api/v1/query/ask",
            json={"text": "test"},
            timeout=10
        )
        print(f"API trigger response: {response.status_code}")
    except Exception as e:
        print(f"Error triggering API: {e}")

    # Check stats
    print("2. Checking vector store stats...")
    try:
        response = requests.get("http://localhost:8004/api/v1/admin/vector/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"Vector store stats: {stats}")
        else:
            print(f"Stats error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error getting stats: {e}")

    # Now create our own vector store with same settings and test it
    print("3. Creating identical vector store...")
    settings = get_settings()
    our_vector_store = create_vector_store(settings)

    await our_vector_store._ensure_loaded()
    our_size = await our_vector_store.get_vector_store_size()
    print(f"Our vector store size: {our_size}")

    # Test direct search on our vector store
    print("4. Testing direct search on our vector store...")
    our_results = await our_vector_store.search("LinkedIn development practices", top_k=3)
    print(f"Our search returned {len(our_results)} results")
    for i, result in enumerate(our_results[:2]):
        print(f"  Result {i+1}: score={result.score:.4f}, text='{result.chunk.text[:100]}...'")

    # Test with different queries
    queries = [
        "linkedin",
        "development",
        "practices",
        "What are some LinkedIn development practices?",
        "python"
    ]

    print("5. Testing various queries...")
    for query in queries:
        try:
            results = await our_vector_store.search(query, top_k=3)
            print(f"Query '{query}': {len(results)} results")
            if results:
                print(f"  Top score: {results[0].score:.4f}")
        except Exception as e:
            print(f"Query '{query}' failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_vector_store_state())
