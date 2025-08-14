from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Chunk:
    """Represents a text chunk derived from a Document."""

    id: str
    text: str
    document_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None  # Optional vector embedding
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Document:
    """Represents an input document."""

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunks: list[Chunk] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Entity:
    """Represents an extracted entity."""

    id: str
    name: str
    type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Relationship:
    """Represents a relationship between two entities."""

    source: Entity
    target: Entity
    type: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class ProcessedDocument(Document):
    """Represents a document after entity/relationship extraction."""

    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
