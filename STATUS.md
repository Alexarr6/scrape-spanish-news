- State: IMPLEMENTATION_DONE
- Current phase: canonical app promoted to repo root; runtime no longer depends on `runs/`
- Last update: 2026-03-15 17:55 UTC

## Progress log
- [x] promoted canonical `src/` and `tests/` from `runs/20260314-1212-8ff9/` into repo root
- [x] promoted required support assets to root (`docs/contracts/comparison_summary.schema.json`, `scripts/generate_comparison_summary.py`)
- [x] updated root `pyproject.toml` to describe the real app and use `psycopg[binary]`
- [x] normalized Postgres URL handling to prefer `postgresql+psycopg://`
- [x] simplified `Makefile`, `scripts/detect_app_root.sh`, and `scripts/run_scheduled.sh` to treat repo root as canonical
- [x] kept `runs/` intact as archive/evidence only

## Current outcome
- Repo root is now a normal Python project layout with authoritative `src/` and `tests/`.
- Scheduler and operator commands execute against root, not against `runs/...` discovery.
- Archived run artifacts are still available for evidence-based contract tests, but they are no longer on the runtime path.

## Remaining blockers / caveats
- Validation still depends on host capabilities: `uv`, outbound scraping network access, and Docker Compose for the optional local Postgres path.
- Evidence-based tests intentionally still read fixture artifacts from `runs/20260314-1212-8ff9/`.
