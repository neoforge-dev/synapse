# Synapse Installation Guide

Complete installation guide for Synapse Graph-RAG system.

## Prerequisites

- **Python**: 3.11 or later
- **Docker**: For Memgraph graph database (optional for vector-only mode)
- **uv**: Recommended package manager (or pip)
- **macOS, Linux, or Windows** (WSL2 supported)

## Installation Methods

### Method 1: Homebrew (macOS/Linux) - Recommended for macOS

```bash
# Clone the repository
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag

# Install via Homebrew
brew install ./homebrew-tap/Formula/synapse.rb
```

**What gets installed:**
- Synapse CLI (`synapse` command)
- All Python dependencies
- System libraries (cmake, pkg-config)
- Shell completions (bash, zsh, fish)
- Default configuration in `/opt/homebrew/etc/synapse/` (Apple Silicon) or `/usr/local/etc/synapse/` (Intel)

**Post-installation:**
```bash
# Verify installation
synapse --version

# Quick start (vector-only, no Docker)
SYNAPSE_DISABLE_GRAPH=true synapse ingest ~/Documents

# Full setup with graph database
synapse up
```

**Port mappings:**
| Service          | Port  |
|------------------|-------|
| API (FastAPI)    | 18888 |
| Memgraph (Bolt)  | 17687 |
| Memgraph (HTTP)  | 17444 |
| PostgreSQL       | 15432 |

**Troubleshooting Homebrew:**

```bash
# Check Homebrew health
brew doctor

# Reinstall if needed
brew uninstall synapse
brew install ./homebrew-tap/Formula/synapse.rb

# macOS Beta (26.x) compatibility issue
# If Homebrew fails on macOS beta, use Method 2 instead
```

---

### Method 2: uv (Universal, Recommended for Development)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag

# Install in development mode
uv pip install -e .

# Download NLP models (optional, for entity extraction)
python -m spacy download en_core_web_sm
```

**Verify installation:**
```bash
synapse --version
synapse --help
```

---

### Method 3: pip (Traditional)

```bash
# Clone repository
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Download NLP models (optional)
python -m spacy download en_core_web_sm
```

---

### Method 4: pipx (Isolated Global Install)

```bash
# Install pipx if not available
python -m pip install pipx
python -m pipx ensurepath

# Build and install Synapse
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
python -m build
pipx install dist/synapse_graph_rag-*.whl
```

---

## Quick Start Workflows

### Scenario 1: Vector-Only Mode (No Docker Required)

Perfect for testing, lightweight use cases, or when graph database isn't needed.

```bash
# Configure vector-only mode
export SYNAPSE_DISABLE_GRAPH=true
export SYNAPSE_VECTOR_STORE_TYPE=simple
export SYNAPSE_EMBEDDING_PROVIDER=sentence-transformers

# Ingest documents
synapse ingest ~/Documents --embeddings

# Search your data
synapse search "machine learning concepts" --limit 5

# Q&A
synapse query ask "What is the main topic of my documents?"
```

### Scenario 2: Full Graph-RAG Setup

```bash
# Start services (Memgraph + API)
synapse up --wait

# Verify services
curl http://localhost:18888/health
# Expected: {"status": "healthy"}

# Ingest with graph relationships
synapse ingest ~/Documents --embeddings

# Explore graph visually
open http://localhost:3000  # Memgraph Lab

# Graph-enhanced search
synapse query ask "What are the key concepts?" --show-graph
```

### Scenario 3: LinkedIn Data Ingestion

```bash
# Extract from LinkedIn CSV
python analytics/comprehensive_linkedin_extractor.py

# Ingest extracted entities
synapse ingest data/linkedin_extracted/ --embeddings --batch-size 50

# Explore beliefs and preferences
synapse search "beliefs about AI" --type vector --limit 10
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# API Configuration
SYNAPSE_API_HOST=0.0.0.0
SYNAPSE_API_PORT=8000

# Graph Database
SYNAPSE_MEMGRAPH_HOST=127.0.0.1
SYNAPSE_MEMGRAPH_PORT=7687
SYNAPSE_DISABLE_GRAPH=false

# Vector Store
SYNAPSE_VECTOR_STORE_TYPE=simple          # simple, faiss, or mock
SYNAPSE_VECTOR_STORE_PATH=~/.graph_rag/vector_store
SYNAPSE_SIMPLE_VECTOR_STORE_PERSISTENT=true

# Embeddings
SYNAPSE_EMBEDDING_PROVIDER=sentence-transformers
SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL=all-MiniLM-L6-v2

# LLM (for Q&A)
SYNAPSE_LLM_TYPE=mock                     # mock, openai, anthropic, ollama
SYNAPSE_OPENAI_API_KEY=your_key_here
SYNAPSE_ANTHROPIC_API_KEY=your_key_here

