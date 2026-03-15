- State: CLEANUP_DONE
- Current phase: surgical scheduler bugfix applied; `verify-output` no longer expands `source_2026`-style bogus variables and scheduler failures now propagate honestly through retries/status
- Last update: 2026-03-15 21:48 UTC

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

## Scheduler bugfix outcome
- Fixed `make verify-output` shell expansion so file paths use `$${source}` instead of accidentally interpolating names like `source_2026` under `set -u`.
- Fixed `scripts/run_scheduled.sh` so every stage in `run_attempt()` has explicit `|| return $?`; this avoids Bash's annoying `set -e` suppression when a function is executed inside an `if` condition.
- Result: failed verification now makes the attempt fail, increments scheduler failure state after retries, and prevents bogus `scheduler success` log lines.

## Remaining follow-up
1. Re-run `uv run pre-commit run --all-files` and commit the resulting formatting so `make check` is genuinely green from a clean working tree.
2. Add a small Postgres-backed smoke/integration verification path (documented local target or CI step) beyond the SQLite-backed tests.
