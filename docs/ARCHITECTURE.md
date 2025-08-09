# Architecture (One-Pager)

- API (FastAPI) → Services → Core → Infrastructure → LLM
- Dependency injection in `graph_rag/api/dependencies.py` creates:
  - Graph store (`MemgraphGraphRepository`), Vector store (`SimpleVectorStore`/`FaissVectorStore`)
  - `IngestionService`, `SearchService`, `SimpleKnowledgeGraphBuilder`
- CLI (Typer) calls services directly in-process (`synapse ingest`, `synapse search`).
- Ingestion flow:
  1) Parse front matter / Notion property table → normalized metadata (`topics`, `aliases`, dates)
  2) Process to chunks via `DocumentProcessor`
  3) Optional embeddings via `EmbeddingService` → `VectorStore`
  4) Persist `Document`/`Chunk` to graph and create relationships (`CONTAINS`, topics)
  5) Project `Topic` nodes and relationships to `Document` and `Chunk`
- Search flow (planned): vector + graph retrieval, topic-aware ranking.
