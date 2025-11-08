# Quick Install Reference

Need the short version? Pick the scenario that matches your workflow.

---

## 1. CLI Install (PyPI)

```bash
uv pip install synapse-graph-rag[mcp]
synapse --version
```

Installs the Synapse CLI with MCP support into your current Python environment. Substitute `pipx` if you prefer an isolated install.

---

## 2. Full Development Setup

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
make install-dev
make download-nlp-data
synapse up             # starts Docker services on 18888/17687/17444/15432
```

This yields a ready-to-hack environment with Docker, Memgraph, and the FastAPI server. Hit `curl http://localhost:18888/health` to verify the stack.

---

## 3. Homebrew (local formula)

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb
```

Great when you want the CLI managed by Homebrew without publishing a public tap. Use `brew services start synapse` to run it in the background.

---

## After Installation

```bash
synapse init wizard --no-interactive --type vector-only
curl http://localhost:18888/api/v1/health
```

Additional details, including troubleshooting steps, live in `docs/guides/INSTALLATION_GUIDE.md` and `docs/HOMEBREW.md`.
