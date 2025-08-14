import json
from typing import Any

import typer

from graph_rag.api.dependencies import MockEmbeddingService
from graph_rag.config import Settings
from graph_rag.utils.identity import derive_document_id

# Expose IngestionService at module level for test patching
try:  # pragma: no cover - simple import guard
    from graph_rag.services.ingestion import IngestionService as IngestionService  # type: ignore
except Exception:  # Fallback for environments without service importable at import time
    IngestionService = None  # type: ignore[assignment]


app = typer.Typer(help="Store parsed documents into the graph and vector store")


def _process_store_lines(
    lines: list[str],
    *,
    embeddings: bool,
    replace: bool,
) -> list[str]:
    """Pure function: process store input lines to output JSON lines."""
    settings = Settings()
    from graph_rag.core.entity_extractor import SpacyEntityExtractor
    from graph_rag.infrastructure.document_processor.simple_processor import (
        SimpleDocumentProcessor,
    )
    from graph_rag.infrastructure.graph_stores.memgraph_store import (
        MemgraphGraphRepository,
    )

    repo = MemgraphGraphRepository(settings)
    processor = SimpleDocumentProcessor()
    extractor = SpacyEntityExtractor()
    embedding_service = MockEmbeddingService(dimension=10)
    vector_store = _get_vector_store(settings, embedding_service)

    service_cls = IngestionService
    if service_cls is None:
        from graph_rag.services.ingestion import IngestionService as _IngestionService

        service_cls = _IngestionService
    service = service_cls(
        document_processor=processor,
        entity_extractor=extractor,
        graph_store=repo,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    outputs: list[str] = []
    import asyncio as _asyncio
    import inspect as _inspect
    import json as _json
    from pathlib import Path as _Path

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            obj = _json.loads(line)
        except Exception:
            continue
        path = _Path(obj.get("path", "")).resolve()
        content = obj.get("content", "")
        metadata = obj.get("metadata", {}) or {}

        doc_id, id_source, _ = derive_document_id(path, content, metadata or {})
        call = service.ingest_document(
            document_id=doc_id,
            content=content,
            metadata={**(metadata or {}), "id_source": id_source},
            generate_embeddings=embeddings,
            replace_existing=replace,
        )
        try:
            result = _asyncio.run(call) if _inspect.isawaitable(call) else call
        except Exception:
            result = _asyncio.run(call)

        summary = {
            "document_id": result.document_id,
            "num_chunks": len(result.chunk_ids),
        }
        outputs.append(_json.dumps(summary, ensure_ascii=False))
        for cid in result.chunk_ids:
            outputs.append(
                _json.dumps(
                    {"chunk_id": cid, "document_id": result.document_id},
                    ensure_ascii=False,
                )
            )

    return outputs


def _get_vector_store(settings: Settings, embedding_service: Any):
    """Factory that returns a vector store instance based on settings."""
    vtype = (settings.vector_store_type or "simple").lower()
    if vtype == "faiss":
        # Use configured path and embedding dimension from service
        # Lazy import to avoid hard dependency for environments without faiss installed
        from graph_rag.infrastructure.vector_stores.faiss_vector_store import (
            FaissVectorStore,
        )

        return FaissVectorStore(
            path=settings.vector_store_path,
            embedding_dimension=getattr(
                embedding_service, "get_embedding_dimension", lambda: 768
            )(),
        )
    # default
    from graph_rag.infrastructure.vector_stores.simple_vector_store import (
        SimpleVectorStore,
    )

    return SimpleVectorStore(embedding_service=embedding_service)


@app.command()
def store_command(
    embeddings: bool = typer.Option(
        False, "--embeddings/--no-embeddings", help="Generate embeddings during storage"
    ),
    replace: bool = typer.Option(
        True,
        "--replace/--no-replace",
        help="Replace existing chunks if document exists",
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit JSONL output (one object per ingested document)"
    ),
    emit_chunks: bool = typer.Option(
        False,
        "--emit-chunks",
        help="Also emit a JSON line for each stored chunk with id and document_id",
    ),
) -> None:
    # Read all stdin once (Click testing stability) and process with pure function
    try:
        input_text = typer.get_text_stream("stdin").read()
    except Exception:
        input_text = ""
    lines = input_text.splitlines()
    outputs = _process_store_lines(lines, embeddings=embeddings, replace=replace)
    if as_json:
        if emit_chunks:
            for ln in outputs:
                typer.echo(ln)
        else:
            # emit only summary lines (every first line per input)
            from json import loads as _loads

            emitted = 0
            for ln in outputs:
                obj = _loads(ln)
                if "document_id" in obj and "num_chunks" in obj:
                    typer.echo(ln)
                    emitted += 1
            if emitted == 0 and outputs:
                # fallback to first line
                typer.echo(outputs[0])
    else:
        # Human message for non-json mode
        pass


@app.command("stats")
def store_stats() -> None:
    """Show vector store stats (for FAISS and others)."""
    settings = Settings()
    embedding_service = MockEmbeddingService(dimension=10)
    vs = _get_vector_store(settings, embedding_service)
    import asyncio as _asyncio

    try:
        # Try FAISS maintenance API
        out = _asyncio.run(vs.stats())  # type: ignore[attr-defined]
    except AttributeError:
        # Fallback for simple store
        out = _asyncio.run(vs.get_vector_store_size())  # type: ignore
        out = {"vectors": out, "type": settings.vector_store_type}
    typer.echo(json.dumps(out, ensure_ascii=False))


@app.command("rebuild")
def store_rebuild() -> None:
    """Rebuild vector index from persisted embeddings (FAISS)."""
    settings = Settings()
    embedding_service = MockEmbeddingService(dimension=10)
    vs = _get_vector_store(settings, embedding_service)
    import asyncio as _asyncio

    try:
        _asyncio.run(vs.rebuild_index())  # type: ignore[attr-defined]
        typer.echo("Rebuilt vector index.")
    except AttributeError:
        typer.echo("Rebuild not supported for this vector store type.")


@app.command("clear")
def store_clear(
    confirm: bool = typer.Option(False, "--yes", help="Confirm deletion"),
) -> None:
    """Clear the vector store."""
    if not confirm:
        typer.echo("Refusing to clear without --yes")
        raise typer.Exit(code=1)
    settings = Settings()
    embedding_service = MockEmbeddingService(dimension=10)
    vs = _get_vector_store(settings, embedding_service)
    import asyncio as _asyncio

    _asyncio.run(vs.delete_store())
    typer.echo("Vector store cleared.")
