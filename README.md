# spain-news-bias-scraper

Repo root is now the operator surface.

## Quick start

```bash
make preflight
make test
make smoke SOURCE=elpais
make run-all DATE=$(date +%F)
```

For persistent runs / API against any Postgres:

```bash
export DATABASE_URL='postgresql://user:pass@host:5432/dbname'
make run-all-persist DATE=$(date +%F)
make api
```

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
# prints: postgresql://spain_news:spain_news_dev@127.0.0.1:5432/spain_news_bias
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
15 7,12,17,22 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='***external-or-local***' bash scripts/run_scheduled.sh
```

## Runtime detection

This repo intentionally treats `runs/` as legacy/history.
The root Makefile and scheduler detect the best available runnable app root like this:

1. repo root, if `src/main.py` exists there in the future
2. otherwise the newest `runs/*` directory that contains `src/main.py`

Override manually if needed:

```bash
make preflight APP_ROOT=runs/20260314-1212-8ff9
```
