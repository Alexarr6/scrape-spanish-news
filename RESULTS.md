# RESULTS.md

## Scheduler orchestration implementation

**Date:** 2026-03-20 UTC  
**Outcome:** ✅ implemented

---

## What was accomplished

Implemented the approved recurring-job orchestration with repo-native wrapper scripts instead of cursed cron spaghetti.

### New scripts
- `scripts/run_stories_refresh.sh`
- `scripts/run_explorer_refresh.sh`

### New Make targets
- `make stories-refresh-once`
- `make explorer-refresh-once`

### Docs updated
- `README.md`
- `docs/operator-guide/scheduler.md`
- `STATUS.md`

---

## Implemented behavior

### Stories refresh wrapper
Runs, in order:

```bash
make preflight
make run-all-persist DATE="$DATE_LOCAL" OUT_PREFIX="$OUT_PREFIX"
make analysis-db-init
make enrich-articles DAYS_BACK=3
make build-story-clusters DAYS_BACK=3 SCORE_THRESHOLD=0.50
make verify-output DATE="$DATE_LOCAL" OUT_PREFIX="$OUT_PREFIX"
make verify-db
```

Operational behavior:
- requires `DATABASE_URL`
- defaults `LOCAL_TZ=Europe/Madrid`
- defaults `DAYS_BACK=3`
- defaults `SCORE_THRESHOLD=0.50`
- defaults `OUT_PREFIX=sched`
- uses `var/lock/stories-refresh.lock`
- logs to `var/log/stories-refresh.log`
- writes state under `var/state/stories_*`
- exits `0` with `lock_busy` state if a previous stories run is still active
- stops on first failure and records failed state

### Explorer refresh wrapper
Runs, in order:

```bash
make preflight
make semantic-db-init SEMANTIC_ARGS='--embedding-model text-embedding-3-large'
make semantic-sync SEMANTIC_ARGS='--embedding-model text-embedding-3-large --days-back 3'
make semantic-project SEMANTIC_ARGS='--days-back 3'
make semantic-build SEMANTIC_ARGS='--days-back 3'
```

Operational behavior:
- requires `DATABASE_URL`
- requires `OPENAI_API_KEY`
- defaults `DAYS_BACK=3`
- defaults `EMBEDDING_MODEL=text-embedding-3-large`
- defaults `PROJECTION_SET=pca_3d_latest`
- defaults `SEMANTIC_LIMIT=100`
- defaults `SEMANTIC_BUILD_LIMIT=500`
- uses `var/lock/explorer-refresh.lock`
- logs to `var/log/explorer-refresh.log`
- writes state under `var/state/explorer_*`
- exits `0` with `lock_busy` state if a previous explorer run is still active
- stops on first failure and records failed state

---

## Cron recommendation kept simple

```cron
CRON_TZ=Europe/Madrid
5 */6 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='postgresql+psycopg://...' bash scripts/run_stories_refresh.sh >> var/log/cron.log 2>&1
35 */6 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='postgresql+psycopg://...' OPENAI_API_KEY='sk-...' bash scripts/run_explorer_refresh.sh >> var/log/cron.log 2>&1
```

Why this is right:
- jobs are every 6 hours
- they are staggered by 30 minutes
- each job has its own lock instead of one muddy global lock
- cron stays readable instead of becoming a shell crime scene

---

## Verification performed

- verified the referenced Make targets and env names are real
- ran shell syntax checks on both new wrapper scripts
- confirmed the docs warn about the embedding-model migration caveat

---

## Important caveat documented honestly

If the current semantic data was built with `text-embedding-3-small`, moving the explorer scheduler to `text-embedding-3-large` may require a one-time rebuild/reset of semantic embeddings or tables before results are trustworthy.

That warning is now explicit in the docs, because burying it would be bullshit.

---

## Not done automatically

- cron was not installed on the host
- no semantic reset/rebuild was forced
- the legacy `run_scheduled.sh` wrapper was not removed; it remains available for scrape-only scheduling
