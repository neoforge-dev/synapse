"""Test data for GraphRAG tests."""

from typing import Dict, List, Any
from datetime import datetime

# --- Sample Documents ---

SAMPLE_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "doc_1",
        "content": "John Smith works at Acme Corp. He lives in New York.",
        "metadata": {
            "source": "test",
            "created_at": datetime.utcnow().isoformat()
        }
    },
    {
        "id": "doc_2",
        "content": "Acme Corp is a technology company based in New York.",
        "metadata": {
            "source": "test",
            "created_at": datetime.utcnow().isoformat()
        }
    }
]

# --- Sample Chunks ---

SAMPLE_CHUNKS: List[Dict[str, Any]] = [
    {
        "id": "chunk_1",
        "text": "John Smith works at Acme Corp.",
        "document_id": "doc_1",
        "embedding": [0.1, 0.2, 0.3]
    },
    {
        "id": "chunk_2",
        "text": "He lives in New York.",
        "document_id": "doc_1",
        "embedding": [0.4, 0.5, 0.6]
    },
    {
        "id": "chunk_3",
        "text": "Acme Corp is a technology company based in New York.",
        "document_id": "doc_2",
        "embedding": [0.7, 0.8, 0.9]
    }
]

# --- Sample Entities ---

SAMPLE_ENTITIES: List[Dict[str, Any]] = [
    {
        "id": "person_1",
        "name": "John Smith",
        "type": "PERSON",
        "metadata": {"confidence": 0.95}
    },
    {
        "id": "org_1",
        "name": "Acme Corp",
        "type": "ORGANIZATION",
        "metadata": {"confidence": 0.90}
    },
    {
        "id": "loc_1",
        "name": "New York",
        "type": "LOCATION",
        "metadata": {"confidence": 0.95}
    }
]

# --- Sample Relationships ---

SAMPLE_RELATIONSHIPS: List[Dict[str, Any]] = [
    {
        "source_id": "person_1",
        "target_id": "org_1",
        "type": "WORKS_AT",
        "metadata": {"confidence": 0.85}
    },
    {
        "source_id": "person_1",
        "target_id": "loc_1",
        "type": "LIVES_IN",
        "metadata": {"confidence": 0.90}
    },
    {
        "source_id": "org_1",
        "target_id": "loc_1",
        "type": "BASED_IN",
        "metadata": {"confidence": 0.95}
    }
]

# --- Sample Queries ---

SAMPLE_QUERIES: List[Dict[str, Any]] = [
    {
        "query": "Where does John Smith work?",
        "expected_entities": ["John Smith"],
        "expected_relationships": ["WORKS_AT"]
    },
    {
        "query": "What companies are based in New York?",
        "expected_entities": ["New York"],
        "expected_relationships": ["BASED_IN"]
    }
] 