# Maintaining the Homebrew Tap

Synapse keeps its Homebrew formula under `homebrew-tap/Formula/synapse.rb`. This guide documents the lightweight process for keeping that tap healthy.

## Repository Layout

```
homebrew-tap/
├── Formula/
│   └── synapse.rb
└── README.md
```

Users install directly from the main repository:

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb
```

## Updating the Formula

1. Bump the `url` and `sha256` fields in `homebrew-tap/Formula/synapse.rb` when you tag a new release.
2. Recalculate the checksum:
   ```bash
   curl -sL https://github.com/neoforge-ai/synapse-graph-rag/archive/refs/tags/v0.2.0.tar.gz | shasum -a 256
   ```
3. Test locally before pushing:
   ```bash
   brew install --build-from-source ./homebrew-tap/Formula/synapse.rb
   brew test synapse
   ```
4. Commit and push the updated formula.

## Keeping Ports in Sync

The formula simply installs the CLI—the Docker stack lives in this repository. Whenever you change host port mappings (API 18888, Memgraph 17687/17444, Postgres 15432) make sure the documentation in `docs/HOMEBREW.md` reflects those values.

## Automation Ideas

Want to automate updates? Add a GitHub workflow that listens for new tags, computes the SHA256, and opens a PR updating the formula. The tap folder already matches Homebrew’s expectations, so the workflow is the only missing piece.

That’s all—no publisher scripts or mirrored tap repositories required.
