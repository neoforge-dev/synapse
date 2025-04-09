from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Node(BaseModel):
    """Base node model for graph entities."""
    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Type of the node")
    properties: dict = Field(default_factory=dict, description="Node properties")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Edge(BaseModel):
    """Base edge model for graph relationships."""
    id: str = Field(..., description="Unique identifier for the edge")
    type: str = Field(..., description="Type of the relationship")
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    properties: dict = Field(default_factory=dict, description="Edge properties")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Document(Node):
    """Document node in the knowledge graph."""
    type: str = "Document"
    content: str = Field(..., description="Document content")
    metadata: dict = Field(default_factory=dict, description="Document metadata")


class Chunk(Node):
    """Text chunk node in the knowledge graph."""
    type: str = "Chunk"
    content: str = Field(..., description="Chunk content")
    document_id: str = Field(..., description="Reference to parent document")
    embedding: Optional[list[float]] = Field(None, description="Vector embedding of the chunk") 