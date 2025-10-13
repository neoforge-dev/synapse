# 🚀 Synapse Installation Guide

This guide covers the supported ways to install and run Synapse, from the fastest CLI setup to a fully reproducible Docker development environment.

---

## Quick CLI Installation

Synapse is published on PyPI as `synapse-graph-rag`. The recommended installer is [uv](https://docs.astral.sh/uv/) because it is fast and reproducible.

```bash
# Install uv if you do not already have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Synapse with MCP tooling enabled
uv pip install synapse-graph-rag[mcp]

# Confirm it is available
synapse --version
synapse --help
```

> **Tip:** Prefer `pipx install synapse-graph-rag[mcp]` if you want the CLI isolated from your global Python.

---

## Development Setup (recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/neoforge-ai/synapse-graph-rag.git
   cd synapse-graph-rag
   ```

2. **Install dependencies**
   ```bash
   make install-dev          # uses uv under the hood
   make download-nlp-data    # installs spaCy + NLTK data
   ```

3. **Start the stack with Docker**
   ```bash
   synapse up
   # or: make up
   ```

   The Docker compose stack exposes non-standard ports so it can run alongside other services:

   | Service            | Host Port | Notes                                  |
   |--------------------|-----------|----------------------------------------|
   | Synapse API (FastAPI) | 18888    | Container still listens on 8000        |
   | Memgraph (Bolt)       | 17687    | Graph database for knowledge graph     |
   | Memgraph (HTTP)       | 17444    | Memgraph Lab / REST access             |
   | Postgres              | 15432    | Optional analytics database            |

4. **Verify the deployment**
   ```bash
   curl http://localhost:18888/health
   synapse mcp health
   ```

   You should see healthy responses for the API and MCP tooling.

5. **Stop the stack**
   ```bash
   synapse down
   # or: make down
   ```

> **Need to enable production backends (Memgraph, FAISS, real LLM providers, Postgres analytics)?**  
> See `docs/guides/PRODUCTION_BACKENDS.md` for the environment variables and validation steps.

---

## Homebrew (local formula)

The repository ships a tap under `homebrew-tap/`. You can install Synapse via Homebrew without waiting for a public tap.

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb

# Optional: manage as a service
brew services start synapse
```

Uninstall with `brew uninstall synapse`.

---

## Verifying Your Environment

After any installation method:

```bash
synapse config show --json | head -n 20
synapse init wizard --quiet --vector-only

# With Docker running
curl http://localhost:18888/api/v1/health
synapse search "graph rag architecture" --api http://localhost:18888/api/v1
```

If you see successful responses, Synapse is ready to ingest documents and serve graph-enhanced RAG queries.

---

## Troubleshooting Checklist

- **`synapse` not on PATH:** ensure the location reported by `uv tool path` or `pipx environment` is added to your shell profile.
- **spaCy model missing:** run `make download-nlp-data` or install `python -m spacy download en_core_web_sm`.
- **Docker ports in use:** update `docker-compose.yml` host ports (18888/17687/17444/15432) if they collide with local services.
- **Memgraph not reachable:** confirm Docker Desktop is running and retry `synapse up`.

---

Need help or want to contribute? See `CONTRIBUTING.md` for coding standards and `docs/HOMEBREW.md` for advanced packaging instructions.
