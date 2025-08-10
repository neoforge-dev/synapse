from pathlib import Path
import json
from typer.testing import CliRunner

from graph_rag.cli.main import app


def create_fs(tmp_path: Path):
    (tmp_path / "a.md").write_text("hello", encoding="utf-8")
    (tmp_path / ".hidden.md").write_text("secret", encoding="utf-8")
    # Obsidian folder should be ignored
    obs = tmp_path / ".obsidian"
    obs.mkdir()
    (obs / "ignored.md").write_text("ignore", encoding="utf-8")
    # Notion export style folder with assets
    page = tmp_path / "My Page"
    page.mkdir()
    (page / "My Page.md").write_text("content", encoding="utf-8")
    assets = page / "assets"
    assets.mkdir()
    (assets / "image.png").write_bytes(b"\x89PNG\r\n")


def test_discover_text_stream(tmp_path: Path):
    create_fs(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["discover", str(tmp_path)])
    assert result.exit_code == 0, result.output
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    # Expect absolute paths for allowed files only
    expected = {
        str((tmp_path / "a.md").resolve()),
        str((tmp_path / "My Page" / "My Page.md").resolve()),
    }
    assert set(lines) == expected
    # Ensure hidden and assets are excluded
    assert all(".hidden.md" not in ln for ln in lines)
    assert all(".obsidian" not in ln for ln in lines)
    assert all("assets" not in ln for ln in lines)


def test_discover_with_patterns_and_json(tmp_path: Path):
    create_fs(tmp_path)
    # Add a txt file which matches default extension filter
    (tmp_path / "note.txt").write_text("txt", encoding="utf-8")
    runner = CliRunner()
    # Use include to only select md files; then JSON output
    result = runner.invoke(
        app,
        [
            "discover",
            str(tmp_path),
            "--include",
            "**/*.md",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    objs = [json.loads(ln) for ln in lines]
    paths = {obj["path"] for obj in objs}
    assert paths == {
        str((tmp_path / "a.md").resolve()),
        str((tmp_path / "My Page" / "My Page.md").resolve()),
    }
    # Objects should only contain a path field for discover
    assert all(set(obj.keys()) == {"path"} for obj in objs)


def test_discover_from_stdin_multiple_dirs(tmp_path: Path):
    # Create two roots
    root1 = tmp_path / "r1"
    root2 = tmp_path / "r2"
    root1.mkdir()
    root2.mkdir()
    (root1 / "a.md").write_text("a", encoding="utf-8")
    (root1 / "x.txt").write_text("x", encoding="utf-8")
    (root2 / "b.markdown").write_text("b", encoding="utf-8")
    (root2 / ".hidden.md").write_text("h", encoding="utf-8")

    runner = CliRunner()
    stdin_payload = json.dumps([str(root1), str(root2)])
    result = runner.invoke(
        app,
        [
            "discover",
            "--stdin",
            "--json",
        ],
        input=stdin_payload,
    )
    assert result.exit_code == 0, result.output
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    objs = [json.loads(ln) for ln in lines]
    paths = {obj["path"] for obj in objs}
    assert paths == {
        str((root1 / "a.md").resolve()),
        str((root1 / "x.txt").resolve()),
        str((root2 / "b.markdown").resolve()),
    }
    # Ensure hidden excluded
    assert all(".hidden.md" not in p for p in paths)
