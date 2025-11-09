# Synapse Documentation

Welcome to the Synapse Graph-RAG documentation. This guide will help you find what you need quickly.

## 📚 Documentation Structure

### 🚀 Getting Started
**New to Synapse? Start here.**

- [**Quickstart Guide**](./getting-started/QUICKSTART.md) - Get up and running in 10 minutes
- [**MCP Integration**](./getting-started/MCP.md) - Connect Synapse to VS Code and Claude Desktop

### 📖 Guides
**Step-by-step tutorials and how-to guides.**

#### Installation & Setup
- [**Installation Guide**](./guides/INSTALLATION.md) - Complete installation instructions (Homebrew, uv, pip, pipx)
- [**Homebrew Tap Guide**](./guides/HOMEBREW_TAP_GUIDE.md) - Maintaining the Homebrew formula (maintainers)
- [**Production Backends**](./guides/PRODUCTION_BACKENDS.md) - LLM provider configuration

#### Data Ingestion & Exploration
- [**LinkedIn CSV Ingestion Quickstart**](./guides/LINKEDIN_CSV_INGESTION_QUICKSTART.md) - Ingest LinkedIn exports in 10 minutes
- [**LinkedIn Data Exploration**](./guides/LINKEDIN_DATA_EXPLORATION.md) - Query beliefs, preferences, controversial takes
- [**Tap Publishing Summary**](./guides/TAP_PUBLISHING_SUMMARY.md) - Publishing workflow

#### Content Strategy
- [**Content Strategy Guide**](./guides/CONTENT_STRATEGY_GUIDE.md) - LinkedIn automation and business development

#### Troubleshooting
- [**Troubleshooting Guide**](./guides/TROUBLESHOOTING.md) - Comprehensive error solutions and debugging guide

### 📘 Reference
**Technical specifications and API documentation.**

- ⭐ [**HANDBOOK.md**](./HANDBOOK.md) - **Complete user/developer reference** (1300+ lines)
  - All 22 CLI commands with examples
  - All 44+ API endpoints across 4 routers
  - All 100+ configuration variables
  - Database architecture
  - Authentication & authorization
  - Troubleshooting guide

- [**Architecture**](./reference/ARCHITECTURE.md) - System architecture deep dive (comprehensive)
  - 16+ specialized services
  - Observability architecture
  - Vector store implementations
  - Authentication flows

- [**Configuration**](./reference/CONFIGURATION.md) - Complete configuration reference
  - All 100+ environment variables
  - Development vs. production setups
  - Security best practices
  - Performance tuning

- [**Product Requirements**](./reference/PRD.md) - Product specifications

### 🔬 Advanced
**Deep dives and advanced topics.**

- [**Advanced Graph RAG Capabilities**](./advanced/advanced_graph_rag_capabilities.md) - Graph reasoning and advanced features
- [**macOS Autostart**](./advanced/MACOS_AUTOSTART.md) - LaunchD configuration for background services

### 📊 Analysis
**Technical evaluations and comparisons.**

- [**Memgraph vs FalkorDB Evaluation**](./analysis/MEMGRAPH_VS_FALKORDB_EVALUATION.md) - Graph database comparison

### 🧪 Experimental
**Future features and experimental projects.**

- [**BeeHive PRD**](./experimental/BEE_HIVE_PRD.md) - Multi-agent orchestration (planned)
- [**CLI/Mobile/PWA Architecture**](./experimental/CLI_MOBILE_PWA_ARCHITECTURE.md) - Cross-platform expansion
- [**Human-Agent Swarm Patterns**](./experimental/HUMAN_AGENT_SWARM_PATTERNS.md) - Collaboration patterns
- [**XP 2025 Agentic Methodology**](./experimental/XP_2025_AGENTIC_METHODOLOGY.md) - Development methodology
- [**Unexpected Claude Code Insights**](./experimental/UNEXPECTED_CLAUDE_CODE_INSIGHTS.md) - Discovery notes

---

## 🎯 Quick Links by Task

### I want to...

**Install Synapse**
→ [Installation Guide](./guides/INSTALLATION.md)

**Get started quickly**
→ [Quickstart Guide](./getting-started/QUICKSTART.md)

