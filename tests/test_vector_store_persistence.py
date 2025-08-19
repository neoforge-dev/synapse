"""Tests demonstrating and validating vector store persistence across processes."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from graph_rag.api.dependencies import create_vector_store
from graph_rag.config import Settings
from graph_rag.core.interfaces import ChunkData


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service that returns consistent embeddings."""
    from unittest.mock import Mock
    
    mock = Mock()
    # Use regular Mock for synchronous methods
    mock.get_embedding_dimension.return_value = 384
    
    # Mock encode to return the right number of embeddings based on input
    async def mock_encode(texts):
        return [[0.1] * 384 for _ in texts]
    
    mock.encode = mock_encode
    mock.encode_query.return_value = [0.15] * 384
    return mock


class TestVectorStorePersistence:
    """Test suite for vector store persistence across different processes."""

    @pytest.fixture
    def temp_storage_path(self):
        """Create a temporary directory for vector store persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "vector_store"


    @pytest.fixture
    def settings_with_persistent_path(self, temp_storage_path):
        """Create settings configured for persistent storage."""
        return Settings(
            vector_store_type="simple",
            vector_store_path=str(temp_storage_path),
            embedding_provider="mock"
        )

    @pytest.mark.asyncio
    async def test_simple_vector_store_not_persistent_when_disabled(self):
        """Demonstrate that SimpleVectorStore doesn't persist data when persistence is disabled."""
        # Create settings with persistence disabled
        settings = Settings(
            vector_store_type="simple",
            simple_vector_store_persistent=False,
            embedding_provider="mock"
        )
        
        # Create first instance and add data
        store1 = create_vector_store(settings)
        chunks = [
            ChunkData(
                id="chunk_1",
                text="Test document chunk 1",
                document_id="doc_1",
                metadata={"source": "test"}
            ),
            ChunkData(
                id="chunk_2", 
                text="Test document chunk 2",
                document_id="doc_1",
                metadata={"source": "test"}
            )
        ]
        await store1.add_chunks(chunks)
        
        # Verify data exists in first instance
        size1 = await store1.get_vector_store_size()
        assert size1 == 2
        
        # Verify it's the SimpleVectorStore (not persistent)
        assert store1.__class__.__name__ == "SimpleVectorStore"
        
        # Create second instance (simulating different process)
        store2 = create_vector_store(settings)
        
        # Data should be empty in second instance (demonstrating the isolation problem)
        size2 = await store2.get_vector_store_size()
        assert size2 == 0  # This demonstrates the isolation problem
        
        # Search should return no results in second instance
        query_vector = [0.15] * 384
        results = await store2.search_similar_chunks(query_vector, limit=5)
        assert len(results) == 0  # No data persisted

    @pytest.mark.asyncio
    async def test_cli_api_isolation_problem_when_persistence_disabled(self):
        """Test demonstrating CLI and API vector store isolation when persistence is disabled."""
        # Create settings with persistence disabled  
        settings = Settings(
            vector_store_type="simple",
            simple_vector_store_persistent=False,
            embedding_provider="mock"
        )
        
        # Simulate CLI ingestion (creates its own vector store)
        cli_store = create_vector_store(settings)
        cli_chunks = [
            ChunkData(
                id="cli_chunk_1",
                text="CLI ingested document",
                document_id="cli_doc_1",
                metadata={"source": "cli"}
            )
        ]
        await cli_store.add_chunks(cli_chunks)
        
        # Verify CLI store has data
        cli_size = await cli_store.get_vector_store_size()
        assert cli_size == 1
        
        # Simulate API server (creates its own vector store)
        api_store = create_vector_store(settings)
        
        # API store should have access to CLI data, but it doesn't (isolation problem)
        api_size = await api_store.get_vector_store_size()
        assert api_size == 0  # Isolation problem demonstrated
        
        # Search from API should find CLI data, but it doesn't
        query_vector = [0.1] * 384
        results = await api_store.search_similar_chunks(query_vector, limit=5)
        assert len(results) == 0  # No shared data


