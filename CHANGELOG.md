# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- MCP (Model Context Protocol) server integration for IDE workflows
- Enhanced MCP tools with comprehensive error handling and validation
- VS Code and Claude IDE configuration examples
- Docker Compose management with health checks and monitoring
- Comprehensive CLI commands for MCP server management
- PyPI packaging infrastructure with proper metadata
- Type hints support (PEP 561)
- Rich CLI interface with progress bars and colored output

### Enhanced
- Improved docker-compose wrapper with service health monitoring
- Enhanced error handling and logging throughout the system
- Better input validation and schema enforcement
- Comprehensive documentation and examples

### Fixed
- Improved connection handling and retry logic
- Better error messages and user feedback
- More robust service startup and health checking

## [0.1.0] - 2024-XX-XX

### Added
- Initial release of Synapse GraphRAG
- Graph-enhanced retrieval-augmented generation system
- Memgraph integration for knowledge graph storage
- FastAPI-based REST API
- Typer CLI for command-line operations
- Document ingestion and processing pipeline
- Vector similarity search with FAISS
- Question answering with source citations
- Notion integration for document import
- Docker Compose setup for easy deployment

### Features
- **Graph Storage**: Memgraph-based knowledge graph with entity relationships
- **Vector Search**: FAISS-powered similarity search for relevant content retrieval
- **Document Processing**: Automatic chunking and embedding generation
- **REST API**: Comprehensive endpoints for ingestion, search, and querying
- **CLI Tools**: Rich command-line interface for all operations
- **Docker Support**: Container-based deployment with compose configuration
- **Extensible Architecture**: Modular design for easy customization and extension

### Supported Operations
- Document ingestion from files and Notion
- Semantic search across document chunks
- Question answering with graph-enhanced context
- Administrative operations and health monitoring
- Development tools and debugging utilities