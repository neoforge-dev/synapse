### XP-inspired autonomous development workflow (optimize uninterrupted throughput)

- **North Star**: Ship tiny, reversible changes in a continuous TDD loop with aggressive automation, so the system (tests + CI + conventions) becomes the “on-call human” for you.

## Principles
- **TDD everywhere**: Red → Green → Refactor; tests are executable specs and guardrails.
- **Micro-batches**: Small scope per iteration (≤5 files, ≤150 LOC changes).
- **Always releasable**: Feature flags/toggles; trunk-based with short-lived branches.
- **Fast feedback first**: Unit tests in <5 minutes; defer heavy checks to later stages.
- **Automate boring things**: Format, lint, type-check, commit message lint, versioning.
- **Contracts at boundaries**: Stable interfaces with contract tests to prevent regressions.
- **Observation > speculation**: Metrics, coverage gates, flaky quarantining, build budgets.

## Daily loop (hands-free as much as possible)
1. Pull latest main; auto-rebase short branch if needed.
2. Pick a single, narrow goal; write/extend a failing test first.
3. Implement minimal code to go green.
4. Refactor while tests stay green; keep public APIs stable.
5. Auto-run “fast lane” checks locally:
   - make format, make lint, mypy (or pyright), make test
6. Commit with conventional message; push; let CI advance.
7. Merge via merge queue once all required checks pass; auto-release if applicable.
8. Update `memory-bank/progress.md` automatically with changes and next TODO.

## Commit discipline
- **TCR/CCR hybrid**:
  - If tests pass: auto-commit.
  - If tests fail: auto-revert or auto-stash and open a “fix-forward” micro-task.
- **Conventional commits**: Keep subject ≤72 chars; scope accurate (e.g., feat(api): …).
- **One intent per commit**: Test + code + docs for that intent.

## Test strategy (pyramid with high automation)
- **Unit**: Majority of coverage; deterministic; mocks for external systems.
- **API/router tests**: Validate schemas, streaming, error paths; NDJSON lines verified.
- **Contract tests**: For `GraphRepository`, `VectorStore`, `GraphRAGEngine` protocols.
- **Property-based tests**: Graph invariants (no dangling edges, idempotent upserts).
- **Mutation testing (budgeted)**: Weekly on hot modules to strengthen assertions.
- **Flaky guard**: Auto-detect; quarantine to “flaky” marker; open follow-up task.

## Tooling you already have (wire for autonomy)
- **Fast lane (pre-commit/CI required)**:
  - Format/lint/type-check/commit-msg lint
  - Unit tests with coverage gate (≥80%)
- **Slow lane (CI nightly/label-triggered)**:
  - Integration tests (Memgraph-backed): `make test-memgraph`
  - End-to-end flows; mutation tests on core
- **Make targets** (align with CI):
  - install-dev, lint, format, test, test-integration, test-memgraph, run-api, run-memgraph

## CI/CD stages (maximize unattended progress)
- **Stage 1: Validate (PR)**
  - Setup env cache, install-dev
  - Lint + mypy + unit tests + coverage gate
  - Contract tests for DI interfaces
- **Stage 2: Memgraph (PR label: memgraph)**
  - Spin ephemeral Memgraph service
  - Run integration suite with retries-on-connect
- **Stage 3: Merge Queue**
  - Re-run Stage 1 minimally; auto-merge on pass
- **Stage 4: Release**
  - Version bump on feat/fix; changelog from conventional commits
  - Publish artifacts; post-run smoke test (run-api, basic endpoint probes)

## Patterns that extend autonomous runtime
- **Feature toggles**: Ship incomplete work safely; enable per-branch/PR.
- **Backwards-compatible evolution**: Add fields, dual-read/write, deprecate later.
- **Resilience in tests**: Timeouts, deterministic seeds, bounded resource use.
- **Hermetic dev env**: Lock Python + deps; devcontainer; reproducible make.
- **Observability**:
  - Budgets (max unit test duration, mut. test timebox)
  - Coverage deltas; alert if hot files lose coverage
  - Flaky tracker with auto-quarantine + issue creation
- **Auto-triage**:
  - When unit tests fail: auto-bisect commit range; propose revert PR if necessary.
  - When integration fails only: auto-open investigation with logs + repro steps.

## Repo conventions (make the “rails” visible)
- **Interfaces live in `core/interfaces.py`** with Protocols + contract tests.
- **Routers map domain types → schemas**; streaming standardized to NDJSON.
- **Memory bank updates** appended per change set (what/why/next).
- **Docs-lite**: Test names and types as primary docs; ADRs only for irreversible decisions.

## Starting a new capability (template)
- Write a focused failing test under `tests/...` (unit first; API if external).
- Implement minimal domain logic behind a Protocol.
- Wire DI in `api/dependencies.py` with guards and types.
- Add contract test(s) for the Protocol.
- Add CLI/API coverage if user-facing; stream outputs as needed (NDJSON).
- Run fast lane; commit; push; let CI proceed.

## When to pause and ask a human
- Ambiguity in product intent not translatable into a failing test.
- Non-trivial schema/contract break affecting external integrators.
- Security/privacy trade-offs requiring policy decisions.
- Long-running performance budgets that require real-world data.

- Implemented for this repo: streaming normalization and tests; the workflow above will let you keep iterating on API streaming, DI hardening, and Memgraph CI jobs with minimal human input by encoding expectations as executable tests and leaning on merge automation, coverage gates, and contract tests.
