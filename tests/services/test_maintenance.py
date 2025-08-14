"""Tests for maintenance services."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graph_rag.services.maintenance import (
    FaissMaintenanceJob,
    IntegrityCheckJob,
    MaintenanceJobStatus,
    MaintenanceScheduler,
)


class MockVectorStore:
    """Mock vector store for testing."""
    
    def __init__(self, size: int = 100, supports_rebuild: bool = True):
        self.size = size
        self.supports_rebuild = supports_rebuild
        self.rebuild_called = 0
        
    async def get_vector_store_size(self) -> int:
        return self.size
        
    async def stats(self) -> dict:
        return {"vectors": self.size}
        
    async def rebuild_index(self) -> None:
        if not self.supports_rebuild:
            raise ValueError("Rebuild not supported")
        self.rebuild_called += 1
        # Simulate work
        await asyncio.sleep(0.01)
        
    async def search(self, query: str, limit: int = 10) -> list:
        # Simulate search results
        return [{"id": f"chunk_{i}", "score": 0.8} for i in range(min(limit, 3))]


class MockGraphRepository:
    """Mock graph repository for testing."""
    
    def __init__(self, chunk_count: int = 95):
        self.chunk_count = chunk_count
        
    async def execute_query(self, query: str) -> list:
        if "count(c)" in query:
            return [{"chunk_count": self.chunk_count}]
        elif "c.id" in query and "rand()" in query:
            # Return sample chunk IDs
            return [{"chunk_id": f"chunk_{i}"} for i in range(min(10, self.chunk_count))]
        return []


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    return MockVectorStore()


@pytest.fixture
def mock_graph_repository():
    """Create a mock graph repository."""
    return MockGraphRepository()


@pytest.mark.asyncio
class TestMaintenanceJobs:
    """Test maintenance job classes."""
    
    async def test_faiss_maintenance_job_success(self, mock_vector_store):
        """Test successful FAISS maintenance job execution."""
        job = FaissMaintenanceJob(mock_vector_store)
        
        result = await job.run()
        
        assert result["status"] == MaintenanceJobStatus.SUCCESS.value
        assert "duration_seconds" in result
        assert result["duration_seconds"] > 0
        assert mock_vector_store.rebuild_called == 1
        
        # Check job status
        status = job.get_status()
        assert status["name"] == "faiss_maintenance"
        assert status["status"] == MaintenanceJobStatus.SUCCESS.value
        assert status["run_count"] == 1
        assert status["failure_count"] == 0
    
    async def test_faiss_maintenance_job_failure(self):
        """Test FAISS maintenance job failure handling."""
        mock_store = MockVectorStore(supports_rebuild=False)
        job = FaissMaintenanceJob(mock_store)
        
        result = await job.run()
        
        assert result["status"] == MaintenanceJobStatus.FAILED.value
        assert "error" in result
        assert result["error"] == "Rebuild not supported"
        
        # Check job status
        status = job.get_status()
        assert status["status"] == MaintenanceJobStatus.FAILED.value
        assert status["run_count"] == 1
        assert status["failure_count"] == 1
    
    async def test_faiss_maintenance_job_no_rebuild_support(self):
        """Test FAISS job with vector store that doesn't support rebuild."""
        mock_store = MagicMock()
        # Remove rebuild_index method
        del mock_store.rebuild_index
        
        job = FaissMaintenanceJob(mock_store)
        result = await job.run()
        
        assert result["status"] == MaintenanceJobStatus.FAILED.value
        assert "does not support index rebuilding" in result["error"]
    
    async def test_integrity_check_job_success(self, mock_graph_repository, mock_vector_store):
        """Test successful integrity check execution."""
        job = IntegrityCheckJob(mock_graph_repository, mock_vector_store, sample_size=5)
        
        result = await job.run()
        
        assert result["status"] == MaintenanceJobStatus.SUCCESS.value
        assert "result" in result
        
        check_result = result["result"]
        assert check_result["status"] == "passed"
        assert check_result["graph_chunks"] == 95
        assert check_result["vector_count"] == 100
        assert len(check_result["warnings"]) == 0  # Vector count > graph chunks is acceptable
        assert len(check_result["errors"]) == 0
    
    async def test_integrity_check_missing_embeddings_warning(self):
        """Test integrity check with missing embeddings warning."""
        mock_graph = MockGraphRepository(chunk_count=100)
        mock_vector = MockVectorStore(size=80)  # Fewer vectors than chunks
        
        job = IntegrityCheckJob(mock_graph, mock_vector, sample_size=5)
        result = await job.run()
        
        assert result["status"] == MaintenanceJobStatus.SUCCESS.value
        check_result = result["result"]
        assert len(check_result["warnings"]) >= 1
        assert "less than graph chunks" in check_result["warnings"][0]
    
    async def test_integrity_check_with_json_logging(self, mock_graph_repository, mock_vector_store):
        """Test integrity check with JSON logging enabled."""
        job = IntegrityCheckJob(
            mock_graph_repository, 
            mock_vector_store, 
            sample_size=3, 
            log_json=True
        )
        
        with patch('graph_rag.services.maintenance.jobs.logger') as mock_logger:
            result = await job.run()
            
            # Check that JSON logging was used
            mock_logger.info.assert_called()
            # At least one call should contain JSON data
            json_calls = [call for call in mock_logger.info.call_args_list 
                         if len(call[0]) > 0 and call[0][0].startswith('{')]
            assert len(json_calls) > 0
            
            # Verify JSON format
            json_log = json.loads(json_calls[0][0][0])
            assert "job_name" in json_log
            assert json_log["job_name"] == "integrity_check"
    
    async def test_integrity_check_error_handling(self):
        """Test integrity check error handling when graph query fails."""
        mock_graph = MagicMock()
        mock_graph.execute_query = AsyncMock(side_effect=Exception("Graph connection error"))
        mock_vector = MockVectorStore()
        
        job = IntegrityCheckJob(mock_graph, mock_vector)
        result = await job.run()
        
        assert result["status"] == MaintenanceJobStatus.SUCCESS.value  # Job runs despite errors
        check_result = result["result"]
        assert len(check_result["errors"]) > 0
        assert "Graph connection error" in str(check_result["errors"])


