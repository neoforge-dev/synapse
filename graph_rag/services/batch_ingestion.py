"""Incremental batch processing service for large document collections."""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from graph_rag.services.ingestion import IngestionService

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 50
    max_retries: int = 3
    retry_delay: float = 1.0
    progress_callback: Callable[[int, int, int, int], None] | None = None


class BatchProgress(BaseModel):
    """Progress tracking for batch processing."""
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    current_batch: int
    total_batches: int
    files_in_current_batch: int
    processing_rate: float = 0.0  # files per second
    estimated_time_remaining: float = 0.0  # seconds


class FileProcessingResult(BaseModel):
    """Result of processing a single file."""
    file_path: str
    success: bool
    document_id: str | None = None
    chunk_count: int = 0
    error: str | None = None
    processing_time: float = 0.0


class BatchResult(BaseModel):
    """Result of processing a batch of files."""
    batch_number: int
    total_files: int
    successful_files: int
    failed_files: int
    file_results: list[FileProcessingResult]
    processing_time: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this batch."""
        if self.total_files == 0:
            return 1.0
        return self.successful_files / self.total_files


class IncrementalIngestionResult(BaseModel):
    """Final result of incremental batch ingestion."""
    total_files: int
    total_batches: int
    successful_files: int
    failed_files: int
    batch_results: list[BatchResult]
    total_processing_time: float
    failed_file_paths: list[str]

    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_files == 0:
            return 1.0
        return self.successful_files / self.total_files


class IncrementalIngestion:
    """
    Service for processing large document collections in manageable batches.

    Provides progress tracking, error handling, and recovery capabilities
    for sustainable processing of thousands of documents.
    """

    def __init__(
        self,
        ingestion_service: IngestionService,
        config: BatchConfig | None = None,
    ):
        """
        Initialize incremental ingestion service.

        Args:
            ingestion_service: The base ingestion service to use
            config: Batch processing configuration
        """
        self.ingestion_service = ingestion_service
        self.config = config or BatchConfig()
        self._start_time = 0.0
        self._processed_count = 0

    async def process_files(
        self,
        file_paths: list[Path],
        enable_embeddings: bool = False,
        replace_existing: bool = True,
        metadata_parser: Callable[[Path], dict[str, Any]] | None = None,
    ) -> IncrementalIngestionResult:
        """
        Process a list of files in batches with progress tracking.

        Args:
            file_paths: List of file paths to process
            enable_embeddings: Whether to generate embeddings
            replace_existing: Whether to replace existing documents
            metadata_parser: Optional function to extract metadata from files

        Returns:
            IncrementalIngestionResult with processing summary
        """
        logger.info(f"Starting incremental ingestion of {len(file_paths)} files")
        logger.info(f"Batch size: {self.config.batch_size}")

        self._start_time = time.monotonic()
        self._processed_count = 0

        # Split files into batches
        batches = self._create_batches(file_paths)
        total_batches = len(batches)

        logger.info(f"Created {total_batches} batches")

        # Track results
        batch_results: list[BatchResult] = []
        total_successful = 0
        total_failed = 0
        failed_file_paths: list[str] = []

        # Process each batch
        for batch_num, batch_files in enumerate(batches, 1):
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_files)} files)")

            batch_start_time = time.monotonic()

            # Process files in the current batch
            batch_result = await self._process_batch(
                batch_files=batch_files,
                batch_number=batch_num,
                enable_embeddings=enable_embeddings,
                replace_existing=replace_existing,
                metadata_parser=metadata_parser,
            )

            batch_processing_time = time.monotonic() - batch_start_time
            batch_result.processing_time = batch_processing_time

            # Update totals
            total_successful += batch_result.successful_files
            total_failed += batch_result.failed_files
            self._processed_count += len(batch_files)

            # Collect failed file paths
            failed_file_paths.extend([
                result.file_path for result in batch_result.file_results
                if not result.success
            ])

            batch_results.append(batch_result)

            # Report progress
            await self._report_progress(
                batch_num=batch_num,
                total_batches=total_batches,
                processed_files=self._processed_count,
                total_files=len(file_paths),
                successful_files=total_successful,
                failed_files=total_failed,
            )

            # Validate batch before continuing
            if not self._validate_batch_result(batch_result):
                logger.warning(f"Batch {batch_num} validation failed, but continuing")

            # Memory cleanup after each batch
            await self._cleanup_batch_memory()

        total_processing_time = time.monotonic() - self._start_time

        result = IncrementalIngestionResult(
            total_files=len(file_paths),
            total_batches=total_batches,
            successful_files=total_successful,
            failed_files=total_failed,
            batch_results=batch_results,
            total_processing_time=total_processing_time,
            failed_file_paths=failed_file_paths,
        )

        logger.info(f"Incremental ingestion completed in {total_processing_time:.2f}s")
        logger.info(f"Success rate: {result.overall_success_rate:.1%}")
        logger.info(f"Processed {result.successful_files}/{result.total_files} files successfully")

        return result

    def _create_batches(self, file_paths: list[Path]) -> list[list[Path]]:
        """Split file paths into batches."""
        batches = []
        for i in range(0, len(file_paths), self.config.batch_size):
            batch = file_paths[i:i + self.config.batch_size]
            batches.append(batch)
        return batches

    async def _process_batch(
        self,
        batch_files: list[Path],
        batch_number: int,
        enable_embeddings: bool,
        replace_existing: bool,
        metadata_parser: Callable[[Path], dict[str, Any]] | None = None,
    ) -> BatchResult:
        """Process a single batch of files."""
        file_results: list[FileProcessingResult] = []
        successful_count = 0
        failed_count = 0

        for file_path in batch_files:
            result = await self._process_single_file(
                file_path=file_path,
                enable_embeddings=enable_embeddings,
                replace_existing=replace_existing,
                metadata_parser=metadata_parser,
            )

            file_results.append(result)

            if result.success:
                successful_count += 1
                logger.debug(f"Successfully processed: {file_path}")
            else:
                failed_count += 1
                logger.warning(f"Failed to process: {file_path} - {result.error}")

        return BatchResult(
            batch_number=batch_number,
            total_files=len(batch_files),
            successful_files=successful_count,
            failed_files=failed_count,
            file_results=file_results,
            processing_time=0.0,  # Will be set by caller
        )

    async def _process_single_file(
        self,
        file_path: Path,
        enable_embeddings: bool,
        replace_existing: bool,
        metadata_parser: Callable[[Path], dict[str, Any]] | None = None,
    ) -> FileProcessingResult:
        """Process a single file with retry logic."""
        start_time = time.monotonic()

        for attempt in range(self.config.max_retries):
            try:
                # Extract metadata if parser provided
                metadata = {}
                if metadata_parser:
                    try:
                        metadata = metadata_parser(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to parse metadata for {file_path}: {e}")

                # Read file content
                content = file_path.read_text(encoding='utf-8')

                # Derive document ID
                from graph_rag.utils.identity import derive_document_id
                document_id, id_source, _ = derive_document_id(file_path, content, metadata)

                # Add id_source to metadata
                metadata["id_source"] = id_source

                # Ingest document
                ingestion_result = await self.ingestion_service.ingest_document(
                    document_id=document_id,
                    content=content,
                    metadata=metadata,
                    generate_embeddings=enable_embeddings,
                    replace_existing=replace_existing,
                )

                processing_time = time.monotonic() - start_time

                return FileProcessingResult(
                    file_path=str(file_path),
                    success=True,
                    document_id=document_id,
                    chunk_count=ingestion_result.num_chunks,
                    processing_time=processing_time,
                )

            except Exception as e:
                error_msg = str(e)

                if attempt < self.config.max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed for {file_path}: {error_msg}, retrying...")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All {self.config.max_retries} attempts failed for {file_path}: {error_msg}")
                    processing_time = time.monotonic() - start_time

                    return FileProcessingResult(
                        file_path=str(file_path),
                        success=False,
                        error=error_msg,
                        processing_time=processing_time,
                    )

        # Should never reach here, but provide fallback
        processing_time = time.monotonic() - start_time
        return FileProcessingResult(
            file_path=str(file_path),
            success=False,
            error="Unknown error after all retries",
            processing_time=processing_time,
        )

    def _validate_batch_result(self, batch_result: BatchResult) -> bool:
        """Validate batch result to ensure processing quality."""
        # Check if batch has reasonable success rate
        if batch_result.success_rate < 0.5:  # Less than 50% success
            logger.warning(f"Batch {batch_result.batch_number} has low success rate: {batch_result.success_rate:.1%}")
            return False

        # Check if any files were processed
        if batch_result.total_files == 0:
            logger.warning(f"Batch {batch_result.batch_number} processed no files")
            return False

        return True

    async def _report_progress(
        self,
        batch_num: int,
        total_batches: int,
        processed_files: int,
        total_files: int,
        successful_files: int,
        failed_files: int,
    ) -> None:
        """Report current progress."""
        elapsed_time = time.monotonic() - self._start_time
        processing_rate = processed_files / elapsed_time if elapsed_time > 0 else 0

        remaining_files = total_files - processed_files
        estimated_time_remaining = remaining_files / processing_rate if processing_rate > 0 else 0

        logger.info(
            f"Progress: {processed_files}/{total_files} files "
            f"({processed_files/total_files:.1%}) | "
            f"Batch {batch_num}/{total_batches} | "
            f"Success: {successful_files} | Failed: {failed_files} | "
            f"Rate: {processing_rate:.1f} files/s | "
            f"ETA: {estimated_time_remaining:.0f}s"
        )

        # Call progress callback if provided
        if self.config.progress_callback:
            self.config.progress_callback(
                processed_files, total_files, successful_files, failed_files
            )

    async def _cleanup_batch_memory(self) -> None:
        """Clean up memory after processing a batch."""
        # Force garbage collection to manage memory usage
        import gc
        gc.collect()

        # Small delay to allow cleanup
        await asyncio.sleep(0.1)

    async def resume_from_failed(
        self,
        failed_file_paths: list[str],
        enable_embeddings: bool = False,
        replace_existing: bool = True,
        metadata_parser: Callable[[Path], dict[str, Any]] | None = None,
    ) -> IncrementalIngestionResult:
        """
        Resume processing from a list of failed files.

        Args:
            failed_file_paths: List of file paths that failed in previous run
            enable_embeddings: Whether to generate embeddings
            replace_existing: Whether to replace existing documents
            metadata_parser: Optional function to extract metadata from files

        Returns:
            IncrementalIngestionResult with processing summary
        """
        logger.info(f"Resuming processing of {len(failed_file_paths)} failed files")

        failed_paths = [Path(path) for path in failed_file_paths if Path(path).exists()]

        if len(failed_paths) != len(failed_file_paths):
            logger.warning(f"Some failed files no longer exist: {len(failed_file_paths) - len(failed_paths)} missing")

        return await self.process_files(
            file_paths=failed_paths,
            enable_embeddings=enable_embeddings,
            replace_existing=replace_existing,
            metadata_parser=metadata_parser,
        )
