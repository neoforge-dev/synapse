"""Test data for GraphRAG tests."""

import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np

from graph_rag.core.interfaces import ChunkData, DocumentData

# Embedding dimension constant (adjust as needed)
EMBEDDING_DIM = 384


def create_test_document_data(**kwargs) -> DocumentData:
    """Helper to create DocumentData for tests."""
    defaults = {
        "id": str(uuid.uuid4()),
        "content": "This is a test document.",
        "metadata": {
            "source": "test",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    defaults.update(kwargs)
    return DocumentData(**defaults)


def create_test_chunk_data(**kwargs) -> ChunkData:
    """Helper to create ChunkData for tests."""
    defaults = {
        "id": str(uuid.uuid4()),
        "document_id": kwargs.get(
            "document_id", str(uuid.uuid4())
        ),  # Ensure document_id exists
        "text": "This is a test chunk.",
        "metadata": {
            "source_document": "test_doc",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "embedding": np.random.rand(EMBEDDING_DIM).tolist(),
    }
    # Ensure embedding matches expectation if provided
    if "embedding" in kwargs:
        defaults["embedding"] = kwargs["embedding"]

    defaults.update(kwargs)
    # Ensure embedding is always set, even if not provided in kwargs
    if "embedding" not in defaults or defaults["embedding"] is None:
        defaults["embedding"] = np.random.rand(EMBEDDING_DIM).tolist()

    return ChunkData(**defaults)


# --- Sample Documents ---

SAMPLE_DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "doc_1",
        "content": "John Smith works at Acme Corp. He lives in New York.",
        "metadata": {
            "source": "test",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    },
    {
        "id": "doc_2",
        "content": "Acme Corp is a technology company based in New York.",
        "metadata": {
            "source": "test",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    },
]

# --- Sample Chunks ---

SAMPLE_CHUNKS: list[dict[str, Any]] = [
    {
        "id": "chunk_1",
        "text": "John Smith works at Acme Corp.",
        "document_id": "doc_1",
        "embedding": [0.1, 0.2, 0.3],
    },
    {
        "id": "chunk_2",
        "text": "He lives in New York.",
        "document_id": "doc_1",
        "embedding": [0.4, 0.5, 0.6],
    },
    {
        "id": "chunk_3",
        "text": "Acme Corp is a technology company based in New York.",
        "document_id": "doc_2",
        "embedding": [0.7, 0.8, 0.9],
    },
]

# --- Sample Entities ---

SAMPLE_ENTITIES: list[dict[str, Any]] = [
    {
        "id": "person_1",
        "name": "John Smith",
        "type": "PERSON",
        "metadata": {"confidence": 0.95},
    },
    {
        "id": "org_1",
        "name": "Acme Corp",
        "type": "ORGANIZATION",
        "metadata": {"confidence": 0.90},
    },
    {
        "id": "loc_1",
        "name": "New York",
        "type": "LOCATION",
        "metadata": {"confidence": 0.95},
    },
]

# --- Sample Relationships ---

SAMPLE_RELATIONSHIPS: list[dict[str, Any]] = [
    {
        "source_id": "person_1",
        "target_id": "org_1",
        "type": "WORKS_AT",
        "metadata": {"confidence": 0.85},
    },
    {
        "source_id": "person_1",
        "target_id": "loc_1",
        "type": "LIVES_IN",
        "metadata": {"confidence": 0.90},
    },
    {
        "source_id": "org_1",
        "target_id": "loc_1",
        "type": "BASED_IN",
        "metadata": {"confidence": 0.95},
    },
]

# --- Sample Queries ---

SAMPLE_QUERIES: list[dict[str, Any]] = [
    {
        "query": "Where does John Smith work?",
        "expected_entities": ["John Smith"],
        "expected_relationships": ["WORKS_AT"],
    },
    {
        "query": "What companies are based in New York?",
        "expected_entities": ["New York"],
        "expected_relationships": ["BASED_IN"],
    },
]


# Document data examples
def get_sample_document_data(doc_id: str = "doc-1") -> DocumentData:
    return DocumentData(
        id=doc_id,
        content="Alice lives in Wonderland. Bob works at Acme Corp.",
        metadata={"source": "fiction", "year": 1865},
    )


def get_another_sample_document_data(doc_id: str = "doc-2") -> DocumentData:
    return DocumentData(
        id=doc_id,
        content="Quantum physics is fascinating. Graphs are useful.",
        metadata={"source": "science", "category": "physics"},
    )


# Chunk data examples
def get_sample_chunk_data(
    chunk_id: str = "chunk-1a", doc_id: str = "doc-1", embedding=None
) -> ChunkData:
    if embedding is None:
        embedding = np.random.rand(EMBEDDING_DIM).tolist()
    return ChunkData(
        id=chunk_id,
        document_id=doc_id,
        text="Alice lives in Wonderland.",
        metadata={"sentence_num": 1},
        embedding=embedding,
    )


def get_another_sample_chunk_data(
    chunk_id: str = "chunk-1b", doc_id: str = "doc-1", embedding=None
) -> ChunkData:
    if embedding is None:
        embedding = np.random.rand(EMBEDDING_DIM).tolist()
    return ChunkData(
        id=chunk_id,
        document_id=doc_id,
        text="Bob works at Acme Corp.",
        metadata={"sentence_num": 2},
        embedding=embedding,
    )
