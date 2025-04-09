from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# --- Core Data Schemas (for API Responses) ---
# Mirroring core.interfaces data structures but potentially simplified for API

class ChunkResultSchema(BaseModel):
    id: str
    text: str
    document_id: str
    # Exclude embedding by default in API response for brevity

class DocumentResultSchema(BaseModel):
    id: str
    metadata: Dict[str, Any]
    # Exclude content by default in API response for brevity
    # Add created_at/updated_at if needed and available from store

class SearchResultSchema(BaseModel):
    chunk: ChunkResultSchema
    score: float
    document: Optional[DocumentResultSchema] = None # Include simplified doc info

# --- Ingestion Schemas ---

class DocumentIngestRequest(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    document_id: Optional[str] = None # Allow client to specify ID (optional)

class IngestionResponse(BaseModel):
    document_id: str
    status: str = "processing started"
    # We might not know chunk IDs immediately if processing is async

# --- Search Schemas ---

class SearchQueryRequest(BaseModel):
    query: str
    search_type: str = Field("vector", pattern="^(vector|keyword)$") # Enforce allowed types
    limit: int = Field(10, gt=0, le=50) # Sensible limits for results

class SearchQueryResponse(BaseModel):
    query: str
    search_type: str
    results: List[SearchResultSchema]

# --- Update Schemas --- 
# (Keep DocumentUpdateMetadata if PATCH endpoint is still planned)
class DocumentUpdateMetadataRequest(BaseModel):
    metadata: Dict[str, Any] # Require metadata for update

    # Prevent extra fields if needed
    # class Config:
    #     extra = "forbid"

# Response for update could be the updated document metadata or just status
class UpdateResponse(BaseModel):
    document_id: str
    status: str = "updated"

# --- Delete Schemas ---
class DeleteResponse(BaseModel):
    document_id: str
    status: str # e.g., "deleted", "not_found"

# Removed unused/superseded schemas:
# NodeBase, EdgeBase, DocumentCreate, ChunkCreate, DocumentRead, ChunkRead,
# CreateResponse, DocumentIngestionRequest, DocumentIngestionResponse, 
# SearchRequest, VectorSearchRequest, SearchResultResponse, SearchResponse, DocumentUpdateMetadata 

class CreateResponse(BaseModel):
    """Response schema for create operations that return an ID."""
    id: str 

class DocumentCreate(BaseModel):
    """Schema for creating a new document."""
    content: str
    metadata: Optional[Dict[str, Any]] = None

class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: str
    type: str # Added type field
    content: str
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None # Added created_at
    updated_at: Optional[datetime] = None # Added updated_at

class ChunkCreate(BaseModel):
    """Schema for creating a new chunk."""
    text: str
    document_id: str
    metadata: Optional[Dict[str, Any]] = None

class ChunkResponse(BaseModel):
    """Schema for chunk response."""
    id: str
    text: str
    document_id: str
    metadata: Dict[str, Any]

class QueryRequest(BaseModel):
    """Schema for query request."""
    query_text: str
    k: int = 5

class ResultItem(BaseModel):
    """Schema for a single result item."""
    content: str
    metadata: Dict[str, Any]

class QueryResult(BaseModel):
    """Schema for query response."""
    query: str
    results: List[ResultItem] 