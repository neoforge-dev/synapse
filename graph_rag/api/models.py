from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

# --- Ingestion Models --- 

class IngestRequest(BaseModel):
    """Request model for ingesting a single document."""
    content: str = Field(..., description="The text content of the document to ingest.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the document.")
    document_id: Optional[str] = Field(None, description="Optional explicit ID for the document. If not provided, one may be generated.")

class IngestResponse(BaseModel):
    """Response model after accepting an ingestion request."""
    message: str = "Ingestion task accepted."
    document_id: str = Field(..., description="The final ID assigned to the ingested document.")
    task_id: Optional[str] = Field(None, description="Optional ID for background processing task, if applicable.")

# --- Query Models --- 

class QueryRequest(BaseModel):
    """Request model for submitting a query."""
    query_text: str = Field(..., description="The natural language query.")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional query configuration (e.g., k for vector search).")
    # stream: bool = Field(False, description="Whether to stream the response.") # Add later if streaming is implemented

class QueryResultChunk(BaseModel):
    """Represents a chunk relevant to the query result."""
    id: str
    text: str
    document_id: str
    metadata: Dict[str, Any]
    score: Optional[float] = None # Optional relevance score

class QueryResultGraphContext(BaseModel):
    """Represents graph context relevant to the query result."""
    entities: List[Dict[str, Any]] # Simplified representation for API
    relationships: List[Dict[str, Any]] # Simplified representation for API

class QueryResponse(BaseModel):
    """Response model for a query."""
    answer: str = Field(..., description="The generated answer to the query.")
    relevant_chunks: List[QueryResultChunk] = Field(default_factory=list, description="List of relevant text chunks.")
    graph_context: Optional[QueryResultGraphContext] = Field(None, description="Context retrieved from the knowledge graph.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the query execution.")

# --- Admin/Management Models (Add later if needed) --- 

class SystemStatus(BaseModel):
    status: str = "OK"
    memgraph_connected: bool
    vector_store_status: str # e.g., OK, Unavailable
    # Add more status indicators as needed 