from typing import Any

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
    document_id: str | None = Field(
        None,
        description="Optional explicit ID for the document. If not provided, one may be generated.",
    )
    generate_embeddings: bool = Field(
        True,
        description="Whether to create embeddings for the document's chunks during ingestion.",
    )
    replace_existing: bool = Field(
        True,
        description="Replace previously ingested content for the same document_id if present.",
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
    score: float | None = None  # Optional relevance score


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
    graph_context: QueryResultGraphContext | None = Field(
        None, description="Context retrieved from the knowledge graph."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the query execution.",
    )
    # Citation-enhanced fields
    answer_with_citations: str | None = Field(
        None, description="Answer text enhanced with inline citation markers."
    )
    citations: list[dict[str, Any]] = Field(
        default_factory=list, description="Detailed citation metadata for sources used."
    )
    bibliography: dict[str, str] = Field(
        default_factory=dict, description="Formatted bibliography by citation style."
    )


# --- Ask Models ---


class AskRequest(BaseModel):
    """Request model for submitting an ask (answer synthesis) request."""

    text: str = Field(..., description="The user's question.")
    k: int = Field(5, description="Number of chunks to retrieve.")
    include_graph: bool = Field(
        False, description="Whether to include graph-based context retrieval."
    )
    conversation_id: str | None = Field(
        None, description="Optional conversation ID for context-aware responses."
    )
    provider: str | None = Field(
        None,
        description="LLM provider to use (e.g., openai, anthropic, mock). Optional override.",
    )
    model: str | None = Field(
        None, description="LLM model name to use. Optional override."
    )
    streaming: bool = Field(
        False, description="Enable streaming responses when supported."
    )
    # Retrieval/Prompting knobs
    search_type: str = Field(
        "hybrid", description="Search type: 'vector', 'keyword', or 'hybrid'."
    )
    style: str | None = Field(
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
    extract_relationships_dry_run: bool = Field(
        False,
        description=(
            "When true, do not write LLM relationships; return planned writes in metadata."
        ),
    )


# --- Conversation Memory Models ---


class StartConversationRequest(BaseModel):
    """Request model for starting a new conversation."""

    user_id: str = Field(..., description="User identifier for the conversation.")


class StartConversationResponse(BaseModel):
    """Response model for starting a new conversation."""

    conversation_id: str = Field(..., description="Unique conversation identifier.")
    message: str = Field(default="Conversation started successfully.")


class ConversationContextResponse(BaseModel):
    """Response model for conversation context."""

    conversation_id: str = Field(..., description="Conversation identifier.")
    context: str = Field(..., description="Formatted conversation context.")
    has_summary: bool = Field(False, description="Whether conversation has a summary.")


# --- Enhanced Query Models with Confidence Scoring ---


class ConfidenceMetricsResponse(BaseModel):
    """API response model for confidence metrics."""

    overall_score: float = Field(..., description="Overall confidence score (0.0-1.0).")
    level: str = Field(..., description="Confidence level (very_low, low, medium, high, very_high).")
    context_coverage: float = Field(..., description="How well context covers the query (0.0-1.0).")
    context_relevance: float = Field(..., description="How relevant retrieved context is (0.0-1.0).")
    uncertainty_indicators: list[str] = Field(default_factory=list, description="Detected uncertainty phrases.")
    source_count: int = Field(0, description="Number of source chunks used.")
    source_quality_score: float = Field(0.0, description="Quality score of source material (0.0-1.0).")
    answer_completeness: float = Field(0.0, description="How complete the answer appears (0.0-1.0).")
    factual_consistency: float = Field(0.0, description="Consistency with source material (0.0-1.0).")
    reasoning: str | None = Field(None, description="Human-readable confidence reasoning.")


class AnswerValidationResponse(BaseModel):
    """API response model for answer validation results."""

    is_valid: bool = Field(..., description="Whether the answer passed validation.")
    validation_score: float = Field(..., description="Overall validation score (0.0-1.0).")
    validation_level: str = Field(..., description="Validation level used (strict, moderate, lenient).")

    # Quality metrics
    total_claims: int = Field(0, description="Total number of claims identified.")
    supported_claims: int = Field(0, description="Number of claims with source support.")
    unsupported_claims: int = Field(0, description="Number of claims without source support.")
    conflicting_claims: int = Field(0, description="Number of claims that conflict with sources.")

    # Coverage metrics
    chunk_coverage: float = Field(0.0, description="Portion of source chunks referenced (0.0-1.0).")
    answer_coverage: float = Field(0.0, description="Portion of answer supported by sources (0.0-1.0).")
    citation_completeness: float = Field(0.0, description="Completeness of citations (0.0-1.0).")

    # Quality indicators
    hallucination_risk: bool = Field(False, description="Whether answer has hallucination risk.")
    requires_fact_check: bool = Field(False, description="Whether answer requires fact checking.")

    # Issues and recommendations
    num_issues: int = Field(0, description="Number of validation issues found.")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations for improvement.")


class EnhancedQueryResponse(BaseModel):
    """Enhanced response model for queries with confidence scoring."""

    answer: str = Field(..., description="The generated answer to the query.")
    confidence: ConfidenceMetricsResponse = Field(..., description="Confidence metrics for the answer.")
    validation: AnswerValidationResponse | None = Field(None, description="Answer validation results.")
    relevant_chunks: list[QueryResultChunk] = Field(
        default_factory=list, description="List of relevant text chunks."
    )
    graph_context: QueryResultGraphContext | None = Field(
        None, description="Context retrieved from the knowledge graph."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the query execution.",
    )
    # Citation-enhanced fields
    answer_with_citations: str | None = Field(
        None, description="Answer text enhanced with inline citation markers."
    )
    citations: list[dict[str, Any]] = Field(
        default_factory=list, description="Detailed citation metadata for sources used."
    )
    bibliography: dict[str, str] = Field(
        default_factory=dict, description="Formatted bibliography by citation style."
    )
    # Enhanced response metadata
    input_tokens: int | None = Field(None, description="Number of input tokens used.")
    output_tokens: int | None = Field(None, description="Number of output tokens generated.")
    processing_time: float | None = Field(None, description="Processing time in seconds.")
    model_name: str | None = Field(None, description="Name of the LLM model used.")
    temperature: float | None = Field(None, description="Temperature parameter used.")
    has_hallucination_risk: bool = Field(False, description="Whether the response has hallucination risk.")
    requires_verification: bool = Field(False, description="Whether the answer requires verification.")


class EnhancedAskRequest(BaseModel):
    """Enhanced request model for ask queries with confidence scoring options."""

    text: str = Field(..., description="The user's question.")
    k: int = Field(5, description="Number of chunks to retrieve.")
    include_graph: bool = Field(
        False, description="Whether to include graph-based context retrieval."
    )
    conversation_id: str | None = Field(
        None, description="Optional conversation ID for context-aware responses."
    )
    provider: str | None = Field(
        None,
        description="LLM provider to use (e.g., openai, anthropic, mock). Optional override.",
    )
    model: str | None = Field(
        None, description="LLM model name to use. Optional override."
    )
    streaming: bool = Field(
        False, description="Enable streaming responses when supported."
    )
    # Retrieval/Prompting knobs
    search_type: str = Field(
        "hybrid", description="Search type: 'vector', 'keyword', or 'hybrid'."
    )
    style: str | None = Field(
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
    extract_relationships_dry_run: bool = Field(
        False,
        description=(
            "When true, do not write LLM relationships; return planned writes in metadata."
        ),
    )
    # Enhanced response options
    include_confidence_metrics: bool = Field(
        True, description="Whether to include detailed confidence scoring."
    )


# --- Admin/Management Models (Add later if needed) ---


class SystemStatus(BaseModel):
    status: str = "OK"
    memgraph_connected: bool
    vector_store_status: str  # e.g., OK, Unavailable
    # Add more status indicators as needed
