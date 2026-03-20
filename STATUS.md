- State: COMPLETE
- Current phase: scheduler orchestration implemented
- Last update: 2026-03-20 UTC

## Completed deliverables
- created `scripts/run_stories_refresh.sh` for recurring scrape + analysis + clustering refreshes
- created `scripts/run_explorer_refresh.sh` for recurring semantic explorer refreshes
- added thin `Makefile` entrypoints:
  - `make stories-refresh-once`
  - `make explorer-refresh-once`
- updated `README.md` and `docs/operator-guide/scheduler.md` with wrapper usage, env requirements, cron examples, and the embedding-model migration caveat
- preserved the old `scripts/run_scheduled.sh` flow as a legacy scrape-only wrapper instead of silently mutating its behavior

## Implementation details
- stories wrapper runs:
  - `preflight`
  - `run-all-persist`
  - `analysis-db-init`
  - `enrich-articles` with `DAYS_BACK=3`
  - `build-story-clusters` with `DAYS_BACK=3` and `SCORE_THRESHOLD=0.50`
  - `verify-output`
  - `verify-db`
- explorer wrapper runs:
  - `preflight`
  - `semantic-db-init`
  - `semantic-sync --embedding-model text-embedding-3-large --days-back 3`
  - `semantic-project --days-back 3`
  - `semantic-build --days-back 3`
- both wrappers use per-job `flock -n` locks, append-only logs, and separate state files under `var/`
- both wrappers fail clearly when required env is missing
- no retry loop was added to the new wrappers in v1

## Verification completed
- verified `Makefile` targets and env names against the current repo surface
- ran shell syntax checks for both new wrapper scripts
- inspected updated docs and scheduler guidance for consistency with the approved design

## Important caveat carried into docs
- if semantic data currently exists for `text-embedding-3-small`, moving scheduled explorer refreshes to `text-embedding-3-large` may require a one-time semantic rebuild/reset

## Not done in this pass
- no cron entries were installed on the host
- no semantic reset/rebuild was performed automatically
