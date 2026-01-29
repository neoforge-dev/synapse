# Deployment Guide

## Prerequisites

- Python 3.10+
- Docker (for Memgraph)
- uv (for dependency management)

## Quick Start

1. Install dependencies: `make install-dev`
2. Start Memgraph: `make run-memgraph`
3. Start API: `make run-api`
4. Verify: `curl http://localhost:8000/health`

## Production Deployment

For production deployments, use Docker Compose or Kubernetes manifests provided in the infrastructure directory.
