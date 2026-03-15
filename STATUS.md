- State: CLEANUP_DONE
- Current phase: article metadata diagnosis complete; `article_text` now comes from JSON-LD `articleBody` when present and `tags` now come from page metadata (`article:tag` first, then `news_keywords`/`keywords`)
- Last update: 2026-03-15 22:30 UTC

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

## Article metadata diagnosis outcome
- Root cause: persistence/DB were fine; extraction was the dumb part. `Article`, export, CRUD and ORM already carried `article_text` and `tags` end-to-end, but `GenericRSSAdapter.normalize()` never populated either field, so they defaulted to `""` and were stored as empty strings.
- `article_text` should now populate when an article page exposes `articleBody` inside JSON-LD (confirmed on sampled live article pages from EL PAÍS, El Mundo, elDiario.es, La Vanguardia and 20minutos).
- `tags` should now populate when the page exposes repeated `article:tag` metadata or keyword metadata (`news_keywords` / `keywords`). If a source page exposes none of those, `tags` still remain empty on purpose; no fake inference was added.

## Remaining follow-up
1. Re-run `uv run pre-commit run --all-files` and commit the resulting formatting so `make check` is genuinely green from a clean working tree.
2. Add a small Postgres-backed smoke/integration verification path (documented local target or CI step) beyond the SQLite-backed tests.
