# Operator guide: commands

This page translates the `Makefile` into operator language. It is not a raw dump of `make help`.

## Bootstrap and quality

### `make sync`
Create or update the `uv` environment.

### `make preflight`
Verify runtime wiring, create working directories, and warn about missing optional dependencies such as Docker.

### `make lint`
Run Ruff over `src`, `tests`, and `scripts`.

### `make pre-commit`
Run the configured hooks across all files.

### `make test`
Run pytest from repo root.

### `make check`
The normal local gate: `pre-commit` plus `test`.

### `make docs-build`
Build the MkDocs site into `site/` with strict validation.

### `make docs-serve`
Serve the docs locally on `127.0.0.1:8001`.

## Scrape runtime

### `make smoke SOURCE=elpais`
Short, bounded scrape with conservative limits. Good for sanity checks.

### `make run-source SOURCE=<source> DATE=<yyyy-mm-dd> [OUT_PREFIX=manual]`
Run one source with JSON and metrics output. No persistence unless you route through `run-source-persist` or set `PERSIST=1` internally.

### `make run-all DATE=<yyyy-mm-dd>`
Run all configured sources sequentially without persistence.

## Persistence-backed runtime

### `make run-source-persist SOURCE=<source> DATABASE_URL=...`
Same as `run-source`, but adds `--persist --db-url ...` under the hood.

### `make run-all-persist DATABASE_URL=...`
Run every configured source sequentially and persist the results.

### `make verify-db DATABASE_URL=...`
Check that the `articles` table is queryable and print a total row count.

## API and frontend

### `make api DATABASE_URL=...`
Run FastAPI via `uvicorn src.api.app:create_app --factory`.

### `make frontend-build`
Build the Vite frontend into `frontend/dist/`.

### `make frontend-check`
Install frontend deps and run the build. This is the sane verification target after frontend changes.

## Analysis and clustering

### `make analysis-db-init DATABASE_URL=...`
Create analysis/enrichment schema objects and seed the canonical tag taxonomy.

### `make enrich-articles DATABASE_URL=... [DAYS_BACK=2] [LIMIT=150]`
Enrich recent persisted articles with article type, tags, entities, key phrases, and claims.

The current code path can use OpenRouter if the expected env is present. If not, it falls back to heuristic enrichment.

### `make build-story-clusters DATABASE_URL=... [DAYS_BACK=3] [LIMIT=200] [SCORE_THRESHOLD=0.68]`
Rebuild same-story clusters from enriched article state.

### `make story-cluster-report DATABASE_URL=... [LIMIT=20]`
Print recent cluster summaries.

## Semantic pipeline

### `make semantic-db-init DATABASE_URL=... [SEMANTIC_ARGS='--embedding-model ...']`
Create or extend pgvector-backed semantic tables.

### `make semantic-sync DATABASE_URL=... OPENAI_API_KEY=... [LIMIT=100] [SEMANTIC_ARGS='...']`
Backfill or refresh missing/changed embeddings from persisted articles.

### `make semantic-project DATABASE_URL=... [PROJECTION_SET=pca_3d_latest] [SEMANTIC_ARGS='...']`
Rebuild the named projection set from persisted embeddings and optionally emit JSON/HTML artifacts.

### `make semantic-neighbors DATABASE_URL=... ARTICLE_ID=<id> [LIMIT=5]`
Query nearest neighbors for a persisted embedded article.

### `make semantic-build DATABASE_URL=... [LIMIT=500] [PROJECTION_SET=pca_3d_latest] [SEMANTIC_ARGS='...']`
Export offline semantic artifacts from persisted state.

### `make semantic-smoke DATABASE_URL=... [LIMIT=50]`
Smaller semantic artifact export for a bounded check.

## Scheduler and state

### `make scheduler-dry-run`
Show the deprecated legacy scrape-only scheduler plan without running scraping.

### `make scheduler-once`
Run the deprecated legacy scrape-only scheduler wrapper once.

### `make status`
Print legacy scheduler state files from `var/state/`.

### `make tail-log`
Tail the legacy scheduler log at `var/log/scheduler.log`.

### `make verify-output [SOURCE=...] [DATE=...] [OUT_PREFIX=...]`
Verify expected JSON and metrics artifacts exist for the run window.

## Optional local Postgres

### `make db-url`
Print the Docker Compose local Postgres URL.

### `make db-up`
Start local Postgres with Docker Compose and wait for readiness.

### `make db-check`
Check local Postgres readiness.

### `make db-logs`
Tail local Postgres logs.

### `make db-psql`
Open `psql` inside the running local Postgres container.

### `make db-down`
Stop the local Docker Compose stack.
