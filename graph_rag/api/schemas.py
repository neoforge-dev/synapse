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