import json
from pathlib import Path
from typing import Any, Optional

import typer
import yaml

app = typer.Typer(help="Parse files into JSON objects with content and metadata")


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        if "," in value:
            return [s.strip().lstrip("#") for s in value.split(",") if s.strip()]
        if "#" in value:
            return [s.strip().lstrip("#") for s in value.split() if s.strip()]
        return [value.strip()] if value.strip() else []
    return [str(value)]


def _parse_front_matter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if text.startswith("---\n"):
        end_idx = text.find("\n---\n", 4)
        if end_idx == -1:
            return {}
        fm_text = text[4:end_idx]
        try:
            raw = yaml.safe_load(fm_text) or {}
            data = raw if isinstance(raw, dict) else {}
            normalized: dict[str, Any] = dict(data)
            if "tags" in data and data.get("tags") is not None:
                normalized["topics"] = _ensure_list(data.get("tags"))
            if "Topics" in data and data.get("Topics") is not None:
                topics = _ensure_list(data.get("Topics"))
                normalized["topics"] = list({*(normalized.get("topics", [])), *topics})
            if "aliases" in data and data.get("aliases") is not None:
                normalized["aliases"] = _ensure_list(data.get("aliases"))
            for k in ("created", "created_at"):
                if k in data and data.get(k):
                    normalized["created_at"] = str(data.get(k))
                    break
            for k in ("updated", "updated_at", "last_edited_time", "Last edited time"):
                if k in data and data.get(k):
                    normalized["updated_at"] = str(data.get(k))
                    break
            # Ensure all metadata values are JSON-serializable (e.g., dates -> str)
            for k, v in list(normalized.items()):
                try:
                    json.dumps(v)
                except Exception:
                    normalized[k] = str(v)
            return normalized
        except Exception:
            return {}
    # Notion property table (beginning of file)
    try:
        lines = text.splitlines()
        window = [ln.strip() for ln in lines[:20] if ln.strip()]
        if (
            len(window) >= 3
            and "|" in window[0]
            and "|" in window[1]
            and set(window[1]) <= set("|- :")
        ):
            props: dict[str, str] = {}
            for row in window[2:]:
                if "|" not in row:
                    break
                row_norm = row.strip().strip("|")
                cols = [c.strip() for c in row_norm.split("|")]
                cols = [c for c in cols if c]
                if len(cols) < 2:
                    continue
                key, value = cols[0], cols[1]
                if key:
                    props[key] = value
            normalized: dict[str, Any] = {}
            for k in ("Tags", "tags", "Topics"):
                if k in props:
                    normalized["topics"] = _ensure_list(props[k])
                    break
            for k in ("Aliases", "aliases"):
                if k in props:
                    normalized["aliases"] = _ensure_list(props[k])
                    break
            for k in ("Created", "Created time", "created", "created_at"):
                if k in props:
                    normalized["created_at"] = props[k]
                    break
            for k in ("Last edited time", "Updated", "updated", "updated_at"):
                if k in props:
                    normalized["updated_at"] = props[k]
                    break
            for k, v in props.items():
                if k not in (
                    "Tags",
                    "tags",
                    "Topics",
                    "Aliases",
                    "aliases",
                    "Created",
                    "Created time",
                    "Last edited time",
                    "Updated",
                    "created",
                    "created_at",
                    "updated",
                    "updated_at",
                ):
                    normalized[k.lower().replace(" ", "_")] = v
            return normalized
    except Exception:
        return {}
    return {}


@app.command()
def parse_command(
    meta: Optional[list[str]] = typer.Option(
        None,
        "--meta",
        help="Additional metadata entries key=value or key:=json (repeatable)",
    ),
    meta_file: Optional[Path] = typer.Option(
        None, "--meta-file", help="Path to YAML/JSON meta file to merge"
    ),
) -> None:
    metadata_from_kv: dict[str, Any] = {}
    if meta:
        for it in meta:
            if ":=" in it:
                k, v = it.split(":=", 1)
                k = k.strip()
                try:
                    metadata_from_kv[k] = json.loads(v)
                except Exception:
                    # fallback to raw string if JSON parsing fails
                    metadata_from_kv[k] = v
            elif "=" in it:
                k, v = it.split("=", 1)
                metadata_from_kv[k.strip()] = v.strip()
    metadata_from_file: dict[str, Any] = {}
    if meta_file:
        try:
            txt = meta_file.read_text(encoding="utf-8")
            if meta_file.suffix.lower() in {".yaml", ".yml"}:
                obj = yaml.safe_load(txt) or {}
            elif meta_file.suffix.lower() == ".json":
                obj = json.loads(txt)
            else:
                try:
                    obj = yaml.safe_load(txt) or {}
                except Exception:
                    obj = json.loads(txt)
            if isinstance(obj, dict):
                metadata_from_file = obj
        except Exception:
            metadata_from_file = {}

    # Read file paths from stdin
    for line in typer.get_text_stream("stdin"):
        p = Path(line.strip())
        if not p.exists() or not p.is_file():
            # Skip silently to keep pipelines robust
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            content = ""
        fm = _parse_front_matter(p)
        merged = {**fm, **metadata_from_file, **metadata_from_kv}
        obj = {"path": str(p.resolve()), "content": content, "metadata": merged}
        typer.echo(json.dumps(obj, ensure_ascii=False))
