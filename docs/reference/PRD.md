# PRD (Pragmatic Graph RAG)

## Mission
Turn personal notes (Notion/Obsidian) into a queryable knowledge graph with topic organization and semantic retrieval. Mac-first, CLI/API now, MCP soon.

## Personas
- Mac power user with large personal KB; wants fast ingest, topic organization, and search.

## Scope (v0)
- CLI ingest for Markdown/Notion export
- Topic extraction and topic graph projection
- Embeddings (opt-in in CLI) and vector store (simple/FAISS)
- FastAPI for API queries and health
- Mac ergonomics: `make up/down`, optional autostart doc

## Non-goals (v0)
- Cloud deployment, multi-tenant auth, advanced LLM-based extraction

## Success Criteria
- Ingest a Notion/Obsidian folder in minutes
- Topics visible as graph edges; semantic search returns relevant chunks
- One-command startup and clear Quickstart
- Stable document identity: re-ingesting the same page/file updates in-place; renames/moves do not duplicate documents
