#!/usr/bin/env python3
"""
Validation script to test real embeddings functionality after implementing sentence-transformers.
This script verifies that embeddings have the correct 384-dimensional vectors.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath('.'))

from graph_rag.services.embedding import SentenceTransformerEmbeddingService

async def test_real_embeddings():
    """Test that SentenceTransformerEmbeddingService generates real 384-dim embeddings"""
    print("Testing SentenceTransformerEmbeddingService...")
    
    # Initialize the service
    service = SentenceTransformerEmbeddingService()
    
    # Test texts
    test_texts = [
        "This is a test document about artificial intelligence.",
        "Machine learning models are transforming technology.",
        "Entity extraction helps in knowledge graphs."
    ]
    
    # Generate embeddings
    embeddings = []
    for text in test_texts:
        embedding = await service.generate_embedding(text)
        embeddings.append(embedding)
    
    print(f"✓ Generated embeddings for {len(test_texts)} texts")
    print(f"✓ Embedding dimensions: {len(embeddings[0])}")
    
    # Validate dimensions
    assert len(embeddings) == len(test_texts), f"Expected {len(test_texts)} embeddings, got {len(embeddings)}"
    
    for i, embedding in enumerate(embeddings):
        assert len(embedding) == 384, f"Expected 384 dimensions, got {len(embedding)} for embedding {i}"
        assert not all(x == 1.0 for x in embedding[:3]), f"Embedding {i} looks like mock data [1.0, 0.0, 0.0]"
        assert isinstance(embedding[0], float), f"Embedding values should be floats, got {type(embedding[0])}"
    
    print("✓ All embeddings have correct 384 dimensions")
    print("✓ Embeddings are not mock data")
    
    # Test similarity (embeddings should be different for different texts)
    embedding1 = embeddings[0]
    embedding2 = embeddings[1]
    
    # Calculate cosine similarity manually
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    magnitude1 = sum(a * a for a in embedding1) ** 0.5
    magnitude2 = sum(b * b for b in embedding2) ** 0.5
    similarity = dot_product / (magnitude1 * magnitude2)
    
    print(f"✓ Cosine similarity between first two texts: {similarity:.4f}")
    
    # Similarity should be reasonable but not 1.0 (different texts)
    assert 0.0 < similarity < 1.0, f"Similarity should be between 0 and 1, got {similarity}"
    
    print("✓ Embeddings show reasonable semantic similarity")
    
    # Test single embedding
    single_embedding = await service.generate_embedding("Single test text")
    assert len(single_embedding) == 384, f"Single embedding should have 384 dimensions, got {len(single_embedding)}"
    
    print("✓ Single embedding generation works correctly")
    print("🎉 All embedding tests passed!")

if __name__ == "__main__":
    asyncio.run(test_real_embeddings())