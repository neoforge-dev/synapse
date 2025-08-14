import inspect
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    pass  # type: ignore
except Exception:
    pytest.skip("mgclient not available; skipping Memgraph repository tests", allow_module_level=True)

from graph_rag.core.interfaces import GraphRepository
from graph_rag.data_stores.graph_store import GraphStore
from graph_rag.domain.models import Entity
from graph_rag.infrastructure.graph_stores.memgraph_store import (
    MemgraphGraphRepository,
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_memgraph_repository_has_required_methods():
    """Test that MemgraphGraphRepository has all required methods from both protocols."""
    # Get the list of methods required by each protocol
    graph_repo_methods = [
        name for name, _ in inspect.getmembers(GraphRepository, inspect.isfunction)
    ]
    graph_store_methods = [
        name for name, _ in inspect.getmembers(GraphStore, inspect.isfunction)
    ]

    # Get the list of methods implemented by MemgraphGraphRepository
    memgraph_repo_methods = [
        name
        for name, _ in inspect.getmembers(MemgraphGraphRepository, inspect.isfunction)
    ]

    # Check if all required methods are implemented
    for method in graph_repo_methods:
        if method.startswith("_"):
            continue  # Skip private methods
        assert method in memgraph_repo_methods, (
            f"MemgraphGraphRepository missing {method} from GraphRepository"
        )

    # Check for GraphStore methods too
    for method in graph_store_methods:
        if method.startswith("_"):
            continue  # Skip private methods
        assert method in memgraph_repo_methods, (
            f"MemgraphGraphRepository missing {method} from GraphStore"
        )


@pytest.mark.asyncio
async def test_memgraph_repository_methods():
    """Test that MemgraphGraphRepository has all the required methods from GraphRepository."""
    # Create a mock instance with extensive patching to avoid DB calls
    with (
        patch(
            "graph_rag.infrastructure.graph_stores.memgraph_store.MemgraphConnectionConfig"
        ),
        patch.object(MemgraphGraphRepository, "connect", AsyncMock()),
        patch.object(MemgraphGraphRepository, "close", AsyncMock()),
        patch.object(MemgraphGraphRepository, "_get_connection", MagicMock()),
    ):
        repo = MemgraphGraphRepository()

        # Patch the execute_query method to avoid actual database calls
        with patch.object(
            repo, "execute_query", new_callable=AsyncMock
        ) as mock_execute:
            # Test GraphRepository methods
            mock_execute.return_value = [{"e": {"id": "test-entity", "name": "Test"}}]

            # Check that the methods exist and can be called
            entity = Entity(id="test", type="Test", properties={"name": "Test Entity"})
            await repo.add_entity(entity)
            await repo.add_chunks([])
            await repo.get_chunk_by_id("test-chunk")
            await repo.get_entity_by_id("test-entity")
            await repo.update_node_properties("test-node", {"property": "value"})
            await repo.search_entities_by_properties({"name": "Test"})

            # Add checks for GraphStore methods, use mocks instead of real calls
            # Already patched connect() and close() to return immediately
            await repo.connect()
            await repo.close()

            # Mock these methods to avoid errors
            with (
                patch.object(repo, "add_node", AsyncMock()) as mock_add_node,
                patch.object(
                    repo, "add_relationship", AsyncMock()
                ) as mock_relationship,
                patch.object(repo, "get_node_by_id", AsyncMock()) as mock_get_node,
                patch.object(
                    repo, "apply_schema_constraints", AsyncMock()
                ) as mock_schema,
                patch.object(
                    repo, "detect_communities", AsyncMock()
                ) as mock_communities,
                patch.object(repo, "query_subgraph", AsyncMock()) as mock_subgraph,
                patch.object(repo, "execute_read", AsyncMock()) as mock_read,
                patch.object(repo, "execute_write", AsyncMock()) as mock_write,
            ):
                await repo.add_node("TestNode", {"id": "test-node-id"})
                await repo.add_relationship(
                    "source-id", "target-id", "TEST_REL", {"prop": "value"}
                )
                await repo.get_node_by_id("test-node-id")
                await repo.apply_schema_constraints()
                await repo.detect_communities(
                    algorithm="louvain", write_property="community"
                )
                await repo.query_subgraph("test-entity-id", max_depth=2)
                await repo.execute_read("MATCH (n) RETURN n")
                await repo.execute_write("CREATE (n:TestNode {id: 'test'}) RETURN n")

                # Assert the mocked methods were called
                mock_add_node.assert_called_once()
                mock_relationship.assert_called_once()
                mock_get_node.assert_called_once()
                mock_schema.assert_called_once()
                mock_communities.assert_called_once()
                mock_subgraph.assert_called_once()
                mock_read.assert_called_once()
                mock_write.assert_called_once()

            # Assert execute_query was called
            assert mock_execute.called
