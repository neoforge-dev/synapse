# 🍺 Homebrew Installation for Synapse

> **Current Status:** Synapse does not yet publish a public Homebrew tap. Use the commands below to install directly from the repository or adapt them for your own tap.

## Quick Install (local formula)

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb
```

## What This Installs

- **Synapse CLI** - Available as `synapse` command
- **All dependencies** - Python packages, system libraries (cmake, pkg-config)
- **Shell completions** - For bash, zsh, and fish
- **Configuration files** - Default settings in `/opt/homebrew/etc/synapse/`

## Post-Installation

After installation:

```bash
# Check version
synapse --version

# See all commands
synapse --help

# Quick start (vector-only mode, no Docker required)
SYNAPSE_DISABLE_GRAPH=true synapse ingest ~/Documents

# Full setup with Docker/Memgraph
synapse up
```

## Tap Information

- **Formula Location**: `homebrew-tap/Formula/synapse.rb`
- **Homepage**: https://github.com/neoforge-ai/synapse-graph-rag

## Manual Installation (if Homebrew fails)

If the Homebrew installation encounters issues:

```bash
# Clone the repository
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag

# Install with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install -e .

# Or install with pip
pip install -e .
```

## Updates

```bash
# Update Synapse
brew upgrade synapse  # works if you host your tap; otherwise reinstall from the formula path

# Update the tap
brew update
```

## Troubleshooting

### Homebrew Installation Issues

```bash
# Check installation status
brew doctor

# Reinstall if needed
brew uninstall synapse
brew install synapse

# Check formula info (replace with your tap if you publish one)
brew info synapse
```

### macOS Beta Compatibility

If you're running macOS beta (26.x), Homebrew may show warnings and installation might fail due to Tier 2 support status. In this case, use the manual installation method:

```bash
# Clone and install manually
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
uv pip install -e .
```

### Installation Status

✅ **Local formula available**: `homebrew-tap/Formula/synapse.rb`  
⚠️ **macOS 26 compatibility**: Use manual installation for beta macOS versions

---

**Generated with ❤️ by [Synapse](https://github.com/neoforge-ai/synapse-graph-rag)**
