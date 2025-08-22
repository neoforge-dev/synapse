# Multi-stage Dockerfile for TechLead AutoPilot

# Build stage
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install --no-cache -r pyproject.toml

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Install uv in production image
RUN pip install uv

# Fix permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uv", "run", "uvicorn", "techlead_autopilot.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# Development stage (for docker-compose)
FROM production as development

# Switch back to root for development setup
USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install development dependencies
RUN uv pip install --no-cache \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    mypy \
    ruff

# Switch back to appuser
USER appuser

# Development command with hot reload
CMD ["uv", "run", "uvicorn", "techlead_autopilot.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]