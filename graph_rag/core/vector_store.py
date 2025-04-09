import logging
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any

from graph_rag.models import Chunk # Assuming Chunks have optional embeddings

logger = logging.getLogger(__name__)

# Type alias for embedding vector
EmbeddingVector = List[float]
# Type alias for search result (e.g., chunk ID and score)
SearchResult = Tuple[str, float]

class VectorStore(ABC):
    """Abstract base class for storing and searching vector embeddings."""

    @abstractmethod
    def add_chunks(self, chunks: List[Chunk]):
        """Adds chunks (potentially with embeddings) to the vector store."""
        pass

    @abstractmethod
    def search(self, query_embedding: EmbeddingVector, top_k: int = 5) -> List[SearchResult]:
        """Searches for chunks with embeddings similar to the query embedding."""
        pass
        
    # Optional: Method to get embeddings for text
    # @abstractmethod
    # def get_embedding(self, text: str) -> EmbeddingVector:
    #    pass

class MockVectorStore(VectorStore):
    """In-memory mock implementation of VectorStore for testing."""
    
    def __init__(self):
        # Store chunks by ID, assuming they might have embeddings already
        self.chunks: Dict[str, Chunk] = {}
        self.calls: Dict[str, List[Any]] = {
            "add_chunks": [],
            "search": []
        }
        logger.info("MockVectorStore initialized.")

    def add_chunks(self, chunks: List[Chunk]):
        logger.info(f"MockVectorStore: Adding {len(chunks)} chunks.")
        self.calls["add_chunks"].append(chunks)
        for chunk in chunks:
            if chunk.id in self.chunks:
                 logger.warning(f"Chunk ID {chunk.id} already exists in MockVectorStore. Overwriting.")
            self.chunks[chunk.id] = chunk
            # In a real store, embedding generation might happen here if not already present
            # For the mock, we assume embeddings are provided or handled elsewhere

    def search(self, query_embedding: EmbeddingVector, top_k: int = 5) -> List[SearchResult]:
        logger.info(f"MockVectorStore: Performing search with top_k={top_k}.")
        self.calls["search"].append((query_embedding, top_k))
        
        # Mock search logic: return some predefined results or based on simple criteria
        # This is highly simplified and doesn't actually use the query_embedding
        results: List[SearchResult] = []
        
        # Example: return the first `top_k` chunks that have an embedding
        count = 0
        for chunk_id, chunk in self.chunks.items():
            if chunk.embedding is not None:
                 # Return chunk ID and a mock score (e.g., inverse order)
                 results.append((chunk_id, 1.0 / (count + 1)))
                 count += 1
                 if count >= top_k:
                     break
                     
        logger.info(f"MockVectorStore: Search returned {len(results)} results.")
        return results
        
    def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Helper to retrieve a chunk by ID (useful for tests)."""
        return self.chunks.get(chunk_id)

    def clear(self):
        """Clears the mock store for test isolation."""
        self.chunks = {}
        self.calls = {"add_chunks": [], "search": []}
        logger.info("MockVectorStore cleared.") 