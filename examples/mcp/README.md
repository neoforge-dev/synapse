# MCP Integration Examples

This directory contains configuration examples for integrating Synapse GraphRAG with various IDEs and MCP clients.

## Prerequisites

1. **Install Synapse GraphRAG**:
   ```bash
   pip install synapse-graph-rag[mcp]
   # or
   brew install synapse-graph-rag
   ```

2. **Start the API server**:
   ```bash
   synapse up
   ```

3. **Verify MCP server works**:
   ```bash
   synapse mcp health
   ```

## VS Code Integration

### Setup

1. **Install the MCP extension** (if available) or configure manually in settings.

2. **Add to VS Code settings.json**:
   - Open VS Code settings (Cmd/Ctrl + ,)
   - Click "Open Settings (JSON)" icon
   - Merge the configuration from `vscode-settings.json`

3. **Alternative: User settings location**:
   ```bash
   # macOS
   ~/Library/Application Support/Code/User/settings.json
   
   # Linux
   ~/.config/Code/User/settings.json
   
   # Windows
   %APPDATA%\Code\User\settings.json
   ```

### Configuration Options

```json
{
  "mcp.servers": {
    "synapse-graph-rag": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000"
      },
      "initializationOptions": {
        "serverInfo": {
          "name": "Synapse GraphRAG",
          "version": "1.0.0"
        }
      }
    }
  }
}
```

### Usage in VS Code

Once configured, you can:

1. **Use the Command Palette** (Cmd/Ctrl + Shift + P):
   - "MCP: Ingest Files" - Upload documents to the knowledge base
   - "MCP: Search Documents" - Find relevant content
   - "MCP: Ask Question" - Get AI-powered answers with citations

2. **Right-click context menu**:
   - Select files in Explorer → "Ingest into Synapse"
   - Select text in editor → "Search in Synapse"

3. **Integrated chat interface**:
   - Ask questions about your codebase and documents
   - Get answers with source citations and links

## Claude Desktop Integration

### Setup

1. **Locate Claude Desktop config**:
   ```bash
   # macOS
   ~/Library/Application Support/Claude/claude_desktop_config.json
   
   # Windows
   %APPDATA%\Claude\claude_desktop_config.json
   
   # Linux
   ~/.config/claude/claude_desktop_config.json
   ```

2. **Copy configuration**:
   ```bash
   cp examples/mcp/claude-desktop-config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Restart Claude Desktop**

### Configuration Options

```json
{
  "mcpServers": {
    "synapse-graph-rag": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000",
        "SYNAPSE_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Usage in Claude Desktop

Available tools in Claude conversations:

1. **ingest_files**: Upload documents to your knowledge base
   ```
   Please ingest these files: /path/to/docs/*.md
   ```

2. **search**: Find relevant information
   ```
   Search for information about "machine learning algorithms"
   ```

3. **query_answer**: Ask questions with full context
   ```
   What are the key differences between supervised and unsupervised learning?
   ```

## Advanced Configuration

### Custom API Endpoints

If running Synapse on a different host/port:

```json
{
  "env": {
    "SYNAPSE_API_BASE_URL": "http://192.168.1.100:8000"
  }
}
```

### Development Setup

For development with hot reload:

```json
{
  "command": "synapse",
  "args": [
    "mcp", "start", 
    "--transport", "stdio",
    "--api-url", "http://localhost:8000",
    "--no-check-health"
  ],
  "env": {
    "SYNAPSE_API_BASE_URL": "http://localhost:8000",
    "DEBUG": "true"
  }
}
```

### Docker Compose Integration

When using Docker Compose:

```json
{
  "env": {
    "SYNAPSE_API_BASE_URL": "http://localhost:8001"
  }
}
```

### Multiple Environments

Configure different environments:

```json
{
  "mcpServers": {
    "synapse-dev": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000"
      }
    },
    "synapse-prod": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "https://api.mycompany.com"
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **"MCP server not found"**:
   ```bash
   # Verify installation
   which synapse
   synapse --version
   ```

2. **"Connection refused"**:
   ```bash
   # Check API server is running
   synapse up
   curl http://localhost:8000/health
   ```

3. **"Permission denied"**:
   ```bash
   # Fix permissions
   chmod +x $(which synapse)
   ```

4. **"Transport error"**:
   - Ensure no other process is using stdio
   - Try TCP transport instead:
     ```json
     {
       "args": ["mcp", "start", "--transport", "tcp", "--port", "8765"]
     }
     ```

### Debug Mode

Enable debug logging:

```json
{
  "env": {
    "SYNAPSE_API_BASE_URL": "http://localhost:8000",
    "SYNAPSE_LOG_LEVEL": "DEBUG"
  }
}
```

### Testing Configuration

Test your configuration:

```bash
# Test MCP server directly
synapse mcp start --transport stdio &
PID=$!

# Send test message (in another terminal)
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | nc localhost 8765

# Cleanup
kill $PID
```

### Health Check

Verify everything is working:

```bash
# Check system health
synapse mcp health

# Test tools
synapse mcp test

# Check API connectivity
curl http://localhost:8000/health
```

## IDE-Specific Notes

### VS Code Extensions

Compatible extensions:
- MCP Client (official)
- Synapse GraphRAG Extension (if available)
- Any extension supporting MCP protocol

### Claude Desktop Versions

Supported versions:
- Claude Desktop 1.0+
- Claude Desktop Beta

### Other MCP Clients

The configuration can be adapted for other MCP clients:
- Zed Editor
- Cursor IDE  
- Any editor with MCP support

For specific client configuration, refer to their MCP integration documentation.

## Support

If you encounter issues:

1. Check the [Troubleshooting Guide](../docs/TROUBLESHOOTING.md)
2. Review [GitHub Issues](https://github.com/neoforge-ai/synapse-graph-rag/issues)
3. Join our [Discord Community](https://discord.gg/synapse-graphrag)
4. Email support at support@neoforge.dev