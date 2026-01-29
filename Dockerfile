# Multi-stage Dockerfile for Synapse Graph-RAG
# Optimized for production deployments with security best practices

# Stage 1: Base Python environment with uv
FROM python:3.11-slim as base

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Stage 2: Build dependencies
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv pip install --system --no-cache-dir -e .[all]

# Download NLP models (optional - can be done at runtime)
# RUN python -c "import spacy; spacy.cli.download('en_core_web_sm')"

# Stage 3: Production runtime
FROM python:3.11-slim as production

# Security: Create non-root user
RUN useradd -m -u 1000 -s /bin/bash synapse && \
    mkdir -p /app && \
    chown -R synapse:synapse /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=synapse:synapse . .

# Switch to non-root user
USER synapse

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SYNAPSE_API_HOST=0.0.0.0 \
    SYNAPSE_API_PORT=8000 \
    SYNAPSE_MEMGRAPH_HOST=memgraph \
    SYNAPSE_MEMGRAPH_PORT=7687

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose API port
EXPOSE 8000

# Run API server
CMD ["python", "-m", "uvicorn", "graph_rag.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
