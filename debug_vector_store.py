#!/usr/bin/env python3
"""Debug script to test vector store loading and search."""

import asyncio
import logging
from pathlib import Path

from graph_rag.api.dependencies import create_vector_store
from graph_rag.config import get_settings
from graph_rag.infrastructure.vector_stores.shared_persistent_vector_store import (
    SharedPersistentVectorStore,
)
from graph_rag.services.embedding import SentenceTransformerEmbeddingService

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_vector_store():
    """Test vector store loading and search."""
    print("=" * 50)
    print("DEBUGGING VECTOR STORE ISOLATION ISSUE")
    print("=" * 50)

    # Get settings
    settings = get_settings()
    print(f"Vector store type: {settings.vector_store_type}")
    print(f"Vector store path: {settings.vector_store_path}")
    print(f"Storage path exists: {Path(settings.vector_store_path).exists()}")

    # Test creating vector store via API method
    print("\n1. Creating vector store via API method...")
    try:
        api_vector_store = create_vector_store(settings)
        print(f"API vector store type: {type(api_vector_store).__name__}")

        # Test loading
        if hasattr(api_vector_store, '_ensure_loaded'):
            await api_vector_store._ensure_loaded()
            print(f"Load attempted: {api_vector_store._load_attempted}")

        # Check size
        size = await api_vector_store.get_vector_store_size()
        print(f"API vector store size: {size}")

        if size > 0:
            # Test search
            print("\n2. Testing vector search...")
            results = await api_vector_store.search("LinkedIn development practices", top_k=3)
            print(f"Search returned {len(results)} results")
            for i, result in enumerate(results[:2]):
                print(f"  Result {i+1}: score={result.score:.4f}, text_preview='{result.chunk.text[:100]}...'")
        else:
            print("Vector store is empty, skipping search test")

        # Test stats
        if hasattr(api_vector_store, 'stats'):
            stats = await api_vector_store.stats()
            print(f"\nVector store stats: {stats}")

    except Exception as e:
        print(f"Error testing API vector store: {e}")
        import traceback
        traceback.print_exc()

    # Test creating directly
    print("\n3. Creating vector store directly...")
    try:
        embedding_service = SentenceTransformerEmbeddingService(
            model_name=settings.vector_store_embedding_model
        )
        direct_vector_store = SharedPersistentVectorStore(
            embedding_service=embedding_service,
            storage_path=settings.vector_store_path
        )

        await direct_vector_store._ensure_loaded()
        direct_size = await direct_vector_store.get_vector_store_size()
        print(f"Direct vector store size: {direct_size}")

        if direct_size > 0:
            # Test search
            direct_results = await direct_vector_store.search("LinkedIn development practices", top_k=3)
            print(f"Direct search returned {len(direct_results)} results")
            for i, result in enumerate(direct_results[:2]):
                print(f"  Result {i+1}: score={result.score:.4f}, text_preview='{result.chunk.text[:100]}...'")

    except Exception as e:
        print(f"Error testing direct vector store: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_vector_store())
