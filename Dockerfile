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

# Copy project definition
COPY pyproject.toml ./
# Copy README as setuptools might look for it
COPY README.md ./

# Copy the application code BEFORE installing the local package
COPY . .

# Install the project and its dependencies using standard pip
# Now it can find the 'graph_rag' directory
RUN pip install --no-cache-dir .

# Download spaCy model needed by the application
RUN python -m spacy download en_core_web_sm

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "graph_rag.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"] 