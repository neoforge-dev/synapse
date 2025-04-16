import logging
from typing import Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from graph_rag.core.vector_store import VectorStore
from graph_rag.models import Chunk

logger = logging.getLogger(__name__)

class SimpleVectorStore(VectorStore):
    """A simple in-memory vector store using sentence-transformers and numpy."""

    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        try:
            logger.info(f"Loading sentence-transformer model: {embedding_model_name}")
            self._model = SentenceTransformer(embedding_model_name)
            logger.info("Sentence-transformer model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer model '{embedding_model_name}': {e}", exc_info=True)
            raise RuntimeError(f"Could not load embedding model: {embedding_model_name}") from e
            
        self._chunks: List[Chunk] = []
        self._embeddings: Optional[np.ndarray] = None
        self._chunk_id_to_index: Dict[str, int] = {}

    def add_chunks(self, chunks: List[Chunk]):
        """Adds chunks and computes their embeddings."""
        if not chunks:
            return
            
        logger.info(f"Adding {len(chunks)} chunks to SimpleVectorStore.")
        new_chunk_texts = [chunk.text for chunk in chunks if chunk.id not in self._chunk_id_to_index]
        new_chunks_to_add = [chunk for chunk in chunks if chunk.id not in self._chunk_id_to_index]
        
        if not new_chunks_to_add:
            logger.info("No new chunks to add (all provided chunk IDs already exist).")
            return

        logger.debug(f"Generating embeddings for {len(new_chunk_texts)} new chunks...")
        try:
            new_embeddings = self._model.encode(new_chunk_texts, show_progress_bar=False)
        except Exception as e:
             logger.error(f"Failed to encode chunk texts: {e}", exc_info=True)
             # Decide handling: skip adding these chunks or raise?
             # For simplicity, log error and don't add the problematic batch.
             logger.warning("Skipping adding chunks due to embedding error.")
             return
             
        start_index = len(self._chunks)
        for i, chunk in enumerate(new_chunks_to_add):
            chunk_index = start_index + i
            self._chunks.append(chunk)
            self._chunk_id_to_index[chunk.id] = chunk_index
            
        if self._embeddings is None:
            self._embeddings = new_embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, new_embeddings])
            
        logger.info(f"Successfully added {len(new_chunks_to_add)} new chunks. Total chunks: {len(self._chunks)}")

    def search(self, query_text: str, k: int = 5) -> List[Chunk]:
        """Performs cosine similarity search."""
        if not self._chunks or self._embeddings is None:
            logger.warning("Search called on empty or uninitialized SimpleVectorStore.")
            return []
            
        if k <= 0:
            raise ValueError("k must be a positive integer")
            
        logger.debug(f"Performing vector search for query: '{query_text[:50]}...' with k={k}")
        try:
            query_embedding = self._model.encode([query_text], show_progress_bar=False)
        except Exception as e:
             logger.error(f"Failed to encode query text: {e}", exc_info=True)
             return [] # Return empty on query encoding error
             
        # Calculate cosine similarities
        similarities = cosine_similarity(query_embedding, self._embeddings)[0] # Get similarities for the single query
        
        # Get top k indices (handles k > number of chunks)
        num_results = min(k, len(self._chunks))
        # Get indices of the highest scores in descending order
        top_k_indices = np.argsort(similarities)[::-1][:num_results]
        
        # Retrieve corresponding chunks
        results = [self._chunks[i] for i in top_k_indices]
        result_similarities = [similarities[i] for i in top_k_indices]
        
        logger.info(f"Vector search found {len(results)} chunks. Top score: {result_similarities[0] if results else 'N/A'}")
        # Optionally add similarity score to chunk metadata? Requires modifying Chunk model or returning different structure.
        # for i, chunk in enumerate(results):
        #     chunk.metadata['similarity_score'] = result_similarities[i]
            
        return results

    def clear(self):
        """Clears all stored chunks and embeddings."""
        self._chunks = []
        self._embeddings = None
        self._chunk_id_to_index = {}
        logger.info("SimpleVectorStore cleared.") 