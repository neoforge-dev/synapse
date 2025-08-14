from __future__ import annotations

try:  # optional dependency
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
except Exception:  # pragma: no cover - metrics are optional
    Counter = None  # type: ignore
    Gauge = None  # type: ignore
    Histogram = None  # type: ignore
    CollectorRegistry = None  # type: ignore

# Module-level handles (initialized by init_metrics)
ASK_TOTAL: Counter | None = None
INGEST_TOTAL: Counter | None = None
LLM_REL_INFERRED: Counter | None = None
LLM_REL_PERSISTED: Counter | None = None
INGESTION_CHUNKS_TOTAL: Counter | None = None
INGESTION_VECTORS_TOTAL: Counter | None = None
QUERY_LATENCY_SECONDS: Histogram | None = None
INGEST_LATENCY_SECONDS: Histogram | None = None
VECTOR_STORE_SIZE: Gauge | None = None
GRAPH_CHUNK_COUNT: Gauge | None = None


def init_metrics(registry: CollectorRegistry | None) -> None:
    """Initialize counters and histograms on the provided registry.

    If prometheus_client is not available or registry is None, this is a no-op.
    """
    global ASK_TOTAL, INGEST_TOTAL, LLM_REL_INFERRED, LLM_REL_PERSISTED
    global INGESTION_CHUNKS_TOTAL, INGESTION_VECTORS_TOTAL
    global QUERY_LATENCY_SECONDS, INGEST_LATENCY_SECONDS
    global VECTOR_STORE_SIZE, GRAPH_CHUNK_COUNT

    if Counter is None or registry is None:  # pragma: no cover
        return

    ASK_TOTAL = Counter(
        "ask_requests_total",
        "Total ask requests (includes streaming and non-streaming)",
        registry=registry,
    )
    INGEST_TOTAL = Counter(
        "ingestion_requests_total",
        "Total ingestion requests accepted",
        registry=registry,
    )
    LLM_REL_INFERRED = Counter(
        "llm_relations_inferred_total",
        "LLM-inferred relationships observed during queries",
        registry=registry,
    )
    LLM_REL_PERSISTED = Counter(
        "llm_relations_persisted_total",
        "LLM-inferred relationships persisted to the graph",
        registry=registry,
    )
    INGESTION_CHUNKS_TOTAL = Counter(
        "ingestion_chunks_total",
        "Total chunks ingested (successful saves)",
        registry=registry,
    )
    INGESTION_VECTORS_TOTAL = Counter(
        "ingestion_vectors_total",
        "Total vectors added to the vector store",
        registry=registry,
    )
    QUERY_LATENCY_SECONDS = Histogram(
        "query_latency_seconds",
        "End-to-end query latency in seconds",
        buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10),
        registry=registry,
    )
    INGEST_LATENCY_SECONDS = Histogram(
        "ingest_latency_seconds",
        "End-to-end ingestion latency in seconds",
        buckets=(0.1, 0.2, 0.5, 1, 2, 5, 10, 30),
        registry=registry,
    )
    VECTOR_STORE_SIZE = Gauge(
        "vector_store_size",
        "Current number of vectors in the vector store",
        registry=registry,
    )
    GRAPH_CHUNK_COUNT = Gauge(
        "graph_chunk_count",
        "Current number of chunks in the graph store",
        registry=registry,
    )


def inc_ask_total() -> None:
    try:
        if ASK_TOTAL:
            ASK_TOTAL.inc()  # type: ignore[call-arg]
    except Exception:
        pass


def inc_ingest_total() -> None:
    try:
        if INGEST_TOTAL:
            INGEST_TOTAL.inc()  # type: ignore[call-arg]
    except Exception:
        pass


def inc_llm_rel_inferred(n: int) -> None:
    try:
        if LLM_REL_INFERRED and n:
            LLM_REL_INFERRED.inc(n)  # type: ignore[call-arg]
    except Exception:
        pass


def inc_llm_rel_persisted(n: int) -> None:
    try:
        if LLM_REL_PERSISTED and n:
            LLM_REL_PERSISTED.inc(n)  # type: ignore[call-arg]
    except Exception:
        pass


def inc_ingested_chunks(n: int) -> None:
    try:
        if INGESTION_CHUNKS_TOTAL and n:
            INGESTION_CHUNKS_TOTAL.inc(n)  # type: ignore[call-arg]
    except Exception:
        pass


def inc_ingested_vectors(n: int) -> None:
    try:
        if INGESTION_VECTORS_TOTAL and n:
            INGESTION_VECTORS_TOTAL.inc(n)  # type: ignore[call-arg]
    except Exception:
        pass


def observe_query_latency(seconds: float) -> None:
    try:
        if QUERY_LATENCY_SECONDS and seconds >= 0:
            QUERY_LATENCY_SECONDS.observe(seconds)  # type: ignore[call-arg]
    except Exception:
        pass


def observe_ingest_latency(seconds: float) -> None:
    try:
        if INGEST_LATENCY_SECONDS and seconds >= 0:
            INGEST_LATENCY_SECONDS.observe(seconds)  # type: ignore[call-arg]
    except Exception:
        pass


def set_vector_store_size(size: int) -> None:
    """Update the vector store size gauge."""
    try:
        if VECTOR_STORE_SIZE and size >= 0:
            VECTOR_STORE_SIZE.set(size)  # type: ignore[call-arg]
    except Exception:
        pass


def set_graph_chunk_count(count: int) -> None:
    """Update the graph chunk count gauge."""
    try:
        if GRAPH_CHUNK_COUNT and count >= 0:
            GRAPH_CHUNK_COUNT.set(count)  # type: ignore[call-arg]
    except Exception:
        pass
