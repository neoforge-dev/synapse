#!/usr/bin/env python3
"""Debug script to test embedding service differences."""

import asyncio
import logging

from graph_rag.api.dependencies import create_embedding_service
from graph_rag.config import get_settings
from graph_rag.services.embedding import SentenceTransformerEmbeddingService

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_embedding_services():
    """Test embedding service differences."""
    print("=" * 50)
    print("DEBUGGING EMBEDDING SERVICE DIFFERENCES")
    print("=" * 50)

    settings = get_settings()

    # Test 1: Direct SentenceTransformerEmbeddingService creation
    print("1. Creating direct SentenceTransformerEmbeddingService...")
    direct_service = SentenceTransformerEmbeddingService(
        model_name=settings.vector_store_embedding_model
    )

    # Test 2: Using API dependencies method
    print("2. Creating via API dependencies...")
    api_service = create_embedding_service(settings)

    # Test both services with the same text
    test_text = "What are some LinkedIn development practices?"

    print("3. Testing direct service...")
    try:
        direct_embedding = await direct_service.encode_query(test_text)
        print(f"Direct embedding length: {len(direct_embedding)}")
        print(f"Direct embedding first 5 values: {direct_embedding[:5]}")
    except Exception as e:
        print(f"Direct service failed: {e}")

    print("4. Testing API service...")
    try:
        if hasattr(api_service, 'encode_query'):
            api_embedding = await api_service.encode_query(test_text)
        else:
            # Fall back to encode method
            api_embedding_list = await api_service.encode([test_text])
            api_embedding = api_embedding_list[0] if api_embedding_list else []

        print(f"API embedding length: {len(api_embedding)}")
        print(f"API embedding first 5 values: {api_embedding[:5]}")

        # Compare if both embeddings are similar
        if 'direct_embedding' in locals() and len(direct_embedding) == len(api_embedding):
            import numpy as np
            similarity = np.dot(direct_embedding, api_embedding) / (
                np.linalg.norm(direct_embedding) * np.linalg.norm(api_embedding)
            )
            print(f"Embedding similarity: {similarity:.6f}")

    except Exception as e:
        print(f"API service failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 5: Service type comparison
    print("5. Service type comparison...")
    print(f"Direct service type: {type(direct_service).__name__}")
    print(f"API service type: {type(api_service).__name__}")
    print(f"Settings embedding provider: {settings.embedding_provider}")
    print(f"Settings vector store embedding model: {settings.vector_store_embedding_model}")

if __name__ == "__main__":
    asyncio.run(test_embedding_services())
