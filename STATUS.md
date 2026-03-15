- State: CLEANUP_DONE
- Current phase: final archive removal completed; `runs/` deleted, `make check` is clean on first run, Postgres smoke attempted and blocked by missing Docker on host
- Last update: 2026-03-15 20:41 UTC

## Phase 2 outcome
- `src/persistence/crud.py` no longer commits row-by-row during `ingest_many()`; rows are flushed as needed and committed once per batch.
- Batch ingest semantics are now explicit: SQLAlchemy write failures roll back the entire batch and return `rolled_back: true` with zero persisted insert/update counters.
- Added DB-backed tests covering insert, update/upsert, unchanged/idempotent re-run, and rollback-on-failure behavior.
- Added FastAPI article route tests for 200 / 404 / 422 with dependency overrides and session-close assertions.
- Added `httpx` to the dev dependency group so FastAPI/Starlette route tests run in the managed env.

## Verification completed on this host
```bash
PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_persistence_crud.py tests/test_api_articles.py
make check
make test
```

## Remaining follow-up
1. Re-run `uv run pre-commit run --all-files` and commit the resulting formatting so `make check` is genuinely green from a clean working tree.
2. Add a small Postgres-backed smoke/integration verification path (documented local target or CI step) beyond the SQLite-backed tests.
3. Final archive removal is in progress in this cleanup pass; no active code/tests should depend on historical run paths when done.
