import fnmatch
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Discover files for ingestion")


def _match_globs(
    root: Path, candidate: Path, include: Optional[list[str]], exclude: Optional[list[str]]
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
    directory: Path = typer.Argument(..., help="Directory to search"),
    include: Optional[list[str]] = typer.Option(None, "--include", help="Glob pattern to include (repeatable)."),
    exclude: Optional[list[str]] = typer.Option(None, "--exclude", help="Glob pattern to exclude (repeatable)."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON lines with a 'path' field."),
) -> None:
    if not directory.exists() or not directory.is_dir():
        typer.echo(f"Error: {directory} is not a directory", err=True)
        raise typer.Exit(1)

    exts = {".md", ".markdown", ".txt"}
    results: list[Path] = []
    for path in sorted(directory.rglob("*")):
        if (
            path.is_file()
            and not path.name.startswith(".")
            and ".obsidian" not in path.parts
            and not any("assets" in part.lower() for part in path.parts)
            and path.suffix.lower() in exts
            and _match_globs(directory, path, include, exclude)
        ):
            results.append(path.resolve())

    for p in results:
        if as_json:
            typer.echo(f"{{\"path\": \"{str(p)}\"}}")
        else:
            typer.echo(str(p))
