# Synapse Graph-RAG

**A production-ready Graph-augmented Retrieval-Augmented Generation (RAG) system with enterprise business intelligence capabilities.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## 🚀 Quick Start

### **Development Setup (Recommended)**
```bash
# Clone and install for development
git clone https://github.com/yourusername/graph-rag-mcp.git
cd graph-rag-mcp
make install-dev

# Start the system (Memgraph + API)
make up

# Verify installation
synapse --version
```

### **Production Installation**
```bash
# Install dependencies using uv
uv pip install -e .[dev]

# Download NLP models
make download-nlp-data

# Start services
make run-memgraph    # Start graph database
make run-api         # Start FastAPI server
```

## 📚 Documentation

- **[📖 Installation Guide](docs/guides/installation.md)** - Complete installation instructions
- **[🚀 Quick Start](docs/QUICKSTART.md)** - Get up and running in minutes
- **[🍺 Homebrew Setup](docs/guides/HOMEBREW_TAP_GUIDE.md)** - Install via Homebrew
- **[🏗️ Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[🔧 Development](CONTRIBUTING.md)** - Development setup and contribution guide

## 🎯 What is Synapse?

Synapse is a production-ready Graph-augmented RAG system that powers enterprise business intelligence:

- **Advanced Graph-RAG** - Combines knowledge graphs (Memgraph) with vector search (FAISS)
- **Business Intelligence** - $555K+ consultation pipeline tracking and optimization
- **LinkedIn Automation** - Automated content posting with 15-30% engagement rates
- **Document Processing** - Markdown, Notion, and text file ingestion with entity extraction
- **MCP Integration** - Model Context Protocol server for IDE integration
- **Enterprise API** - FastAPI backend with authentication and metrics

## ✨ Key Features

- **🧠 Advanced Graph-RAG** - Multi-hop relationship traversal and graph-based intelligence
- **💼 Business Development** - Automated consultation inquiry detection and pipeline management  
- **📈 Content Strategy** - AI-powered LinkedIn content generation and performance optimization
- **🔍 Intelligent Search** - Hybrid vector + graph retrieval with semantic understanding
- **📊 Analytics Dashboard** - Real-time business intelligence and ROI tracking
- **🚀 Production Ready** - Enterprise-grade reliability with 99.5% uptime targets

## 📊 Business Development Intelligence

Synapse powers **enterprise business development** with advanced automation:

- **💰 Pipeline Tracking** - Real-time consultation pipeline management ($555K+ tracked value)
- **🤖 LinkedIn Automation** - Automated posting at optimal times (6:30 AM Tue/Thu)
- **📈 Analytics Dashboard** - A/B testing, engagement tracking, and ROI attribution  
- **🎯 Inquiry Detection** - NLP-based consultation opportunity identification and scoring

### **Business Development Examples**
```bash
# Start business automation dashboard
python business_development/automation_dashboard.py

# Monitor consultation pipeline
python business_development/consultation_inquiry_detector.py

# Schedule LinkedIn content
python business_development/content_scheduler.py

# Analytics and performance tracking
python analytics/performance_analyzer.py
```

**Enterprise Business Intelligence**: Transform your content strategy into systematic business development with proven frameworks for technical leadership and consultation generation.

## 🛠️ Usage Examples

### **Basic Document Ingestion**
```bash
# Ingest documents with embeddings
synapse ingest ~/Documents

# Search your knowledge base
synapse search "machine learning applications"

# Ask questions about your documents
synapse query "What are the main themes in my documents?"
```

### **Advanced Graph-RAG Features**
```bash
# Start the full system
make up

# Graph operations
synapse graph neighbors "artificial intelligence" --depth 2
synapse graph entities --type ORGANIZATION

# Advanced search with graph context
synapse search "scaling systems" --use-graph --max-results 10
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
git clone https://github.com/yourusername/graph-rag-mcp.git
cd graph-rag-mcp
make install-dev
make test
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Documentation**: [CLAUDE.md](CLAUDE.md) - Development guidance and architecture
- **Strategic Planning**: [docs/PLAN.md](docs/PLAN.md) - Implementation roadmap
- **Configuration**: [docs/guides/installation.md](docs/guides/installation.md) - Setup instructions

---

**Synapse Graph-RAG - Production-Ready Enterprise Business Intelligence**