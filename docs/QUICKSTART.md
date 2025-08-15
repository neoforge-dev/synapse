# Synapse GraphRAG Quick Start Guide

Get up and running with Synapse GraphRAG in under 10 minutes! This guide will help you set up the complete system including MCP integration for IDE workflows.

## Prerequisites

- **Python 3.10+** or **Homebrew** (macOS/Linux)
- **Docker** (for Memgraph database)
- **VS Code** or **Claude Desktop** (for MCP integration)

## Installation

### Option 1: PyPI (Recommended)

```bash
# Install with MCP support (via uv)
uv pip install synapse-graph-rag[mcp,all]

# Verify installation
synapse --version
```

### Option 2: Homebrew (macOS/Linux)

```bash
# Install from homebrew
brew install synapse-graph-rag

# Or from tap (when available)
brew tap neoforge-ai/synapse
brew install synapse-graph-rag
```

### Option 3: Development Setup

```bash
# Clone repository
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag

# Install in development mode (via uv)
uv pip install -e ".[dev,mcp,all]"
```

## 2-Minute Setup

### Step 1: Initialize Configuration

```bash
# Interactive configuration wizard
synapse config init

# Or quick non-interactive setup
synapse config init --no-interactive --type development
```

This creates:
- `.env` file with optimal settings
- `mcp-config/` directory with IDE integration examples
- Required directories (`~/.synapse/`)

### Step 2: Start Services

```bash
# Start the full stack (API + Memgraph)
synapse up

# Wait for services to be ready (usually 30-60 seconds)
```

The `up` command:
- ✅ Starts Docker Desktop (macOS)
- ✅ Pulls and starts Memgraph database
- ✅ Starts GraphRAG API server
- ✅ Performs health checks
- ✅ Shows status summary

### Step 3: Verify Setup

```bash
# Check system health
synapse mcp health

# Test API connectivity
curl http://localhost:8000/health
```

**You should see:**
- ✅ MCP Package: Available
- ✅ Synapse API: Connected  
- ✅ MCP Tools: 3 available

## 5-Minute IDE Integration

### VS Code Integration

1. **Copy MCP configuration**:
   ```bash
   # Configuration was created during init
   cat mcp-config/vscode-settings.json
   ```

2. **Add to VS Code settings**:
   - Open VS Code settings (`Cmd/Ctrl + ,`)
   - Click "Open Settings (JSON)" icon
   - Merge the MCP configuration

3. **Restart VS Code** and start using the tools!

### Claude Desktop Integration

