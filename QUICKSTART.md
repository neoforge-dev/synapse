# 🚀 Synapse GraphRAG - 2 Minute Quickstart

Transform your knowledge base into an intelligent, queryable system in under 2 minutes!

## ⚡ Zero-Config Quick Start

### Option 1: Vector-Only Mode (No Docker required)
Perfect for trying Synapse without any setup complexity.

```bash
# Install Synapse 
uv pip install synapse-graph-rag

# Run the interactive setup wizard
synapse init wizard --quick --vector-only

# Ingest your first document
echo "Machine learning is transforming healthcare through better diagnostics and personalized treatments." | synapse ingest dummy_path --stdin --meta title="ML in Healthcare"

# Ask intelligent questions
synapse query ask "How is ML being used in healthcare?"
```

### Option 2: Full Graph Features (Docker required)
Get the complete graph-enhanced experience with relationship extraction and advanced retrieval.

```bash
# Install Synapse
uv pip install synapse-graph-rag

# One-command setup with auto-Docker management
synapse up

# Ingest and immediately query
echo "Artificial intelligence enables doctors to analyze medical images with unprecedented accuracy." | synapse ingest dummy_path --stdin --meta title="AI Diagnostics"
synapse query ask "What can AI help doctors with?"
```

## ✅ Verification Checkpoints

After each step, verify your setup:

```bash
# Check system status
synapse init check

# View service health
synapse compose status

# Test basic functionality
synapse search "test query"
```

## 📁 Real-World Usage Examples

### Ingest Your Notes
```bash
# Single file
synapse ingest ~/Documents/meeting-notes.md

# Entire directory with progress tracking
synapse discover ~/Documents/research/ | synapse parse | synapse store --embeddings

# With metadata for better organization
synapse ingest project-summary.md --meta project=apollo --meta status=active
```

### Query Your Knowledge
```bash
# Natural language search
synapse search "project deadlines"

# AI-powered Q&A with citations
synapse query ask "What are the key findings from last week's research?"

# Explore connections
synapse graph neighbors "machine learning"
```

### IDE Integration (VS Code, Claude Desktop)
```bash
# Start MCP server for IDE integration
synapse mcp start --port 3001

# Your IDE can now use Synapse as a knowledge assistant!
```

## 🎯 Next Steps (30 seconds each)

1. **Configure LLM Provider** for better answers:
   ```bash
   # OpenAI (recommended)
   export SYNAPSE_LLM_TYPE=openai
   export SYNAPSE_OPENAI_API_KEY=your_key_here
   
   # Or Anthropic Claude
   export SYNAPSE_LLM_TYPE=anthropic
   export SYNAPSE_ANTHROPIC_API_KEY=your_key_here
   ```

2. **Connect Your Notion** workspace:
   ```bash
   synapse notion auth
   synapse notion sync --database-id your_database_id
   ```

3. **Set up monitoring** for production use:
   ```bash
   synapse admin health
   synapse compose logs --follow
   ```

## 🔧 Troubleshooting

**Services won't start?**
```bash
synapse init wizard --vector-only  # Skip Docker for now
```

**Getting mock responses?**
```bash
synapse init check  # Verify LLM configuration
export SYNAPSE_LLM_TYPE=openai  # Set a real provider
```

**Import errors?**
```bash
uv pip install --upgrade synapse-graph-rag
uv pip install -e .[dev]  # For development
```

## 🎉 Success Metrics

You know Synapse is working when:
- ✅ `synapse init check` shows all green
- ✅ Questions return intelligent answers (not "Mock response...")
- ✅ Search finds relevant content from your documents
- ✅ `synapse compose status` shows services running (full mode)

## 🚀 Performance Tips

**Fast ingestion:**
```bash
# Process multiple files in parallel
find docs/ -name "*.md" | xargs -P 4 -I {} synapse ingest {}
```

**Better search results:**
```bash
# Enable embeddings for semantic search
synapse store --embeddings your-docs/

# Use graph context for related concepts
synapse query ask "project status" --include-graph
```

**Memory efficiency:**
```bash
# Monitor resource usage
synapse admin metrics

# Optimize vector store
synapse admin rebuild-index
```

---

🎯 **Goal**: From zero to intelligent knowledge assistant in 2 minutes!

💡 **Need help?** Run `synapse --help` or visit our [documentation](https://github.com/neoforge-ai/synapse-graph-rag).

Ready to turn your documents into an AI-powered knowledge system? Let's go! 🚀