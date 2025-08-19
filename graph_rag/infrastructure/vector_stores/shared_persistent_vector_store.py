"""Shared persistent vector store implementation with file locking for concurrent access."""

import asyncio
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Any

import fcntl
import numpy as np
from starlette.concurrency import run_in_threadpool

from graph_rag.core.interfaces import (
    ChunkData,
    EmbeddingService,
    SearchResultData,
    VectorStore,
)

logger = logging.getLogger(__name__)


class SharedPersistentVectorStore(VectorStore):
    """
    A vector store that persists data to disk and supports concurrent access 
    from multiple processes through file locking.
    """

    def __init__(self, embedding_service: EmbeddingService, storage_path: str | Path):
        self.embedding_service = embedding_service
        self.dimension = embedding_service.get_embedding_dimension()
        self.storage_path = Path(storage_path)
        
        # In-memory storage (same as SimpleVectorStore)
        self.vectors: list[np.ndarray] = []
        self.metadata: list[dict] = []
        self.documents: list[str] = []
        self.chunk_ids: list[str] = []
        self.lock = asyncio.Lock()
        
        # BM25 structures
        self._bm25_docs: list[list[str]] = []
        self._bm25_doc_freq: dict[str, int] = {}
        self._bm25_avgdl: float = 0.0
        self._bm25_dirty: bool = False
        
        # Persistence files
        self.vectors_file = self.storage_path / "vectors.pkl"
        self.metadata_file = self.storage_path / "metadata.json"
        self.lock_file = self.storage_path / "store.lock"
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Flag to track if we've attempted to load
        self._load_attempted = False

    async def _ensure_loaded(self) -> None:
        """Ensure data is loaded if it exists on disk."""
        if self._load_attempted:
            return
            
        self._load_attempted = True
        if self.vectors_file.exists() and self.metadata_file.exists():
            try:
                await self.load()
                logger.info(f"Loaded existing vector store from {self.storage_path}")
            except Exception as e:
                logger.warning(f"Failed to load existing vector store: {e}")

    def _acquire_file_lock(self, file_handle) -> None:
        """Acquire an exclusive file lock."""
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
        except OSError as e:
            logger.error(f"Failed to acquire file lock: {e}")
            raise

    def _release_file_lock(self, file_handle) -> None:
        """Release a file lock."""
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except OSError as e:
            logger.warning(f"Failed to release file lock: {e}")

    async def load(self) -> None:
        """Load vector store data from persistent storage with file locking."""
        if not self.vectors_file.exists() or not self.metadata_file.exists():
            logger.debug("No persistent data found, starting with empty store")
            return

        async with self.lock:
            try:
                # Use lock file for coordination
                with open(self.lock_file, 'w') as lock_handle:
                    self._acquire_file_lock(lock_handle)
                    
                    try:
                        # Load vectors
                        with open(self.vectors_file, 'rb') as f:
                            data = pickle.load(f)
                            self.vectors = data.get('vectors', [])
                            self.documents = data.get('documents', [])
                            self.chunk_ids = data.get('chunk_ids', [])
                            self._bm25_docs = data.get('bm25_docs', [])
                            self._bm25_doc_freq = data.get('bm25_doc_freq', {})
                            self._bm25_avgdl = data.get('bm25_avgdl', 0.0)
                            self._bm25_dirty = data.get('bm25_dirty', False)

                        # Load metadata
                        with open(self.metadata_file, 'r') as f:
                            self.metadata = json.load(f)

                        logger.info(f"Loaded {len(self.vectors)} vectors from persistent storage")
                        
                    finally:
                        self._release_file_lock(lock_handle)
                        
            except Exception as e:
                logger.error(f"Failed to load vector store data: {e}")
                # Reset to empty state on load failure
                self.vectors = []
                self.metadata = []
                self.documents = []
                self.chunk_ids = []
                self._bm25_docs = []
                self._bm25_doc_freq = {}
                self._bm25_avgdl = 0.0
                self._bm25_dirty = False

    async def save(self) -> None:
        """Save vector store data to persistent storage with file locking."""
        async with self.lock:
            try:
                # Use lock file for coordination
                with open(self.lock_file, 'w') as lock_handle:
                    self._acquire_file_lock(lock_handle)
                    
                    try:
                        # Save vectors and related data
                        vectors_data = {
                            'vectors': self.vectors,
                            'documents': self.documents,
                            'chunk_ids': self.chunk_ids,
                            'bm25_docs': self._bm25_docs,
                            'bm25_doc_freq': self._bm25_doc_freq,
                            'bm25_avgdl': self._bm25_avgdl,
                            'bm25_dirty': self._bm25_dirty,
                        }
                        
                        with open(self.vectors_file, 'wb') as f:
                            pickle.dump(vectors_data, f)

                        # Save metadata as JSON for readability
                        with open(self.metadata_file, 'w') as f:
                            json.dump(self.metadata, f, indent=2)

                        logger.debug(f"Saved {len(self.vectors)} vectors to persistent storage")
                        
                    finally:
                        self._release_file_lock(lock_handle)
                        
            except Exception as e:
                logger.error(f"Failed to save vector store data: {e}")
                raise

    async def add_chunks(self, chunks: list[ChunkData]) -> None:
        """
        Add chunks to vector store and persist to disk.
        Implementation of the VectorStore protocol method.
        """
        await self.ingest_chunks(chunks)
        await self.save()  # Auto-save after adding chunks

    async def ingest_chunks(self, chunks: list[ChunkData]) -> None:
        """
        Ingest chunks into the vector store (same as SimpleVectorStore).
        This inherits all the logic from SimpleVectorStore for consistency.
        """
        logger.info(f"Ingesting {len(chunks)} chunks...")
        if not chunks:
            logger.warning("No chunks provided for ingestion.")
            return

        new_vectors = []
        new_metadata = []
        new_documents = []
        new_chunk_ids = []

        texts_to_embed = []
        indices_needing_embedding = []

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
                indices_needing_embedding.append(i)

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

            generated_embeddings = [np.array(emb) for emb in embeddings_list]

            if len(generated_embeddings) != len(texts_to_embed):
                raise ValueError(
                    "Embedding generation returned unexpected number of vectors."
                )

        # Second pass: merge chunks with generated embeddings
        temp_generated_vectors = {}
        for i, original_idx in enumerate(indices_needing_embedding):
            if i < len(generated_embeddings):
                temp_generated_vectors[original_idx] = generated_embeddings[i]

        # Combine chunks with existing embeddings and newly generated ones
        final_vectors = []
        final_metadata = []
        final_documents = []
        final_chunk_ids = []

        for i, chunk in enumerate(chunks):
            if i in temp_generated_vectors:  # This chunk had its embedding generated
                final_vectors.append(temp_generated_vectors[i])
                final_metadata.append({} if chunk.metadata is None else chunk.metadata)
                final_documents.append(chunk.text)
                final_chunk_ids.append(chunk.id)
            elif (
                chunk.embedding and len(chunk.embedding) == self.dimension
            ):  # This chunk had a valid existing embedding
                final_vectors.append(np.array(chunk.embedding))
                final_metadata.append({} if chunk.metadata is None else chunk.metadata)
                final_documents.append(chunk.text)
                final_chunk_ids.append(chunk.id)

        # Update the store under lock
        if final_vectors:
            async with self.lock:
                self.vectors.extend(final_vectors)
                self.metadata.extend(final_metadata)
                self.documents.extend(final_documents)
                self.chunk_ids.extend(final_chunk_ids)
                self._bm25_dirty = True  # Mark BM25 index as needing rebuild
                
            logger.info(
                f"Finished ingestion. Added {len(final_vectors)} vectors. Total vectors in store: {len(self.vectors)}"
            )
        else:
            logger.warning(
                "No valid chunks or embeddings found to add after processing."
            )

    async def search_similar_chunks(
        self,
        query_vector: list[float],
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[SearchResultData]:
        """
        Search for similar chunks (same as SimpleVectorStore).
        Auto-loads data if not already loaded.
        """
        # Ensure data is loaded
        await self._ensure_loaded()
            
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

        # Use lightweight cosine similarity implementation
        def cosine_similarity(X, Y=None):
            if Y is None:
                Y = X
            X_norm = X / np.linalg.norm(X, axis=1, keepdims=True)
            Y_norm = Y / np.linalg.norm(Y, axis=1, keepdims=True)
            return np.dot(X_norm, Y_norm.T)

        async with self.lock:
            if not self.vectors:
                return []

            vector_matrix = np.array(self.vectors)
            if vector_matrix.size == 0:
                return []
            if vector_matrix.ndim == 1:
                vector_matrix = vector_matrix.reshape(1, -1)
            elif vector_matrix.ndim != 2:
                logger.error(f"Unexpected vector matrix dimensions: {vector_matrix.ndim}")
                return []

            similarities = cosine_similarity(query_embedding, vector_matrix)[0]

            # Apply threshold if specified
            if threshold is not None:
                mask = similarities >= threshold
                indices = np.where(mask)[0]
                top_indices = indices[np.argsort(similarities[indices])[::-1]]
                top_indices = top_indices[:limit]
            else:
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
        """Retrieve a chunk by its ID (same as SimpleVectorStore)."""
        # Ensure data is loaded
        await self._ensure_loaded()
            
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
        """Delete chunks by their IDs and persist changes."""
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

        # Persist changes
        await self.save()

    async def delete_store(self) -> None:
        """Delete the entire vector store and its persistent storage."""
        logger.info("Deleting entire vector store")
        async with self.lock:
            # Clear in-memory data
            self.vectors = []
            self.metadata = []
            self.documents = []
            self.chunk_ids = []
            self._bm25_docs = []
            self._bm25_doc_freq = {}
            self._bm25_avgdl = 0.0
            self._bm25_dirty = False

        # Delete persistent files
        try:
            if self.vectors_file.exists():
                self.vectors_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            if self.lock_file.exists():
                self.lock_file.unlink()
            logger.info("Deleted persistent vector store files")
        except Exception as e:
            logger.error(f"Failed to delete persistent files: {e}")

    async def get_vector_store_size(self) -> int:
        """Return the number of vectors in the store."""
        # Ensure data is loaded
        await self._ensure_loaded()
            
        async with self.lock:
            return len(self.vectors)

    async def clear_vector_store(self) -> None:
        """Clear all data from the vector store and persist changes."""
        async with self.lock:
            self.vectors = []
            self.metadata = []
            self.documents = []
            self.chunk_ids = []
            self._bm25_docs = []
            self._bm25_doc_freq = {}
            self._bm25_avgdl = 0.0
            self._bm25_dirty = False
            
        await self.save()
        logger.info("SharedPersistentVectorStore cleared and persisted.")

    # Include search methods from SimpleVectorStore for compatibility
    async def search(
        self, query_text: str, top_k: int = 5, search_type: str = "vector"
    ) -> list[SearchResultData]:
        """Perform search with auto-loading."""
        # Ensure data is loaded
        await self._ensure_loaded()
            
        logger.debug(f"Search called with search_type={search_type}, query='{query_text[:50]}...'")

        results_with_scores: list[tuple[ChunkData, float]] = []
        if search_type.lower() == "keyword":
            results_with_scores = await self.keyword_search(query_text, k=top_k)
        else:
            # Generate embedding
            if hasattr(self.embedding_service, "encode_query"):
                query_embedding = await self.embedding_service.encode_query(query_text)
            else:
                query_embedding = await self.embedding_service.generate_embedding(query_text)
                
            if query_embedding:
                results_with_scores = await self.vector_search(query_text, k=top_k)
            else:
                logger.error(f"Failed to generate embedding for query: '{query_text}'")
                return []

        search_results = [
            SearchResultData(chunk=chunk_data, score=score)
            for chunk_data, score in results_with_scores
        ]

        logger.debug(f"Search returned {len(search_results)} results.")
        return search_results

    async def vector_search(self, query: str, k: int = 5) -> list[tuple[ChunkData, float]]:
        """Vector search with auto-loading."""
        # Ensure data is loaded
        await self._ensure_loaded()
            
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

        # Use lightweight cosine similarity
        def cosine_similarity(X, Y=None):
            if Y is None:
                Y = X
            X_norm = X / np.linalg.norm(X, axis=1, keepdims=True)
            Y_norm = Y / np.linalg.norm(Y, axis=1, keepdims=True)
            return np.dot(X_norm, Y_norm.T)

        async with self.lock:
            if not self.vectors:
                return []
                
            vector_matrix = np.array(self.vectors)
            if vector_matrix.size == 0:
                return []
            if vector_matrix.ndim == 1:
                vector_matrix = vector_matrix.reshape(1, -1)
            elif vector_matrix.ndim != 2:
                logger.error(f"Unexpected vector matrix dimensions: {vector_matrix.ndim}")
                return []

            similarities = cosine_similarity(query_embedding, vector_matrix)[0]

            actual_k = min(k, len(similarities))
            if actual_k <= 0:
                return []

            top_k_indices = np.argsort(similarities)[-actual_k:][::-1]

            results = []
            for i in top_k_indices:
                score = similarities[i]
                chunk_data = ChunkData(
                    id=self.chunk_ids[i] if i < len(self.chunk_ids) else f"chunk_{i}",
                    text=self.documents[i],
                    document_id=self.metadata[i].get("document_id", "unknown"),
                    metadata=self.metadata[i],
                    score=float(score),
                )
                results.append((chunk_data, float(score)))

        logger.debug(f"Vector search returned {len(results)} results.")
        return results

    async def keyword_search(self, query: str, k: int = 5) -> list[tuple[ChunkData, float]]:
        """BM25 keyword search with auto-loading."""
        # Ensure data is loaded
        await self._ensure_loaded()
            
        logger.debug(f"Performing BM25 keyword search for query: '{query[:50]}...'")
        tokens = self._tokenize(query)
        results: list[tuple[int, float]] = []
        
        async with self.lock:
            self._ensure_bm25_index()
            N = max(1, len(self._bm25_docs))
            k1 = 1.5
            b = 0.75
            
            for i, doc_tokens in enumerate(self._bm25_docs):
                if not doc_tokens:
                    continue
                score = 0.0
                dl = len(doc_tokens)
                tf: dict[str, int] = {}
                for t in doc_tokens:
                    tf[t] = tf.get(t, 0) + 1
                for q in tokens:
                    df = self._bm25_doc_freq.get(q, 0)
                    if df == 0:
                        continue
                    idf = max(0.0, ((N - df + 0.5) / (df + 0.5)))
                    import math as _math
                    idf = _math.log(1.0 + idf)
                    f = tf.get(q, 0)
                    if f == 0:
                        continue
                    denom = f + k1 * (1.0 - b + b * (dl / (self._bm25_avgdl or 1.0)))
                    score += idf * ((f * (k1 + 1.0)) / denom)
                if score > 0.0:
                    results.append((i, float(score)))

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

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        import re as _re
        text = (text or "").lower()
        tokens = _re.findall(r"[a-z0-9]+", text)
        return tokens

    def _ensure_bm25_index(self) -> None:
        """Ensure BM25 index is up to date."""
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