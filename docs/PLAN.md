# Synapse Work Plan (Q4 2025)

This document tracks the near-term engineering and documentation priorities based on the current codebase state.

## Current Snapshot
- CLI, MCP server, and FastAPI all reuse the same service layer; advanced analytics now backed by `AdvancedFeaturesService`.
- Default runtime still uses mock repositories/LLMs unless Memgraph and credentials are configured.
- Documentation refresh is in progress (installation, architecture, MCP, Homebrew), but historical “epic” roadmaps are archived.

## Priority Backlog
1. **Production backend enablement** – finish end-to-end documentation/tests for running with Memgraph + FAISS + real LLM providers (tracked via `docs/guides/PRODUCTION_BACKENDS.md`).
2. **Homebrew story** – decide whether to publish the tap (complete GitHub workflow + repo) or keep the local-formula instructions only; update README accordingly.
3. **Advanced features hardening** – expand coverage for `AdvancedFeaturesService`, especially graph stats and brand-safety paths when Memgraph is active.
4. **Observability cleanup** – resolve remaining bcrypt warning during auth setup by ensuring compatible backend and revisit logging defaults.
5. **Doc navigation** – add a “Start Here”/index page that links to installation, production backends, API reference, and archived plans.

## Near-Term Milestones
- **Week 1**: Finalise Homebrew decision; if publishing, run workflow to update tap repo; otherwise remove remaining references to public tap commands.
- **Week 2**: Author a Memgraph-backed integration test (skip if mgclient unavailable) and document the expected environment variables in README.
- **Week 3**: Draft the documentation index (“Docs overview”) and link from README/PLAN.
- **Continuous**: Keep docs in sync after feature changes (MCP server, advanced analytics, docker ports).

## Done Recently
- Advanced analytics router replaced placeholders with service-backed responses.
- Installation/Homebrew/MCP/architecture docs aligned with the actual code.
- Legacy strategic roadmaps moved to `docs/archive/`.
- Added production backend guide for Memgraph/FAISS/LLM/Postgres configuration.

Last updated: 2025-10-12.
