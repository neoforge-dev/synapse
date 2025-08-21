import asyncio
import logging
import os
from typing import Any

import numpy as np
from starlette.concurrency import run_in_threadpool

# Use lightweight implementation in hot coverage mode to avoid scipy import issues
if os.getenv("SKIP_SPACY_IMPORT") == "1":
    def cosine_similarity(X, Y=None):
        """Lightweight cosine similarity implementation using only numpy."""
        if Y is None:
            Y = X
        X_norm = X / np.linalg.norm(X, axis=1, keepdims=True)
        Y_norm = Y / np.linalg.norm(Y, axis=1, keepdims=True)
        return np.dot(X_norm, Y_norm.T)
else:
    from sklearn.metrics.pairwise import cosine_similarity

# Corrected import path for ChunkData and VectorStore protocol
from graph_rag.core.interfaces import (
    ChunkData,
    EmbeddingService,
    SearchResultData,
    VectorStore,
)

# We still need Chunk model for internal representation maybe? Let's keep it for now
# Or maybe ChunkData is enough. Review if Chunk is actually used.

logger = logging.getLogger(__name__)


class SimpleVectorStore(VectorStore):
    """A simple in-memory vector store implementation."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.dimension = embedding_service.get_embedding_dimension()
        self.vectors: list[np.ndarray] = []
        self.metadata: list[dict] = []
        self.documents: list[str] = []  # Store original document text
        self.chunk_ids: list[str] = []  # Store chunk IDs for retrieval by ID
        self.lock = asyncio.Lock()
        # --- BM25 structures ---
        self._bm25_docs: list[list[str]] = []
        self._bm25_doc_freq: dict[str, int] = {}
        self._bm25_avgdl: float = 0.0
        self._bm25_dirty: bool = False

    async def add_chunks(self, chunks: list[ChunkData]) -> None:
        """
        Add chunks to vector store - implementation of the VectorStore protocol method.

        Args:
            chunks: List of ChunkData objects to add to the vector store
        """
        logger.debug(f"Add chunks method called with {len(chunks)} chunks")
        await self.ingest_chunks(chunks)

    async def search_similar_chunks(
        self,
        query_vector: list[float],
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[SearchResultData]:
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
        logger.debug(
            f"Searching for similar chunks with vector (dim={len(query_vector)})"
        )
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
            if not self.vectors:  # Re-check after acquiring lock
                return []

            # Calculate cosine similarities
            vector_matrix = np.array(self.vectors)
            if vector_matrix.size == 0:
                return []  # Handle empty store explicitly
            if vector_matrix.ndim == 1:
                vector_matrix = vector_matrix.reshape(1, -1)
            elif vector_matrix.ndim != 2:
                logger.error(
                    f"Unexpected vector matrix dimensions: {vector_matrix.ndim}"
                )
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
                    score=score,
                )
                search_result = SearchResultData(chunk=chunk_data, score=score)
                results.append(search_result)

        logger.debug(f"Vector similarity search returned {len(results)} results.")
        return results

    async def get_chunk_by_id(self, chunk_id: str) -> ChunkData | None:
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
                    embedding=self.vectors[index].tolist()
                    if index < len(self.vectors)
                    else None,
                )
            except ValueError:
                logger.debug(f"Chunk with ID {chunk_id} not found")
                return None
            except Exception as e:
                logger.error(f"Error retrieving chunk {chunk_id}: {e}")
                return None

    async def delete_chunks(self, chunk_ids: list[str]) -> None:
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
                if index < len(self._bm25_docs):
                    self._bm25_docs.pop(index)
                    self._bm25_dirty = True

            logger.info(f"Removed {len(indices_to_remove)} chunks from vector store")

    async def delete_store(self) -> None:
        """
        Deletes the entire vector store collection.
        Implementation of the VectorStore protocol method.
        """
        logger.info("Deleting entire vector store")
        await self.clear_vector_store()

    async def search(
        self, query_text: str, top_k: int = 5, search_type: str = "vector"
    ) -> list[SearchResultData]:
        """
        Performs a search based on the query text and search type.

        Args:
            query_text: The search query text
            top_k: Number of results to return
            search_type: Either "vector" or "keyword" to determine search method (default: vector)

        Returns:
            List of SearchResultData objects containing chunks and their scores.
        """
        logger.debug(
            f"Search called with search_type={search_type}, query='{query_text[:50]}...'"
        )

        results_with_scores: list[tuple[ChunkData, float]] = []
        if search_type.lower() == "keyword":
            # Keyword search implementation might need adjustment if it doesn't return scores
            results_with_scores = await self.keyword_search(query_text, k=top_k)
        else:  # Default to vector search
            # Generate embedding (compat across providers)
            if hasattr(self.embedding_service, "encode_query"):
                query_embedding = await self.embedding_service.encode_query(query_text)
            else:
                query_embedding = await self.embedding_service.generate_embedding(
                    query_text
                )
            if query_embedding:
                # Vector search now directly returns List[SearchResultData]
                # We need to call the specific vector search method which returns List[tuple[ChunkData, float]]
                # Let's assume self.vector_search returns List[tuple[ChunkData, float]]
                results_with_scores = await self.vector_search(query_text, k=top_k)
                # results_with_scores = await self.search_similar_chunks(query_embedding, limit=top_k)
            else:
                logger.error(f"Failed to generate embedding for query: '{query_text}'")
                return []

        # Convert (ChunkData, score) tuples to SearchResultData objects
        search_results = [
            SearchResultData(chunk=chunk_data, score=score)
            for chunk_data, score in results_with_scores
        ]

        logger.debug(f"Search returned {len(search_results)} results.")
        return search_results

    async def ingest_chunks(self, chunks: list[ChunkData]):
        """Ingests chunks into the vector store, generating embeddings only if needed."""
        logger.info(f"Ingesting {len(chunks)} chunks...")
        if not chunks:
            logger.warning("No chunks provided for ingestion.")
            return

        new_vectors = []
        new_metadata = []
        new_documents = []
        new_chunk_ids = []

        texts_to_embed = []
        indices_needing_embedding = []  # Store original index to map back generated embeddings

        # First pass: identify chunks needing embedding vs those with existing ones
        for i, chunk in enumerate(chunks):
            valid_embedding_present = False
            if chunk.embedding and len(chunk.embedding) == self.dimension:
                valid_embedding_present = True

            if valid_embedding_present:
                # Use existing embedding
                new_vectors.append(np.array(chunk.embedding))
                new_metadata.append({} if chunk.metadata is None else chunk.metadata)
                new_documents.append(chunk.text)
                new_chunk_ids.append(chunk.id)
            else:
                # Mark for embedding generation
                texts_to_embed.append(chunk.text)
                indices_needing_embedding.append(i)  # Store original index

        # Generate embeddings only for those chunks that need it
        generated_embeddings = []
        if texts_to_embed:
            logger.debug(f"Generating embeddings for {len(texts_to_embed)} chunks.")
            if asyncio.iscoroutinefunction(self.embedding_service.encode):
                embeddings_list = await self.embedding_service.encode(texts_to_embed)
            else:
                embeddings_list = await run_in_threadpool(
                    self.embedding_service.encode, texts_to_embed
                )

            # Convert list of lists/tuples to list of numpy arrays
            generated_embeddings = [np.array(emb) for emb in embeddings_list]

            if len(generated_embeddings) != len(texts_to_embed):
                logger.error(
                    "Mismatch between number of texts and generated embeddings."
                )
                # Decide how to handle: raise error, log and skip, etc.
                # For now, let's log and potentially skip adding these problematic chunks
                # Or maybe better to raise an error to signal failure
                raise ValueError(
                    "Embedding generation returned unexpected number of vectors."
                )

        # Second pass: merge chunks with generated embeddings
        generated_embedding_idx = 0
        temp_generated_vectors = {}  # Temporary dict to hold generated embeddings by original index
        for original_idx in indices_needing_embedding:
            if generated_embedding_idx < len(generated_embeddings):
                temp_generated_vectors[original_idx] = generated_embeddings[
                    generated_embedding_idx
                ]
                generated_embedding_idx += 1
            else:
                # This case should ideally not happen if the check above works, but as a safeguard:
                logger.error(
                    f"Missing generated embedding for chunk at original index {original_idx}"
                )
                # Handle missing embedding (e.g., skip this chunk or raise error)

        # Combine chunks with existing embeddings and newly generated ones
        final_vectors = []
        final_metadata = []
        final_documents = []
        final_chunk_ids = []

        current_generated_idx = 0
        for i, chunk in enumerate(chunks):
            if i in temp_generated_vectors:  # This chunk had its embedding generated
                final_vectors.append(temp_generated_vectors[i])
                final_metadata.append({} if chunk.metadata is None else chunk.metadata)
                final_documents.append(chunk.text)
                final_chunk_ids.append(chunk.id)
                current_generated_idx += 1
            elif (
                chunk.embedding and len(chunk.embedding) == self.dimension
            ):  # This chunk had a valid existing embedding
                final_vectors.append(np.array(chunk.embedding))
                final_metadata.append({} if chunk.metadata is None else chunk.metadata)
                final_documents.append(chunk.text)
                final_chunk_ids.append(chunk.id)
            # Else: Chunk had no embedding and failed generation (if error handling allows skipping) - skip it

        # Update the store under lock
        if final_vectors:  # Proceed only if there's something to add
            async with self.lock:
                self.vectors.extend(final_vectors)
                self.metadata.extend(final_metadata)
                self.documents.extend(final_documents)
                self.chunk_ids.extend(final_chunk_ids)
            logger.info(
                f"Finished ingestion. Added {len(final_vectors)} vectors. Total vectors in store: {len(self.vectors)}"
            )
        else:
            logger.warning(
                "No valid chunks or embeddings found to add after processing."
            )

    async def vector_search(
        self, query: str, k: int = 5
    ) -> list[tuple[ChunkData, float]]:
        """Performs vector search using cosine similarity."""
        logger.debug(f"Performing vector search for query: '{query[:50]}...'")
        if not self.vectors:
            logger.warning("Vector store is empty, cannot perform search.")
            return []

        # Get query embedding
        if asyncio.iscoroutinefunction(self.embedding_service.encode):
            query_embedding_list = await self.embedding_service.encode([query])
        else:
            query_embedding_list = await run_in_threadpool(
                self.embedding_service.encode, [query]
            )

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
            if not self.vectors:  # Re-check after acquiring lock
                return []
            # Calculate cosine similarities
            # Ensure vectors is a 2D array
            vector_matrix = np.array(self.vectors)
            if vector_matrix.size == 0:
                return []  # Handle empty store explicitly
            if vector_matrix.ndim == 1:
                vector_matrix = vector_matrix.reshape(1, -1)
            elif vector_matrix.ndim != 2:
                logger.error(
                    f"Unexpected vector matrix dimensions: {vector_matrix.ndim}"
                )
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
                    score=float(score),
                )
                results.append((chunk_data, float(score)))  # Ensure score is float

        logger.debug(f"Vector search returned {len(results)} results.")
        return results

    async def keyword_search(
        self, query: str, k: int = 5
    ) -> list[tuple[ChunkData, float]]:
        """Performs BM25 keyword search (lowercase tokenization)."""
        logger.debug(f"Performing BM25 keyword search for query: '{query[:50]}...'")
        tokens = self._tokenize(query)
        results: list[tuple[int, float]] = []
        async with self.lock:
            self._ensure_bm25_index()
            N = max(1, len(self._bm25_docs))
            # Okapi BM25 params
            k1 = 1.5
            b = 0.75
            for i, doc_tokens in enumerate(self._bm25_docs):
                if not doc_tokens:
                    continue
                score = 0.0
                dl = len(doc_tokens)
                # term frequencies for this doc
                tf: dict[str, int] = {}
                for t in doc_tokens:
                    tf[t] = tf.get(t, 0) + 1
                for q in tokens:
                    df = self._bm25_doc_freq.get(q, 0)
                    if df == 0:
                        continue
                    idf = max(0.0, ( (N - df + 0.5) / (df + 0.5) ))
                    # Use log on idf-like ratio to stabilize
                    import math as _math

                    idf = _math.log(1.0 + idf)
                    f = tf.get(q, 0)
                    if f == 0:
                        continue
                    denom = f + k1 * (1.0 - b + b * (dl / (self._bm25_avgdl or 1.0)))
                    score += idf * ((f * (k1 + 1.0)) / denom)
                if score > 0.0:
                    results.append((i, float(score)))

            # Sort and take top-k
            results.sort(key=lambda t: t[1], reverse=True)
            top = results[: min(k, len(results))]
            out: list[tuple[ChunkData, float]] = []
            for i, s in top:
                chunk_data = ChunkData(
                    id=self.chunk_ids[i] if i < len(self.chunk_ids) else f"chunk_{i}",
                    text=self.documents[i],
                    document_id=self.metadata[i].get("document_id", "unknown"),
                    metadata=self.metadata[i],
                    score=s,
                )
                out.append((chunk_data, s))

        logger.debug(f"BM25 keyword search returned {len(out)} results.")
        return out

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
            self._bm25_docs = []
            self._bm25_doc_freq = {}
            self._bm25_avgdl = 0.0
            self._bm25_dirty = False
        logger.info("SimpleVectorStore cleared.")

    # --- BM25 helpers ---
    def _tokenize(self, text: str) -> list[str]:
        # Simple whitespace + lowercase; strip punctuation crudely
        import re as _re

        text = (text or "").lower()
        tokens = _re.findall(r"[a-z0-9]+", text)
        return tokens

    def _ensure_bm25_index(self) -> None:
        if not self._bm25_dirty and self._bm25_docs and self._bm25_doc_freq:
            return
        # Rebuild doc list and stats from self.documents
        self._bm25_docs = [self._tokenize(t) for t in self.documents]
        df: dict[str, int] = {}
        total_len = 0
        for doc in self._bm25_docs:
            total_len += len(doc)
            seen: set[str] = set()
            for tok in doc:
                if tok in seen:
                    continue
                df[tok] = df.get(tok, 0) + 1
                seen.add(tok)
        self._bm25_doc_freq = df
        self._bm25_avgdl = (total_len / max(1, len(self._bm25_docs))) if self._bm25_docs else 0.0
        self._bm25_dirty = False

    async def stats(self) -> dict[str, Any]:
        """
        Returns implementation-specific statistics such as vector count.
        Implementation of the VectorStore protocol method.
        """
        return {
            "vector_count": len(self.vectors),
            "chunk_count": len(self.chunk_ids),
            "document_count": len(set(self.documents)),
            "embedding_dimension": self.dimension,
            "bm25_index_built": not self._bm25_dirty,
            "bm25_vocabulary_size": len(self._bm25_doc_freq),
        }
