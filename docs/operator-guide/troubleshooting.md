# Operator guide: troubleshooting

## `make preflight` warns that `DATABASE_URL` is not set

That is only a warning until you hit persistence, API, analysis, semantic, or scheduler targets. Export `DATABASE_URL` before using those flows.

## `make api` fails immediately

The app factory initializes the database schema on startup, so a bad `DATABASE_URL` or unreachable Postgres fails fast. That is the correct behavior.

## `make semantic-sync` says `OPENAI_API_KEY is required`

That target embeds articles through the OpenAI client path. Export `OPENAI_API_KEY` first.

## Semantic model dimension mismatch errors

The semantic schema stores the vector width expected by the selected embedding model.

- `text-embedding-3-small` → 1536 dims
- `text-embedding-3-large` → 3072 dims

If you change models against a populated table, the current code intentionally refuses to paper over the mismatch. Rebuild or clear semantic embeddings first.

## The frontend route is missing from FastAPI

`/explorer` is only mounted when `frontend/dist/index.html` exists. Build the frontend first:

```bash
make frontend-build
```

## Scheduler says the lock is busy

That means another scheduler run still holds `var/lock/spain-news-bias-scraper.lock`. Check:

```bash
make status
make tail-log
```

Do not just delete the lock file blindly unless you have confirmed the prior run is dead.

## Docs build fails

Run:

```bash
make docs-build
```

The MkDocs config uses `strict: true`, so broken links or missing nav files fail the build on purpose.

## Local Docker Postgres commands fail

The local DB flow needs both `docker` and `docker compose`. The repo treats Docker as optional because host-based scraping and remote Postgres are still valid.
