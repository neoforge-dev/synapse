# Enabling Production Backends

Synapse defaults to lightweight mock services so the CLI, API, and tests run without external dependencies. Follow this guide when you are ready to enable the full stack (Memgraph graph store, real LLMs, optional Postgres analytics).

## 1. Memgraph Graph Store

1. Start Memgraph (included in `synapse up`):
   ```bash
   synapse up --wait
   ```

2. Ensure `mgclient` is installed (it ships with the project). If you disabled graph support earlier, unset the flag:
   ```bash
   export SYNAPSE_DISABLE_GRAPH=false
   ```

3. Optional tuning:
   ```bash
   export SYNAPSE_MEMGRAPH_HOST=127.0.0.1
   export SYNAPSE_MEMGRAPH_PORT=17687    # host port from docker-compose
   export SYNAPSE_MEMGRAPH_USER=memgraph
   export SYNAPSE_MEMGRAPH_PASSWORD=your-password
   ```

4. Restart the API/CLI session; `create_graph_repository` will now return `MemgraphGraphRepository` instead of the mock implementation.

## 2. Vector Store Persistence

By default the simple in-memory vector store is used. For persisted embeddings shared across processes, set:
```bash
export SYNAPSE_VECTOR_STORE_TYPE=faiss
export SYNAPSE_VECTOR_STORE_PATH=~/.synapse/faiss_store
```
Run `synapse admin vector-stats` to verify the FAISS index is active.

## 3. LLM Providers

1. Choose a provider via `SYNAPSE_LLM_TYPE` (`openai`, `anthropic`, `ollama`, etc.).
2. Provide credentials:
   ```bash
   export SYNAPSE_LLM_TYPE=openai
   export OPENAI_API_KEY=sk-...
   ```
3. Optional settings:
   ```bash
   export SYNAPSE_LLM_MODEL_NAME=gpt-4o-mini
   export SYNAPSE_LLM_TEMPERATURE=0.3
   ```
4. Restart the API; requests that use the LLM (e.g. `/advanced/` endpoints) now call the real provider.

## 4. Postgres Analytics (Optional)

1. Ensure the Docker service is running (`synapse up` starts Postgres on host port 15432).
2. Configure the URI:
   ```bash
   export SYNAPSE_POSTGRES_URL=postgresql://synapse:synapse_password@127.0.0.1:15432/synapse_business_core
   ```
3. Run any required migrations or analytics scripts before relying on the dashboards.

## 5. Verifying the Setup

```bash
# API health
curl http://localhost:18888/health

# Graph connectivity check
synapse admin graph-stats

# LLM smoke test
synapse query ask "Summarise the current knowledge graph status"
```

If any component fails, review the logs (`synapse compose logs`) and adjust the environment variables accordingly.
