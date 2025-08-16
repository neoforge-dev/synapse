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
# Test that configuration is recognized
curl -X POST "http://localhost:8000/api/v1/search/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key business strategies?",
    "search_type": "vector",
    "limit": 3
  }'
```

### Current Status: ✅ READY FOR PRODUCTION

The LLM integration infrastructure is **fully implemented and tested**. Simply add your API key to enable real LLM functionality.

🎯 **Phase 1 LLM Integration: Complete**