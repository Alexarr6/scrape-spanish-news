# spain-news-bias-scraper

Repo root is now the operator surface.

## Quick start

```bash
make preflight
make test
make smoke SOURCE=elpais
make run-all DATE=$(date +%F)
```

For persistent runs / API:

```bash
export DATABASE_URL='postgresql://user:pass@host:5432/dbname'
make run-all-persist DATE=$(date +%F)
make api
```

## Scheduler

The supported scheduler entrypoint is:

```bash
bash scripts/run_scheduled.sh
```

Recommended cron pattern (Madrid time, 4 runs/day):

```cron
CRON_TZ=Europe/Madrid
15 7,12,17,22 * * * cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper && DATABASE_URL='***external***' bash scripts/run_scheduled.sh
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
