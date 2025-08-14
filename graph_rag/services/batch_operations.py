"""Batch operations service for high-scale processing."""

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from graph_rag.core.interfaces import (
    EmbeddingService,
    GraphRepository,
    VectorStore,
)
from graph_rag.services.ingestion import IngestionService
from graph_rag.services.search import AdvancedSearchService
from graph_rag.utils.identity import derive_document_id

logger = logging.getLogger(__name__)


class BatchOperationType(Enum):
    """Types of batch operations."""
    INGEST = "ingest"
    SEARCH = "search"
    EMBED = "embed"
    EXTRACT = "extract"
    DELETE = "delete"


class BatchStatus(Enum):
    """Status of batch operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


@dataclass
class BatchResult:
    """Result of a single item in a batch operation."""
    item_id: str
    status: BatchStatus
    data: Any | None = None
    error: str | None = None
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] | None = None


class BatchOperationResult(BaseModel):
    """Result of a complete batch operation."""
    operation_type: BatchOperationType
    total_items: int
    successful_items: int
    failed_items: int
    execution_time_ms: float
    results: list[BatchResult]

    @property
    def success_rate(self) -> float:
        if self.total_items == 0:
            return 1.0
        return self.successful_items / self.total_items

    @property
    def average_item_time_ms(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.execution_time_ms / self.total_items


class BatchIngestionRequest(BaseModel):
    """Request for batch document ingestion."""
    documents: list[dict[str, Any]]  # List of {path, content, metadata}
    generate_embeddings: bool = False
    replace_existing: bool = True
    extract_entities: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200


class BatchSearchRequest(BaseModel):
    """Request for batch search operations."""
    queries: list[str]
    search_strategy: str = "hybrid"
    limit_per_query: int = 10
    rerank: bool = True
    cluster: bool = False


class BatchOperationsService:
    """Service for handling large-scale batch operations efficiently."""

    def __init__(
        self,
        ingestion_service: IngestionService | None = None,
        search_service: AdvancedSearchService | None = None,
        vector_store: VectorStore | None = None,
        graph_repository: GraphRepository | None = None,
        embedding_service: EmbeddingService | None = None,
        max_workers: int = 4,
        batch_size: int = 100,
        enable_progress_callback: bool = True
    ):
        """Initialize batch operations service.
        
        Args:
            ingestion_service: Service for document ingestion
            search_service: Service for advanced search operations
            vector_store: Vector store for embeddings
            graph_repository: Graph repository for knowledge graph
            embedding_service: Service for generating embeddings
            max_workers: Maximum number of concurrent workers
            batch_size: Size of batches for processing
            enable_progress_callback: Whether to enable progress callbacks
        """
        self.ingestion_service = ingestion_service
        self.search_service = search_service
        self.vector_store = vector_store
        self.graph_repository = graph_repository
        self.embedding_service = embedding_service
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.enable_progress_callback = enable_progress_callback

        # Thread pool for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)

    async def batch_ingest_documents(
        self,
        request: BatchIngestionRequest,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> BatchOperationResult:
        """Ingest multiple documents in batch.
        
        Args:
            request: Batch ingestion request
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchOperationResult with ingestion results
        """
        start_time = time.time()
        results = []
        processed = 0

        logger.info(f"Starting batch ingestion of {len(request.documents)} documents")

        # Process documents in batches
        for i in range(0, len(request.documents), self.batch_size):
            batch = request.documents[i:i + self.batch_size]
            batch_results = await self._process_ingestion_batch(batch, request)
            results.extend(batch_results)

            processed += len(batch)
            if progress_callback and self.enable_progress_callback:
                progress_callback(processed, len(request.documents))

        execution_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.status == BatchStatus.COMPLETED)
        failed = len(results) - successful

        logger.info(
            f"Batch ingestion completed: {successful}/{len(results)} successful "
            f"in {execution_time:.1f}ms"
        )

        return BatchOperationResult(
            operation_type=BatchOperationType.INGEST,
            total_items=len(request.documents),
            successful_items=successful,
            failed_items=failed,
            execution_time_ms=execution_time,
            results=results
        )

    async def _process_ingestion_batch(
        self,
        batch: list[dict[str, Any]],
        request: BatchIngestionRequest
    ) -> list[BatchResult]:
        """Process a single batch of documents for ingestion."""
        if not self.ingestion_service:
            return [
                BatchResult(
                    item_id=str(i),
                    status=BatchStatus.FAILED,
                    error="Ingestion service not available"
                )
                for i, _ in enumerate(batch)
            ]

        # Create async tasks for concurrent processing
        tasks = []
        for i, doc in enumerate(batch):
            task = self._ingest_single_document(doc, request, str(i))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                batch_results.append(BatchResult(
                    item_id=str(i),
                    status=BatchStatus.FAILED,
                    error=str(result)
                ))
            else:
                batch_results.append(result)

        return batch_results

    async def _ingest_single_document(
        self,
        doc: dict[str, Any],
        request: BatchIngestionRequest,
        item_id: str
    ) -> BatchResult:
        """Ingest a single document."""
        start_time = time.time()

        try:
            # Extract document information
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            path = doc.get("path")

            # Derive document ID
            if path:
                document_id, id_source, _ = derive_document_id(
                    Path(path), content, metadata
                )
            else:
                document_id, id_source, _ = derive_document_id(
                    Path(f"batch_doc_{item_id}"), content, metadata
                )

            # Perform ingestion
            await self.ingestion_service.ingest_document(
                document_id=document_id,
                content=content,
                metadata=metadata,
                generate_embeddings=request.generate_embeddings,
                replace_existing=request.replace_existing
            )

            execution_time = (time.time() - start_time) * 1000

            return BatchResult(
                item_id=item_id,
                status=BatchStatus.COMPLETED,
                data={"document_id": document_id, "id_source": id_source},
                execution_time_ms=execution_time,
                metadata={"path": path}
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to ingest document {item_id}: {e}")

            return BatchResult(
                item_id=item_id,
                status=BatchStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time
            )

    async def batch_search(
        self,
        request: BatchSearchRequest,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> BatchOperationResult:
        """Perform batch search operations.
        
        Args:
            request: Batch search request
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchOperationResult with search results
        """
        if not self.search_service:
            return BatchOperationResult(
                operation_type=BatchOperationType.SEARCH,
                total_items=len(request.queries),
                successful_items=0,
                failed_items=len(request.queries),
                execution_time_ms=0,
                results=[
                    BatchResult(
                        item_id=str(i),
                        status=BatchStatus.FAILED,
                        error="Search service not available"
                    )
                    for i, _ in enumerate(request.queries)
                ]
            )

        start_time = time.time()
        results = []
        processed = 0

        logger.info(f"Starting batch search for {len(request.queries)} queries")

        # Process queries in batches
        for i in range(0, len(request.queries), self.batch_size):
            batch = request.queries[i:i + self.batch_size]
            batch_results = await self._process_search_batch(batch, request, i)
            results.extend(batch_results)

            processed += len(batch)
            if progress_callback and self.enable_progress_callback:
                progress_callback(processed, len(request.queries))

        execution_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.status == BatchStatus.COMPLETED)
        failed = len(results) - successful

        logger.info(
            f"Batch search completed: {successful}/{len(results)} successful "
            f"in {execution_time:.1f}ms"
        )

        return BatchOperationResult(
            operation_type=BatchOperationType.SEARCH,
            total_items=len(request.queries),
            successful_items=successful,
            failed_items=failed,
            execution_time_ms=execution_time,
            results=results
        )

    async def _process_search_batch(
        self,
        batch: list[str],
        request: BatchSearchRequest,
        offset: int
    ) -> list[BatchResult]:
        """Process a single batch of search queries."""
        # Create async tasks for concurrent processing
        tasks = []
        for i, query in enumerate(batch):
            task = self._search_single_query(query, request, str(offset + i))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                batch_results.append(BatchResult(
                    item_id=str(offset + i),
                    status=BatchStatus.FAILED,
                    error=str(result)
                ))
            else:
                batch_results.append(result)

        return batch_results

    async def _search_single_query(
        self,
        query: str,
        request: BatchSearchRequest,
        item_id: str
    ) -> BatchResult:
        """Perform search for a single query."""
        start_time = time.time()

        try:
            from graph_rag.services.search import SearchStrategy

            # Map strategy string to enum
            strategy_map = {
                "vector_only": SearchStrategy.VECTOR_ONLY,
                "keyword_only": SearchStrategy.KEYWORD_ONLY,
                "hybrid": SearchStrategy.HYBRID,
                "graph_enhanced": SearchStrategy.GRAPH_ENHANCED
            }

            search_strategy = strategy_map.get(
                request.search_strategy, SearchStrategy.HYBRID
            )

            # Perform search
            search_result = await self.search_service.search(
                query=query,
                strategy=search_strategy,
                limit=request.limit_per_query,
                rerank=request.rerank,
                cluster=request.cluster
            )

            execution_time = (time.time() - start_time) * 1000

            return BatchResult(
                item_id=item_id,
                status=BatchStatus.COMPLETED,
                data=search_result,
                execution_time_ms=execution_time,
                metadata={"query": query}
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to search query {query}: {e}")

            return BatchResult(
                item_id=item_id,
                status=BatchStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"query": query}
            )

    async def batch_generate_embeddings(
        self,
        texts: list[str],
        progress_callback: Callable[[int, int], None] | None = None
    ) -> BatchOperationResult:
        """Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to generate embeddings for
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchOperationResult with embedding results
        """
        if not self.embedding_service:
            return BatchOperationResult(
                operation_type=BatchOperationType.EMBED,
                total_items=len(texts),
                successful_items=0,
                failed_items=len(texts),
                execution_time_ms=0,
                results=[
                    BatchResult(
                        item_id=str(i),
                        status=BatchStatus.FAILED,
                        error="Embedding service not available"
                    )
                    for i, _ in enumerate(texts)
                ]
            )

        start_time = time.time()
        results = []
        processed = 0

        logger.info(f"Starting batch embedding generation for {len(texts)} texts")

        # Process texts in smaller batches for memory efficiency
        embedding_batch_size = min(self.batch_size, 50)  # Smaller batches for embeddings

        for i in range(0, len(texts), embedding_batch_size):
            batch = texts[i:i + embedding_batch_size]
            batch_results = await self._process_embedding_batch(batch, i)
            results.extend(batch_results)

            processed += len(batch)
            if progress_callback and self.enable_progress_callback:
                progress_callback(processed, len(texts))

        execution_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.status == BatchStatus.COMPLETED)
        failed = len(results) - successful

        logger.info(
            f"Batch embedding generation completed: {successful}/{len(results)} successful "
            f"in {execution_time:.1f}ms"
        )

        return BatchOperationResult(
            operation_type=BatchOperationType.EMBED,
            total_items=len(texts),
            successful_items=successful,
            failed_items=failed,
            execution_time_ms=execution_time,
            results=results
        )

    async def _process_embedding_batch(
        self,
        batch: list[str],
        offset: int
    ) -> list[BatchResult]:
        """Process a single batch of texts for embedding generation."""
        start_time = time.time()

        try:
            # Generate embeddings for the entire batch at once for efficiency
            embeddings = await self.embedding_service.generate_embeddings(batch)

            execution_time = (time.time() - start_time) * 1000
            avg_time_per_item = execution_time / len(batch)

            # Create results for each item
            results = []
            for i, (text, embedding) in enumerate(zip(batch, embeddings, strict=False)):
                results.append(BatchResult(
                    item_id=str(offset + i),
                    status=BatchStatus.COMPLETED,
                    data=embedding,
                    execution_time_ms=avg_time_per_item,
                    metadata={"text_length": len(text)}
                ))

            return results

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to generate embeddings for batch: {e}")

            # Create failed results for all items in batch
            return [
                BatchResult(
                    item_id=str(offset + i),
                    status=BatchStatus.FAILED,
                    error=str(e),
                    execution_time_ms=execution_time / len(batch)
                )
                for i in range(len(batch))
            ]

    async def batch_delete_documents(
        self,
        document_ids: list[str],
        progress_callback: Callable[[int, int], None] | None = None
    ) -> BatchOperationResult:
        """Delete multiple documents in batch.
        
        Args:
            document_ids: List of document IDs to delete
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchOperationResult with deletion results
        """
        start_time = time.time()
        results = []
        processed = 0

        logger.info(f"Starting batch deletion of {len(document_ids)} documents")

        # Process deletions in batches
        for i in range(0, len(document_ids), self.batch_size):
            batch = document_ids[i:i + self.batch_size]
            batch_results = await self._process_deletion_batch(batch, i)
            results.extend(batch_results)

            processed += len(batch)
            if progress_callback and self.enable_progress_callback:
                progress_callback(processed, len(document_ids))

        execution_time = (time.time() - start_time) * 1000
        successful = sum(1 for r in results if r.status == BatchStatus.COMPLETED)
        failed = len(results) - successful

        logger.info(
            f"Batch deletion completed: {successful}/{len(results)} successful "
            f"in {execution_time:.1f}ms"
        )

        return BatchOperationResult(
            operation_type=BatchOperationType.DELETE,
            total_items=len(document_ids),
            successful_items=successful,
            failed_items=failed,
            execution_time_ms=execution_time,
            results=results
        )

    async def _process_deletion_batch(
        self,
        batch: list[str],
        offset: int
    ) -> list[BatchResult]:
        """Process a single batch of document deletions."""
        # Create async tasks for concurrent processing
        tasks = []
        for i, doc_id in enumerate(batch):
            task = self._delete_single_document(doc_id, str(offset + i))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                batch_results.append(BatchResult(
                    item_id=str(offset + i),
                    status=BatchStatus.FAILED,
                    error=str(result)
                ))
            else:
                batch_results.append(result)

        return batch_results

    async def _delete_single_document(self, document_id: str, item_id: str) -> BatchResult:
        """Delete a single document."""
        start_time = time.time()

        try:
            # Delete from graph repository
            if self.graph_repository:
                success = await self.graph_repository.delete_document(document_id)
                if not success:
                    raise ValueError(f"Failed to delete document {document_id} from graph")

            # Delete from vector store
            if self.vector_store:
                # Get chunks to delete from vector store
                if hasattr(self.vector_store, 'delete_by_document_id'):
                    await self.vector_store.delete_by_document_id(document_id)
                else:
                    # Fallback: get chunks and delete individually
                    if self.graph_repository:
                        chunks = await self.graph_repository.get_chunks_by_document_id(document_id)
                        chunk_ids = [chunk.id for chunk in chunks]
                        if chunk_ids:
                            await self.vector_store.delete_chunks(chunk_ids)

            execution_time = (time.time() - start_time) * 1000

            return BatchResult(
                item_id=item_id,
                status=BatchStatus.COMPLETED,
                data={"document_id": document_id},
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to delete document {document_id}: {e}")

            return BatchResult(
                item_id=item_id,
                status=BatchStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"document_id": document_id}
            )

    async def get_batch_statistics(
        self,
        results: list[BatchOperationResult]
    ) -> dict[str, Any]:
        """Generate statistics from batch operation results.
        
        Args:
            results: List of batch operation results
            
        Returns:
            Dictionary with comprehensive statistics
        """
        if not results:
            return {"message": "No batch results to analyze"}

        stats = {
            "total_operations": len(results),
            "operations_by_type": defaultdict(int),
            "total_items": 0,
            "total_successful": 0,
            "total_failed": 0,
            "total_execution_time_ms": 0,
            "average_success_rate": 0,
            "performance_by_type": {}
        }

        for result in results:
            stats["operations_by_type"][result.operation_type.value] += 1
            stats["total_items"] += result.total_items
            stats["total_successful"] += result.successful_items
            stats["total_failed"] += result.failed_items
            stats["total_execution_time_ms"] += result.execution_time_ms

            # Performance by operation type
            op_type = result.operation_type.value
            if op_type not in stats["performance_by_type"]:
                stats["performance_by_type"][op_type] = {
                    "operations": 0,
                    "items": 0,
                    "total_time_ms": 0,
                    "avg_time_per_operation_ms": 0,
                    "avg_time_per_item_ms": 0,
                    "success_rate": 0
                }

            perf = stats["performance_by_type"][op_type]
            perf["operations"] += 1
            perf["items"] += result.total_items
            perf["total_time_ms"] += result.execution_time_ms

        # Calculate averages
        if stats["total_items"] > 0:
            stats["overall_success_rate"] = stats["total_successful"] / stats["total_items"]
            stats["average_time_per_item_ms"] = stats["total_execution_time_ms"] / stats["total_items"]

        # Calculate performance averages by type
        for op_type, perf in stats["performance_by_type"].items():
            if perf["operations"] > 0:
                perf["avg_time_per_operation_ms"] = perf["total_time_ms"] / perf["operations"]
            if perf["items"] > 0:
                perf["avg_time_per_item_ms"] = perf["total_time_ms"] / perf["items"]

                # Calculate success rate for this operation type
                successful_for_type = sum(
                    r.successful_items for r in results
                    if r.operation_type.value == op_type
                )
                perf["success_rate"] = successful_for_type / perf["items"]

        return dict(stats)

    def close(self):
        """Clean up resources."""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
