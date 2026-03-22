# spain-news-bias-scraper

A Spanish news ingestion and analysis repo with five real surfaces: source scraping, PostgreSQL persistence, enrichment and story clustering, semantic embeddings/projections, and a FastAPI + React explorer UI.

This README is the operator front door. It covers the commands you actually run and points deeper detail at the docs site instead of turning into a prose landfill.

## What lives here

- `src/` — scraper runtime, persistence, analysis, semantic pipeline, API
- `scripts/` — operational entrypoints for enrichment, clustering, semantic sync/project/export
- `frontend/` — Vite + React + TypeScript explorer and story browser
- `docs/` — MkDocs-backed project documentation plus historical review material
- `tests/` — API, persistence, semantic, and runtime contract checks
- `data/`, `logs/`, `var/` — generated artifacts, metrics, and scheduler state

## Quickstart

The canonical workflow is `uv` from repo root.

### Python environment with `uv`

If you want the explicit environment flow instead of going through `make`, use:

```bash
uv sync --dev
uv run python -m src.main --help
uv run pytest
```

Notes:

- `uv sync --dev` creates or updates the project-managed virtual environment from `pyproject.toml` and `uv.lock`
- you do **not** need to activate `.venv` manually for normal repo work; prefer `uv run ...`
- `make sync`, `make test`, `make lint`, and the other repo targets are thin wrappers around this `uv` workflow

The shortest repo bootstrap remains:

```bash
make sync
make preflight
make check
make smoke SOURCE=elpais
```

What those do:

- `make sync` — create/update the managed Python environment
- `make preflight` — verify repo wiring, create runtime dirs, and sanity-check the Python entrypoint
- `make check` — run the local gate: pre-commit hooks plus tests
- `make smoke SOURCE=elpais` — bounded non-persistent scrape for one source

If you also want the frontend ready:

```bash
make frontend-check
```

That installs frontend dependencies and runs the production build.

## Environment you actually need

### Required for persistence and API

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
```

Needed by:

- `make run-source-persist`
- `make run-all-persist`
- `make api`
- `make analysis-db-init`
- `make enrich-articles`
- `make build-story-clusters`
- all semantic `make semantic-*` targets
- scheduler runs

### Required for semantic embedding sync

```bash
export OPENAI_API_KEY='sk-...'
```

Needed by:

- `make semantic-sync`

### Optional local overrides

`.env` is optional and mainly useful for local Docker Postgres values and boring operator defaults.

## Important command guide

These are the commands worth remembering because the `Makefile` says they are the real operator surface.

### Bootstrap and verification

```bash
make sync
make preflight
make lint
make pre-commit
make test
make check
make docs-build
```

- `make lint` — run Ruff over `src`, `tests`, and `scripts`
- `make pre-commit` — run repo hooks across tracked files
- `make test` — run pytest from repo root
- `make check` — the main local gate
- `make docs-build` — build the MkDocs site with strict link/nav checking

### Scrape runtime

```bash
make smoke SOURCE=elpais
make run-source SOURCE=elpais DATE=$(TZ=UTC date +%F)
make run-all DATE=$(TZ=UTC date +%F)
```

Use these when you want JSON output only, with no database writes.

### Persistence-backed scraping

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make run-source-persist SOURCE=elpais OUT_PREFIX=manual DATE=$(TZ=UTC date +%F)
make run-all-persist DATE=$(TZ=UTC date +%F)
make verify-db
```

Use these when scraped rows should land in Postgres.

### API and frontend

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make api
```

In a second terminal:

```bash
cd frontend && npm run dev
```

Useful related commands:

```bash
make frontend-build
make frontend-check
```

Notes:

- `make api` runs `uvicorn src.api.app:create_app --factory`
- if `frontend/dist` exists, FastAPI also serves the built UI at `/explorer`
- Vite dev server is separate and intended for frontend iteration

### Analysis and story clustering

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make analysis-db-init
make enrich-articles DAYS_BACK=2 LIMIT=150
make build-story-clusters DAYS_BACK=3 LIMIT=200 SCORE_THRESHOLD=0.68
make story-cluster-report LIMIT=20
```

Use this flow after persistent scraping when you want tags, entities, and same-story clusters.

### Semantic pipeline

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'

