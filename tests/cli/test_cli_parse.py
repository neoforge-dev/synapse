from pathlib import Path
import json
from typer.testing import CliRunner

from graph_rag.cli.main import app


def test_parse_front_matter_and_meta_merge(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text(
        """---
tags: [AI, Notes]
aliases: alias1
created: 2021-01-01
---
Hello world
""",
        encoding="utf-8",
    )
    meta_file = tmp_path / "meta.yml"
    meta_file.write_text("topic: extra\nstatus: complete\n", encoding="utf-8")

    runner = CliRunner()
    input_stream = f"{md.resolve()}\n"
    result = runner.invoke(
        app,
        [
            "parse",
            "--meta",
            "source=cli",
            "--meta-file",
            str(meta_file),
        ],
        input=input_stream,
    )
    assert result.exit_code == 0, result.output
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    obj = json.loads(lines[0])
    assert obj["path"].endswith("doc.md")
    assert "Hello world" in obj["content"]
    meta = obj["metadata"]
    # topics normalized from tags
    assert "topics" in meta and "AI" in meta["topics"]
    # merged meta-file and --meta
    assert meta["status"] == "complete"
    assert meta["source"] == "cli"


def test_parse_notion_property_table(tmp_path: Path):
    md = tmp_path / "notion.md"
    md.write_text(
        """| Property | Value |
|---|---|
| Tags | AI, #ML |
| Aliases | alt1 |
| Created time | 2020-02-02 |
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["parse"], input=f"{md.resolve()}\n")
    assert result.exit_code == 0, result.output
    obj = json.loads(result.stdout.strip().splitlines()[0])
    meta = obj["metadata"]
    assert "AI" in meta.get("topics", [])
    assert meta.get("aliases") == ["alt1"]
    assert meta.get("created_at") == "2020-02-02"
