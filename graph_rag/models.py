from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Chunk:
    """Represents a text chunk derived from a Document.

    Accepts either 'text' or 'content' at initialization time for convenience.
    """

    id: str
    # Support both 'text' and legacy 'content' init kwargs
    text: str | None = None
    document_id: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        # Normalize text/content so both are populated consistently
        if self.text and not self.content:
            self.content = self.text
        elif self.content and not self.text:
            self.text = self.content


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