@pytest.mark.asyncio
class TestMaintenanceScheduler:
    """Test maintenance scheduler."""
    
    async def test_scheduler_lifecycle(self):
        """Test scheduler start and stop."""
        scheduler = MaintenanceScheduler(interval_seconds=60)
        
        # Initial state
        assert not scheduler.running
        assert len(scheduler.jobs) == 0
        
        # Start scheduler
        await scheduler.start()
        assert scheduler.running
        
        # Stop scheduler
        await scheduler.stop()
        assert not scheduler.running
    
    async def test_scheduler_add_remove_jobs(self, mock_vector_store):
        """Test adding and removing jobs from scheduler."""
        scheduler = MaintenanceScheduler()
        job = FaissMaintenanceJob(mock_vector_store)
        
        # Add job
        scheduler.add_job(job)
        assert len(scheduler.jobs) == 1
        assert job in scheduler.jobs
        
        # Remove job
        scheduler.remove_job(job)
        assert len(scheduler.jobs) == 0
        assert job not in scheduler.jobs
    
    async def test_scheduler_run_jobs_once(self, mock_vector_store, mock_graph_repository):
        """Test running all jobs once immediately."""
        scheduler = MaintenanceScheduler()
        
        faiss_job = FaissMaintenanceJob(mock_vector_store)
        integrity_job = IntegrityCheckJob(mock_graph_repository, mock_vector_store)
        
        scheduler.add_job(faiss_job)
        scheduler.add_job(integrity_job)
        
        results = await scheduler.run_jobs_once()
        
        assert len(results) == 2
        assert "faiss_maintenance" in results
        assert "integrity_check" in results
        assert results["faiss_maintenance"]["status"] == MaintenanceJobStatus.SUCCESS.value
        assert results["integrity_check"]["status"] == MaintenanceJobStatus.SUCCESS.value
        
        # Verify jobs were actually run
        assert mock_vector_store.rebuild_called == 1
    
    async def test_scheduler_get_status(self, mock_vector_store):
        """Test getting scheduler and job status."""
        scheduler = MaintenanceScheduler(interval_seconds=3600)
        job = FaissMaintenanceJob(mock_vector_store)
        scheduler.add_job(job)
        
        scheduler_status = scheduler.get_scheduler_status()
        assert scheduler_status["running"] is False
        assert scheduler_status["interval_seconds"] == 3600
        assert scheduler_status["job_count"] == 1
        assert "faiss_maintenance" in scheduler_status["jobs"]
        
        job_status = scheduler.get_job_status()
        assert "faiss_maintenance" in job_status
        assert job_status["faiss_maintenance"]["status"] == MaintenanceJobStatus.IDLE.value
    
    async def test_scheduler_trigger_specific_job(self, mock_vector_store):
        """Test triggering a specific job by name."""
        scheduler = MaintenanceScheduler()
        job = FaissMaintenanceJob(mock_vector_store)
        scheduler.add_job(job)
        
        result = await scheduler.trigger_job("faiss_maintenance")
        
        assert result is not None
        assert result["status"] == MaintenanceJobStatus.SUCCESS.value
        assert mock_vector_store.rebuild_called == 1
        
        # Try triggering non-existent job
        result = await scheduler.trigger_job("non_existent")
        assert result is None
    
    async def test_scheduler_job_failure_handling(self):
        """Test scheduler handles job failures gracefully."""
        scheduler = MaintenanceScheduler()
        
        # Create a job that will fail
        failing_store = MockVectorStore(supports_rebuild=False)
        failing_job = FaissMaintenanceJob(failing_store)
        scheduler.add_job(failing_job)
        
        results = await scheduler.run_jobs_once()
        
        assert len(results) == 1
        assert results["faiss_maintenance"]["status"] == MaintenanceJobStatus.FAILED.value
        assert "error" in results["faiss_maintenance"]
    
    async def test_scheduler_minimum_interval(self):
        """Test scheduler enforces minimum interval."""
        scheduler = MaintenanceScheduler(interval_seconds=30)  # Less than minimum
        assert scheduler.interval_seconds == 60  # Should be set to minimum
    
    async def test_scheduler_background_loop_error_recovery(self, mock_vector_store):
        """Test that scheduler recovers from errors in background loop."""
        scheduler = MaintenanceScheduler(interval_seconds=60)
        
        # Create a job that fails intermittently
        class FlakeyJob(FaissMaintenanceJob):
            def __init__(self, vector_store):
                super().__init__(vector_store)
                self.call_count = 0
            
            async def execute(self):
                self.call_count += 1
                if self.call_count == 1:
                    raise Exception("Simulated failure")
                return await super().execute()
        
        flakey_job = FlakeyJob(mock_vector_store)
        scheduler.add_job(flakey_job)
        
        # Start scheduler
        await scheduler.start()
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop scheduler
        await scheduler.stop()
        
        # Scheduler should have handled the error gracefully
        assert not scheduler.running


