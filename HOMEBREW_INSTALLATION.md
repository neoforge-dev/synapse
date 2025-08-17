# 🍺 Homebrew Installation for Synapse

## Quick Install

```bash
# Add the tap
brew tap neoforge-dev/synapse

# Install Synapse
brew install synapse
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

- **Tap Repository**: `neoforge-dev/synapse`
- **Formula Location**: `/opt/homebrew/Library/Taps/neoforge-dev/homebrew-synapse/Formula/synapse.rb`
- **Homepage**: https://github.com/neoforge-dev/synapse

## Manual Installation (if Homebrew fails)

If the Homebrew installation encounters issues:

```bash
# Clone the repository
git clone https://github.com/neoforge-dev/synapse.git
cd synapse

# Install with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install -e .

# Or install with pip
pip install -e .
```

## Updates

```bash
# Update Synapse
brew upgrade synapse

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

# Check formula info
brew info neoforge-dev/synapse/synapse
```

### macOS Beta Compatibility

If you're running macOS beta (26.x), Homebrew may show warnings and installation might fail due to Tier 2 support status. In this case, use the manual installation method:

```bash
# Clone and install manually
git clone https://github.com/neoforge-dev/synapse.git
cd synapse
uv pip install -e .
```

### Installation Status

✅ **Homebrew tap published**: `neoforge-dev/synapse`  
✅ **Formula available**: `brew install neoforge-dev/synapse/synapse`  
⚠️ **macOS 26 compatibility**: Use manual installation for beta macOS versions

---

**Generated with ❤️ by [Synapse](https://github.com/neoforge-dev/synapse)**