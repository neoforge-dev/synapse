# Homebrew Installation Guide

This document describes how to install and distribute Synapse GraphRAG via Homebrew.

## For Users

### Installation

```bash
# Install from the official formula (once published)
brew install synapse-graph-rag

# Or install from the tap
brew tap neoforge-ai/synapse
brew install synapse-graph-rag

# Or install from the GitHub repository directly
brew install --build-from-source https://raw.githubusercontent.com/neoforge-ai/synapse-graph-rag/main/Formula/synapse-graph-rag.rb
```

### Quick Start

After installation, you can start using Synapse GraphRAG immediately:

```bash
# Check installation
synapse --version

# Get help
synapse --help

# Start the full stack (API + Memgraph)
synapse up

# Start MCP server for IDE integration
synapse mcp start

# Check system health
synapse mcp health
```

### Configuration

Homebrew installs a default configuration file at `/opt/homebrew/etc/synapse/config.yml` (Apple Silicon) or `/usr/local/etc/synapse/config.yml` (Intel).

You can customize this configuration as needed:

```yaml
# Synapse GraphRAG Configuration
api:
  host: 0.0.0.0
  port: 8000
  log_level: INFO

memgraph:
  uri: bolt://localhost:7687
  username: ""
  password: ""

embedding:
  model_name: all-MiniLM-L6-v2

mcp:
  host: 127.0.0.1
  port: 8765
```

### Service Management

Homebrew can manage Synapse GraphRAG as a system service:

```bash
# Start the service
brew services start synapse-graph-rag

# Stop the service
brew services stop synapse-graph-rag

# Restart the service
brew services restart synapse-graph-rag

# Check service status
brew services list | grep synapse
```

### Dependencies

The Homebrew formula automatically handles all dependencies:

- **Python 3.11**: Required runtime
- **Rust**: For building certain Python dependencies
- **NumPy & SciPy**: Optimized versions from Homebrew
- **All Python packages**: Installed in an isolated virtual environment

### Upgrade

```bash
# Upgrade to the latest version
brew upgrade synapse-graph-rag

# Check what's new
brew info synapse-graph-rag
```

### Uninstallation

```bash
# Stop services first
brew services stop synapse-graph-rag

# Remove the package
brew uninstall synapse-graph-rag

# Clean up configuration (optional)
rm -rf /opt/homebrew/etc/synapse
rm -rf /opt/homebrew/var/log/synapse
rm -rf /opt/homebrew/var/lib/synapse
```

## For Maintainers

### Publishing Process

The Homebrew formula is automatically updated when new releases are tagged:

1. **Create a release** by tagging a version:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **GitHub Actions** automatically:
   - Builds and tests the package
   - Publishes to PyPI
   - Updates the Homebrew formula with new SHA256
   - Submits PR to homebrew-core (if configured)

### Manual Formula Updates

If you need to manually update the formula:

1. **Calculate new SHA256**:
   ```bash
   curl -sL https://files.pythonhosted.org/packages/source/s/synapse-graph-rag/synapse-graph-rag-0.1.0.tar.gz | shasum -a 256
   ```

2. **Update the formula**:
   ```ruby
   url "https://files.pythonhosted.org/packages/source/s/synapse-graph-rag/synapse-graph-rag-0.1.0.tar.gz"
   sha256 "new-sha256-hash"
   ```

3. **Test the formula**:
   ```bash
   brew install --build-from-source ./Formula/synapse-graph-rag.rb
   brew test synapse-graph-rag
   ```

### Custom Tap

To create your own Homebrew tap:

```bash
# Create a new tap repository
hub create neoforge-ai/homebrew-synapse

# Add the formula
cp Formula/synapse-graph-rag.rb /path/to/homebrew-synapse/Formula/

# Users can then install with:
brew tap neoforge-ai/synapse
brew install synapse-graph-rag
```

### Formula Structure

The formula includes:

- **Dependencies**: Python 3.11, Rust for compilation, system packages
- **Resources**: All PyPI dependencies with locked versions
- **Installation**: Virtual environment setup with all dependencies
- **Post-install**: Default configuration generation
- **Service**: launchd service definition for macOS
- **Tests**: Basic functionality verification

### Testing

Comprehensive testing of the Homebrew formula:

```bash
# Install from source
brew install --build-from-source ./Formula/synapse-graph-rag.rb

# Run built-in tests
brew test synapse-graph-rag

# Test service
brew services start synapse-graph-rag
sleep 10
curl http://localhost:8000/health
brew services stop synapse-graph-rag

# Test MCP functionality
synapse mcp health
synapse mcp start --transport stdio &
PID=$!
sleep 5
kill $PID

# Cleanup
brew uninstall synapse-graph-rag
```

### Release Checklist

Before releasing a new version:

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md`
- [ ] Test formula with new version locally
- [ ] Ensure all dependencies are up to date
- [ ] Verify service configuration
- [ ] Test on clean macOS system
- [ ] Tag release and push

### Troubleshooting

Common issues and solutions:

1. **Build failures**: Check Rust toolchain and Python dependencies
2. **Service not starting**: Verify configuration file permissions
3. **Port conflicts**: Adjust default ports in configuration
4. **Permission issues**: Ensure proper directory ownership

For more help, check the [GitHub Issues](https://github.com/neoforge-ai/synapse-graph-rag/issues) or contact the maintainers.