- State: COMPLETE
- Current phase: documentation overhaul implemented
- Last update: 2026-03-20 UTC

## Completed deliverables
- README rewritten into a tighter operator/quickstart guide
- MkDocs integrated via `mkdocs.yml`
- new primary docs structure added under `docs/`
- selective backend/script docstrings added in semantic, analysis, API, and CLI entrypoints
- `Makefile` updated with `docs-build` and `docs-serve`
- `pyproject.toml` updated with MkDocs dev dependency

## Implementation scope actually touched
### README / operator surface
- `README.md`
- `Makefile`
- `pyproject.toml`
- `mkdocs.yml`

### Docs IA and content
- `docs/index.md`
- `docs/getting-started.md`
- `docs/operator-guide/*`
- `docs/semantic/*`
- `docs/architecture/*`
- `docs/reference/*`
- `docs/testing-quality.md`
- `docs/web-app-api.md`
- `docs/historical/index.md`

### Code docstrings / comments
- `src/semantic/dbstore.py`
- `src/semantic/analyze.py`
- `src/semantic/project.py`
- `src/analysis/pipeline.py`
- `src/analysis/readside.py`
- `src/analysis/canonicalization.py`
- `src/analysis/heuristics.py`
- `src/api/app.py`
- `src/api/v1/clusters.py`
- `src/api/v1/semantic.py`
- `scripts/semantic_sync.py`
- `scripts/semantic_project.py`
- `scripts/build_semantic_map.py`
- `scripts/build_story_clusters.py`
- `scripts/enrich_articles.py`
- `scripts/run_scheduled.sh`
- `src/main.py`

## Verification status
- `make sync` — ✅ passed
- `make docs-build` — ✅ passed
- `make frontend-check` — ✅ passed
- `make test` — ⚠️ repo has 3 pre-existing fixture-path failures in archived evidence tests for missing `20minutos` fixture JSON under `tests/fixtures/evidence/20260314-1212-8ff9`

## Notes for handoff
- Docs were written against current `Makefile`, scripts, API app factory, and frontend package commands.
- Historical docs were kept and clearly demoted to historical context instead of being deleted.
- Frontend comments were not expanded; existing code was left mostly alone to avoid comment spam.
- Commit policy target was prepared around atomic slices, but commits themselves were not created in this session yet.
