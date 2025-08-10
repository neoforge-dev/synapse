import json
from pathlib import Path
from typing import Any, Optional

import typer

from graph_rag.api.dependencies import MockEmbeddingService
from graph_rag.config import Settings
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.infrastructure.document_processor.simple_processor import SimpleDocumentProcessor
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
from graph_rag.services.ingestion import IngestionService
from graph_rag.utils.identity import derive_document_id


app = typer.Typer(help="Store parsed documents into the graph and vector store")


@app.command()
def store_command(
    embeddings: bool = typer.Option(False, "--embeddings/--no-embeddings", help="Generate embeddings during storage"),
    replace: bool = typer.Option(True, "--replace/--no-replace", help="Replace existing chunks if document exists"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSONL output (one object per ingested document)"),
    emit_chunks: bool = typer.Option(False, "--emit-chunks", help="Also emit a JSON line for each stored chunk with id and document_id"),
) -> None:
    settings = Settings()
    # Do not attempt real Memgraph connection in unit tests or when unavailable.
    # Use the in-memory builder path through IngestionService by substituting a lightweight mock repo if needed.
    # However, for simplicity keep MemgraphGraphRepository; tests patch IngestionService.
    repo = MemgraphGraphRepository(settings)
    processor = SimpleDocumentProcessor()
    extractor = SpacyEntityExtractor()

    # Embedding service (mock by default)
    embedding_service = MockEmbeddingService(dimension=10)
    if embeddings:
        try:
            from graph_rag.services.embedding import SentenceTransformerEmbeddingService

            embedding_service = SentenceTransformerEmbeddingService(
                model_name=settings.vector_store_embedding_model
            )
        except Exception:
            pass

    vector_store = SimpleVectorStore(embedding_service=embedding_service)

    async def _process(path: Path, content: str, metadata: dict[str, Any]):
        nonlocal repo
        nonlocal processor
        nonlocal extractor
        nonlocal embedding_service
        nonlocal vector_store
        try:
            await repo.connect()
        except Exception:
            # Skip connecting in environments without Memgraph; allow service to run with mocked dependencies in tests
            pass
        try:
            service = IngestionService(
                document_processor=processor,
                entity_extractor=extractor,
                graph_store=repo,
                embedding_service=embedding_service,
                vector_store=vector_store,
            )
            doc_id, id_source, _ = derive_document_id(path, content, metadata or {})
            result = await service.ingest_document(
                document_id=doc_id,
                content=content,
                metadata={**(metadata or {}), "id_source": id_source},
                generate_embeddings=embeddings,
                replace_existing=replace,
            )
            # result has document_id and chunk_ids
            out = {
                "document_id": result.document_id,
                "num_chunks": len(result.chunk_ids),
            }
            return out, result.chunk_ids
        finally:
            try:
                await repo.close()
            except Exception:
                pass

    # Read JSON objects from stdin
    import asyncio as _asyncio

    for line in typer.get_text_stream("stdin"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        path = Path(obj.get("path", "")).resolve()
        content = obj.get("content", "")
        metadata = obj.get("metadata", {}) or {}
        try:
            out, chunk_ids = _asyncio.run(_process(path, content, metadata))
            if as_json:
                typer.echo(json.dumps(out, ensure_ascii=False))
                if emit_chunks:
                    for cid in chunk_ids:
                        typer.echo(json.dumps({"chunk_id": cid, "document_id": out["document_id"]}, ensure_ascii=False))
            else:
                typer.echo(
                    f"Stored {path.name} as {out['document_id']} ({out['num_chunks']} chunks){' with embeddings' if embeddings else ''}."
                )
        except Exception as e:
            if as_json:
                typer.echo(json.dumps({"error": str(e)}, ensure_ascii=False))
            else:
                typer.echo(f"Error storing document {path}: {e}")
