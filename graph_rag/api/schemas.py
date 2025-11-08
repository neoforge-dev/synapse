from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Core Data Schemas (for API Responses) ---
# Mirroring core.interfaces data structures but potentially simplified for API


class ChunkResultSchema(BaseModel):
    id: str
    text: str
    document_id: str | None = "unknown"  # Allow None, default to unknown
    score: float | None = None
    properties: dict[str, Any] | None = None  # Add properties field


class DocumentResultSchema(BaseModel):
    id: str
    metadata: dict[str, Any]
    # Exclude content by default in API response for brevity
    # Add created_at/updated_at if needed and available from store


class SearchResultSchema(BaseModel):
    chunk: ChunkResultSchema
    score: float
    document: DocumentResultSchema | None = None  # Include simplified doc info


# --- Ingestion Schemas ---


class DocumentIngestRequest(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    document_id: str | None = None  # Allow client to specify ID (optional)
    generate_embeddings: bool = Field(
        True,
        description="Generate embeddings for the ingested document chunks.",
    )
    replace_existing: bool = Field(
        True,
        description="Replace existing chunks when the document_id already exists.",
    )


class IngestionResponse(BaseModel):
    document_id: str
    status: str = "processing started"
    # We might not know chunk IDs immediately if processing is async


# --- Search Schemas ---


class SearchQueryRequest(BaseModel):
    query: str
    search_type: str = Field(
        "vector", pattern="^(vector|keyword)$"
    )  # Enforce allowed types
    limit: int = Field(10, gt=0, le=50)  # Sensible limits for results


class ErrorDetail(BaseModel):
    """Standard error response detail."""

    message: str
    type: str | None = None


class SearchQueryResponse(BaseModel):
    query: str
    search_type: str
    results: list[SearchResultSchema] = []
    llm_response: str | None = None
    graph_context: str | None = None
    # Fields specifically for batch responses
    status_code: int | None = None
    error: ErrorDetail | None = None


class SearchBatchQueryRequest(BaseModel):
    queries: list[SearchQueryRequest] = Field(
        ..., min_length=1, max_length=10
    )  # Require at least one query, cap at 10


# --- Update Schemas ---
# (Keep DocumentUpdateMetadata if PATCH endpoint is still planned)
class DocumentUpdateMetadataRequest(BaseModel):
    metadata: dict[str, Any]  # Require metadata for update

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
    status: str  # e.g., "deleted", "not_found"


# Removed unused/superseded schemas:
# NodeBase, EdgeBase, DocumentCreate, ChunkCreate, DocumentRead, ChunkRead,
# CreateResponse, DocumentIngestionRequest, DocumentIngestionResponse,
# SearchRequest, VectorSearchRequest, SearchResultResponse, SearchResponse, DocumentUpdateMetadata


class CreateResponse(BaseModel):
    """Response schema for create operations that return an ID."""

    id: str


# --- Document Schemas ---
# Removed DocumentProperties as it's not used directly in the response


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    id: str | None = Field(
        default=None, description="Optional client-provided ID for the document."
    )  # Add optional ID
    title: str = Field(
        default="Untitled", description="The title of the document."
    )
    content: str = Field(
        ..., min_length=1, description="The text content of the document."
    )  # Add validation
    metadata: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    """Response model for a single document, matching repository structure."""

    id: str
    metadata: dict[str, Any] = Field(default_factory=dict)  # Direct metadata field
    type: str | None = None  # Add type to match test expectations
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentMetadataUpdate(BaseModel):
    """Request model for updating document metadata. Allows arbitrary key-value pairs."""

    properties: dict[str, Any] = Field(
        ..., description="Metadata key-value pairs to update."
    )


# --- Unified Content Router Schemas (Epic 2) ---

class DocumentResponse(BaseModel):
    """Enhanced document response for unified content router."""
    id: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChunkResponse(BaseModel):
    """Enhanced chunk response for unified content router."""
    id: str
    text: str
    document_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class DocumentIngestionRequest(BaseModel):
    """Request schema for unified document ingestion."""
    title: str = Field(..., min_length=1, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Document metadata")
    source_type: str | None = Field(default="api", description="Source type (api, file_upload, batch_api)")


class IngestionResponse(BaseModel):
    """Response schema for unified document ingestion."""
    document_id: str
    chunks_created: int
    chunk_ids: list[str]
    processing_time_ms: float
    message: str


class ContentAnalyticsSummary(BaseModel):
    """Summary analytics for unified content system."""
    total_documents: int
    total_chunks: int
    total_vectors: int
    total_content_size_bytes: int
    average_chunks_per_document: float
    system_health: str = "healthy"
    last_updated: datetime | None = Field(default_factory=datetime.now)


# --- Unified Retrieval Router Schemas (Epic 2) ---

class QueryRequest(BaseModel):
    """Request schema for unified query processing."""
    query: str = Field(..., min_length=1, description="Query text")
    top_k: int | None = Field(default=5, description="Number of results to return")
    search_type: str | None = Field(default="hybrid", description="Search type: vector, keyword, hybrid, graph, auto")
    include_embeddings: bool | None = Field(default=False, description="Include embeddings in response")
    context_limit: int | None = Field(default=8, description="Maximum context sources")
    graph_depth: int | None = Field(default=2, description="Maximum graph traversal depth")


class ReasoningRequest(BaseModel):
    """Request schema for unified reasoning analysis."""
    prompt: str = Field(..., min_length=1, description="Reasoning prompt")
    reasoning_type: str | None = Field(default="analytical", description="Type of reasoning: analytical, logical, creative")
    use_context_expansion: bool | None = Field(default=True, description="Use context expansion via entity relationships")
    context_limit: int | None = Field(default=8, description="Maximum context sources")
    relationship_types: list[str] | None = Field(default_factory=lambda: ["RELATES_TO", "MENTIONS"], description="Relationship types for context expansion")


class SearchQueryResponse(BaseModel):
    """Response schema for unified search operations."""
    results: list[SearchResultSchema]
    query: str
    search_type: str
    total_results: int
    processing_time_ms: float


class QueryResponse(BaseModel):
    """Response schema for unified query operations."""
    query: str
    answer: str
    sources: list[dict]
    metadata: dict


class ReasoningResponse(BaseModel):
    """Response schema for unified reasoning operations."""
    prompt: str
    reasoning: str
    context_sources: list[dict]
    related_context: list[dict]
    analysis_metadata: dict
