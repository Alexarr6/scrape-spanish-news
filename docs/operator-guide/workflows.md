# Operator guide: workflows

## Fresh local sanity pass

Use this when you want to prove the repo still works before doing anything clever.

```bash
make sync
make preflight
make check
make smoke SOURCE=elpais
```

Expected outcome:

- Python env resolves
- repo hooks and tests pass
- one source produces bounded JSON and metrics output

## Persistent scrape flow

Use this when Postgres should become the durable source of truth.

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make run-all-persist DATE=$(date +%F)
make verify-db
```

Artifacts land in `data/` and `logs/`, while article rows land in `articles`.

## API + frontend dev flow

Terminal 1:

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make api
```

Terminal 2:

```bash
cd frontend && npm run dev
```

This is the intended split during frontend iteration.

If you want FastAPI to serve the built frontend instead:

```bash
make frontend-build
```

That requires `frontend/dist/index.html` to exist. The app factory only mounts `/explorer` when the built assets are present.

## Enrichment and story clustering flow

This is the path from raw persisted articles to story clusters.

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
make analysis-db-init
make enrich-articles DAYS_BACK=2 LIMIT=150
make build-story-clusters DAYS_BACK=3 LIMIT=200 SCORE_THRESHOLD=0.68
make story-cluster-report LIMIT=20
```

What happens:

1. analysis tables and canonical tag taxonomy are prepared
2. recent persisted articles are enriched with article type, tags, entities, and key phrases
3. accepted pair scores become connected components and then persisted story clusters
4. the API can read those clusters through `/api/v1/clusters`

## Semantic explorer rebuild flow

This is the path from persisted articles to semantic explorer artifacts.

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'
make semantic-db-init SEMANTIC_ARGS='--embedding-model text-embedding-3-small'
make semantic-sync LIMIT=100 SEMANTIC_ARGS='--embedding-model text-embedding-3-small --days-back 2'
make semantic-project PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
make semantic-build LIMIT=100 PROJECTION_SET=pca_3d_latest SEMANTIC_ARGS='--days-back 2'
```

Why the split matters:

- `semantic-sync` decides which articles need embeddings
- `semantic-project` rebuilds persisted PCA coordinates and cluster/outlier metadata for one `projection_set`
- `semantic-build` exports JSON/HTML artifacts from persisted state

## Date-windowed semantic rebuilds

The semantic scripts share one date-window contract:

- `--days-back N`
- `--date-from YYYY-MM-DD`
- `--date-to YYYY-MM-DD`

Rules enforced in code:

- `--days-back` cannot be combined with explicit dates
- `--days-back N` is an inclusive UTC window ending today
- explicit `date_from > date_to` is rejected
- no window flags means full-history behavior

Example explicit range:

```bash
uv run python scripts/semantic_sync.py --db-url "$DATABASE_URL" --limit 100 --embedding-model text-embedding-3-small --date-from 2026-03-16 --date-to 2026-03-18
uv run python scripts/semantic_project.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest --date-from 2026-03-16 --date-to 2026-03-18
uv run python scripts/build_semantic_map.py --db-url "$DATABASE_URL" --projection-set pca_3d_latest --limit 100 --date-from 2026-03-16 --date-to 2026-03-18
```

## Scheduler wrapper flow

The supported scheduler entrypoint is:

```bash
bash scripts/run_scheduled.sh
```

What it currently does per attempt:

1. `make preflight`
2. `make run-all-persist`
3. `make verify-output`
4. `make verify-db` when `DATABASE_URL` is set

It also handles:

- flock-based single-run locking
- retry with delay
- state files under `var/state/`
- optional alert command after repeated failures

Recommended cron example:

```cron
CRON_TZ=Europe/Madrid
15 7,12,17,22 * * * cd /path/to/spain-news-bias-scraper && DATABASE_URL='postgresql+psycopg://***' bash scripts/run_scheduled.sh
```

## Optional local database flow

Use this if you want a disposable local Postgres instead of an existing host DB.

```bash
cp .env.example .env
make db-up
make db-check
export DATABASE_URL="$(make --no-print-directory db-url)"
make run-source-persist SOURCE=elpais OUT_PREFIX=localdb DATE=$(date +%F)
make verify-db
```
