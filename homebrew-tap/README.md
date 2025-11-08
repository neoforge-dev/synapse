# 🍺 Synapse Homebrew Tap

> **Note:** The Synapse team currently recommends installing straight from the repository. These instructions show how you can host your own tap using the assets in `homebrew-tap/`.

This repository accompanies [Synapse](https://github.com/neoforge-ai/synapse-graph-rag), a graph‑augmented RAG system.

## 🚀 Quick Install

```bash
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb
```

## 🔧 What Gets Installed

- **Synapse CLI** - Available as `synapse` command
- **All dependencies** - Python packages, system libraries
- **Shell completions** - For bash, zsh, and fish
- **Configuration files** - Default settings in `/usr/local/etc/synapse/`

## 📱 Usage

After installation:

```bash
# Check version
synapse --version

# See all commands
synapse --help

# Quick start (no Docker required)
synapse init wizard --quick --vector-only

# Full setup with Docker
synapse up
```

## 🔄 Updates

```bash
# Update Synapse
brew upgrade synapse

# Update the tap
brew update
```

## 🐛 Troubleshooting

If you encounter issues:

```bash
# Check installation
brew doctor

# Reinstall Synapse
brew uninstall synapse
brew install synapse

# Check formula info
brew info synapse
```

## 📚 More Information

- **Documentation**: [Synapse](https://github.com/neoforge-ai/synapse-graph-rag)
- **Issues**: [GitHub Issues](https://github.com/neoforge-ai/synapse-graph-rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/neoforge-ai/synapse-graph-rag/discussions)

## 🏗️ Development

This tap is automatically updated when new versions of Synapse are released. The formula is maintained by the Synapse development team.

---

**Made with ❤️ by [Neoforge](https://neoforge.dev)**
