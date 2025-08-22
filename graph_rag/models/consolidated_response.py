"""Response models for consolidated answers with dual-purpose format."""

from typing import Any

from pydantic import BaseModel, Field


class ArchitecturalPatternResponse(BaseModel):
    """Response model for architectural patterns."""
    pattern_name: str
    description: str
    benefits: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    evidence_strength: float = Field(ge=0.0, le=1.0)


class SuccessMetricResponse(BaseModel):
    """Response model for success metrics."""
    metric_type: str
    value: float
    unit: str
    context: str
    source_location: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class MachineReadableResponse(BaseModel):
    """Machine-readable structured data format."""
    concepts: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    patterns: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)


class SourceResponse(BaseModel):
    """Response model for source information."""
    id: str
    document_id: str
    score: float
    text_preview: str
    metadata: dict[str, Any] | None = None
    consolidated_from: int | None = None


class ConsolidatedAnswerResponse(BaseModel):
    """Dual-purpose response format for both human and machine consumption."""

    # Human-readable content
    answer: str
    answer_with_citations: str | None = None

    # Consolidated knowledge components
    consolidated_chunks: list[dict[str, Any]] = Field(default_factory=list)
    architectural_patterns: list[ArchitecturalPatternResponse] = Field(default_factory=list)
    success_metrics: list[SuccessMetricResponse] = Field(default_factory=list)
    best_practices: list[str] = Field(default_factory=list)

    # Quality metrics
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    consolidation_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence_ranking: float = Field(ge=0.0, le=1.0, default=0.0)

    # Source information
    sources: list[SourceResponse] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    bibliography: dict[str, Any] = Field(default_factory=dict)

    # Machine-readable structured data
    machine_readable: MachineReadableResponse = Field(default_factory=MachineReadableResponse)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            # Handle any special encoding needs
        }
        json_schema_extra = {
            "example": {
                "answer": "Based on the consolidated analysis of architectural patterns...",
                "answer_with_citations": "Based on the consolidated analysis [1,2] of architectural patterns...",
                "consolidated_chunks": [
                    {
                        "id": "chunk_123",
                        "text": "Universal orchestrator pattern provides centralized control...",
                        "document_id": "doc_456",
                        "score": 0.95
                    }
                ],
                "architectural_patterns": [
                    {
                        "pattern_name": "Universal Orchestrator",
                        "description": "Centralized coordination pattern",
                        "benefits": ["Simplified coordination", "Clear responsibility"],
                        "challenges": ["Single point of failure"],
                        "use_cases": ["Workflow orchestration"],
                        "evidence_strength": 0.85
                    }
                ],
                "success_metrics": [
                    {
                        "metric_type": "performance_improvement",
                        "value": 39092.0,
                        "unit": "x",
                        "context": "39,092x improvement in processing speed",
                        "source_location": "Character 150-200",
                        "confidence_score": 0.9
                    }
                ],
                "best_practices": [
                    "Use centralized orchestration for complex workflows",
                    "Implement proper error handling and fallback mechanisms"
                ],
                "confidence_score": 0.85,
                "consolidation_confidence": 0.78,
                "evidence_ranking": 0.82,
                "sources": [
                    {
                        "id": "chunk_123",
                        "document_id": "doc_456",
                        "score": 0.95,
                        "text_preview": "Universal orchestrator pattern provides...",
                        "consolidated_from": 3
                    }
                ],
                "machine_readable": {
                    "concepts": [
                        {
                            "id": "chunk_123",
                            "text": "Universal orchestrator pattern provides centralized control...",
                            "score": 0.95
                        }
                    ],
                    "relationships": [
                        {
                            "source_id": "orchestrator",
                            "target_id": "workflow",
                            "type": "MANAGES"
                        }
                    ],
                    "evidence": [
                        {
                            "type": "metric",
                            "value": 39092.0,
                            "unit": "x",
                            "confidence": 0.9
                        }
                    ]
                },
                "metadata": {
                    "query": "How does universal orchestrator improve performance?",
                    "chunks_count": 5,
                    "patterns_count": 2,
                    "metrics_count": 3,
                    "engine_type": "ImprovedSynapseEngine"
                }
            }
        }


class ConsolidatedQueryRequest(BaseModel):
    """Request model for consolidated queries."""
    query_text: str = Field(..., description="The query text to process")
    include_patterns: bool = Field(default=True, description="Include architectural patterns in response")
    include_metrics: bool = Field(default=True, description="Include success metrics in response")
    include_best_practices: bool = Field(default=True, description="Include best practices in response")
    include_machine_readable: bool = Field(default=True, description="Include machine-readable format")
    consolidation_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold for consolidation")
    max_chunks: int = Field(default=10, ge=1, le=50, description="Maximum number of chunks to retrieve")
    search_type: str = Field(default="hybrid", description="Search type: vector, keyword, or hybrid")
    conversation_id: str | None = Field(default=None, description="Conversation ID for context")

    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "How does the universal orchestrator pattern improve system performance?",
                "include_patterns": True,
                "include_metrics": True,
                "include_best_practices": True,
                "include_machine_readable": True,
                "consolidation_threshold": 0.7,
                "max_chunks": 10,
                "search_type": "hybrid",
                "conversation_id": "conv_123"
            }
        }


class VectorStoreStatusResponse(BaseModel):
    """Response model for vector store status."""
    vector_count: int
    store_type: str
    is_persistent: bool
    storage_path: str | None = None
    error: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "vector_count": 1250,
                "store_type": "SharedPersistentVectorStore",
                "is_persistent": True,
                "storage_path": "data/vector_store"
            }
        }
