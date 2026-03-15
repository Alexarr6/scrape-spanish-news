# spain-news-bias-scraper

Repo root is the canonical app root. Historical `runs/` baggage is gone.

## Quick start

The authoritative workflow is `uv`-managed from repo root.

```bash
make sync
make preflight
make check
make smoke SOURCE=elpais
```

Canonical local gate:

```bash
make check
```

## Persistence/API behavior notes

- `ArticleCRUD.ingest_many()` is now atomic per batch: rows are flushed during the batch and committed once at the end.
- If any SQLAlchemy persistence error is raised during batch ingest, the whole batch is rolled back and the response reports `rolled_back: true` with zero persisted insert/update counters.
- Route coverage now includes 200 / 404 / 422 behavior with dependency overrides against an isolated SQLAlchemy test session.
- `article_text` and `tags` are persisted end-to-end, but they only populate if the source article page exposes them. The scraper now reads `articleBody` from JSON-LD for full text and prefers explicit `article:tag` metadata, falling back to `news_keywords`/`keywords` when present. If a page exposes none of those, the fields remain empty by design.

If you want the hooks installed locally:

```bash
uv run pre-commit install
```

For persistent runs / API against any Postgres:

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make run-all-persist DATE=$(date +%F)
make api
```

## Optional local Postgres for persistence testing

Host-based scraping stays the default. Docker is only for the local dev database path.

### 1) Start local Postgres

```bash
cp .env.example .env
make db-up
make db-check
```

Default local dev connection string:

```bash
make db-url
# prints: postgresql+psycopg://spain_news:spain_news_dev@127.0.0.1:5433/spain_news_bias
```

If you want different local dev values, edit `.env` before `make db-up`.

### 2) Export `DATABASE_URL`

```bash
export DATABASE_URL="$(make --no-print-directory db-url)"
```

### 3) Manual persistence test

```bash
make run-source-persist SOURCE=elpais OUT_PREFIX=localdb DATE=$(date +%F)
make verify-db
```

### 4) Scheduler persistence test

Scheduled persistent runs remain strict: `DATABASE_URL` must be set.

`scheduler-once` runs one scheduled batch end-to-end: preflight, `run-all-persist`, `verify-output`, and `verify-db` (when `DATABASE_URL` is set). If any verification step fails, the attempt now fails honestly and the wrapper retries/fails instead of reporting a false success.

```bash
export DATABASE_URL="$(make --no-print-directory db-url)"
make scheduler-once
make verify-db
make status
```

Useful extras:

```bash
make db-logs
make db-psql
make db-down
```

## Scheduler

The supported scheduler entrypoint is:

```bash
bash scripts/run_scheduled.sh
```

Recommended cron pattern (Madrid time, 4 runs/day):

```cron
CRON_TZ=Europe/Madrid
15 7,12,17,22 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='postgresql+psycopg://***external-or-local***' bash scripts/run_scheduled.sh
```

## Notes

- `make` uses the root uv workflow and falls back to `~/.local/bin/uv` if `uv` is not already on `PATH`.
- `.env` is optional and only meant for boring local overrides like `LOCAL_DB_*` or `DATABASE_URL`.
- Runtime code and tests do not depend on `runs/` anymore. The active evidence fixtures used by contract tests live under `tests/fixtures/evidence/20260314-1212-8ff9/`.
- `scripts/detect_app_root.sh` was removed; repo root is the only supported app root.
- `make check` is expected to pass cleanly on the first run from a fresh `make sync` state without mutating tracked files.