make semantic-db-init SEMANTIC_ARGS='--embedding-model text-embedding-3-small'
make semantic-sync LIMIT=100 SEMANTIC_ARGS='--embedding-model text-embedding-3-small --days-back 2'
make semantic-project PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
make semantic-build LIMIT=100 PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
make semantic-smoke LIMIT=50 PROJECTION_SET=pca_3d_latest
```

Use the same embedding model for schema init and sync. `text-embedding-3-small` means 1536 dims; `text-embedding-3-large` means 3072. Switching models against an already-populated semantic table requires rebuilding or clearing semantic embeddings first.

### Scheduler and verification

Legacy scrape-only scheduler (deprecated; keeps scrape + verify only, no enrichment or clustering):

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make scheduler-dry-run
make scheduler-once
make status
make tail-log
```

New recurring orchestration wrappers:

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'
make stories-refresh-once
make explorer-refresh-once
make verify-output DATE=$(TZ=UTC date +%F) OUT_PREFIX=sched
make verify-db
```

Entrypoints:
- `bash scripts/run_scheduled.sh` — deprecated legacy scrape + verify wrapper; does **not** run analysis or clustering
- `bash scripts/run_stories_refresh.sh` — scrape + persist + analysis + clustering
- `bash scripts/run_explorer_refresh.sh` — semantic sync + projection + explorer export

The new wrappers keep separate lock, log, and state files under `var/` and are the right surface for recurring 6-hour jobs. If you want fresh story clusters, using `run_scheduled.sh` is the wrong hammer.

Default stories wrapper tuning:
- `DAYS_BACK=3`
- `ENRICH_LIMIT=300`
- `CLUSTER_LIMIT=1000`
- `SCORE_THRESHOLD=0.45`

You can override these per run, for example:

```bash
ENRICH_LIMIT=400 CLUSTER_LIMIT=1200 bash scripts/run_stories_refresh.sh
```

### Optional local Postgres via Docker

```bash
cp .env.example .env
make db-up
make db-check
export DATABASE_URL="$(make --no-print-directory db-url)"
make db-down
```

This is for local persistence testing. Host-based scraping against an existing Postgres is still the normal path.

## Common operator flows

### 1) Fresh repo sanity check

```bash
make sync
make preflight
make check
make smoke SOURCE=elpais
```

Use this if you just want to prove the repo is alive.

### 2) Persist a full scrape batch

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make run-all-persist DATE=$(TZ=UTC date +%F)
make verify-db
```

Use this when Postgres is the source of truth.

### 3) Bring up the API and inspect the UI

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make api
```

Then either:

```bash
cd frontend && npm run dev
```

or build once and let FastAPI serve the built frontend:

```bash
make frontend-build
```

### 4) Rebuild tags, entities, and story clusters

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make analysis-db-init
make enrich-articles
make build-story-clusters
```

### 5) Rebuild semantic explorer data for a bounded recent window

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'
make semantic-db-init SEMANTIC_ARGS='--embedding-model text-embedding-3-small'
make semantic-sync LIMIT=100 SEMANTIC_ARGS='--embedding-model text-embedding-3-small --days-back 2'
make semantic-project PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
make semantic-build LIMIT=100 PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
```

### 6) Run the stories refresh wrapper once

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make stories-refresh-once
```

### 7) Run the explorer refresh wrapper once

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'
make explorer-refresh-once
```

## Where outputs go

- scrape JSON output — `data/<prefix>_<source>_<date>.json`
- scrape metrics — `logs/<prefix>_<source>_<date>_metrics.json`
- semantic exports — `data/semantic/`
- semantic metrics — `logs/semantic_*_metrics.json`
- scheduler state and logs — `var/state/`, `var/log/`
- built frontend — `frontend/dist/`

## Documentation

Build the docs locally:

```bash
make docs-build
```

Main docs entry points:

- `docs/index.md` — docs home
- `docs/getting-started.md` — setup and repo layout
- `docs/operator-guide/commands.md` — command reference grounded in `Makefile`
- `docs/operator-guide/workflows.md` — real run flows
- `docs/operator-guide/scheduler.md` — scheduler behavior and cron usage
- `docs/semantic/` — semantic storage, sync, projection, export
- `docs/architecture/` — scrape, persistence, analysis, semantic, API/frontend architecture
- `docs/reference/` — environment variables and output conventions
- `docs/historical/` — review/archive material kept for context, not as primary docs

## Notes and constraints

- Repo root is the only supported app root.
- `make` uses the repo-root `uv` workflow and falls back to `~/.local/bin/uv` when needed.
- Runtime code and tests do not depend on historical `runs/` layout anymore.
- The README only documents workflows that are clearly backed by the current `Makefile`, scripts, and code paths. If you need deeper behavior, the docs site is where that detail belongs.
