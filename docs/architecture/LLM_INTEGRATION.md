# LLM Integration Guide

## ✅ Real LLM Integration Available

The Graph-RAG system supports real LLM integration with **OpenAI**, **Anthropic**, and **Ollama**.

### Configuration Options

#### 1. Anthropic (Claude) - **Recommended**
```bash
export SYNAPSE_LLM_TYPE=anthropic
export SYNAPSE_ANTHROPIC_API_KEY=sk-ant-api03-...
export SYNAPSE_LLM_MODEL_NAME=claude-3-5-sonnet-20241022
```

#### 2. OpenAI (GPT)
```bash
export SYNAPSE_LLM_TYPE=openai  
export SYNAPSE_OPENAI_API_KEY=sk-...
export SYNAPSE_LLM_MODEL_NAME=gpt-4o-mini
```

#### 3. Ollama (Local)
```bash
export SYNAPSE_LLM_TYPE=ollama
export SYNAPSE_OLLAMA_BASE_URL=http://localhost:11434
export SYNAPSE_LLM_MODEL_NAME=llama3.1:8b
```

#### 4. Mock (Testing/Demo)
```bash
export SYNAPSE_LLM_TYPE=mock  # Default for testing
```

### Usage

Once configured with a valid API key, the system will:

- ✅ **Generate real answers** to queries using LLM reasoning
- ✅ **Provide explanations** for search results  
- ✅ **Create citations** with proper source attribution
- ✅ **Enable advanced reasoning** over knowledge graphs

### Testing Integration

```bash
# Test that configuration is recognised
curl -X POST "http://localhost:18888/api/v1/search/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key business strategies?",
    "search_type": "vector",
    "limit": 3
  }'
```

### Current Status

By default the application runs in a **mock** mode:

- `create_graph_repository` falls back to `MockGraphRepository` unless Memgraph is available and enabled.
- `create_llm_service` uses `MockLLMService` unless you set `SYNAPSE_LLM_TYPE=openai` (or another provider) and provide credentials.

To enable full production behaviour:

1. Run `synapse up` (or your own Memgraph instance) and set `SYNAPSE_DISABLE_GRAPH=false`.
2. Export your provider credentials, e.g. `export SYNAPSE_LLM_TYPE=openai` and `export OPENAI_API_KEY=...`.
3. Restart the API and re-run the health checks above.

🎯 **Phase 1 LLM Integration:** routing, dependency wiring, and fallbacks are complete. Production scenarios still require real credentials and Memgraph connectivity.
