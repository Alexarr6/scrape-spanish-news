# Getting started

## Baseline setup

The repo expects a `uv`-managed Python environment from repo root.

```bash
make sync
make preflight
make check
```

What that gives you:

- dependencies installed from `pyproject.toml` and `uv.lock`
- runtime directories such as `data/` and `var/` created when missing
- a sanity check that `src.main` is runnable from repo root
- lint/test coverage through the normal local gate

## Repo layout

### Backend

- `src/main.py` — scrape CLI entrypoint
- `src/adapters/` — source-specific discovery and extraction adapters
- `src/persistence/` — SQLAlchemy engine/session setup, ORM models, CRUD
- `src/analysis/` — enrichment, canonicalization, clustering, read-side payloads
- `src/semantic/` — embeddings, projections, point analysis, export helpers
- `src/api/` — FastAPI app factory and API routes

### Operational scripts

- `scripts/init_analysis_schema.py` — create analysis tables and seed taxonomy
- `scripts/enrich_articles.py` — enrich recent persisted articles
- `scripts/build_story_clusters.py` — rebuild same-story clusters
- `scripts/init_pgvector.py` — create pgvector-backed semantic tables
- `scripts/semantic_sync.py` — embed missing or changed articles
- `scripts/semantic_project.py` — rebuild persisted projection sets
- `scripts/build_semantic_map.py` — export offline semantic artifacts
- `scripts/run_scheduled.sh` — deprecated legacy scrape-only scheduler wrapper; prefer `scripts/run_stories_refresh.sh` for recurring full-pipeline runs

### Frontend and docs

- `frontend/` — Vite + React + TypeScript UI
- `docs/` — MkDocs content plus historical reviews/archive material
- `tests/` — backend/API/semantic contracts

## First smoke check

Run one bounded scrape without touching Postgres:

```bash
make smoke SOURCE=elpais
```

That dispatches through `make run-source` with lowered runtime/discovery limits so you can verify the scraper without waiting forever.

## Persistence setup

If you want database-backed runs or the API, export `DATABASE_URL` first.

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
```

For local-only Postgres via Docker Compose:

```bash
cp .env.example .env
make db-up
make db-check
export DATABASE_URL="$(make --no-print-directory db-url)"
```

## Frontend setup

The frontend has its own Node workspace and command surface in `frontend/package.json`.

```bash
make frontend-check
cd frontend && npm run dev
```

`make frontend-check` is the quick verification path because it installs dependencies and runs the production build.

## Documentation build

```bash
make docs-build
```

That runs `mkdocs build --strict`, so broken links and missing nav files fail loudly instead of quietly rotting.
