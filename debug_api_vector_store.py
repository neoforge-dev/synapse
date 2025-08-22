#!/usr/bin/env python3
"""
Debug script to test what the API vector store is seeing.
"""
import asyncio
import logging
from pathlib import Path

from graph_rag.api.dependencies import create_vector_store
from graph_rag.config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_api_vector_store():
    """Test the API vector store configuration and data loading."""

    # Get the same settings the API uses
    settings = get_settings()

    logger.info(f"Settings vector_store_type: {settings.vector_store_type}")
    logger.info(f"Settings vector_store_path: {settings.vector_store_path}")
    logger.info(f"Settings simple_vector_store_persistent: {getattr(settings, 'simple_vector_store_persistent', True)}")
    logger.info(f"Settings embedding_provider: {settings.embedding_provider}")

    # Check if vector store files exist
    storage_path = Path(settings.vector_store_path)
    vectors_file = storage_path / "vectors.pkl"
    metadata_file = storage_path / "metadata.json"

    logger.info(f"Storage path: {storage_path}")
    logger.info(f"Storage path exists: {storage_path.exists()}")
    logger.info(f"Vectors file exists: {vectors_file.exists()}")
    logger.info(f"Metadata file exists: {metadata_file.exists()}")

    # Create vector store using same factory as API
    logger.info("Creating vector store using API factory...")
    vector_store = create_vector_store(settings)

    logger.info(f"Vector store type: {type(vector_store).__name__}")
    logger.info(f"Vector store storage path: {getattr(vector_store, 'storage_path', 'N/A')}")

    # Try to get stats
    try:
        if hasattr(vector_store, 'get_vector_store_size'):
            size = await vector_store.get_vector_store_size()
            logger.info(f"Vector store size: {size}")

        if hasattr(vector_store, 'stats'):
            stats = await vector_store.stats()
            logger.info(f"Vector store stats: {stats}")
    except Exception as e:
        logger.error(f"Error getting vector store stats: {e}")

    # Try a simple search
    try:
        logger.info("Attempting vector store search...")
        if hasattr(vector_store, 'search'):
            results = await vector_store.search("LinkedIn", top_k=3)
            logger.info(f"Search returned {len(results)} results")
            for i, result in enumerate(results):
                logger.info(f"Result {i}: score={getattr(result, 'score', 'N/A')}, chunk_id={getattr(result.chunk if hasattr(result, 'chunk') else result, 'id', 'N/A')}")
        else:
            logger.warning("Vector store does not have search method")
    except Exception as e:
        logger.error(f"Error during search: {e}", exc_info=True)

    # Check _ensure_loaded functionality specifically
    if hasattr(vector_store, '_ensure_loaded'):
        logger.info("Testing _ensure_loaded method...")
        try:
            await vector_store._ensure_loaded()
            logger.info(f"After _ensure_loaded: {len(vector_store.vectors)} vectors, {len(vector_store.documents)} documents")
        except Exception as e:
            logger.error(f"Error in _ensure_loaded: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_api_vector_store())
