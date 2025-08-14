import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from graph_rag.core.interfaces import (
    DocumentProcessor,
    EmbeddingService,
    EntityExtractor,
    GraphRepository,
    VectorStore,
)
from graph_rag.domain.models import Document
from graph_rag.services.ingestion import IngestionService


@pytest.fixture
def svc() -> IngestionService:
    repo = AsyncMock(spec=GraphRepository)
    repo.add_document = AsyncMock()
    repo.add_chunk = AsyncMock()
    repo.add_relationship = AsyncMock()

    dp = AsyncMock(spec=DocumentProcessor)
    extractor = MagicMock(spec=EntityExtractor)
    embed = AsyncMock(spec=EmbeddingService)
    vstore = AsyncMock(spec=VectorStore)

    return IngestionService(
        document_processor=dp,
        entity_extractor=extractor,
        graph_store=repo,
        embedding_service=embed,
        vector_store=vstore,
    )


@pytest.mark.asyncio
async def test_extract_topics_from_metadata_list(svc: IngestionService):
    doc_id = str(uuid.uuid4())
    content = "# Title\nBody"
    metadata = {"topics": ["ai", "ml"]}

    # Avoid downstream calls
    svc.document_processor.chunk_document.return_value = []

    result = await svc.ingest_document(doc_id, content, metadata, generate_embeddings=False)
    assert result.document_id == doc_id
    # Ensures topics preserved on saved document
    doc_call = svc.graph_store.add_document.call_args.args[0]
    assert isinstance(doc_call, Document)
    assert doc_call.metadata.get("topics") == ["ai", "ml"]


@pytest.mark.asyncio
async def test_extract_topics_from_heading_when_missing(svc: IngestionService):
    doc_id = str(uuid.uuid4())
    content = "# My Big Idea\nSome text"
    metadata = {}

    svc.document_processor.chunk_document.return_value = []

    await svc.ingest_document(doc_id, content, metadata, generate_embeddings=False)
    doc_call = svc.graph_store.add_document.call_args.args[0]
    assert doc_call.metadata.get("topics") == ["My Big Idea"]
