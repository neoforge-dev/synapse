# Homebrew Installation Guide

Synapse ships with a self-hosted tap so you can install the CLI with Homebrew today—no waiting for a public tap or unmaintained scripts.

---

## User Workflow

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb

# optional: run the API + Memgraph stack
synapse up
curl http://localhost:18888/health
```

The formula bundles a virtual environment inside Homebrew’s `libexec` directory and exposes the `synapse` launcher on your PATH. When you run `synapse up`, Docker Compose publishes:

| Service            | Host Port |
|--------------------|-----------|
| API (FastAPI)      | 18888     |
| Memgraph (Bolt)    | 17687     |
| Memgraph (HTTP)    | 17444     |
| Postgres           | 15432     |

Configuration lives at `/opt/homebrew/etc/synapse/config.yml` (Apple Silicon) or `/usr/local/etc/synapse/config.yml` (Intel). Adjust the ports there if you need different local mappings.

```yaml
api:
  host: 0.0.0.0
  port: 18888

memgraph:
  uri: bolt://localhost:17687

mcp:
  host: 127.0.0.1
  port: 8765
```

To keep Synapse running in the background:

```bash
brew services start synapse
# ...
brew services stop synapse
```

Uninstall with `brew uninstall synapse` and remove `/opt/homebrew/etc/synapse` if you want to start fresh.

---

## Maintainer Notes

- The canonical formula lives at `homebrew-tap/Formula/synapse.rb`.
- Releases pull the source tarball from GitHub; update `url` and `sha256` whenever you tag a new version.
- Validate changes locally:
  ```bash
  brew install --build-from-source ./homebrew-tap/Formula/synapse.rb
  brew test synapse
  ```
- Keep the host ports (18888/17687/17444/15432) in sync with `docker-compose.yml` so documentation and services agree.
- The tap repository includes an `update-formula` workflow that runs on macOS and rewrites the formula when you publish a tagged release.

That’s it—no unpublished scripts or manual tap scaffolding required.
