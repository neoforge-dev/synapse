# Synapse Installation Guide

This page complements the “Quick Install Reference” and the detailed `INSTALLATION_GUIDE.md`. It summarises the three supported paths without referencing any deprecated shell scripts.

---

## 1. Install the CLI (PyPI)

Recommended when you want the Synapse CLI and MCP tooling without cloning the repo.

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Synapse with MCP extras
uv pip install synapse-graph-rag[mcp]

# Verify
synapse --version
synapse --help
```

Prefer isolation? Replace the last command with `pipx install "synapse-graph-rag[mcp]"`.

---

## 2. Full Development Environment

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
make install-dev          # installs editable package + dev deps via uv
make download-nlp-data    # downloads spaCy + NLTK resources
synapse up                # Docker stack (API 18888, Memgraph 17687/17444, Postgres 15432)
```

Sanity check:

```bash
curl http://localhost:18888/health
synapse mcp health
```

Shut everything down with `synapse down` (or `make down`).

---

## 3. Homebrew (local tap)

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb

# Optional: manage as a background service
brew services start synapse
```

Uninstall with `brew uninstall synapse`.

---

## After Installation

```bash
synapse config show --json | head -n 20
synapse init wizard --no-interactive --type vector-only
curl http://localhost:18888/api/v1/health
```

For troubleshooting tips, see `docs/guides/INSTALLATION_GUIDE.md` and `docs/HOMEBREW.md`.

---

## Common Issues

- **Command not found** – ensure uv/pipx bin directories are on `PATH`.
- **spaCy model missing** – run `make download-nlp-data` or `python -m spacy download en_core_web_sm`.
- **Port conflicts** – adjust host ports in `docker-compose.yml` if 18888/17687/17444/15432 are already taken.
- **Memgraph connection errors** – confirm Docker Desktop is running; `synapse up` starts Memgraph automatically.
