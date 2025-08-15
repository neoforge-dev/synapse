# Launch Scripts for MCP Integration

This document provides various launch scripts and automation for Synapse GraphRAG MCP integration.

## Quick Start Script

### macOS/Linux

```bash
#!/bin/bash
# start-synapse-mcp.sh

set -e

echo "🚀 Starting Synapse GraphRAG MCP Server..."

# Check if synapse is installed
if ! command -v synapse &> /dev/null; then
    echo "❌ Synapse is not installed. Please install with:"
    echo "   uv pip install synapse-graph-rag[mcp]"
    echo "   or"
    echo "   brew install synapse-graph-rag"
    exit 1
fi

# Start API server in background if not running
if ! curl -f http://localhost:8000/health &> /dev/null; then
    echo "🔧 Starting API server..."
    synapse up --detached --wait
    
    # Wait for API to be ready
    echo "⏳ Waiting for API server to be ready..."
    timeout 60s bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done' || {
        echo "❌ API server failed to start"
        exit 1
    }
    echo "✅ API server is ready"
else
    echo "✅ API server is already running"
fi

# Check MCP health
echo "🔍 Checking MCP server health..."
if synapse mcp health; then
    echo "✅ MCP server is ready"
else
    echo "❌ MCP server health check failed"
    exit 1
fi

echo "🎉 Synapse GraphRAG MCP is ready for IDE integration!"
echo ""
echo "Configuration for VS Code:"
echo '{
  "mcp.servers": {
    "synapse-graph-rag": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}'
```

### Windows (PowerShell)

```powershell
# start-synapse-mcp.ps1

Write-Host "🚀 Starting Synapse GraphRAG MCP Server..." -ForegroundColor Green

# Check if synapse is installed
if (-not (Get-Command synapse -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Synapse is not installed. Please install with:" -ForegroundColor Red
    Write-Host "   uv pip install synapse-graph-rag[mcp]"
    exit 1
}

# Start API server if not running
try {
    Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get | Out-Null
    Write-Host "✅ API server is already running" -ForegroundColor Green
} catch {
    Write-Host "🔧 Starting API server..." -ForegroundColor Yellow
    Start-Process -FilePath "synapse" -ArgumentList "up", "--detached", "--wait" -Wait
    
    # Wait for API to be ready
    Write-Host "⏳ Waiting for API server to be ready..." -ForegroundColor Yellow
    $timeout = 60
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        try {
            Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get | Out-Null
            Write-Host "✅ API server is ready" -ForegroundColor Green
            break
        } catch {
            Start-Sleep 2
            $elapsed += 2
        }
    }
    if ($elapsed -ge $timeout) {
        Write-Host "❌ API server failed to start" -ForegroundColor Red
        exit 1
    }
}

# Check MCP health
Write-Host "🔍 Checking MCP server health..." -ForegroundColor Yellow
$result = Start-Process -FilePath "synapse" -ArgumentList "mcp", "health" -Wait -PassThru
if ($result.ExitCode -eq 0) {
    Write-Host "✅ MCP server is ready" -ForegroundColor Green
} else {
    Write-Host "❌ MCP server health check failed" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 Synapse GraphRAG MCP is ready for IDE integration!" -ForegroundColor Green
```

## Systemd Service (Linux)

### Service File

```ini
# /etc/systemd/system/synapse-mcp.service

[Unit]
Description=Synapse GraphRAG MCP Server
After=network.target
Requires=synapse-api.service

[Service]
Type=simple
User=synapse
Group=synapse
WorkingDirectory=/opt/synapse
Environment=SYNAPSE_API_BASE_URL=http://localhost:8000
Environment=PATH=/opt/synapse/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/synapse/venv/bin/synapse mcp start --transport tcp --host 0.0.0.0 --port 8765
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### API Service File

```ini
# /etc/systemd/system/synapse-api.service

[Unit]
Description=Synapse GraphRAG API Server
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=synapse
Group=synapse
WorkingDirectory=/opt/synapse
Environment=PATH=/opt/synapse/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/synapse/venv/bin/synapse up --no-detached
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Enable and start services
sudo systemctl enable synapse-api.service
sudo systemctl enable synapse-mcp.service
sudo systemctl start synapse-api.service
sudo systemctl start synapse-mcp.service

# Check status
sudo systemctl status synapse-api.service
sudo systemctl status synapse-mcp.service

# View logs
sudo journalctl -u synapse-api.service -f
sudo journalctl -u synapse-mcp.service -f
```

## launchd Service (macOS)

### Service Plist

```xml
<!-- ~/Library/LaunchAgents/com.neoforge.synapse.mcp.plist -->

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.neoforge.synapse.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/synapse</string>
        <string>mcp</string>
        <string>start</string>
        <string>--transport</string>
        <string>tcp</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8765</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>SYNAPSE_API_BASE_URL</key>
        <string>http://localhost:8000</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>/usr/local/var/log/synapse-mcp.log</string>
    <key>StandardErrorPath</key>
    <string>/usr/local/var/log/synapse-mcp-error.log</string>
</dict>
</plist>
```

### Service Management

```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.neoforge.synapse.mcp.plist

# Start the service
launchctl start com.neoforge.synapse.mcp

# Check status
launchctl list | grep synapse

# Stop the service
launchctl stop com.neoforge.synapse.mcp

