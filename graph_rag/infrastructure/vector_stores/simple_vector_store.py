import asyncio
import logging
import os
import pickle
from typing import Optional, List, Dict, Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from starlette.concurrency import run_in_threadpool
import faiss

# Corrected import path for ChunkData and VectorStore protocol
from graph_rag.core.interfaces import ChunkData, EmbeddingService, VectorStore, SearchResultData
# We still need Chunk model for internal representation maybe? Let's keep it for now
# Or maybe ChunkData is enough. Review if Chunk is actually used.
from graph_rag.models import Chunk # Keeping this for now, review usage later

logger = logging.getLogger(__name__)


class SimpleVectorStore(VectorStore):
    """A simple in-memory vector store implementation."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.dimension = embedding_service.get_embedding_dimension()
        self.vectors: List[np.ndarray] = []
        self.metadata: List[dict] = []
        self.documents: List[str] = [] # Store original document text
        self.chunk_ids: List[str] = [] # Store chunk IDs for retrieval by ID
        self.lock = asyncio.Lock()

    async def add_chunks(self, chunks: List[ChunkData]) -> None:
        """
        Add chunks to vector store - implementation of the VectorStore protocol method.
        
        Args:
            chunks: List of ChunkData objects to add to the vector store
        """
        logger.debug(f"Add chunks method called with {len(chunks)} chunks")
        await self.ingest_chunks(chunks)

    async def search_similar_chunks(self, query_vector: List[float], limit: int = 10, threshold: Optional[float] = None) -> List[SearchResultData]:
        """
        Searches for chunks with embeddings similar to the query vector.
        Implementation of the VectorStore protocol method.
        
        Args:
            query_vector: The query vector to compare against
            limit: Maximum number of results to return
            threshold: Optional similarity threshold (0-1), results below this are filtered out
            
        Returns:
            List of SearchResultData objects
        """
        logger.debug(f"Searching for similar chunks with vector (dim={len(query_vector)})")
        if not self.vectors:
            logger.warning("Vector store is empty, cannot perform search.")
            return []

        query_embedding = np.array(query_vector).reshape(1, -1)
        if query_embedding.shape[1] != self.dimension:
             logger.error(
                f"Query embedding dimension mismatch: Expected {self.dimension}, got {query_embedding.shape[1]}"
            )
             return []

        async with self.lock:
            if not self.vectors: # Re-check after acquiring lock
                return []
                
            # Calculate cosine similarities
            vector_matrix = np.array(self.vectors)
            if vector_matrix.ndim == 1:
                vector_matrix = vector_matrix.reshape(1, -1)
            elif vector_matrix.ndim != 2:
                logger.error(f"Unexpected vector matrix dimensions: {vector_matrix.ndim}")
                return []
                
            similarities = cosine_similarity(query_embedding, vector_matrix)[0]

            # Apply threshold if specified
            if threshold is not None:
                # Create mask of indices where similarity >= threshold
                mask = similarities >= threshold
                # Get indices that meet threshold
                indices = np.where(mask)[0]
                # Sort these indices by similarity (descending)
                top_indices = indices[np.argsort(similarities[indices])[::-1]]
                # Limit results
                top_indices = top_indices[:limit]
            else:
                # No threshold, just get top k results
                actual_limit = min(limit, len(similarities))
                if actual_limit <= 0:
                    return []
                top_indices = np.argsort(similarities)[-actual_limit:][::-1]

            results = []
            for i in top_indices:
                score = float(similarities[i])
                chunk_data = ChunkData(
                    id=self.chunk_ids[i] if i < len(self.chunk_ids) else f"chunk_{i}",
                    text=self.documents[i],
                    document_id=self.metadata[i].get("document_id", "unknown"),
                    metadata=self.metadata[i],
                    score=score
                )
                search_result = SearchResultData(chunk=chunk_data, score=score)
                results.append(search_result)

        logger.debug(f"Vector similarity search returned {len(results)} results.")
        return results

    async def get_chunk_by_id(self, chunk_id: str) -> Optional[ChunkData]:
        """
        Retrieves a chunk by its ID.
        Implementation of the VectorStore protocol method (optional).
        
        Args:
            chunk_id: The ID of the chunk to retrieve
            
        Returns:
            ChunkData if found, None otherwise
        """
        logger.debug(f"Looking for chunk with ID: {chunk_id}")
        async with self.lock:
            try:
                index = self.chunk_ids.index(chunk_id)
                return ChunkData(
                    id=chunk_id,
                    text=self.documents[index],
                    document_id=self.metadata[index].get("document_id", "unknown"),
                    metadata=self.metadata[index],
                    embedding=self.vectors[index].tolist() if index < len(self.vectors) else None
                )
            except ValueError:
                logger.debug(f"Chunk with ID {chunk_id} not found")
                return None
            except Exception as e:
                logger.error(f"Error retrieving chunk {chunk_id}: {e}")
                return None

    async def delete_chunks(self, chunk_ids: List[str]) -> None:
        """
        Deletes chunks by their IDs.
        Implementation of the VectorStore protocol method (optional).
        
        Args:
            chunk_ids: List of chunk IDs to delete
        """
        if not chunk_ids:
            return
            
        logger.debug(f"Deleting {len(chunk_ids)} chunks from vector store")
        async with self.lock:
            indices_to_remove = []
            for chunk_id in chunk_ids:
                try:
                    index = self.chunk_ids.index(chunk_id)
                    indices_to_remove.append(index)
                except ValueError:
                    logger.debug(f"Chunk with ID {chunk_id} not found for deletion")
            
            # Sort indices in descending order to avoid index shifting when removing
            indices_to_remove.sort(reverse=True)
            
            # Remove from all lists
            for index in indices_to_remove:
                if index < len(self.chunk_ids):
                    self.chunk_ids.pop(index)
                if index < len(self.vectors):
                    self.vectors.pop(index)
                if index < len(self.metadata):
                    self.metadata.pop(index)
                if index < len(self.documents):
                    self.documents.pop(index)
            
            logger.info(f"Removed {len(indices_to_remove)} chunks from vector store")

    async def delete_store(self) -> None:
        """
        Deletes the entire vector store collection.
        Implementation of the VectorStore protocol method (optional).
        """
        logger.info("Deleting entire vector store")
        await self.clear_vector_store()

    async def search(self, query_text: str, top_k: int = 5, search_type: str = "vector") -> List[ChunkData]:
        """
        Compatibility adapter method to maintain backward compatibility with older API.
        Calls either vector_search or keyword_search based on search_type parameter.
        
        Args:
            query_text: The search query text
            top_k: Number of results to return
            search_type: Either "vector" or "keyword" to determine search method
            
        Returns:
            List of ChunkData objects
        """
        logger.debug(f"Search adapter called with search_type={search_type}, query='{query_text[:50]}...'")
        
        if search_type.lower() == "keyword":
            search_results = await self.keyword_search(query_text, k=top_k)
        else:  # Default to vector search for any other value
            search_results = await self.vector_search(query_text, k=top_k)
            
        # Convert result tuples (ChunkData, score) to just ChunkData objects
        # Note that the score is stored in each ChunkData object's score field
        return [result[0] for result in search_results]

    async def ingest_chunks(self, chunks: List[ChunkData]):
        """Ingests chunks into the vector store."""
        logger.info(f"Ingesting {len(chunks)} chunks...")
        if not chunks:
            logger.warning("No chunks provided for ingestion.")
            return

        # Extract texts and metadata
        texts = [chunk.text for chunk in chunks]
        metadata_list = [{} if chunk.metadata is None else chunk.metadata for chunk in chunks]
        chunk_ids = [chunk.id for chunk in chunks]

        # Check if embedding service requires async
        if asyncio.iscoroutinefunction(self.embedding_service.encode):
            embeddings = await self.embedding_service.encode(texts)
        else:
            # Run synchronous embedding function in a thread pool
            embeddings = await run_in_threadpool(self.embedding_service.encode, texts)

        async with self.lock:
            for i, chunk in enumerate(chunks):
                embedding = embeddings[i] if i < len(embeddings) else None
                if embedding is not None:
                    if len(embedding) != self.dimension:
                        logger.error(
                            f"Embedding dimension mismatch: Expected {self.dimension}, got {len(embedding)} for chunk {i}"
                        )
                        # Handle mismatch: Skip, pad, truncate, or raise error
                        # For now, we'll skip this chunk
                        continue
                    self.vectors.append(np.array(embedding))
                    self.metadata.append(metadata_list[i])
                    self.documents.append(chunk.text)
                    self.chunk_ids.append(chunk.id)
                else:
                    logger.warning(f"Failed to generate embedding for chunk {i}")

        logger.info(f"Finished ingestion. Total vectors in store: {len(self.vectors)}")

    async def vector_search(self, query: str, k: int = 5) -> List[tuple[ChunkData, float]]:
        """Performs vector search using cosine similarity."""
        logger.debug(f"Performing vector search for query: '{query[:50]}...'")
        if not self.vectors:
            logger.warning("Vector store is empty, cannot perform search.")
            return []

        # Get query embedding
        if asyncio.iscoroutinefunction(self.embedding_service.encode):
            query_embedding_list = await self.embedding_service.encode([query])
        else:
            query_embedding_list = await run_in_threadpool(self.embedding_service.encode, [query])
        
        if not query_embedding_list or query_embedding_list[0] is None:
            logger.error("Failed to generate embedding for the query.")
            return []

        query_embedding = np.array(query_embedding_list[0]).reshape(1, -1)
        if query_embedding.shape[1] != self.dimension:
             logger.error(
                f"Query embedding dimension mismatch: Expected {self.dimension}, got {query_embedding.shape[1]}"
            )
             return []

        async with self.lock:
            if not self.vectors: # Re-check after acquiring lock
                return []
            # Calculate cosine similarities
            # Ensure vectors is a 2D array
            vector_matrix = np.array(self.vectors)
            if vector_matrix.ndim == 1:
                # This might happen if only one vector exists and wasn't properly nested
                vector_matrix = vector_matrix.reshape(1, -1)
            elif vector_matrix.ndim != 2:
                logger.error(f"Unexpected vector matrix dimensions: {vector_matrix.ndim}")
                return []
                
            similarities = cosine_similarity(query_embedding, vector_matrix)[0]

            # Get top k results
            # Ensure k is not greater than the number of vectors
            actual_k = min(k, len(similarities))
            if actual_k <= 0:
                return []
                
            top_k_indices = np.argsort(similarities)[-actual_k:][::-1]

            results = []
            for i in top_k_indices:
                score = similarities[i]
                # Reconstruct ChunkData (or similar object)
                # Assuming metadata contains necessary info like document_id, chunk_id
                chunk_data = ChunkData(
                    id=self.chunk_ids[i] if i < len(self.chunk_ids) else f"chunk_{i}",
                    text=self.documents[i],
                    document_id=self.metadata[i].get("document_id", "unknown"),
                    metadata=self.metadata[i],
                    score=float(score)
                )
                results.append((chunk_data, float(score))) # Ensure score is float

        logger.debug(f"Vector search returned {len(results)} results.")
        return results

    async def keyword_search(self, query: str, k: int = 5) -> List[tuple[ChunkData, float]]:
        """Performs simple keyword search (case-insensitive)."""
        logger.debug(f"Performing keyword search for query: '{query[:50]}...'")
        query_lower = query.lower()
        results = []
        async with self.lock:
            for i, doc_text in enumerate(self.documents):
                if query_lower in doc_text.lower():
                    # Score based on presence (simple scoring)
                    # In a real scenario, TF-IDF or BM25 would be better
                    score = 1.0 # Simple score for keyword match
                    chunk_data = ChunkData(
                        id=self.chunk_ids[i] if i < len(self.chunk_ids) else f"chunk_{i}",
                        text=doc_text,
                        document_id=self.metadata[i].get("document_id", "unknown"),
                        metadata=self.metadata[i],
                        score=score
                    )
                    results.append((chunk_data, score))

            # Sort results by score (though all are 1.0 here)
            # In a more complex scoring system, this would be meaningful
            results.sort(key=lambda item: item[1], reverse=True)

            # Get top k results
            actual_k = min(k, len(results))
            top_results = results[:actual_k]

        logger.debug(f"Keyword search returned {len(top_results)} results.")
        return top_results

    async def get_vector_store_size(self) -> int:
        """Returns the number of vectors in the store."""
        async with self.lock:
            return len(self.vectors)

    async def clear_vector_store(self):
        """Clears all data from the vector store."""
        async with self.lock:
            self.vectors = []
            self.metadata = []
            self.documents = []
            self.chunk_ids = []
        logger.info("SimpleVectorStore cleared.")