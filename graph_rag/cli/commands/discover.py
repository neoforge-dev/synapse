import fnmatch
import json
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Discover files for ingestion")


def _match_globs(
    root: Path,
    candidate: Path,
    include: Optional[list[str]],
    exclude: Optional[list[str]],
) -> bool:
    try:
        rel = candidate.relative_to(root)
    except Exception:
        rel = candidate
    rel_posix = rel.as_posix()
    if include:
        # Support patterns like "**/*.md" to also match files at the root ("a.md")
        # and allow basename matching when pattern does not include a slash
        name = candidate.name
        normalized_patterns: list[str] = []
        for pat in include:
            normalized_patterns.append(pat)
            if pat.startswith("**/"):
                normalized_patterns.append(pat.replace("**/", "", 1))
        if not any(
            fnmatch.fnmatch(rel_posix, pat) or fnmatch.fnmatch(name, pat)
            for pat in normalized_patterns
        ):
            return False
    if exclude:
        if any(fnmatch.fnmatch(rel_posix, pat) for pat in exclude):
            return False
    return True


@app.command()
def discover_command(
    directory: Optional[Path] = typer.Argument(None, help="Directory to search"),
    include: Optional[list[str]] = typer.Option(
        None, "--include", help="Glob pattern to include (repeatable)."
    ),
    exclude: Optional[list[str]] = typer.Option(
        None, "--exclude", help="Glob pattern to exclude (repeatable)."
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit JSON lines with a 'path' field."
    ),
    read_stdin: bool = typer.Option(
        False, "--stdin", help="Read a JSON array of directories from stdin"
    ),
) -> None:
    roots: list[Path] = []
    if directory is not None:
        if not directory.exists() or not directory.is_dir():
            typer.echo(f"Error: {directory} is not a directory", err=True)
            raise typer.Exit(1)
        roots.append(directory)

    if read_stdin:
        try:
            data = typer.get_text_stream("stdin").read()
            items = json.loads(data) if data.strip() else []
            if not isinstance(items, list):
                raise ValueError("stdin must be a JSON array of directories")
            for it in items:
                p = Path(it).expanduser()
                if p.exists() and p.is_dir():
                    roots.append(p)
        except Exception as e:
            typer.echo(f"Error: failed to read directories from stdin: {e}", err=True)
            raise typer.Exit(1)

    if not roots:
        typer.echo(
            "Error: provide a DIRECTORY or --stdin JSON array of directories", err=True
        )
        raise typer.Exit(1)

    exts = {".md", ".markdown", ".txt"}
    results_set: set[Path] = set()
    for root in roots:
        for path in root.rglob("*"):
            if (
                path.is_file()
                and not path.name.startswith(".")
                and ".obsidian" not in path.parts
                and not any("assets" in part.lower() for part in path.parts)
                and path.suffix.lower() in exts
                and _match_globs(root, path, include, exclude)
            ):
                results_set.add(path.resolve())

    for p in sorted(results_set):
        if as_json:
            typer.echo(f'{{"path": "{str(p)}"}}')
        else:
            typer.echo(str(p))
