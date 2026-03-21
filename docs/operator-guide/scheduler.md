# Operator guide: scheduler

## Supported entrypoints

The repo now has three scheduler-style wrappers:

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
export OPENAI_API_KEY='sk-...'

bash scripts/run_scheduled.sh
bash scripts/run_stories_refresh.sh
bash scripts/run_explorer_refresh.sh
```

Makefile wrappers:

```bash
make scheduler-dry-run
make scheduler-once
make stories-refresh-once
make explorer-refresh-once
```

## Job split

### Legacy wrapper
`run_scheduled.sh` is the deprecated scrape-only scheduler. It keeps its retry/alert behavior, but it does **not** run enrichment or cluster rebuilds, so it is the wrong entrypoint for the main stories product. It still runs:

1. `make preflight`
2. `make run-all-persist`
3. `make verify-output`
4. `make verify-db`

Useful if you only want persistent scraping and verification.

### Stories refresh
`run_stories_refresh.sh` is the recurring stories pipeline:

1. `make preflight`
2. `make run-all-persist`
3. `make analysis-db-init`
4. `make enrich-articles DAYS_BACK=3`
5. `make build-story-clusters DAYS_BACK=3 SCORE_THRESHOLD=0.50`
6. `make verify-output`
7. `make verify-db`

Defaults:
- `LOCAL_TZ=Europe/Madrid`
- `DAYS_BACK=3`
- `SCORE_THRESHOLD=0.50`
- `OUT_PREFIX=sched`

### Explorer refresh
`run_explorer_refresh.sh` is the recurring semantic/explorer pipeline:

1. `make preflight`
2. `make semantic-db-init SEMANTIC_ARGS='--embedding-model text-embedding-3-large'`
3. `make semantic-sync SEMANTIC_ARGS='--embedding-model text-embedding-3-large --days-back 3'`
4. `make semantic-project SEMANTIC_ARGS='--days-back 3'`
5. `make semantic-build SEMANTIC_ARGS='--days-back 3'`

Defaults:
- `DAYS_BACK=3`
- `EMBEDDING_MODEL=text-embedding-3-large`
- `PROJECTION_SET=pca_3d_latest`
- `SEMANTIC_LIMIT=100`
- `SEMANTIC_BUILD_LIMIT=500`

## Lock, log, and state layout

Per-job locks via `flock -n`:
- `var/lock/stories-refresh.lock`
- `var/lock/explorer-refresh.lock`

Per-job logs:
- `var/log/stories-refresh.log`
- `var/log/explorer-refresh.log`
- `var/log/scheduler.log` for the legacy wrapper

Per-job state files:
- `var/state/stories_last_status`
- `var/state/stories_last_run_utc`
- `var/state/stories_last_success_utc`
- `var/state/stories_last_error`
- `var/state/explorer_last_status`
- `var/state/explorer_last_run_utc`
- `var/state/explorer_last_success_utc`
- `var/state/explorer_last_error`

If a lock is busy, the wrapper logs a skip, writes `lock_busy`, and exits `0`. That is deliberate. Dogpiling the same job on a Pi is dumb.

## Required environment

### Stories refresh
Required:
- `DATABASE_URL`

Optional:
- `UV`
- `LOCAL_TZ`
- `DAYS_BACK`
- `SCORE_THRESHOLD`
- `OUT_PREFIX`

### Explorer refresh
Required:
- `DATABASE_URL`
- `OPENAI_API_KEY`

Optional:
- `UV`
- `DAYS_BACK`
- `EMBEDDING_MODEL`
- `PROJECTION_SET`
- `SEMANTIC_LIMIT`
- `SEMANTIC_BUILD_LIMIT`

The wrappers fail clearly during preflight if required env is missing.

## Failure behavior

The new orchestration wrappers are strict and boring on purpose:

- `set -euo pipefail`
- no loose retry loop in v1
- stop on first failing step
- mark job state as failed
- append details to the per-job log

That matters most for the explorer job because retrying embeddings casually is a neat way to pay twice for the same mistake.

## Cron recommendation

Keep cron simple and staggered:

```cron
CRON_TZ=Europe/Madrid

# Stories refresh every 6 hours
5 */6 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='postgresql+psycopg://...' bash scripts/run_stories_refresh.sh >> var/log/cron.log 2>&1

# Explorer refresh every 6 hours, offset so scrape/analysis lands first
35 */6 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='postgresql+psycopg://...' OPENAI_API_KEY='sk-...' bash scripts/run_explorer_refresh.sh >> var/log/cron.log 2>&1
```

## Important caveat: embedding model migration

The explorer wrapper standardizes on `text-embedding-3-large`.

If your existing semantic tables were built with `text-embedding-3-small`, this is **not** a casual flag flip. Because vector dimensionality changes, you may need a one-time semantic reset/rebuild before the scheduled explorer job is trustworthy.

Use the same embedding model for both `semantic-db-init` and `semantic-sync`. Mixing them would be garbage.