**Learn all CLI commands**
→ [HANDBOOK.md - CLI Reference](./HANDBOOK.md#cli-commands-reference)

**Use the API**
→ [HANDBOOK.md - API Reference](./HANDBOOK.md#api-reference) (44+ endpoints)

**Configure Synapse**
→ [Configuration Reference](./reference/CONFIGURATION.md) (100+ variables)

**Troubleshoot issues**
→ [Troubleshooting Guide](./guides/TROUBLESHOOTING.md) (comprehensive) or [HANDBOOK.md - Troubleshooting](./HANDBOOK.md#troubleshooting)

**Ingest LinkedIn data**
→ [LinkedIn CSV Ingestion Quickstart](./guides/LINKEDIN_CSV_INGESTION_QUICKSTART.md)

**Explore my data**
→ [LinkedIn Data Exploration](./guides/LINKEDIN_DATA_EXPLORATION.md)

**Connect to VS Code/Claude Desktop**
→ [MCP Integration](./getting-started/MCP.md)

**Configure LLM providers**
→ [Production Backends](./guides/PRODUCTION_BACKENDS.md)

**Understand the architecture**
→ [Architecture](./reference/ARCHITECTURE.md)

**Set up autostart on macOS**
→ [macOS Autostart](./advanced/MACOS_AUTOSTART.md)

**Compare graph databases**
→ [Memgraph vs FalkorDB](./analysis/MEMGRAPH_VS_FALKORDB_EVALUATION.md)

---

## 📁 Documentation Organization

```
docs/
├── getting-started/    # First-time user onboarding
├── guides/             # Task-oriented how-to guides
├── reference/          # Technical specifications
├── advanced/           # Deep dives and expert topics
├── analysis/           # Technical evaluations
├── experimental/       # Future/experimental features
├── archive/            # Historical documentation
│   ├── content-strategy/  # LinkedIn/Substack calendars
│   ├── development/       # Phase completion reports
│   ├── strategic/         # Research and planning
│   └── legacy-guides/     # Superseded guides
├── development/        # Active development tracking
└── prompts/            # Agent coordination prompts
```

---

## 🛠️ Active Development

**Current Work:**
- [**Plan**](./PLAN.md) - Current work plan (Q4 2025)
- [**Backlog**](./BACKLOG.md) - Feature backlog

**Development Resources:**
- [**Technical Debt**](./development/TECHNICAL_DEBT.md) - Known technical debt
- [**Exploration Plan**](./development/EXPLORATION_PLAN.md) - Future exploration areas
- [**Idea Mapping Roadmap**](./development/IDEA_MAPPING_IMPLEMENTATION_ROADMAP.md) - Concept mapping plans
- [**Agents**](./development/AGENTS.md) - Agent architecture

---

## 📦 Archive

Historical documentation preserved for reference:

- **Content Strategy** (26 files): LinkedIn calendars, Substack planning, posting guides
- **Development** (12 files): Phase completion summaries, testing reports, Epic implementations
- **Strategic** (15 files): Perplexity research, ROI frameworks, security reports
- **Legacy Guides** (2 files): Superseded installation guides

**Browse**: [docs/archive/](./archive/)

---

## 🤝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) in the project root for contribution guidelines.

---

## 📞 Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/neoforge-ai/synapse-graph-rag/issues)
- **GitHub Discussions**: [Ask questions or share ideas](https://github.com/neoforge-ai/synapse-graph-rag/discussions)
- **Documentation Feedback**: Open an issue with the `documentation` label

---

## 🔍 Search Tips

**Can't find what you need?**

1. **Use GitHub search**: Press `/` and search within this repository
2. **Check the archive**: Some older docs are in [archive/](./archive/)
3. **Check experimental**: Future features are in [experimental/](./experimental/)
4. **Ask in Discussions**: [GitHub Discussions](https://github.com/neoforge-ai/synapse-graph-rag/discussions)

---

## 📈 Documentation Stats

- **Total documentation files**: 150+
- **Active guides**: 20+
- **Archived (historical)**: 60 files
- **Primary reference docs**: 3 comprehensive files (HANDBOOK, ARCHITECTURE, CONFIGURATION)
- **Lines of documentation**: 5000+ (primary docs)
- **Getting started**: 2 files
- **Guides**: 9 files
- **Reference**: 4 files (includes HANDBOOK, ARCHITECTURE, CONFIGURATION, PRD)
- **Advanced**: 2 files
- **Experimental**: 5 files

**Recent Major Updates (Week 1-2, Nov 8, 2025)**:
- ✅ HANDBOOK.md created (1300+ lines, 30% → 80% coverage)
- ✅ ARCHITECTURE.md expanded (500+ lines, 95% → 98% accuracy)
- ✅ CONFIGURATION.md created (1000+ lines, 100+ variables)
- ✅ All 22 CLI commands documented
- ✅ All 44+ API endpoints documented
- ✅ All 16+ services documented

**Last updated**: 2025-11-09
