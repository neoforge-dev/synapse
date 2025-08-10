# Architecture (One-Pager)

- API (FastAPI) → Services → Core → Infrastructure → LLM
- Dependency injection in `graph_rag/api/dependencies.py` creates:
  - Graph store (`MemgraphGraphRepository`), Vector store (`SimpleVectorStore`/`FaissVectorStore`)
  - `IngestionService`, `SearchService`, `SimpleKnowledgeGraphBuilder`
- CLI (Typer) calls services directly in-process (`synapse ingest`, `synapse search`).
- CLI decomposition for scripting: `synapse discover` → `synapse parse` → `synapse store`.
- `discover`: supports `--include/--exclude` globs, and `--stdin` for a JSON array of roots.
- `parse`: merges YAML/Notion metadata; `--meta key=value` and `--meta key:=jsonValue` for typed JSON.
- `store`: optionally `--embeddings`; `--json` output and `--emit-chunks` for per-chunk JSON lines.
- Ingestion flow:
  1) Parse front matter / Notion property table → normalized metadata (`topics`, `aliases`, dates)
  2) Derive canonical `document_id` (metadata `id` → Notion UUID → Obsidian `id` → content hash → path-hash fallback)
  3) Process to chunks via `DocumentProcessor`
  3) Optional embeddings via `EmbeddingService` → `VectorStore`
  4) Persist `Document`/`Chunk` to graph and create relationships (`CONTAINS`, topics)
  5) Project `Topic` nodes and relationships to `Document` and `Chunk`
- Search flow (planned): vector + graph retrieval, topic-aware ranking.

Notes on identity and idempotence:
- `document_id` is stable across renames; re-ingestion with `--replace` deletes prior chunks/vectors before adding new ones.
- `id_source` records how the ID was derived (metadata `id`, Notion UUID, Obsidian `id`, content hash, or path hash).
