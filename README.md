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

## Semantic explorer Phase 0 frontend foundation

The new app foundation lives in `frontend/` as a separate Vite + React + TypeScript workspace.

Development split is intentionally boring:

```bash
# terminal 1
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make api

# terminal 2
make frontend-check
cd frontend && npm run dev
```

That gives you:

- `http://127.0.0.1:4173` for Vite dev
- `/api/v1/semantic/explorer/*` from FastAPI as the canonical semantic data surface
- optional built-app serving at `http://127.0.0.1:8000/explorer` after `make frontend-build`

The current explorer phase is a bounded clustering + UX refinement pass: the backend serves canonical `x/y/z`, persists semantic cluster/outlier analysis by `projection_set`, and the frontend can flip between 2D and 3D deck.gl views with cluster-aware filters, color modes, and better focus/reset controls.

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

## Semantic persistence with pgvector

The semantic workflow is still boring on purpose, but now the durable source of truth is Postgres instead of disposable local files.

### What it does now

- keeps scraped content in `articles`
- stores OpenAI embeddings in `article_embeddings` via pgvector, with the vector width aligned to the selected embedding model
- stores derived PCA coordinates in a separate `article_projections` table, including real `x/y/z` for the canonical 3D explorer set
- stores persisted semantic point analysis + cluster summaries keyed by `projection_set` for explorer filtering and UI modes
- supports bounded backfill / incremental sync for missing or changed articles
- supports nearest-neighbor similarity queries in Postgres
- still exports rebuildable JSON/HTML artifacts under `data/semantic/`

Use the same `--embedding-model` for `semantic-db-init` and `semantic-sync`. `text-embedding-3-small` uses 1536 dims; `text-embedding-3-large` uses 3072. If you switch models against an existing populated semantic table, rebuild or clear semantic embeddings first.

### Required env

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'
```

### Smoke flow

```bash
make sync
make preflight
make semantic-db-init SEMANTIC_ARGS="--embedding-model text-embedding-3-small"
make semantic-sync LIMIT=50 SEMANTIC_ARGS="--embedding-model text-embedding-3-small"
make semantic-project PROJECTION_SET=pca_3d_latest
make semantic-smoke LIMIT=50
```

### Temporal window contract

The semantic DB flow now supports the same bounded window flags across sync / project / build:

- `--days-back N`
- `--date-from YYYY-MM-DD`
- `--date-to YYYY-MM-DD`

Rules:

- pass nothing to keep the old full-history behavior
- `--days-back N` means an inclusive UTC window ending today
- `--days-back` cannot be combined with explicit `--date-from` / `--date-to`
- explicit dates can be used independently or together

Example bounded rebuild for a Raspberry-friendly recent slice:

```bash
make semantic-sync LIMIT=100 SEMANTIC_ARGS='--embedding-model text-embedding-3-small --days-back 2'
make semantic-project PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
make semantic-build LIMIT=100 PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
```

Equivalent explicit-date flow:

```bash
uv run python scripts/semantic_sync.py --db-url "$DATABASE_URL" --limit 100 --embedding-model text-embedding-3-small --date-from 2026-03-16 --date-to 2026-03-18
uv run python scripts/semantic_project.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest --date-from 2026-03-16 --date-to 2026-03-18
uv run python scripts/build_semantic_map.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest --limit 100 --date-from 2026-03-16 --date-to 2026-03-18
```

### Direct commands

```bash
uv run python scripts/init_pgvector.py --db-url "$DATABASE_URL" --embedding-model text-embedding-3-small
uv run python scripts/semantic_sync.py --db-url "$DATABASE_URL" --limit 50 --embedding-model text-embedding-3-small
uv run python scripts/semantic_project.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest
uv run python scripts/semantic_neighbors.py --db-url "$DATABASE_URL" --article-id 123 --limit 5
uv run python scripts/build_semantic_map.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest --limit 50
```

Artifacts land in:

- `data/semantic/articles_embeddings_<stamp>.jsonl`
- `data/semantic/articles_points_<stamp>.json`
- `data/semantic/semantic_map_<stamp>.html`
- `logs/semantic_<stamp>_metrics.json`

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
- Runtime code and tests do not depend on `runs/` anymore. The active evidence fixtures used by contract tests live under `tests/fixtures/evidence/canonical/`.
- `scripts/detect_app_root.sh` was removed; repo root is the only supported app root.
- `make check` is expected to pass cleanly on the first run from a fresh `make sync` state without mutating tracked files.
