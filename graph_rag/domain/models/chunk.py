from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Import Node as the base class
from .node import Node 

class Chunk(Node):
    """Represents a chunk of text derived from a document."""
    text: str = Field(description="The actual text content of the chunk.")
    document_id: str = Field(description="The ID of the document this chunk belongs to.")
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding of the chunk's content.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata associated with the chunk.")

    # Add a default type for Chunk nodes if needed, overriding Node's default
    type: str = Field(default="Chunk", description="Node type, defaults to Chunk.")

    # Override properties field if specific chunk properties are common
    # properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties specific to the chunk.") 