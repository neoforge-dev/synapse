## Deletion Candidates (Pending Approval)

The following appear unused or obsolete. Safe removal reduces noise and speeds up navigation and CI.

- Legacy namespace
  - `graphrag/` (no imports anywhere in repo)

- Empty/placeholder dirs (no Python/Go integration)
  - `handlers/`
  - `middleware/`
  - `services/` (root)
  - `database/`
  - `utils/` (root)

- Stray language file
  - `models/user.go` (isolated Go file; no other Go usage)

- Docs (legacy)
  - `CLAUDE.md` — superseded by `docs/HANDBOOK.md`

Before deletion
- Double-check no references in CI, Makefile, or docs.
- Run: `rg -n "handlers/|middleware/|services/|database/|graphrag/|user.go"` and `make test`.
- Remove directories and update `docs/INDEX.md` and `docs/index.json` accordingly.
