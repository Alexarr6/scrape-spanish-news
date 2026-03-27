# Architecture overview

## System shape

The project has five major layers.

1. scrape runtime
2. persistence
3. analysis and clustering
4. semantic embeddings and explorer data
5. API + frontend presentation

## Scrape runtime

`src/main.py` parses CLI args, builds the requested adapter from `src/adapters/registry.py`, runs it with a `RunConfig`, exports article artifacts, and optionally persists them.

The scraper is deliberately adapter-driven rather than a monolith. That keeps source-specific discovery and extraction logic isolated.

## Persistence

`src/persistence/` owns engine/session setup, ORM models, and CRUD.

Important practical behavior already reflected in repo notes and tests:

- batch ingest is atomic at the batch level
- persistence is opt-in for scrape runs
- the API and downstream pipelines expect Postgres to be the durable source of truth

## Analysis and clustering

`src/analysis/` adds a second layer over raw article rows.

It handles:

- tag taxonomy seeding
- heuristic or LLM-assisted enrichment
- entity canonicalization and alias capture
- same-story pair scoring
- connected-component cluster rebuilds
- read-side payloads for cluster list/detail/filter APIs

## Semantic layer

`src/semantic/` handles:

- article text assembly for embeddings
- pgvector-backed embedding storage
- PCA projection generation
- HDBSCAN-based cluster/outlier analysis for explorer views
- nearest-neighbor queries
- artifact export for offline inspection

## API and frontend

FastAPI routes translate persistence, analysis, and semantic read-side records into stable response models under `src/api/contracts/`.

The React frontend consumes those endpoints for two operator-facing views:

- story browser
- semantic explorer

## Docs truth policy

The commands and behaviors described here are grounded in current code paths. Architecture docs in this repo should describe current behavior and stable design decisions, not dated implementation handoffs.
