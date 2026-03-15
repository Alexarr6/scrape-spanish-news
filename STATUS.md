- State: PHASE_2_TRANSACTIONS_AND_API_TESTS_DONE
- Current phase: persistence transaction semantics are explicit, DB-backed CRUD tests exist, and FastAPI article routes have meaningful coverage
- Last update: 2026-03-15 18:33 UTC

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
1. If desired later, add a Postgres-backed integration path in CI or a documented local DB smoke target beyond the SQLite-backed unit/integration tests.
2. Continue archive pruning under `runs/` separately from this focused persistence/API pass.
