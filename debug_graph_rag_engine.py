#!/usr/bin/env python3
"""Debug script to test GraphRAGEngine directly."""

import asyncio
import logging
from graph_rag.config import get_settings
from graph_rag.api.dependencies import create_vector_store, create_graph_repository, create_entity_extractor, create_llm_service
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_graph_rag_engine():
    """Test GraphRAGEngine directly."""
    print("=" * 50)
    print("DEBUGGING GRAPHRAGENGINE QUERY FLOW")
    print("=" * 50)
    
    # Get settings
    settings = get_settings()
    
    # Create components like the API does
    print("1. Creating components...")
    vector_store = create_vector_store(settings)
    graph_repository = create_graph_repository(settings)
    entity_extractor = create_entity_extractor(settings)
    llm_service = create_llm_service(settings)
    
    # Create GraphRAGEngine
    print("2. Creating GraphRAGEngine...")
    engine = SimpleGraphRAGEngine(
        graph_store=graph_repository,
        vector_store=vector_store,
        entity_extractor=entity_extractor,
        llm_service=llm_service
    )
    
    # Test vector store loading
    print("3. Testing vector store in engine...")
    await vector_store._ensure_loaded()
    size = await vector_store.get_vector_store_size()
    print(f"Engine vector store size: {size}")
    
    # Test direct vector search through engine's vector store
    print("4. Testing direct vector search through engine...")
    direct_results = await engine._vector_store.search("LinkedIn development practices", top_k=3)
    print(f"Direct vector search through engine returned {len(direct_results)} results")
    for i, result in enumerate(direct_results[:2]):
        print(f"  Result {i+1}: score={result.score:.4f}, text='{result.chunk.text[:100]}...'")
    
    # Test the _retrieve_and_build_context method directly
    print("5. Testing _retrieve_and_build_context...")
    config = {
        "k": 3,
        "include_graph": False,
        "search_type": "vector"
    }
    
    try:
        retrieved_chunks, graph_context = await engine._retrieve_and_build_context(
            "LinkedIn development practices", 
            config
        )
        print(f"_retrieve_and_build_context returned {len(retrieved_chunks)} chunks")
        for i, chunk_data in enumerate(retrieved_chunks[:2]):
            print(f"  Chunk {i+1}: score={chunk_data.score:.4f}, text='{chunk_data.chunk.text[:100]}...'")
        
        # Test the full answer_query method
        print("6. Testing answer_query method...")
        answer = await engine.answer_query(
            "What are some LinkedIn development practices?",
            config
        )
        print(f"Answer: {answer[:200]}...")
        
    except Exception as e:
        print(f"Error in _retrieve_and_build_context: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_graph_rag_engine())