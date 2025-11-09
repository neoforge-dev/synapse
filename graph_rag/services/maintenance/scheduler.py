"""Background task scheduler for maintenance jobs."""

import asyncio
import logging
from datetime import datetime, timezone

from .jobs import MaintenanceJob, MaintenanceJobStatus

logger = logging.getLogger(__name__)


class MaintenanceScheduler:
    """Scheduler for background maintenance jobs."""

    def __init__(self, interval_seconds: int = 86400, log_json: bool = False):
        """Initialize scheduler.

        Args:
            interval_seconds: Interval between job runs in seconds (default: 1 day)
            log_json: Whether to use JSON structured logging
        """
        self.interval_seconds = max(60, interval_seconds)  # Minimum 1 minute
        self.log_json = log_json
        self.jobs: list[MaintenanceJob] = []
        self.running = False
        self._task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

    def add_job(self, job: MaintenanceJob) -> None:
        """Add a maintenance job to the scheduler."""
        if job not in self.jobs:
            self.jobs.append(job)
            logger.info(f"Added maintenance job: {job.name}")

    def remove_job(self, job: MaintenanceJob) -> None:
        """Remove a maintenance job from the scheduler."""
        if job in self.jobs:
            self.jobs.remove(job)
            logger.info(f"Removed maintenance job: {job.name}")

    async def start(self) -> None:
        """Start the background maintenance scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Started maintenance scheduler (interval: {self.interval_seconds}s)")

    async def stop(self) -> None:
        """Stop the background maintenance scheduler."""
        if not self.running:
            return

        self.running = False
        self._shutdown_event.set()

        if self._task:
            try:
                # Wait for current job cycle to complete or timeout after 30 seconds
                await asyncio.wait_for(self._task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Scheduler shutdown timed out, cancelling task")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error(f"Error during scheduler shutdown: {e}")
            finally:
                self._task = None

        logger.info("Maintenance scheduler stopped")

    async def run_jobs_once(self) -> dict[str, dict]:
        """Run all jobs once immediately. Returns job results."""
        if not self.jobs:
            logger.info("No maintenance jobs to run")
            return {}

        logger.info(f"Running {len(self.jobs)} maintenance jobs")
        results = {}

        for job in self.jobs:
            try:
                logger.info(f"Running maintenance job: {job.name}")
                result = await job.run()
                results[job.name] = result
            except Exception as e:
                logger.error(f"Failed to run maintenance job {job.name}: {e}")
                results[job.name] = {
                    "status": MaintenanceJobStatus.FAILED.value,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        logger.info(f"Completed maintenance jobs run: {len(results)} jobs")
        return results

    def get_job_status(self) -> dict[str, dict]:
        """Get status of all jobs."""
        return {job.name: job.get_status() for job in self.jobs}

    def get_scheduler_status(self) -> dict:
        """Get scheduler status."""
        return {
            "running": self.running,
            "interval_seconds": self.interval_seconds,
            "job_count": len(self.jobs),
            "jobs": [job.name for job in self.jobs]
        }

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Maintenance scheduler loop started")

        try:
            while self.running:
                try:
                    # Run maintenance jobs
                    if self.jobs:
                        await self.run_jobs_once()

                    # Wait for next interval or shutdown signal
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.interval_seconds
                        )
                        # If we get here, shutdown was requested
                        break
                    except asyncio.TimeoutError:
                        # Normal timeout, continue with next iteration
                        continue

                except Exception as e:
                    logger.error(f"Error in maintenance scheduler loop: {e}", exc_info=True)
                    # Continue running despite errors, but add a small delay
                    await asyncio.sleep(60)  # Wait 1 minute before retrying

        except asyncio.CancelledError:
            logger.info("Maintenance scheduler loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in maintenance scheduler loop: {e}", exc_info=True)
        finally:
            logger.info("Maintenance scheduler loop ended")

    async def trigger_job(self, job_name: str) -> dict | None:
        """Manually trigger a specific job by name."""
        for job in self.jobs:
            if job.name == job_name:
                logger.info(f"Manually triggering job: {job_name}")
                try:
                    result = await job.run()
                    return result
                except Exception as e:
                    logger.error(f"Failed to trigger job {job_name}: {e}")
                    return {
                        "status": MaintenanceJobStatus.FAILED.value,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

        logger.warning(f"Job not found: {job_name}")
        return None

    def __del__(self):
        """Cleanup on deletion."""
        if self.running and self._task and not self._task.done():
            logger.warning("MaintenanceScheduler deleted while still running")
            # Note: We can't call async stop() from __del__, so we just log a warning
