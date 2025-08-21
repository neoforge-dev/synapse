# Synapse

**A system demonstrating Retrieval-Augmented Generation (RAG) enhanced with a Knowledge Graph.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🚀 Quick Start

### **Super Easy Installation (One Command!)**
```bash
# Install Synapse in one command - as easy as brew install!
curl -fsSL https://raw.githubusercontent.com/neoforge-dev/synapse/main/scripts/install.sh | bash
```

### **Alternative Installation Methods**
```bash
# Homebrew (macOS/Linux)
brew install ./Formula/synapse.rb

# Python package managers
pipx install synapse
# or
uv pip install synapse

# Development setup
git clone https://github.com/neoforge-dev/synapse.git
cd synapse
uv pip install -e .[dev]
```

## 📚 Documentation

- **[📖 Installation Guide](docs/guides/installation.md)** - Complete installation instructions
- **[🚀 Quick Start](docs/QUICKSTART.md)** - Get up and running in minutes
- **[🍺 Homebrew Setup](docs/guides/HOMEBREW_TAP_GUIDE.md)** - Install via Homebrew
- **[🏗️ Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[🔧 Development](CONTRIBUTING.md)** - Development setup and contribution guide

## 🎯 What is Synapse?

Synapse is a powerful RAG (Retrieval-Augmented Generation) system that combines:

- **Document Processing** - Markdown, Notion, and text file ingestion
- **Knowledge Graph** - Memgraph-based relationship extraction
- **Vector Search** - FAISS-powered semantic search
- **Content Strategy Intelligence** - RAG-powered content calendars and optimization
- **MCP Integration** - IDE and tool integration via Model Context Protocol
- **CLI Interface** - Powerful command-line tools for knowledge management

## ✨ Key Features

- **🔍 Intelligent Search** - Semantic and keyword-based document retrieval
- **🧠 Knowledge Graph** - Extract and visualize document relationships
- **📝 Content Intelligence** - Strategic content calendars powered by knowledge extraction
- **📱 MCP Integration** - Use Synapse directly in your IDE
- **🚀 Fast Performance** - Optimized for large document collections
- **🔧 Easy Setup** - One-command installation and configuration

## 📊 Strategic Content Intelligence

Synapse powers **advanced content strategy workflows** using knowledge graph insights:

- **📅 Content Calendars** - Generate strategic content plans from your knowledge base
- **🎯 Content Optimization** - ROI-driven content recommendations and A/B testing
- **📈 Business Intelligence** - Track engagement, conversions, and business development
- **🚀 Automation Workflows** - LinkedIn posting, analytics tracking, and lead generation

### **Content Strategy Examples**
```bash
# Generate content calendar from knowledge extraction
synapse insights extract --domain "strategic-tech" --format calendar

# Optimize existing content using RAG analysis
synapse content optimize --source linkedin-posts.csv --strategy viral-potential

# Track business development ROI
synapse analytics roi --timeframe "Q1-2025" --export dashboard
```

**Strategic Content Calendar System**: Transform your knowledge base into systematic content strategies with proven frameworks for technical leadership, business development, and thought leadership content.

## 🛠️ Usage Examples

### **Basic Document Ingestion**
```bash
# Ingest a directory of documents
synapse ingest ~/Documents --embeddings

# Ask questions about your documents
synapse query ask "What are the main themes in my documents?"
```

### **Advanced Features**
```bash
# Start the full stack with Docker
synapse up

# Explore the knowledge graph
synapse graph neighbors "machine learning" --depth 2

# Generate strategic content insights
synapse suggest "AI applications" --style "concise, analytical"

# Extract content opportunities from your knowledge base
synapse insights analyze --focus "strategic-tech" --output content-calendar
```

## 🏗️ Architecture

Synapse is built with a modular architecture:

- **Core Engine** - Document processing and knowledge extraction
- **Vector Store** - FAISS-based semantic search
- **Graph Store** - Memgraph for relationship storage
- **API Layer** - FastAPI-based REST API
- **CLI Interface** - Typer-based command-line tools
- **MCP Server** - IDE integration via Model Context Protocol

## 🚀 Getting Started

1. **Install Synapse** using one of the methods above
2. **Quick Start** - Run `synapse init wizard --quick --vector-only`
3. **Ingest Documents** - Use `synapse ingest ~/Documents`
4. **Ask Questions** - Use `synapse query ask "your question here"`

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### **Development Setup**
```bash
git clone https://github.com/neoforge-dev/synapse.git
cd synapse
uv pip install -e .[dev]
make test
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Repository**: [https://github.com/neoforge-dev/synapse](https://github.com/neoforge-dev/synapse)
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/neoforge-dev/synapse/issues)
- **Discussions**: [GitHub Discussions](https://github.com/neoforge-dev/synapse/discussions)

---

**Made with ❤️ by [Neoforge](https://neoforge.dev)**