"""Maintenance jobs for GraphRAG system background operations."""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from graph_rag.core.interfaces import GraphRepository, VectorStore

logger = logging.getLogger(__name__)


class MaintenanceJobStatus(Enum):
    """Status of maintenance jobs."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MaintenanceJob(ABC):
    """Base class for maintenance jobs."""

    def __init__(self, name: str, log_json: bool = False):
        self.name = name
        self.status = MaintenanceJobStatus.IDLE
        self.last_run: datetime | None = None
        self.last_duration: float | None = None
        self.error_message: str | None = None
        self.log_json = log_json
        self.run_count = 0
        self.failure_count = 0

    @abstractmethod
    async def execute(self) -> dict[str, Any]:
        """Execute the maintenance job. Returns job result details."""
        pass

    def _log_message(self, level: str, message: str, **kwargs) -> None:
        """Log message in JSON format if enabled, otherwise standard format."""
        if self.log_json:
            log_data = {
                "time": datetime.now(timezone.utc).isoformat(),
                "level": level.upper(),
                "name": "maintenance.job",
                "job_name": self.name,
                "message": message,
                **kwargs
            }
            log_func = getattr(logger, level.lower(), logger.info)
            log_func(json.dumps(log_data))
        else:
            log_func = getattr(logger, level.lower(), logger.info)
            log_func(f"[{self.name}] {message}")

    async def run(self) -> dict[str, Any]:
        """Run the maintenance job with error handling and logging."""
        self.status = MaintenanceJobStatus.RUNNING
        self.run_count += 1
        start_time = time.time()

        try:
            self._log_message("info", "Starting maintenance job")
            result = await self.execute()

            self.status = MaintenanceJobStatus.SUCCESS
            self.last_run = datetime.now(timezone.utc)
            self.last_duration = time.time() - start_time
            self.error_message = None

            self._log_message(
                "info",
                "Maintenance job completed successfully",
                duration_seconds=self.last_duration,
                result=result
            )

            return {
                "status": self.status.value,
                "duration_seconds": self.last_duration,
                "result": result,
                "timestamp": self.last_run.isoformat()
            }

        except Exception as e:
            self.status = MaintenanceJobStatus.FAILED
            self.last_run = datetime.now(timezone.utc)
            self.last_duration = time.time() - start_time
            self.error_message = str(e)
            self.failure_count += 1

            self._log_message(
                "error",
                f"Maintenance job failed: {e}",
                duration_seconds=self.last_duration,
                error_type=type(e).__name__,
                exc_info=True
            )

            return {
                "status": self.status.value,
                "duration_seconds": self.last_duration,
                "error": self.error_message,
                "timestamp": self.last_run.isoformat()
            }

    def get_status(self) -> dict[str, Any]:
        """Get current job status."""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_duration_seconds": self.last_duration,
            "error_message": self.error_message,
            "run_count": self.run_count,
            "failure_count": self.failure_count
        }


class FaissMaintenanceJob(MaintenanceJob):
    """Maintenance job for FAISS vector store operations."""

    def __init__(self, vector_store: VectorStore, log_json: bool = False):
        super().__init__("faiss_maintenance", log_json)
        self.vector_store = vector_store

    async def execute(self) -> dict[str, Any]:
        """Execute FAISS maintenance tasks."""
        results = {}

        # Check if vector store supports maintenance operations
        if not hasattr(self.vector_store, 'rebuild_index'):
            raise ValueError("Vector store does not support index rebuilding")

        # Get initial stats
        initial_stats = {}
        if hasattr(self.vector_store, 'stats'):
            initial_stats = await self.vector_store.stats()
        elif hasattr(self.vector_store, 'get_vector_store_size'):
            size = await self.vector_store.get_vector_store_size()
            initial_stats = {"vectors": int(size)}

        self._log_message("info", "Starting FAISS index rebuild", initial_stats=initial_stats)

        # Perform index rebuild
        rebuild_start = time.time()
        await self.vector_store.rebuild_index()
        rebuild_duration = time.time() - rebuild_start

        # Get final stats
        final_stats = {}
        if hasattr(self.vector_store, 'stats'):
            final_stats = await self.vector_store.stats()
        elif hasattr(self.vector_store, 'get_vector_store_size'):
            size = await self.vector_store.get_vector_store_size()
            final_stats = {"vectors": int(size)}

        results = {
            "operation": "faiss_rebuild",
            "rebuild_duration_seconds": rebuild_duration,
            "initial_stats": initial_stats,
            "final_stats": final_stats
        }

        self._log_message("info", "FAISS index rebuild completed", **results)
        return results


class IntegrityCheckJob(MaintenanceJob):
    """Job for checking vector/graph integrity."""

    def __init__(self, graph_repository: GraphRepository, vector_store: VectorStore,
                 sample_size: int = 10, log_json: bool = False):
        super().__init__("integrity_check", log_json)
        self.graph_repository = graph_repository
        self.vector_store = vector_store
        self.sample_size = sample_size

    async def execute(self) -> dict[str, Any]:
        """Execute comprehensive integrity checks."""
        results = {
            "checks_performed": [],
            "warnings": [],
            "errors": []
        }

        # Check 1: Compare chunk counts
        try:
            graph_chunk_count = await self._get_graph_chunk_count()
            vector_count = await self._get_vector_count()

            results["checks_performed"].append("chunk_count_comparison")
            results["graph_chunks"] = graph_chunk_count
            results["vector_count"] = vector_count

            if vector_count < graph_chunk_count:
                warning = f"Vector count ({vector_count}) is less than graph chunks ({graph_chunk_count}); some chunks may be missing embeddings"
                results["warnings"].append(warning)
                self._log_message("warning", warning)
            elif vector_count > graph_chunk_count * 1.1:  # Allow 10% variance
                warning = f"Vector count ({vector_count}) is significantly higher than graph chunks ({graph_chunk_count}); possible orphaned vectors"
                results["warnings"].append(warning)
                self._log_message("warning", warning)
            else:
                self._log_message("info", f"Chunk count consistency check passed: graph={graph_chunk_count}, vectors={vector_count}")

        except Exception as e:
            error = f"Failed to compare chunk counts: {e}"
            results["errors"].append(error)
            self._log_message("error", error)

        # Check 2: Sample random chunks for embedding verification
        try:
            await self._perform_sample_verification(results)
        except Exception as e:
            error = f"Sample verification failed: {e}"
            results["errors"].append(error)
            self._log_message("error", error)

        # Check 3: Vector store health
        try:
            await self._check_vector_store_health(results)
        except Exception as e:
            error = f"Vector store health check failed: {e}"
            results["errors"].append(error)
            self._log_message("error", error)

        # Summary
        results["status"] = "passed" if not results["errors"] else "failed"
        results["warning_count"] = len(results["warnings"])
        results["error_count"] = len(results["errors"])

        self._log_message("info", f"Integrity check completed: {results['status']}",
                         warnings=results["warning_count"], errors=results["error_count"])

        return results

    async def _get_graph_chunk_count(self) -> int:
        """Get count of chunks in the graph."""
        try:
            query = "MATCH (c:Chunk) RETURN count(c) AS chunk_count"
            rows = await self.graph_repository.execute_query(query)
            if rows:
                row = rows[0]
                return int(row.get("chunk_count", 0) if isinstance(row, dict) else list(row.values())[0])
            return 0
        except Exception as e:
            self._log_message("warning", f"Could not get graph chunk count: {e}")
            return 0

    async def _get_vector_count(self) -> int:
        """Get count of vectors in the vector store."""
        if hasattr(self.vector_store, 'stats'):
            stats = await self.vector_store.stats()
            return int(stats.get("vectors", 0))
        elif hasattr(self.vector_store, 'get_vector_store_size'):
            return int(await self.vector_store.get_vector_store_size())
        return 0

    async def _perform_sample_verification(self, results: dict[str, Any]) -> None:
        """Sample random chunks and verify their embeddings exist."""
        results["checks_performed"].append("sample_embedding_verification")

        try:
            # Get sample of chunk IDs from graph
            query = f"MATCH (c:Chunk) RETURN c.id AS chunk_id ORDER BY rand() LIMIT {self.sample_size}"
            rows = await self.graph_repository.execute_query(query)

            if not rows:
                results["warnings"].append("No chunks found in graph for sampling")
                return

            chunk_ids = []
            for row in rows:
                if isinstance(row, dict):
                    chunk_ids.append(row.get("chunk_id"))
                else:
                    chunk_ids.append(list(row.values())[0])

            # Filter out None values
            chunk_ids = [cid for cid in chunk_ids if cid is not None]

            if not chunk_ids:
                results["warnings"].append("No valid chunk IDs found for sampling")
                return

            # Try to search for each chunk (this verifies embeddings exist)
            missing_embeddings = []
            for chunk_id in chunk_ids:
                try:
                    # Use the chunk_id as a query to test embedding existence
                    search_results = await self.vector_store.search(str(chunk_id), limit=1)
                    if not search_results:
                        missing_embeddings.append(chunk_id)
                except Exception:
                    missing_embeddings.append(chunk_id)

            results["sample_size"] = len(chunk_ids)
            results["missing_embeddings"] = len(missing_embeddings)

            if missing_embeddings:
                warning = f"Found {len(missing_embeddings)}/{len(chunk_ids)} sampled chunks without embeddings"
                results["warnings"].append(warning)
                self._log_message("warning", warning, missing_chunks=missing_embeddings[:5])  # Log first 5 IDs
            else:
                self._log_message("info", f"Sample embedding verification passed for {len(chunk_ids)} chunks")

        except Exception as e:
            error = f"Sample verification failed: {e}"
            results["errors"].append(error)
            raise

    async def _check_vector_store_health(self, results: dict[str, Any]) -> None:
        """Perform basic health checks on vector store."""
        results["checks_performed"].append("vector_store_health")

        # Test basic search operation
        try:
            await self.vector_store.search("test_query", limit=1)
            results["vector_store_accessible"] = True
            self._log_message("info", "Vector store health check passed")
        except Exception as e:
            results["vector_store_accessible"] = False
            error = f"Vector store not accessible: {e}"
            results["errors"].append(error)
            raise Exception(error) from e
