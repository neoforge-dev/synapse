"""Unit tests for the graph store implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from graph_rag.core.graph_store import GraphStore
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from tests.utils.test_helpers import (
    create_test_document,
    create_test_chunk,
    create_test_entity,
    create_test_relationship
)
from tests.utils.test_data import SAMPLE_DOCUMENTS, SAMPLE_CHUNKS, SAMPLE_ENTITIES, SAMPLE_RELATIONSHIPS

@pytest.mark.unit
class TestMemgraphGraphRepository:
    """Unit tests for MemgraphGraphRepository."""

    @pytest.fixture
    def mock_driver(self):
        """Creates a mock Neo4j driver."""
        driver = AsyncMock()
        session = AsyncMock()
        driver.session.return_value.__aenter__.return_value = session
        return driver

    @pytest.fixture
    def repo(self, mock_driver):
        """Creates a MemgraphGraphRepository instance with a mock driver."""
        return MemgraphGraphRepository(driver=mock_driver)

    async def test_add_document(self, repo, mock_driver):
        """Tests adding a document to the graph store."""
        # Setup
        doc = create_test_document()
        session = mock_driver.session.return_value.__aenter__.return_value

        # Execute
        await repo.add_document(doc)

        # Verify
        session.run.assert_called_once()
        call_args = session.run.call_args[0]
        assert "MERGE (d:Document {id: $id})" in call_args[0]
        assert call_args[1]["id"] == doc.id

    async def test_add_chunk(self, repo, mock_driver):
        """Tests adding a chunk to the graph store."""
        # Setup
        chunk = create_test_chunk()
        session = mock_driver.session.return_value.__aenter__.return_value

        # Execute
        await repo.add_chunk(chunk)

        # Verify
        session.run.assert_called_once()
        call_args = session.run.call_args[0]
        assert "MATCH (d:Document {id: $doc_id})" in call_args[0]
        assert "MERGE (c:Chunk {id: $id})" in call_args[0]
        assert call_args[1]["id"] == chunk.id
        assert call_args[1]["doc_id"] == chunk.document_id

    async def test_add_entity(self, repo, mock_driver):
        """Tests adding an entity to the graph store."""
        # Setup
        entity = create_test_entity()
        session = mock_driver.session.return_value.__aenter__.return_value

        # Execute
        await repo.add_entity(entity)

        # Verify
        session.run.assert_called_once()
        call_args = session.run.call_args[0]
        assert f"MERGE (n:{entity.type} {{id: $id}})" in call_args[0]
        assert call_args[1]["id"] == entity.id

    async def test_add_relationship(self, repo, mock_driver):
        """Tests adding a relationship to the graph store."""
        # Setup
        source = create_test_entity(entity_id="source_1")
        target = create_test_entity(entity_id="target_1")
        relationship = create_test_relationship(source, target)
        session = mock_driver.session.return_value.__aenter__.return_value

        # Execute
        await repo.add_relationship(relationship)

        # Verify
        session.run.assert_called_once()
        call_args = session.run.call_args[0]
        assert "MATCH (source {id: $source_id}), (target {id: $target_id})" in call_args[0]
        assert f"MERGE (source)-[r:{relationship.type}]->(target)" in call_args[0]
        assert call_args[1]["source_id"] == source.id
        assert call_args[1]["target_id"] == target.id

    async def test_error_handling(self, repo, mock_driver):
        """Tests error handling in the graph store."""
        # Setup
        doc = create_test_document()
        session = mock_driver.session.return_value.__aenter__.return_value
        session.run.side_effect = Exception("Test error")

        # Execute and verify
        with pytest.raises(Exception) as exc_info:
            await repo.add_document(doc)
        assert str(exc_info.value) == "Test error" 