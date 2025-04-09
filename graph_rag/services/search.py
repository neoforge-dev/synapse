from pydantic import BaseModel
from typing import List

from graph_rag.infrastructure.repositories.graph_repository import GraphRepository
from graph_rag.domain.models import Chunk
from graph_rag.services.embedding import EmbeddingService


class SearchResult(BaseModel):
    """Represents a single search result, typically a chunk."""
    chunk_id: str
    document_id: str
    content: str
    score: float  # Relevance score (e.g., keyword match, similarity)


class SearchService:
    """Service for performing search operations over the graph."""
    
    def __init__(self, repository: GraphRepository):
        self.repository = repository
        self.embedding_service = EmbeddingService
        
    async def search_chunks(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search for relevant chunks based on a query string.
        
        Args:
            query: The search query string.
            limit: Maximum number of results to return.
            
        Returns:
            A list of SearchResult objects.
        """
        # 1. Call repository to get matching chunks
        matching_chunks: List[Chunk] = await self.repository.search_chunks_by_content(query, limit)
        
        # 2. Map chunks to SearchResult objects
        search_results = []
        for chunk in matching_chunks:
            # Simple scoring for now: 1.0 for any keyword match
            # Real implementation would use more sophisticated scoring
            score = 1.0 
            search_results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=score
                )
            )
        
        # 3. Return results
        return search_results

    async def search_chunks_by_similarity(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Search for relevant chunks based on semantic similarity.
        
        Args:
            query: The search query string.
            limit: Maximum number of results to return.
            
        Returns:
            A list of SearchResult objects ordered by similarity score.
        """
        # 1. Generate embedding for the query
        query_vector = self.embedding_service.encode(query)
        if not isinstance(query_vector, list):
             # Handle potential errors during encoding if needed, though encode raises
             return [] 
        
        # 2. Call repository for similarity search
        # Repository returns List[tuple[Chunk, float]]
        results_with_scores = await self.repository.search_chunks_by_similarity(
            query_vector=query_vector, 
            limit=limit
        )
        
        # 3. Map results to SearchResult objects
        search_results = [
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                score=score # Score is the similarity from the repository
            ) for chunk, score in results_with_scores
        ]
        
        return search_results

# TODO: Add methods for vector search, graph traversal search, etc. 