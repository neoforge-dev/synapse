import pytest
import asyncio
from pathlib import Path
import tempfile
import json
from typing import Dict, Any
import logging
import uuid
from unittest.mock import AsyncMock, MagicMock
from typer.testing import CliRunner

# Use the actual CLI processing function
from graph_rag.cli.commands.ingest import process_and_store_document
# Use the Memgraph repo fixture
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.core.document_processor import SimpleDocumentProcessor, SentenceSplitter # Use concrete splitter
from graph_rag.core.entity_extractor import SpacyEntityExtractor
# Import the domain model for assertion checks if needed
from graph_rag.domain.models import Document 
# Correct import for the CLI Typer app
from graph_rag.cli.main import app as cli_app # Assuming the Typer app is named 'app' in main.py
from graph_rag.config import settings # Needed for potential overrides

logger = logging.getLogger(__name__)

runner = CliRunner()

@pytest.fixture
def test_document() -> str:
    """Create a test document with known entities."""
    return """
    The Eiffel Tower is a wrought-iron lattice tower in Paris, France.
    It was designed by Gustave Eiffel and completed in 1889.
    The tower is 330 meters tall and is the most-visited paid monument in the world.
    """

@pytest.fixture
def test_metadata() -> Dict[str, Any]:
    """Create test metadata."""
    return {
        "source": "test-cli-ingest", # Make source unique for querying
        "type": "factual",
        "language": "en"
    }

@pytest.fixture
def mock_document_processor(mocker): # Corrected fixture name
    pass # Add pass to fix IndentationError

@pytest.mark.asyncio
async def test_process_and_store_document_cli_logic( # Rename test for clarity
    test_document: str,
    test_metadata: Dict[str, Any],
    memgraph_repo: MemgraphGraphRepository # Use the fixture from conftest
):
    """Test the core document processing and storage logic from the CLI command."""
    doc_content_for_query = test_document # Store for assertion query

    # Create a temporary file with the test document content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding='utf-8', delete=False) as f:
        f.write(test_document)
        file_path = Path(f.name)

    # Define a query to find the document later based on unique metadata
    find_doc_query = "MATCH (d:Document {source: $source}) RETURN d.id as id, d.content as content, d.metadata as metadata LIMIT 1"
    find_doc_params = {"source": test_metadata["source"]}

    try:
        # Initialize components needed by the function
        doc_processor = SimpleDocumentProcessor(chunk_strategy="paragraph")
        entity_extractor = SpacyEntityExtractor() # Assumes model is downloaded/available

        # Call the CLI processing function directly
        await process_and_store_document(
            file_path=file_path,
            metadata_dict=test_metadata,
            graph_repository=memgraph_repo, # Pass the correct repo instance
            doc_processor=doc_processor,
            entity_extractor=entity_extractor
            # No kg_builder needed here
        )

        # Verify document was stored by querying metadata/content
        # Allow some time for potential async writes if necessary, though await should handle it
        await asyncio.sleep(0.1) 
        result = await memgraph_repo._execute_read_query(find_doc_query, find_doc_params)

        assert result is not None and len(result) == 1, f"Document with source '{test_metadata['source']}' not found."
        stored_doc_data = result[0]
        doc_id = stored_doc_data["id"] # Get the generated ID for further checks

        assert stored_doc_data["content"] == doc_content_for_query
        assert stored_doc_data["metadata"] == test_metadata

        # Verify chunks were created and linked (Requires get_chunks_by_document_id or direct query)
        # Example direct query:
        chunk_check_query = "MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk) RETURN count(c) as count"
        chunk_result = await memgraph_repo._execute_read_query(chunk_check_query, {"doc_id": doc_id})
        assert chunk_result[0]["count"] > 0, "No chunks found linked to the document."

        # Verify entities were extracted and linked
        entity_check_query = """
        MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk)<-[:MENTIONED_IN]-(e:Entity)
        RETURN DISTINCT e.name as name 
        """
        # Note: process_and_store_document stores entity 'text', not 'name'. Adjust query/code.
        # Assuming entity node has 'text' property based on process_and_store_document code:
        entity_check_query_alt = """
        MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk)-[:MENTIONS]->(e:Entity) 
        RETURN DISTINCT e.text as name 
        """ # Relationship is :MENTIONS based on process_and_store_document
        result_entities = await memgraph_repo._execute_read_query(entity_check_query_alt, {"doc_id": doc_id})
        
        extracted_entities = {r["name"] for r in result_entities}
        logger.info(f"Extracted entities for doc {doc_id}: {extracted_entities}")
        assert len(extracted_entities) > 0
        assert "Eiffel Tower" in extracted_entities
        assert "Paris" in extracted_entities
        assert "Gustave Eiffel" in extracted_entities

    finally:
        # Clean up the temporary file
        if file_path.exists():
            file_path.unlink()
            
        # Clean up the graph using the retrieved doc_id if found
        if 'doc_id' in locals() and doc_id:
             await memgraph_repo._execute_write_query("MATCH (d:Document {id: $doc_id}) DETACH DELETE d", {"doc_id": doc_id})
        else: # Fallback cleanup based on metadata if doc_id wasn't retrieved
             await memgraph_repo._execute_write_query("MATCH (d:Document {source: $source}) DETACH DELETE d", find_doc_params)

@pytest.mark.asyncio
async def test_ingest_single_file_success(memgraph_repo: MemgraphGraphRepository, mock_document_processor, tmp_path):
    """Test successful ingestion of a single file using the CLI."""
    # ... existing code ...

@pytest.mark.asyncio
async def test_ingest_directory_success(memgraph_repo: MemgraphGraphRepository, mock_document_processor, tmp_path):
    """Test successful ingestion of a directory using the CLI."""
    # ... existing code ...

@pytest.mark.asyncio
async def test_ingest_file_not_found(memgraph_repo: MemgraphGraphRepository, mock_document_processor):
    """Test ingestion command when the file does not exist."""
    # ... existing code ...

@pytest.mark.asyncio
async def test_ingest_processing_error(memgraph_repo: MemgraphGraphRepository, mock_document_processor, tmp_path):
    """Test ingestion command when document processing fails."""
    # ... existing code ...

@pytest.mark.asyncio
async def test_ingest_repository_error(memgraph_repo: MemgraphGraphRepository, mock_document_processor, tmp_path, mocker):
    """Test ingestion command when adding to the repository fails."""
    # ... existing code ...

# Error handling tests for the CLI function need separate design
# They would test argument parsing, file existence checks, etc., which happen *before*
# process_and_store_document is called.
# These tests might be better suited for a CliRunner approach.
# Commenting out the old stubs.

# @pytest.mark.asyncio
# async def test_process_and_store_document_error_handling(...)
# @pytest.mark.asyncio
# async def test_process_and_store_document_invalid_metadata(...) 