1. **Locate Claude config** (create if doesn't exist):
   ```bash
   # macOS
   mkdir -p ~/Library/Application\ Support/Claude
   cp mcp-config/claude-desktop-config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   
   # Linux  
   mkdir -p ~/.config/claude
   cp mcp-config/claude-desktop-config.json ~/.config/claude/claude_desktop_config.json
   
   # Windows
   mkdir %APPDATA%\Claude
   copy mcp-config\claude-desktop-config.json %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Restart Claude Desktop**

## 10-Minute Full Demo

### Step 1: Ingest Sample Documents

```bash
# Ingest the sample Paul Graham essay
synapse ingest data/paul_graham_essay.txt

# Or ingest your own documents
synapse ingest /path/to/your/documents/

# Multiple files at once
find ~/Documents -name "*.md" -o -name "*.txt" | head -5 | xargs synapse ingest
```

### Step 2: Test Search

```bash
# Vector similarity search
synapse search "startup advice" --limit 5

# Keyword search  
synapse search "entrepreneurship" --search-type keyword

# Hybrid search
synapse search "building companies" --search-type hybrid
```

### Step 3: Test Question Answering

```bash
# Basic Q&A
synapse query ask "What advice does Paul Graham give about startups?"

# With graph context
synapse query ask "How should founders think about product development?" --include-graph

# Multiple related questions
synapse query ask "What are the biggest mistakes startup founders make?"
```

### Step 4: Try MCP Tools in Your IDE

**In VS Code or Claude Desktop:**

1. **Ingest files**: "Please ingest the files in my project directory"
2. **Search**: "Search for information about authentication in my codebase"  
3. **Ask questions**: "How does the user registration flow work?"

## Common Use Cases

### 1. Code Documentation Assistant

```bash
# Ingest your codebase
find . -name "*.py" -o -name "*.md" -o -name "*.js" | head -20 | xargs synapse ingest

# Ask questions in your IDE:
# - "How does the authentication system work?"
# - "What are the API endpoints for user management?" 
# - "Find examples of error handling patterns"
```

### 2. Research Assistant

```bash
# Ingest research papers, articles, documentation
synapse ingest ~/Research/*.pdf ~/Documents/*.md

# Query in IDE:
# - "Summarize the key findings about machine learning"
# - "What are the different approaches to natural language processing?"
# - "Find contradictory viewpoints on this topic"
```

### 3. Personal Knowledge Base

```bash
# Ingest notes, articles, documentation
synapse ingest ~/Notes/ ~/Bookmarks/ ~/Documents/

# Query through IDE:
# - "What did I learn about Docker last month?"
# - "Find my notes on Python best practices"
# - "What are my thoughts on project management?"
```

## Advanced Configuration

### Production Setup

```bash
# Production configuration
synapse config init --type production --no-interactive

# Configure for production deployment
export SYNAPSE_MEMGRAPH_HOST=memgraph.production.com
export SYNAPSE_API_HOST=0.0.0.0
export SYNAPSE_API_LOG_JSON=true
```

### Custom Embedding Models

```bash
# Use different embedding model
export SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL=all-mpnet-base-v2

# OpenAI embeddings
export SYNAPSE_EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY=your-api-key
```

### MCP Server Options

```bash
# TCP transport (for remote IDE)
synapse mcp start --transport tcp --host 0.0.0.0 --port 8765

# Custom API endpoint
synapse mcp start --api-url http://my-server:8000

# Debug mode
synapse mcp start --no-check-health
SYNAPSE_LOG_LEVEL=DEBUG synapse mcp start
```

## Docker Compose Setup

For containerized deployment:

```bash
# Use provided docker-compose
docker-compose up -d

# Or with custom configuration
cp examples/mcp/docker-compose.yml .
docker-compose up -d

# Check status
synapse compose status
```

## Monitoring and Maintenance

### Health Monitoring

```bash
# System health check
synapse mcp health

# API health
curl http://localhost:8000/health

# Detailed status  
synapse compose status
```

### Log Management

```bash
# View API logs
synapse compose logs graph-rag

# View all logs
synapse compose logs

# Follow logs
synapse compose logs --follow
```

### Performance Tuning

```bash
# Check vector store stats
synapse admin vector-stats

# Rebuild vector index
synapse admin vector-rebuild

# Database integrity check
synapse admin integrity-check
```

## Troubleshooting

### Common Issues

1. **"Docker not running"**:
   ```bash
   # Start Docker Desktop manually or:
   synapse up --start-docker
   ```

2. **"MCP package not installed"**:
   ```bash
   uv pip install "synapse-graph-rag[mcp]"
   ```

3. **"API not responding"**:
   ```bash
   # Check Docker containers
   docker ps
   
   # Restart services  
   synapse down && synapse up
   ```

4. **"No search results"**:
   ```bash
   # Check if documents are ingested
   curl http://localhost:8000/api/v1/admin/stats
   
   # Re-ingest documents
   synapse ingest /path/to/docs --replace
   ```

### Debug Mode

```bash
# Enable debug logging
export SYNAPSE_API_LOG_LEVEL=DEBUG

# Restart with debug
synapse down && synapse up

# Test MCP with debug
SYNAPSE_LOG_LEVEL=DEBUG synapse mcp test
```

### Getting Help

- **Documentation**: Check `docs/` directory
- **Examples**: See `examples/` directory  
- **Issues**: [GitHub Issues](https://github.com/neoforge-ai/synapse-graph-rag/issues)
- **Community**: Join our Discord server
- **Support**: Email support@neoforge.dev

## What's Next?

Now that you have Synapse GraphRAG running:

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Try advanced queries**: Use graph-enhanced search
3. **Integrate with your workflow**: Set up automated ingestion
4. **Scale up**: Deploy to production with Docker Compose
5. **Customize**: Extend with your own tools and integrations

## Summary

You now have:
- ✅ **Full GraphRAG system** running locally
- ✅ **MCP integration** for VS Code/Claude Desktop  
- ✅ **Document ingestion** and search capabilities
- ✅ **Question answering** with source citations
- ✅ **Production-ready** configuration options

**Total setup time: ~5-10 minutes**

The system is ready for:
- Code documentation and search
- Research and knowledge management  
- Personal note organization
- Team knowledge sharing
- Custom AI assistant development

Start exploring and building with Synapse GraphRAG! 🚀