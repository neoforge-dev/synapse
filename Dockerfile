# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/root/.cargo/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy only the files needed for dependency installation
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy the rest of the application
COPY . .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "graph_rag.api.main:app", "--host", "0.0.0.0", "--port", "8000"] 