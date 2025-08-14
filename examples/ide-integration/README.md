# IDE Integration Examples for Synapse GraphRAG

This directory contains configuration examples and guides for integrating Synapse GraphRAG with various IDEs and AI assistants via the Model Context Protocol (MCP).

## 🚀 Quick Start

1. **Start the Synapse API server**:
   ```bash
   synapse up
   ```

2. **Test the MCP server**:
   ```bash
   synapse mcp health
   synapse mcp start --transport stdio
   ```

3. **Configure your IDE** (see specific sections below)

## 📊 Available MCP Tools

The Synapse MCP server exposes 7 powerful tools for AI assistants:

| Tool | Description | Example Use |
|------|-------------|-------------|
| `ingest_files` | Add documents to knowledge base | "Ingest these project documentation files" |
| `search` | Search for relevant content | "Find information about authentication" |
| `query_answer` | Ask questions with AI synthesis | "How do I configure SSL in this project?" |
| `list_documents` | Browse document collection | "Show me all ingested documents" |
| `get_document` | Retrieve specific document | "Get the content of README.md" |
| `delete_document` | Remove documents | "Delete outdated documentation" |
| `system_status` | Check system health | "What's the current system status?" |

## VS Code Configuration

### Installation

1. Install the MCP extension for VS Code
2. Copy the configuration from `vscode-settings.json` to your VS Code settings:

```json
{
  "mcp.servers": {
    "synapse-graph-rag": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

### Usage Examples

1. **Ingest project files**:
   ```
   @synapse-graph-rag ingest_files {"paths": ["./docs", "./README.md"], "metadata": {"project": "my-app"}}
   ```

2. **Search codebase**:
   ```
   @synapse-graph-rag search {"query": "authentication middleware", "search_type": "hybrid"}
   ```

3. **Ask questions**:
   ```
   @synapse-graph-rag query_answer {"question": "How do I set up the development environment?"}
   ```

## Claude Desktop Configuration

### Installation

1. Locate your Claude Desktop configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
   - **Linux**: `~/.config/claude/claude_desktop_config.json`

2. Add the Synapse server configuration:

```json
{
  "mcpServers": {
    "synapse-graph-rag": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

3. Restart Claude Desktop

### Usage Examples

Once configured, you can use natural language:

- **"Ingest all the markdown files in my project directory"**
  - Claude will use `ingest_files` to add your documentation
  
- **"Search for information about database configuration"**
  - Uses `search` tool with your query
  
- **"What's the current status of the knowledge base system?"**
  - Calls `system_status` to get health information
  
- **"Based on my codebase, how should I implement user authentication?"**
  - Uses `query_answer` to synthesize an answer from your documents

## Other IDEs

### Cursor

Cursor supports MCP through the same configuration as VS Code. Add the server configuration to your settings.

### Vim/Neovim

For Vim users, you can interact with the MCP server programmatically:

```bash
# Test connection
synapse mcp health

# Start server in background  
synapse mcp start --transport tcp --port 8765 &

# Call tools via HTTP (if using TCP transport)
curl -X POST http://localhost:8765/tools/search \
  -H "Content-Type: application/json" \
  -d '{"query": "API documentation"}'
```

## 🛠 Configuration Options

### Environment Variables

- `SYNAPSE_API_BASE_URL`: Base URL of your Synapse API server (default: `http://localhost:8000`)
- `SYNAPSE_MCP_HOST`: MCP server host for TCP transport (default: `127.0.0.1`)
- `SYNAPSE_MCP_PORT`: MCP server port for TCP transport (default: `8765`)

### Transport Types

- **stdio**: For IDE integration (recommended)
- **tcp**: For programmatic access or debugging

### Example with custom API URL:

```json
{
  "command": "synapse",
  "args": ["mcp", "start", "--transport", "stdio", "--api-url", "https://my-synapse.example.com"],
  "env": {
    "SYNAPSE_API_BASE_URL": "https://my-synapse.example.com"
  }
}
```

## 🔧 Troubleshooting

### Common Issues

1. **"MCP server not responding"**
   - Check if Synapse API is running: `curl http://localhost:8000/health`
   - Verify MCP server health: `synapse mcp health`

2. **"Command 'synapse' not found"**
   - Ensure Synapse is installed: `pip install synapse-graph-rag`
   - Check PATH includes the installation directory

3. **"Tools not available"**
   - Verify API connectivity: `synapse mcp health`
   - Check logs: `synapse mcp start --transport stdio` (run manually to see output)

### Debug Mode

Run the MCP server manually to see detailed logs:

```bash
# Terminal 1: Start API
synapse up

# Terminal 2: Start MCP server with logs
synapse mcp start --transport stdio
```

### Health Checks

```bash
# Check overall system health
synapse mcp health

# Check API connectivity
curl http://localhost:8000/health

# Check detailed health (requires API running)
curl http://localhost:8000/api/v1/admin/health/detailed
```

## 📈 Best Practices

### 1. Document Organization
- Use consistent metadata when ingesting files
- Organize documents by project, topic, or date
- Include meaningful filenames and paths

### 2. Search Strategies
- Use **vector search** for semantic similarity
- Use **keyword search** for exact terms
- Use **hybrid search** for best of both worlds

### 3. Performance Optimization
- Ingest larger document collections in batches
- Use pagination when listing many documents
- Monitor system status regularly

### 4. Security Considerations
- Run the API server on localhost for local development
- Use environment variables for configuration
- Consider authentication for production deployments

## 📚 Example Workflows

### Project Documentation Assistant

1. **Setup**: Ingest your project's documentation
   ```bash
   synapse ingest ./docs --embeddings
   ```

2. **Usage**: Ask questions about your codebase
   - "How do I deploy this application?"
   - "What are the available API endpoints?"
   - "Show me examples of error handling patterns"

### Research Knowledge Base

1. **Setup**: Ingest research papers and notes
   ```bash
   synapse ingest ~/research-papers --metadata source:papers
   ```

2. **Usage**: Query across your research
   - "What papers discuss transformer architectures?"
   - "Summarize the key findings about attention mechanisms"
   - "Find methodologies for evaluating language models"

### Technical Documentation Hub

1. **Setup**: Aggregate documentation from multiple sources
   ```bash
   synapse ingest ./internal-docs --metadata team:engineering
   synapse ingest ./external-apis --metadata source:vendors
   ```

2. **Usage**: Unified knowledge search
   - "How do we integrate with the payment API?"
   - "What's our internal policy on code reviews?"
   - "Find examples of similar implementations"

---

For more information, see the main [Synapse GraphRAG documentation](../../README.md).