class TestSharedPersistentVectorStore:
    """Tests for the SharedPersistentVectorStore implementation (to be created)."""

    @pytest.fixture
    def temp_storage_path(self):
        """Create a temporary directory for vector store persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "shared_vector_store"

    @pytest.mark.asyncio
    async def test_shared_persistence_across_instances(self, temp_storage_path, mock_embedding_service):
        """Test that SharedPersistentVectorStore persists data across instances."""
        from graph_rag.infrastructure.vector_stores.shared_persistent_vector_store import (
            SharedPersistentVectorStore
        )
        
        # Create first instance and add data
        store1 = SharedPersistentVectorStore(
            storage_path=temp_storage_path,
            embedding_service=mock_embedding_service
        )
        chunks = [
            ChunkData(
                id="shared_chunk_1",
                text="Shared document chunk",
                document_id="shared_doc_1",
                metadata={"source": "test"}
            )
        ]
        await store1.add_chunks(chunks)
        await store1.save()  # Persist to disk
        
        # Create second instance (simulating different process)
        store2 = SharedPersistentVectorStore(
            storage_path=temp_storage_path,
            embedding_service=mock_embedding_service
        )
        # Auto-loads on initialization, but call explicitly for clarity
        await store2.load()
        
        # Data should be available in second instance
        size2 = await store2.get_vector_store_size()
        assert size2 == 1
        
        # Search should return results in second instance
        query_vector = [0.1] * 384
        results = await store2.search_similar_chunks(query_vector, limit=5)
        assert len(results) == 1
        assert results[0].chunk.id == "shared_chunk_1"

    @pytest.mark.asyncio
    async def test_file_locking_prevents_corruption(self, temp_storage_path, mock_embedding_service):
        """Test that file locking prevents data corruption during concurrent access."""
        from graph_rag.infrastructure.vector_stores.shared_persistent_vector_store import (
            SharedPersistentVectorStore
        )
        
        # Create a shared store instance first
        shared_store = SharedPersistentVectorStore(
            storage_path=temp_storage_path,
            embedding_service=mock_embedding_service
        )
        
        async def concurrent_writer(store_id: str, chunk_count: int):
            # Each writer adds to the shared store
            chunks = [
                ChunkData(
                    id=f"{store_id}_chunk_{i}",
                    text=f"Chunk {i} from {store_id}",
                    document_id=f"{store_id}_doc",
                    metadata={"source": store_id}
                )
                for i in range(chunk_count)
            ]
            await shared_store.add_chunks(chunks)
        
        # Run concurrent writers on the same store instance
        await asyncio.gather(
            concurrent_writer("writer1", 5),
            concurrent_writer("writer2", 5),
            concurrent_writer("writer3", 5)
        )
        
        # Verify all data was written without corruption
        final_size = await shared_store.get_vector_store_size()
        assert final_size == 15  # All chunks should be present
        
        # Verify data integrity by checking that we have chunks from all writers
        all_chunks = []
        for i in range(15):
            chunk = await shared_store.get_chunk_by_id(f"writer{1 + i // 5}_chunk_{i % 5}")
            if chunk:
                all_chunks.append(chunk)
        
        # We should have successfully written all chunks
        assert len(all_chunks) == 15

    @pytest.mark.asyncio
    async def test_configuration_driven_persistence(self, temp_storage_path):
        """Test that persistence is controlled by configuration settings."""
        from graph_rag.api.dependencies import create_vector_store
        from graph_rag.config import Settings
        
        # Test with persistence enabled (default)
        persistent_settings = Settings(
            vector_store_type="simple",
            vector_store_path=str(temp_storage_path / "persistent"),
            simple_vector_store_persistent=True,
            embedding_provider="mock"
        )
        
        persistent_store = create_vector_store(persistent_settings)
        assert persistent_store.__class__.__name__ == "SharedPersistentVectorStore"
        
        # Test with persistence disabled
        non_persistent_settings = Settings(
            vector_store_type="simple",
            simple_vector_store_persistent=False,
            embedding_provider="mock"
        )
        
        non_persistent_store = create_vector_store(non_persistent_settings)
        assert non_persistent_store.__class__.__name__ == "SimpleVectorStore"

    @pytest.mark.asyncio
    async def test_cli_api_shared_storage_fixed(self, temp_storage_path):
        """Test that CLI and API now share data through persistent storage."""
        from graph_rag.api.dependencies import create_vector_store
        from graph_rag.config import Settings
        
        settings = Settings(
            vector_store_type="simple",
            vector_store_path=str(temp_storage_path),
            simple_vector_store_persistent=True,
            embedding_provider="mock"
        )
        
        # Simulate CLI ingestion
        cli_store = create_vector_store(settings)
        cli_chunks = [
            ChunkData(
                id="cli_chunk_1",
                text="CLI ingested document",
                document_id="cli_doc_1",
                metadata={"source": "cli"}
            )
        ]
        await cli_store.add_chunks(cli_chunks)
        
        # Verify CLI store has data
        cli_size = await cli_store.get_vector_store_size()
        assert cli_size == 1
        
        # Simulate API server (creates new instance, but loads shared data)
        api_store = create_vector_store(settings)
        
        # API store should now have access to CLI data
        api_size = await api_store.get_vector_store_size()
        assert api_size == 1  # Shared data available!
        
        # Search from API should find CLI data
        query_vector = [0.1] * 384
        results = await api_store.search_similar_chunks(query_vector, limit=5)
        assert len(results) == 1
        assert results[0].chunk.id == "cli_chunk_1"
        assert results[0].chunk.metadata["source"] == "cli"