from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

# --- Ingestion Models --- 

class IngestRequest(BaseModel):
    """Request model for ingesting a single document."""
    content: str = Field(..., description="The text content of the document to ingest.", min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the document.")
    document_id: Optional[str] = Field(None, description="Optional explicit ID for the document. If not provided, one may be generated.")

class IngestResponse(BaseModel):
    """Response model after accepting an ingestion request."""
    message: str = Field(..., description="Status message about the ingestion request.")
    document_id: str = Field(..., description="The ID assigned to the ingested document.")
    task_id: str = Field(..., description="Unique ID for tracking the ingestion task.")
    status: str = Field("processing", description="Current status of the ingestion task.")

# --- Query Models --- 

class QueryRequest(BaseModel):
    """Request model for submitting a query."""
    query_text: str = Field(..., description="The user's query text.")
    k: int = Field(3, description="Number of results to return.")

class ResultItem(BaseModel):
    """Represents a single result item from a query."""
    content: str = Field(..., description="The content of the result (e.g., chunk text).")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the result (e.g., chunk_id, document_id).")

class QueryResult(BaseModel):
    """Response model for a query result."""
    query: str = Field(..., description="The original query text.")
    results: List[ResultItem] = Field(..., description="List of relevant results matching the query.")

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