@pytest.mark.asyncio
class TestMaintenanceIntegration:
    """Integration tests for maintenance system."""
    
    async def test_end_to_end_maintenance_workflow(self, mock_vector_store, mock_graph_repository):
        """Test complete maintenance workflow."""
        # Create scheduler with both jobs
        scheduler = MaintenanceScheduler(interval_seconds=60, log_json=True)
        
        faiss_job = FaissMaintenanceJob(mock_vector_store, log_json=True)
        integrity_job = IntegrityCheckJob(
            mock_graph_repository, 
            mock_vector_store, 
            sample_size=5, 
            log_json=True
        )
        
        scheduler.add_job(faiss_job)
        scheduler.add_job(integrity_job)
        
        # Get initial status
        initial_status = scheduler.get_scheduler_status()
        assert initial_status["job_count"] == 2
        assert not initial_status["running"]
        
        # Run jobs once
        results = await scheduler.run_jobs_once()
        assert len(results) == 2
        
        # Check that both jobs completed successfully
        for job_name, result in results.items():
            assert result["status"] == MaintenanceJobStatus.SUCCESS.value
            assert "duration_seconds" in result
        
        # Verify FAISS rebuild happened
        assert mock_vector_store.rebuild_called == 1
        
        # Check final job status
        final_job_status = scheduler.get_job_status()
        for job_name, status in final_job_status.items():
            assert status["status"] == MaintenanceJobStatus.SUCCESS.value
            assert status["run_count"] == 1
            assert status["failure_count"] == 0
    
    async def test_maintenance_with_concurrent_operations(self, mock_vector_store):
        """Test maintenance jobs can run concurrently."""
        # Create multiple schedulers to simulate concurrent operations
        scheduler1 = MaintenanceScheduler(interval_seconds=60)
        scheduler2 = MaintenanceScheduler(interval_seconds=60)
        
        job1 = FaissMaintenanceJob(mock_vector_store)
        job2 = FaissMaintenanceJob(mock_vector_store)
        
        scheduler1.add_job(job1)
        scheduler2.add_job(job2)
        
        # Run both schedulers concurrently
        results = await asyncio.gather(
            scheduler1.run_jobs_once(),
            scheduler2.run_jobs_once(),
            return_exceptions=True
        )
        
        # Both should complete successfully
        assert len(results) == 2
        for result in results:
            assert not isinstance(result, Exception)
            assert len(result) == 1  # One job each
        
        # Vector store should have been rebuilt twice
        assert mock_vector_store.rebuild_called == 2