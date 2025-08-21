#!/usr/bin/env python3
"""
Debug script to test vector store loading directly using the same process as API.
"""
import asyncio
import logging
from graph_rag.config import get_settings
from graph_rag.api.dependencies import create_vector_store

# Set up logging to see debug messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_vector_store_loading():
    """Test the vector store loading process step by step."""
    
    logger.info("=== Testing Vector Store Loading Process ===")
    
    # Get settings (same as API)
    settings = get_settings()
    logger.info(f"Settings vector_store_path: {settings.vector_store_path}")
    logger.info(f"Settings vector_store_type: {settings.vector_store_type}")
    logger.info(f"Settings simple_vector_store_persistent: {getattr(settings, 'simple_vector_store_persistent', True)}")
    
    # Create vector store using same factory as API
    logger.info("Creating vector store using API factory...")
    vector_store = create_vector_store(settings)
    logger.info(f"Created vector store: {type(vector_store).__name__}")
    logger.info(f"Storage path: {getattr(vector_store, 'storage_path', 'N/A')}")
    
    # Check initial state
    logger.info(f"Initial vector count: {len(getattr(vector_store, 'vectors', []))}")
    logger.info(f"Load attempted flag: {getattr(vector_store, '_load_attempted', 'N/A')}")
    
    # Force _ensure_loaded call
    logger.info("Calling _ensure_loaded manually...")
    if hasattr(vector_store, '_ensure_loaded'):
        await vector_store._ensure_loaded()
    
    # Check state after loading attempt
    logger.info(f"Vector count after _ensure_loaded: {len(getattr(vector_store, 'vectors', []))}")
    logger.info(f"Documents count: {len(getattr(vector_store, 'documents', []))}")
    logger.info(f"Chunk IDs count: {len(getattr(vector_store, 'chunk_ids', []))}")
    
    # Try a stats call
    if hasattr(vector_store, 'stats'):
        stats = await vector_store.stats()
        logger.info(f"Stats method result: {stats}")
    
    # Try a search
    if hasattr(vector_store, 'search'):
        logger.info("Attempting search...")
        try:
            results = await vector_store.search("test", top_k=3)
            logger.info(f"Search returned {len(results)} results")
            if results:
                logger.info(f"First result score: {results[0].score}")
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_vector_store_loading())