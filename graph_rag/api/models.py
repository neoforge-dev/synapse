from typing import Any, Optional

from pydantic import BaseModel, Field

# --- Ingestion Models ---


class IngestRequest(BaseModel):
    """Request model for ingesting a single document."""

    content: str = Field(
        ..., description="The text content of the document to ingest.", min_length=1
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata associated with the document."
    )
    document_id: Optional[str] = Field(
        None,
        description="Optional explicit ID for the document. If not provided, one may be generated.",
    )


class IngestResponse(BaseModel):
    """Response model after accepting an ingestion request."""

    message: str = Field(..., description="Status message about the ingestion request.")
    document_id: str = Field(
        ..., description="The ID assigned to the ingested document."
    )
    task_id: str = Field(..., description="Unique ID for tracking the ingestion task.")
    status: str = Field(
        "processing", description="Current status of the ingestion task."
    )


# --- Query Models ---


class QueryRequest(BaseModel):
    """Request model for submitting a query."""

    query_text: str = Field(..., description="The user's query text.")
    k: int = Field(3, description="Number of results to return.")


class ResultItem(BaseModel):
    """Represents a single result item from a query."""

    content: str = Field(
        ..., description="The content of the result (e.g., chunk text)."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the result (e.g., chunk_id, document_id).",
    )


class QueryResult(BaseModel):
    """Response model for a query result."""

    query: str = Field(..., description="The original query text.")
    results: list[ResultItem] = Field(
        ..., description="List of relevant results matching the query."
    )


class QueryResultChunk(BaseModel):
    """Represents a chunk relevant to the query result."""

    id: str
    text: str
    document_id: str
    metadata: dict[str, Any]
    score: Optional[float] = None  # Optional relevance score


class QueryResultGraphContext(BaseModel):
    """Represents graph context relevant to the query result."""

    entities: list[dict[str, Any]]  # Simplified representation for API
    relationships: list[dict[str, Any]]  # Simplified representation for API


class QueryResponse(BaseModel):
    """Response model for a query."""

    answer: str = Field(..., description="The generated answer to the query.")
    relevant_chunks: list[QueryResultChunk] = Field(
        default_factory=list, description="List of relevant text chunks."
    )
    graph_context: Optional[QueryResultGraphContext] = Field(
        None, description="Context retrieved from the knowledge graph."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the query execution.",
    )


# --- Ask Models ---


class AskRequest(BaseModel):
    """Request model for submitting an ask (answer synthesis) request."""

    text: str = Field(..., description="The user's question.")
    k: int = Field(5, description="Number of chunks to retrieve.")
    include_graph: bool = Field(
        False, description="Whether to include graph-based context retrieval."
    )
    provider: Optional[str] = Field(
        None,
        description="LLM provider to use (e.g., openai, anthropic, mock). Optional override.",
    )
    model: Optional[str] = Field(
        None, description="LLM model name to use. Optional override."
    )
    streaming: bool = Field(
        False, description="Enable streaming responses when supported."
    )
    # Retrieval/Prompting knobs
    style: Optional[str] = Field(
        None, description="Optional answer style (e.g., concise, analytical, teaching)."
    )
    blend_vector_weight: float = Field(
        1.0, ge=0.0, description="Weight for vector scores in hybrid retrieval."
    )
    blend_keyword_weight: float = Field(
        0.0, ge=0.0, description="Weight for keyword scores in hybrid retrieval."
    )
    rerank: bool = Field(
        False, description="Enable lightweight reranking of top results."
    )
    mmr_lambda: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Maximal Marginal Relevance lambda (0..1). 0=diversity, 1=relevance.",
    )
    no_answer_min_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="If top retrieval score is below this threshold, return a calibrated no-answer.",
    )
    extract_relationships_persist: bool = Field(
        False,
        description=(
            "When true and feature is enabled in settings, persist LLM-inferred relationships."
        ),
    )


# --- Admin/Management Models (Add later if needed) ---


class SystemStatus(BaseModel):
    status: str = "OK"
    memgraph_connected: bool
    vector_store_status: str  # e.g., OK, Unavailable
    # Add more status indicators as needed
