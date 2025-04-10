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
        # Add a dummy uri attribute
        driver.uri = "bolt://mock-memgraph:7687"
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

    async def test_get_neighbors_returns_entities(self, repo, mock_driver):
        """Tests that get_neighbors correctly processes results and returns Entity objects."""
        # Setup
        center_entity_id = "center_node"
        neighbor_node_id = "neighbor_node"
        rel_id = "rel_1"
        
        # Mock the neo4j objects returned by the driver
        mock_neighbor_node = MagicMock(spec=dict) # Mock as dict for easier property access
        mock_neighbor_node.get.side_effect = lambda key: {
            "id": neighbor_node_id, 
            "name": "Neighbor Name", 
            "prop1": "value1"
        }.get(key)
        mock_neighbor_node.labels = {"Entity", "Person"} # Example labels
        
        mock_center_node = MagicMock(spec=dict)
        mock_center_node.get.side_effect = lambda key: {"id": center_entity_id}.get(key)

        mock_relationship = MagicMock(spec=dict)
        mock_relationship.element_id = rel_id
        mock_relationship.type = "KNOWS"
        mock_relationship.start_node = mock_center_node
        mock_relationship.end_node = mock_neighbor_node
        # Add __getitem__ to allow dict(mock_relationship)
        mock_relationship.__getitem__.side_effect = lambda key: {"since": "2023"}.get(key)

        # Mock the result record
        mock_record = MagicMock()
        mock_record.__getitem__.side_effect = lambda key: {
            "n": mock_neighbor_node,
            "r": mock_relationship,
            "e": mock_center_node
        }.get(key)

        # Mock the session and its run method to return an async iterator
        session = mock_driver.session.return_value.__aenter__.return_value
        async def async_iterator(items):
            for item in items:
                yield item
        session.run.return_value = async_iterator([mock_record])

        # Execute
        entities, relationships = await repo.get_neighbors(center_entity_id)

        # Verify Query
        session.run.assert_called_once()
        call_args = session.run.call_args[0]
        assert f"MATCH (e {{id: $id}})-[r]-(n)" in call_args[0] # Check default direction/type
        assert call_args[1]["id"] == center_entity_id

        # Verify Results
        assert len(entities) == 1
        assert len(relationships) == 1

        # Verify Entity Conversion
        retrieved_entity = entities[0]
        assert isinstance(retrieved_entity, Entity)
        assert retrieved_entity.id == neighbor_node_id
        assert retrieved_entity.name == "Neighbor Name"
        assert retrieved_entity.type == "Person" # Should pick specific label
        assert retrieved_entity.metadata == {"prop1": "value1"} # Check metadata mapping

        # Verify Relationship Conversion (basic checks)
        retrieved_rel = relationships[0]
        assert isinstance(retrieved_rel, Relationship)
        assert retrieved_rel.source_id == center_entity_id
        assert retrieved_rel.target_id == neighbor_node_id
        assert retrieved_rel.type == "KNOWS"
        assert retrieved_rel.properties == {"since": "2023"}

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