# Unload the service
launchctl unload ~/Library/LaunchAgents/com.neoforge.synapse.mcp.plist
```

## Docker Development Setup

### Development Compose

```yaml
# docker-compose.dev.yml
version: "3.8"

services:
  synapse-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
      - "8765:8765"  # MCP server
    environment:
      - MEMGRAPH_URI=bolt://memgraph:7687
      - SYNAPSE_LOG_LEVEL=DEBUG
      - PYTHONPATH=/app
    volumes:
      - .:/app
      - /app/node_modules
    depends_on:
      - memgraph
    command: >
      sh -c "
        synapse up --detached --wait &&
        synapse mcp start --transport tcp --host 0.0.0.0 --port 8765
      "

  memgraph:
    image: memgraph/memgraph:latest
    ports:
      - "7687:7687"
    command: --bolt-port=7687 --log-level=DEBUG
```

### Development Scripts

```bash
#!/bin/bash
# dev-setup.sh

echo "🛠️ Setting up development environment..."

# Start development services
docker-compose -f docker-compose.dev.yml up -d

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 15

# Test MCP connection
echo "🔍 Testing MCP server..."
curl -f http://localhost:8765 || echo "MCP server not ready yet"

# Open IDE with MCP configuration
echo "🚀 Opening VS Code with MCP configuration..."
code . --install-extension mcp-client

echo "✅ Development environment is ready!"
```

## IDE Integration Scripts

### VS Code Workspace Setup

```json
// .vscode/settings.json
{
  "mcp.servers": {
    "synapse-graph-rag": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000"
      }
    }
  },
  "mcp.autoStart": true,
  "mcp.logLevel": "info"
}
```

### Automated Setup Script

```bash
#!/bin/bash
# setup-vscode-mcp.sh

VSCODE_SETTINGS_DIR=".vscode"
SETTINGS_FILE="$VSCODE_SETTINGS_DIR/settings.json"

# Create .vscode directory if it doesn't exist
mkdir -p "$VSCODE_SETTINGS_DIR"

# Create or update settings.json
cat > "$SETTINGS_FILE" << 'EOF'
{
  "mcp.servers": {
    "synapse-graph-rag": {
      "command": "synapse",
      "args": ["mcp", "start", "--transport", "stdio"],
      "env": {
        "SYNAPSE_API_BASE_URL": "http://localhost:8000"
      }
    }
  },
  "mcp.autoStart": true,
  "mcp.logLevel": "info"
}
EOF

echo "✅ VS Code MCP settings configured in $SETTINGS_FILE"
echo "📝 Restart VS Code to load the new settings"
```

## Monitoring and Health Checks

### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "🏥 Performing health checks..."

# Check API server
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ API server is healthy"
else
    echo "❌ API server is not responding"
    exit 1
fi

# Check MCP server
if synapse mcp health &> /dev/null; then
    echo "✅ MCP server is healthy"
else
    echo "❌ MCP server is not healthy"
    exit 1
fi

# Check Memgraph connection
if synapse admin health &> /dev/null; then
    echo "✅ Memgraph connection is healthy"
else
    echo "❌ Memgraph connection failed"
    exit 1
fi

echo "🎉 All services are healthy!"
```

### Monitoring with Cron

```bash
# Add to crontab: crontab -e
# Check health every 5 minutes
*/5 * * * * /path/to/health-check.sh >> /var/log/synapse-health.log 2>&1

# Restart services if unhealthy
*/10 * * * * /path/to/restart-if-unhealthy.sh >> /var/log/synapse-restart.log 2>&1
```

### Restart Script

```bash
#!/bin/bash
# restart-if-unhealthy.sh

if ! /path/to/health-check.sh &> /dev/null; then
    echo "$(date): Services unhealthy, restarting..."
    
    # Stop services
    synapse down --volumes
    
    # Wait a bit
    sleep 10
    
    # Start services
    synapse up --wait
    
    # Wait for startup
    sleep 30
    
    # Check again
    if /path/to/health-check.sh &> /dev/null; then
        echo "$(date): Services restarted successfully"
    else
        echo "$(date): Failed to restart services"
    fi
fi
```

## Usage Examples

### Batch Ingestion

```bash
#!/bin/bash
# batch-ingest.sh

DOCS_DIR="$1"
if [ -z "$DOCS_DIR" ]; then
    echo "Usage: $0 <documents-directory>"
    exit 1
fi

echo "📂 Ingesting documents from $DOCS_DIR..."

# Find all supported files
find "$DOCS_DIR" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.pdf" -o -name "*.docx" \) | while read file; do
    echo "📄 Ingesting: $file"
    synapse ingest "$file" || echo "❌ Failed to ingest: $file"
done

echo "✅ Batch ingestion completed!"
```

### Interactive Demo

```bash
#!/bin/bash
# demo.sh

echo "🎬 Synapse GraphRAG MCP Demo"
echo "==============================="

# Start services
echo "1. Starting services..."
synapse up --wait

# Ingest sample data
echo "2. Ingesting sample documents..."
synapse ingest data/paul_graham_essay.txt

# Demo search
echo "3. Demo search..."
synapse search "startup advice" --limit 3

# Demo Q&A
echo "4. Demo question answering..."
synapse query ask "What advice does Paul Graham give about startups?"

# Show MCP tools
echo "5. Available MCP tools..."
synapse mcp info

echo "🎉 Demo completed! Ready for IDE integration."
```