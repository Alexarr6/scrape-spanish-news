# Operator guide: scheduler

## Supported entrypoint

The repo-supported scheduler wrapper is `scripts/run_scheduled.sh`.

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
bash scripts/run_scheduled.sh
```

The `Makefile` wrappers are:

```bash
make scheduler-dry-run
make scheduler-once
```

## What the wrapper enforces

The shell script is intentionally strict.

- `set -euo pipefail`
- lock file under `var/lock/`
- append-only scheduler log at `var/log/scheduler.log`
- state files under `var/state/`
- retry loop with configurable delay
- optional alert hook after repeated failures

## Required environment

### `DATABASE_URL`
Required for scheduled runs. The wrapper exits with `preflight_failed` state if it is missing.

### `UV`
Optional override. Defaults to `~/.local/bin/uv` if not provided.

### `LOCAL_TZ`
Defaults to `Europe/Madrid` and controls the local run date used by scheduled batch output naming.

### Retry and alert knobs

- `SCHEDULER_RETRY_DELAY_SECONDS` — default `120`
- `SCHEDULER_MAX_RETRIES` — default `1`
- `ALERT_COOLDOWN_SECONDS` — default `43200`
- `ALERT_COMMAND` — optional command invoked after repeated failures

## State files

The wrapper updates these files in `var/state/`:

- `last_status`
- `last_run_utc`
- `last_success_utc`
- `last_error`
- `consecutive_failures`
- `last_alert_utc`

`make status` prints them without requiring you to inspect the directory manually.

## Failure behavior

The current implementation does not fake success if verification fails. Each attempt must complete:

1. `make preflight`
2. `make run-all-persist`
3. `make verify-output`
4. `make verify-db`

If the final attempt still fails, the wrapper increments `consecutive_failures`, records `last_error`, and optionally triggers `ALERT_COMMAND` once cooldown rules allow it.

## Cron example

```cron
CRON_TZ=Europe/Madrid
15 7,12,17,22 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='postgresql+psycopg://***external-or-local***' bash scripts/run_scheduled.sh
```

## Dry-run example

```bash
make scheduler-dry-run
```

That logs the planned command and exits before scraping.
