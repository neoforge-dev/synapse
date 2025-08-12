import json
import logging
import re
from typing import Optional
from datetime import datetime, timezone
import json as _json
from pathlib import Path
import uuid

import httpx
import typer

from graph_rag.config import Settings
from graph_rag.infrastructure.notion_client import NotionClient
from graph_rag.infrastructure.notion_render import render_blocks_to_markdown
from graph_rag.utils.identity import derive_document_id
from graph_rag.cli.commands.store import _process_store_lines

app = typer.Typer(help="Notion API sync utilities")
logger = logging.getLogger(__name__)


@app.command()
def sync(
    db_id: Optional[str] = typer.Option(None, "--db", help="Notion database ID"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO timestamp for incremental sync"),
    query: Optional[str] = typer.Option(None, "--query", help="Full-text search query"),
    limit: int = typer.Option(100, "--limit", help="Max pages to fetch"),
    embeddings: bool = typer.Option(False, "--embeddings/--no-embeddings", help="Generate embeddings while storing"),
    replace: bool = typer.Option(True, "--replace/--no-replace", help="Replace existing document chunks"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON lines of pages (id, title) or store results"),
    # Attachments policy: ignore (strip), link (default), download (save locally and rewrite links)
    attachments: str = typer.Option(
        "link",
        "--attachments",
        help="Attachment handling policy: ignore|link|download",
    ),
    download_path: Optional[Path] = typer.Option(
        None, "--download-path", help="Directory to save downloaded attachments"
    ),
    # Safety: preview-only execution that prints the plan (adds/updates/deletes) and exits
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview planned changes only"),
    state_file: Optional[Path] = typer.Option(None, "--state-file", help="Path to save/load incremental sync state"),
    save_state: bool = typer.Option(True, "--save-state/--no-save-state", help="Persist latest cursor/time for next run"),
):
    """Sync pages from Notion; when --json is omitted, store directly via local ingestion pipeline."""
    try:
        client = NotionClient(Settings())
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    # Validate attachments policy
    attachments = (attachments or "link").lower()
    if attachments not in {"ignore", "link", "download"}:
        typer.echo("Error: --attachments must be one of: ignore|link|download")
        raise typer.Exit(2)
    include_assets = attachments in {"link", "download"}

    fetched = 0
    cursor: Optional[str] = None
    # Load previous state if available and since not provided
    state_path = state_file or Path("~/.graph_rag/notion_sync_state.json").expanduser()
    context_key = f"db:{db_id}" if db_id else f"search:{query or ''}"
    last_seen_time: Optional[str] = None
    # Track per-page last_edited_time for diffing in dry-run
    prior_pages: dict[str, str] = {}
    if since:
        last_seen_time = since
    elif state_path.exists():
        try:
            data = _json.loads(state_path.read_text())
            last_seen_time = data.get(context_key, {}).get("last_edited_time")
            prior_pages = data.get(context_key, {}).get("pages", {}) or {}
        except Exception:
            last_seen_time = None
            prior_pages = {}

    # Accumulators for dry-run
    planned_actions: list[dict] = []
    seen_ids: set[str] = set()
    while fetched < limit:
        if db_id:
            # Add server-side filter for since if provided
            page_size = min(50, limit - fetched)
            payload_override = None
            if last_seen_time:
                # Notion DB query filter format
                payload_override = {
                    "filter": {
                        "timestamp": "last_edited_time",
                        "last_edited_time": {"on_or_after": last_seen_time},
                    },
                    "page_size": page_size,
                }
            if payload_override:
                # Use internal client request for custom payload
                data = client._request("POST", f"/databases/{db_id}/query", json=payload_override)
            else:
                data = client.query_database(db_id, start_cursor=cursor, page_size=page_size)
        else:
            data = client.list_pages(query=query, start_cursor=cursor, page_size=min(50, limit - fetched))
        results = data.get("results", [])
        for item in results:
            page_id = item.get("id")
            title = None
            props = item.get("properties", {}) or {}
            for v in props.values():
                if v and v.get("type") == "title":
                    title_parts = v.get("title", [])
                    title = "".join([t.get("plain_text", "") for t in title_parts])
                    break
            # Skip by since for search path (no server filter)
            if last_seen_time and not db_id:
                led = item.get("last_edited_time")
                try:
                    if led and led < last_seen_time:
                        continue
                except Exception:
                    pass
            # Determine dry-run action compared to prior_pages
            seen_ids.add(page_id)
            page_edited = item.get("last_edited_time")
            prior_edit = prior_pages.get(page_id)
            if not prior_edit:
                action = "add"
            elif page_edited and page_edited > prior_edit:
                action = "update"
            else:
                action = "skip"

            if dry_run:
                planned_actions.append(
                    {
                        "action": action,
                        "page_id": page_id,
                        "title": title,
                        "last_edited_time": page_edited,
                    }
                )
            else:
                # fetch blocks to render content
                blocks = client.get_blocks(page_id)
                children = blocks.get("results", [])
                content = render_blocks_to_markdown(children, include_assets=include_assets)

                # If attachments policy is download, fetch assets and rewrite links
                if attachments == "download":
                    content = _download_and_rewrite_assets(
                        content, (download_path or Path.cwd()) / "notion_assets" / page_id
                    )

                # derive metadata (map common Notion properties)
                metadata = {"source": "notion", "id": page_id}
                if title:
                    metadata["title"] = title
                # tags / multi-select
                for k, v in props.items():
                    if v and v.get("type") == "multi_select":
                        tags = [opt.get("name") for opt in v.get("multi_select", []) if opt and opt.get("name")]
                        if tags:
                            metadata.setdefault("topics", tags)
                    if v and v.get("type") == "date":
                        date_obj = v.get("date") or {}
                        if date_obj.get("start"):
                            metadata.setdefault("created_at", date_obj.get("start"))
                        if date_obj.get("end"):
                            metadata.setdefault("updated_at", date_obj.get("end"))
                    if v and v.get("type") == "rich_text" and k.lower() in {"aliases", "alias"}:
                        alias_text = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
                        if alias_text:
                            metadata.setdefault("aliases", [alias_text])

                if json_out:
                    output = {"id": page_id, "title": title, "content": content, "metadata": metadata}
                    typer.echo(json.dumps(output, ensure_ascii=False))
                else:
                    # feed into store pipeline directly
                    line = json.dumps({"path": f"notion://{page_id}", "content": content, "metadata": metadata}, ensure_ascii=False)
                    outputs = _process_store_lines([line], embeddings=embeddings, replace=replace)
                    for out in outputs:
                        typer.echo(out)
            if page_edited and (not last_seen_time or page_edited > last_seen_time):
                last_seen_time = page_edited
            fetched += 1
            if fetched >= limit:
                break
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    # For dry-run, include deletes: pages in prior_pages but not seen in this run (only when querying a DB without since)
    if dry_run and db_id and not since:
        missing = set(prior_pages.keys()) - seen_ids
        for mid in sorted(missing):
            planned_actions.append(
                {
                    "action": "delete",
                    "page_id": mid,
                    "title": None,
                    "last_edited_time": prior_pages.get(mid),
                }
            )

    if dry_run:
        # Print plan lines and exit
        for entry in planned_actions:
            typer.echo(json.dumps(entry, ensure_ascii=False))
        return

    # Save state
    if save_state and last_seen_time:
        try:
            state = {}
            if state_path.exists():
                state = _json.loads(state_path.read_text())
            # Update per-page map
            new_pages = prior_pages.copy()
            for pid in seen_ids:
                # Use latest seen time as conservative baseline
                new_pages[pid] = max(last_seen_time, new_pages.get(pid, "")) if new_pages.get(pid) else last_seen_time
            state[context_key] = {"last_edited_time": last_seen_time, "pages": new_pages}
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(_json.dumps(state, ensure_ascii=False, indent=2))
            logger.info(f"Saved Notion sync state to {state_path}")
        except Exception as e:
            logger.warning(f"Failed to save Notion sync state: {e}")


def _download_and_rewrite_assets(content: str, target_dir: Path) -> str:
    """Download http(s) assets referenced in Markdown and rewrite links to local files.

    Creates the target directory if missing. Returns the rewritten content string.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    def _download(url: str) -> str:
        if not url.startswith("http://") and not url.startswith("https://"):
            return url
        # Choose filename from URL path or random
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            name = Path(parsed.path).name or f"asset-{uuid.uuid4().hex}"
        except Exception:
            name = f"asset-{uuid.uuid4().hex}"
        dest = target_dir / name
        try:
            with httpx.stream("GET", url, timeout=30.0) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes():
                        if chunk:
                            f.write(chunk)
            return str(dest)
        except Exception:
            return url  # Fallback: keep remote link

    # Replace image links ![alt](url)
    def _img_sub(m: re.Match[str]) -> str:
        alt = m.group(1)
        url = m.group(2)
        new_url = _download(url)
        return f"![{alt}]({new_url})"

    # Replace file links [name](url)
    def _file_sub(m: re.Match[str]) -> str:
        name = m.group(1)
        url = m.group(2)
        new_url = _download(url)
        return f"[{name}]({new_url})"

    # Regexes capturing alt/text and URL
    content = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _img_sub, content)
    content = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _file_sub, content)
    return content
