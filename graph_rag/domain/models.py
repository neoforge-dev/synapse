from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Node(BaseModel):
    """Base node model for graph entities."""

    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Type of the node")
    properties: dict = Field(default_factory=dict, description="Node properties")
    created_at: datetime | None = Field(
        None, description="Timestamp of node creation"
    )
    updated_at: datetime | None = Field(
        None, description="Timestamp of last node update"
    )


class Edge(BaseModel):
    """Base edge model for graph relationships."""

    id: str = Field(..., description="Unique identifier for the edge")
    type: str = Field(..., description="Type of the relationship")
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    properties: dict = Field(default_factory=dict, description="Edge properties")
    created_at: datetime | None = Field(
        None, description="Timestamp of edge creation"
    )
    updated_at: datetime | None = Field(
        None, description="Timestamp of last edge update"
    )


class Document(Node):
    """Document node in the knowledge graph."""

    type: str = "Document"
    content: str = Field(..., description="Document content")
    metadata: dict = Field(default_factory=dict, description="Document metadata")


class Chunk(Node):
    """Text chunk node in the knowledge graph."""

    type: str = "Chunk"
    text: str = Field(..., description="Chunk text content")
    document_id: str = Field(..., description="Reference to parent document")
    embedding: list[float] | None = Field(
        None, description="Vector embedding of the chunk"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata associated with the chunk."
    )
    score: float = Field(default=0.0, description="Search relevance score")


class Entity(Node):
    """Represents a generic entity node in the graph."""

    type: str = "Entity"
    # Entities might have specific common properties, like 'name'
    # Add them here if needed, otherwise inherits properties dict from Node
    name: str | None = Field(None, description="Canonical name of the entity")


# Type alias for clarity where Relationship is expected
Relationship = Edge

# --- Context Model ---


class Context(BaseModel):
    """Model to hold the retrieved context for a query."""

    entities: list[Entity] = Field(
        default_factory=list, description="Relevant entities retrieved from the graph."
    )
    relationships: list[Relationship] = Field(
        default_factory=list,
        description="Relationships connecting the relevant entities.",
    )
    # Add other context elements as needed, e.g.:
    # chunks: List[Chunk] = Field(default_factory=list)
    # documents: List[Document] = Field(default_factory=list)
