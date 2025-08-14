import hashlib
import re
from pathlib import Path
from typing import Any

_UUID_DASHED_RE = re.compile(
    r"(?i)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
_UUID_COMPACT_RE = re.compile(r"(?i)([0-9a-f]{32})")


def _normalize_text_for_hash(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


def _hash_content(content: str) -> str:
    normalized = _normalize_text_for_hash(content)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _hash_path(path: Path) -> str:
    try:
        abs_lower = str(path.resolve()).lower()
    except Exception:
        abs_lower = str(path.absolute()).lower()
    return hashlib.sha1(abs_lower.encode("utf-8")).hexdigest()


def _extract_uuid_from_name(name: str) -> str | None:
    m = _UUID_DASHED_RE.search(name)
    if m:
        return m.group(1).lower()
    m2 = _UUID_COMPACT_RE.search(name)
    if m2:
        return m2.group(1).lower()
    return None


def derive_document_id(
    path: Path, content: str, metadata: dict[str, Any] | None = None
) -> tuple[str, str, float]:
    """
    Derive a stable canonical document_id for a file/page.

    Priority:
    1) Explicit metadata id (id, document_id, page_id, notion_id)
    2) Notion page UUID from filename or parent dirs (dashed or 32-hex)
    3) Normalized content hash
    4) Path-hash fallback

    Returns: (document_id, id_source, confidence)
    """
    md = metadata or {}

    # 1) Explicit metadata id keys
    for key in ("id", "document_id", "page_id", "notion_id"):
        val = md.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip(), f"metadata:{key}", 1.0

    # 2) Notion UUID in filename or parent directories
    for candidate in (path.stem, path.name):
        uuid = _extract_uuid_from_name(candidate)
        if uuid:
            return uuid, "notion:filename", 0.95
    for part in list(path.parts)[-4:]:
        uuid = _extract_uuid_from_name(part)
        if uuid:
            return uuid, "notion:parent", 0.9

    # 3) Content hash
    try:
        chash = _hash_content(content)
        if chash:
            return f"content:{chash}", "content-hash", 0.7
    except Exception:
        pass

    # 4) Path hash fallback
    try:
        phash = _hash_path(path)
        return f"path:{phash}", "path-hash", 0.5
    except Exception:
        return str(path), "path", 0.3
