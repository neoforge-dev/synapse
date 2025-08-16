#!/usr/bin/env python3
"""
Fix vector store embeddings by regenerating embeddings for all chunks.

This script identifies chunks that are missing embeddings and regenerates them.
"""

import asyncio
import logging

from graph_rag.api.dependencies import (
    create_embedding_service, 
    create_graph_repository, 
    create_vector_store
)
from graph_rag.config import get_settings
from graph_rag.core.interfaces import ChunkData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_embeddings():
    """Fix embedding consistency between graph store and vector store."""
    settings = get_settings()
    
    # Create services
    logger.info("Initializing services...")
    graph_repo = create_graph_repository(settings)
    vector_store = create_vector_store(settings)
    embedding_service = create_embedding_service(settings)
    
    # Get all chunks from graph store
    logger.info("Fetching all chunks from graph store...")
    try:
        # Query all chunks
        query = "MATCH (c:Chunk) RETURN c.id as id, c.text as text, c.document_id as document_id, c.metadata as metadata"
        rows = await graph_repo.execute_query(query)
        
        logger.info(f"Found {len(rows)} chunks in graph store")
        
        # Convert to ChunkData objects
        chunks_to_embed = []
        for row in rows:
            if isinstance(row, dict):
                chunk_id = row.get("id", "")
                text = row.get("text", "")
                document_id = row.get("document_id", "")
                metadata = row.get("metadata", {})
            else:
                # Handle row as tuple/list
                values = list(row.values()) if hasattr(row, 'values') else list(row)
                chunk_id = str(values[0]) if len(values) > 0 else ""
                text = str(values[1]) if len(values) > 1 else ""
                document_id = str(values[2]) if len(values) > 2 else ""
                metadata = values[3] if len(values) > 3 and isinstance(values[3], dict) else {}
            
            if chunk_id and text:
                chunks_to_embed.append(ChunkData(
                    id=chunk_id,
                    text=text,
                    document_id=document_id,
                    metadata=metadata or {},
                    embedding=None
                ))
        
        logger.info(f"Prepared {len(chunks_to_embed)} chunks for embedding generation")
        
        # Generate embeddings in batches
        batch_size = 50
        total_processed = 0
        
        for i in range(0, len(chunks_to_embed), batch_size):
            batch = chunks_to_embed[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} chunks")
            
            # Generate embeddings for this batch
            for chunk in batch:
                if chunk.text.strip():  # Only embed non-empty text
                    try:
                        embedding = await embedding_service.generate_embedding(chunk.text)
                        chunk.embedding = embedding
                        total_processed += 1
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for chunk {chunk.id}: {e}")
            
            # Add batch to vector store
            chunks_with_embeddings = [c for c in batch if c.embedding is not None]
            if chunks_with_embeddings:
                try:
                    await vector_store.add_chunks(chunks_with_embeddings)
                    logger.info(f"Added {len(chunks_with_embeddings)} chunks to vector store")
                except Exception as e:
                    logger.error(f"Failed to add batch to vector store: {e}")
        
        logger.info(f"✅ Successfully processed {total_processed} chunks")
        
        # Verify the fix
        if hasattr(vector_store, "stats"):
            stats = await vector_store.stats()
            logger.info(f"Vector store now contains: {stats.get('vectors', 0)} vectors")
        
    except Exception as e:
        logger.error(f"Error during embedding fix: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(fix_embeddings())