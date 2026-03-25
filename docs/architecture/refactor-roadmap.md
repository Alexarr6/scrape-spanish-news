# Refactor roadmap

## Why this document exists

This repository already documents a five-layer architecture, but the implementation has drifted in a few places. The goal of this roadmap is to sequence the cleanup so the codebase gets more consistent without turning the work into one giant rewrite.

## Target structural rules

### 1. Explicit package boundaries

Each bounded context should prefer a predictable layout:

- `core.py` — Pydantic data models, enums/constants, validation rules, and schema-facing helpers
- `orm.py` — SQLAlchemy ORM rows only
- `crud.py` — persistence access helpers, isolated from read-side formatting
- `service.py` / `pipeline.py` — business logic and orchestration
- `readside.py` — API-facing shaping and query composition
- `client.py` — external integrations

### 2. One canonical data contract per concern

- Pydantic models define the canonical shape
- JSON schema for LLM/provider calls should derive from those models where practical
- normalization/repair layers may accept looser payloads, but only as an ingestion boundary

### 3. Shared helpers by domain, not junk-drawer utils

Only extract a helper when it is:

- reused
- tested
- semantically stable

Preferred homes:

- `src/shared/text.py`
- `src/shared/dates.py`
- `src/shared/json.py`
- `src/shared/urls.py`

## Execution order

### Phase 0 — planner and operator docs

- document the `uv` workflow explicitly
- document the target package structure
- capture high-risk refactors before moving code

### Phase 1 — analysis/editorial normalization

- move editorial Pydantic models into `src/analysis/editorial/core.py`
- move editorial ORM into `src/analysis/editorial/orm.py`
- keep a dedicated CRUD boundary in `src/analysis/editorial/crud.py`
- split replay tooling into dedicated modules (`core`, `evaluator`, `report`) instead of mixing models and execution logic
- leave compatibility re-exports in place while imports are migrated

### Phase 2 — schema tightening

- reduce hand-written schema drift
- prefer `model_json_schema()` or an equivalent model-driven schema export
- keep a separate permissive raw-payload model only when provider behavior requires it

### Phase 3 — scraper normalization

- standardize discovery metrics across all adapters
- centralize reusable discovery strategies
- add explicit noise rejection rules for weather, service info, sports, and branded content
- compare source yield with structured diagnostics instead of raw article counts

### Phase 4 — project-wide consistency

- unify naming/layout across `analysis`, `semantic`, `persistence`, and `api`
- extract proven shared helpers
- remove compatibility bridges and dead code once replacements are fully adopted

## Current caveat: FastCRUD

FastCRUD is a reasonable target for async SQLAlchemy stacks, but this repository currently uses synchronous SQLAlchemy `Session` objects through the CLI, API routes, and persistence layer. That means the first step is to normalize the code shape (`core` / `orm` / `crud`) and then decide whether the repo will actually migrate the relevant slices to async DB access. Until that decision is made, the CRUD boundary should stay isolated so the backing implementation can change without another structural rewrite.

## Definition of done for each refactor PR

A refactor PR should only be considered done if it:

- preserves or improves tests
- keeps `ruff check` clean
- keeps `uv run pytest` green for the touched area
- updates docs when operator behavior changes
- leaves a simpler import graph than before
