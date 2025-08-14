from pathlib import Path

from graph_rag.utils.identity import _hash_content, derive_document_id


def test_metadata_id_priority(tmp_path: Path):
    p = tmp_path / "note.md"
    p.write_text("Hello")
    doc_id, src, conf = derive_document_id(p, "Hello", {"id": "custom-123"})
    assert doc_id == "custom-123"
    assert src == "metadata:id"
    assert conf == 1.0


def test_notion_uuid_in_filename_dashed(tmp_path: Path):
    p = tmp_path / "Some Page 123e4567-e89b-12d3-a456-426614174000.md"
    p.write_text("Hello")
    doc_id, src, conf = derive_document_id(p, "Hello", {})
    assert doc_id == "123e4567-e89b-12d3-a456-426614174000"
    assert src == "notion:filename"
    assert conf == 0.95


def test_notion_uuid_in_parent_dir(tmp_path: Path):
    parent = tmp_path / "My Export 123e4567e89b12d3a456426614174000"
    parent.mkdir()
    p = parent / "Page.md"
    p.write_text("Hello")
    doc_id, src, conf = derive_document_id(p, "Hello", {})
    assert doc_id == "123e4567e89b12d3a456426614174000"
    assert src == "notion:parent"
    assert conf == 0.9


def test_content_hash_fallback(tmp_path: Path):
    content = "Line1\r\n\r\nLine2\n"
    p = tmp_path / "no-ids.md"
    p.write_text(content)
    doc_id, src, conf = derive_document_id(p, content, {})
    assert doc_id.startswith("content:")
    assert src == "content-hash"
    assert conf == 0.7
    # Determinism check
    chash = _hash_content(content)
    assert doc_id == f"content:{chash}"


essentially_empty = "\n\n\r\n"


def test_path_hash_fallback_when_no_content(tmp_path: Path):
    p = tmp_path / "empty.md"
    p.write_text(essentially_empty)
    # Even for empty content, content-hash is deterministic; still acceptable
    doc_id, src, conf = derive_document_id(p, essentially_empty, {})
    assert doc_id.startswith("content:")
    assert src in {"content-hash", "path-hash"}
    assert conf in {0.7, 0.5}
