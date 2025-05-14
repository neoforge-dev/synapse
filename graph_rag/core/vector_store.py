from graph_rag.models import Chunk  # Assuming Chunks have optional embeddings

# Type alias for embedding vector
EmbeddingVector = list[float]
# Type alias for search result (e.g., chunk ID and score)
SearchResult = tuple[str, float]


class MockVectorStore:
    """In-memory mock implementation of VectorStore for testing."""

    def __init__(self):
        from loguru import logger

        self.chunks: list[Chunk] = []
        logger.info("MockVectorStore initialized.")

    def add_chunks(self, chunks: list[Chunk]):
        from loguru import logger

        self.chunks.extend(chunks)
        logger.debug(f"MockVectorStore: Added {len(chunks)} chunks.")

    async def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        # Simple keyword matching for mock search
        results = []
        for chunk in self.chunks:
            # Use content attribute instead of text
            if query.lower() in chunk.content.lower():
                # Assign a mock score (e.g., 1.0 for match, decay could be added)
                results.append((chunk, 1.0))

        # Sort by score (descending) and return top_k
        # Since score is mock, just take the first top_k found
        return results[:top_k]

    async def get_all_chunks(self) -> list[Chunk]:
        from loguru import logger

        logger.info(f"MockVectorStore: Adding {len(chunks)} chunks.")
        self.calls["add_chunks"].append(chunks)
        for chunk in chunks:
            if chunk.id in self.chunks:
                logger.warning(
                    f"Chunk ID {chunk.id} already exists in MockVectorStore. Overwriting."
                )
            self.chunks[chunk.id] = chunk
            # In a real store, embedding generation might happen here if not already present
            # For the mock, we assume embeddings are provided or handled elsewhere

    def search(
        self, query_embedding: EmbeddingVector, top_k: int = 5
    ) -> list[SearchResult]:
        from loguru import logger

        logger.info(f"MockVectorStore: Performing search with top_k={top_k}.")
        self.calls["search"].append((query_embedding, top_k))

        # Mock search logic: return some predefined results or based on simple criteria
        # This is highly simplified and doesn't actually use the query_embedding
        results: list[SearchResult] = []

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
        from loguru import logger

        """Clears the mock store for test isolation."""
        self.chunks = {}
        self.calls = {"add_chunks": [], "search": []}
        logger.info("MockVectorStore cleared.")