# Authentication (optional)
SYNAPSE_ENABLE_AUTHENTICATION=false
SYNAPSE_JWT_SECRET_KEY=your_secret_here
```

**Configuration wizard:**
```bash
synapse config init --interactive
```

---

## Verify Installation

```bash
# Check CLI version
synapse --version

# Run health checks
synapse admin health

# Check setup
synapse init check
```

**Expected output:**
```
✓ Python 3.11+ detected
✓ Docker available
✓ Synapse CLI installed
✓ Configuration valid
```

---

## Optional Components

### 1. SpaCy NLP Models (for entity extraction)

```bash
# Small model (default)
python -m spacy download en_core_web_sm

# Large model (better accuracy)
python -m spacy download en_core_web_lg
```

### 2. FAISS Vector Store (high performance)

```bash
# Install FAISS (CPU version)
uv pip install faiss-cpu

# Or GPU version
uv pip install faiss-gpu

# Configure
export SYNAPSE_VECTOR_STORE_TYPE=faiss
export SYNAPSE_USE_OPTIMIZED_FAISS=true
```

### 3. LLM Providers

**OpenAI:**
```bash
export SYNAPSE_LLM_TYPE=openai
export SYNAPSE_OPENAI_API_KEY=sk-...
export SYNAPSE_LLM_MODEL_NAME=gpt-4o-mini
```

**Anthropic:**
```bash
export SYNAPSE_LLM_TYPE=anthropic
export SYNAPSE_ANTHROPIC_API_KEY=sk-ant-...
export SYNAPSE_LLM_MODEL_NAME=claude-3-haiku-20240307
```

**Ollama (local):**
```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama2

# Configure Synapse
export SYNAPSE_LLM_TYPE=ollama
export SYNAPSE_OLLAMA_BASE_URL=http://localhost:11434
export SYNAPSE_LLM_MODEL_NAME=llama2
```

---

## Troubleshooting

### Common Issues

**1. ModuleNotFoundError: No module named 'graph_rag'**
```bash
# Ensure you're in the project directory
cd /path/to/synapse-graph-rag

# Reinstall
uv pip install -e .
```

**2. Docker connection errors**
```bash
# Check Docker is running
docker ps

# Start Memgraph manually
docker run -p 7687:7687 memgraph/memgraph-platform:latest

# Or use Synapse's Docker Compose
synapse up
```

**3. SpaCy model not found**
```bash
# Download the model
python -m spacy download en_core_web_sm

# Or disable entity extraction
export SKIP_SPACY_IMPORT=1
```

**4. Permission denied on macOS**
```bash
# Fix Homebrew permissions
sudo chown -R $(whoami) /opt/homebrew

# Or use manual installation
uv pip install -e .
```

**5. Slow ingestion**
```bash
# Use batch mode
synapse ingest ~/Documents --batch-size 100

# Use mock embedding provider for testing
export SYNAPSE_EMBEDDING_PROVIDER=mock
```

### Platform-Specific Issues

**macOS Beta (26.x):**
- Homebrew shows Tier 2 support warnings
- Solution: Use uv installation method instead

**Windows (WSL2):**
- Use WSL2 for best compatibility
- Ensure Docker Desktop is running
- Use Linux paths within WSL2

**Apple Silicon (M1/M2):**
- Most dependencies work natively
- FAISS GPU not supported (use CPU version)
- Homebrew installs to `/opt/homebrew/`

---

## Uninstall

**Homebrew:**
```bash
brew uninstall synapse
rm -rf /opt/homebrew/etc/synapse  # Optional: remove config
```

**uv/pip:**
```bash
pip uninstall synapse-graph-rag
rm -rf ~/.graph_rag  # Optional: remove data
```

**pipx:**
```bash
pipx uninstall synapse-graph-rag
```

**Clean Docker resources:**
```bash
synapse down --volumes
docker rmi memgraph/memgraph-platform
```

---

## Upgrading

**Homebrew:**
```bash
cd synapse-graph-rag
git pull
brew reinstall ./homebrew-tap/Formula/synapse.rb
```

**uv/pip:**
```bash
cd synapse-graph-rag
git pull
uv pip install -e . --force-reinstall
```

**Check version:**
```bash
synapse --version
```

---

## Next Steps

1. **Quick Start**: Follow [QUICKSTART.md](../QUICKSTART.md)
2. **LinkedIn Ingestion**: See [LINKEDIN_CSV_INGESTION_QUICKSTART.md](./LINKEDIN_CSV_INGESTION_QUICKSTART.md)
3. **Configuration**: Review [CONFIGURATION.md](./CONFIGURATION.md) (coming soon)
4. **API Reference**: Explore [API_REFERENCE.md](../reference/API_REFERENCE.md) (coming soon)

---

## Getting Help

- **Documentation**: [docs/](../)
- **Issues**: [GitHub Issues](https://github.com/neoforge-ai/synapse-graph-rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/neoforge-ai/synapse-graph-rag/discussions)

---

**Installation complete!** 🎉

Now run `synapse --help` to see all available commands.
