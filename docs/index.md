# spain-news-bias-scraper docs

This project is not one script with delusions of grandeur. It is a scrape runtime, a persistence layer, an enrichment and clustering pipeline, a semantic embedding/projection stack, and a FastAPI + React app surface.

Use this docs site for durable detail. Use the repo `README.md` for quickstart and command triage.

The canonical docs surface is `README.md` + `docs/`. Repo-tracked documentation here should stay focused on current behavior, stable contracts, and operator workflows.

## Start here

- New to the repo: read [Getting Started](getting-started.md)
- Need the commands that matter: read [Operator Guide / Commands](operator-guide/commands.md)
- Need the actual run flows: read [Operator Guide / Workflows](operator-guide/workflows.md)
- Need scheduler behavior: read [Operator Guide / Scheduler](operator-guide/scheduler.md)
- Need semantic explorer internals: read [Semantic Pipeline](semantic/overview.md)
- Need backend shape: read [Architecture](architecture/overview.md)

## What the project currently does

- Scrapes supported Spanish news sources through adapters in `src/adapters/`
- Writes article rows into Postgres when `--persist` or `make *-persist` flows are used
- Enriches persisted articles with article type, tags, entities, and key phrases
- Builds same-story clusters from enriched articles
- Stores semantic embeddings in pgvector, derives PCA projections, and exports explorer artifacts
- Serves story-cluster and semantic explorer APIs from FastAPI
- Serves or develops a React frontend from `frontend/`

## Truth sources

When docs and vibes disagree, trust these files:

- `Makefile` for commands and operator entrypoints
- `pyproject.toml` for Python dependencies
- `frontend/package.json` for frontend commands
- `src/main.py` for scrape runtime flags and behavior
- `src/api/app.py` and `src/api/v1/*` for API surface
- `scripts/*.py` and `scripts/run_scheduled.sh` for operational flows
- `tests/` for contract expectations

## Documentation scope

This site documents workflows and architecture that are clearly backed by the current repo. If a behavior is still inferred rather than fully verified, the docs call that out instead of pretending otherwise.
