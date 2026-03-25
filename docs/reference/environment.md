# Reference: environment variables

## Core runtime

### `DATABASE_URL`
PostgreSQL SQLAlchemy URL used by persistence, API, analysis, semantic, and scheduler flows.

Example:

```bash
export DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname'
```

### `OPENAI_API_KEY`
Required by semantic embedding sync.

## Scheduler-specific

### `UV`
Override the `uv` binary path for scheduler runs.

### `LOCAL_TZ`
Controls the default scrape date timezone used by Makefile date expansion. Defaults to `UTC` so it matches the CLI date contract.

### `SCHEDULER_RETRY_DELAY_SECONDS`
Delay between retries in `scripts/run_scheduled.sh`.

### `SCHEDULER_MAX_RETRIES`
Number of retries after the first failed attempt.

### `ALERT_COOLDOWN_SECONDS`
Cooldown between alert-command executions.

### `ALERT_COMMAND`
Optional command invoked after repeated failures.

## Local Docker Postgres variables

These can come from `.env` and are used by the Docker Compose helper targets.

- `LOCAL_DB_SERVICE`
- `LOCAL_DB_HOST`
- `LOCAL_DB_PORT`
- `LOCAL_DB_NAME`
- `LOCAL_DB_USER`
- `LOCAL_DB_PASSWORD`
- `COMPOSE_FILE`

## Frontend

### `VITE_API_BASE_URL`
Optional frontend base URL override used by `frontend/src/lib/api.ts`.

If unset, the frontend defaults to same-origin API requests.

## Analysis / LLM note

The enrichment script constructs `OpenRouterSettings` from environment variables through the analysis client layer. The exact env surface is defined in code there rather than in the `Makefile`, so document or change it only after checking `src/analysis/llm_client.py`.
