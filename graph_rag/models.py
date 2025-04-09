from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Chunk:
    """Represents a text chunk derived from a Document."""
    id: str
    text: str
    document_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None # Optional vector embedding
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Document:
    """Represents an input document."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Chunk] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Entity:
    """Represents an extracted entity."""
    id: str
    name: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Relationship:
    """Represents a relationship between two entities."""
    source: Entity
    target: Entity
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class ProcessedDocument(Document):
    """Represents a document after entity/relationship extraction."""
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list) 