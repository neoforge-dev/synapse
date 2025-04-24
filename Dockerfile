# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
# Rely on standard PATH

# Install system dependencies needed for builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN pip install uv

# Copy project definition
COPY pyproject.toml ./
# Copy README as setuptools might look for it
COPY README.md ./

# Copy the application code BEFORE installing the local package
COPY . .

# Install the project and its dependencies using UV
RUN uv pip install --no-cache-dir ".[dev]"

# Download spaCy model needed by the application
RUN python -m spacy download en_core_web_sm

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uv", "run", "uvicorn", "graph_rag.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]