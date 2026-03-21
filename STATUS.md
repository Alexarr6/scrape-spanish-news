- State: CLEANUP_IMPLEMENTATION_COMPLETE
- Current phase: cleanup implementation completed for scoped audit items in `spain-news-bias-scraper`
- Last update: 2026-03-21 UTC

## What completed in this implementation pass

- Completed the scoped cleanup items from `ARCH_AUDIT.md` that were explicitly requested in this pass.
- Landed three atomic commits:
  1. `refactor(db): deduplicate schema sql constants`
  2. `fix(clustering): make cluster rebuild transactional`
  3. `chore(ops): deprecate legacy scheduled wrapper`
- Ran narrow validation after each change.

## Key findings summary

### P0 (dangerous, fix immediately)
- `INIT_SQL_TEMPLATE` and `ADDITIVE_SCHEMA_SQL` in `dbstore.py` are byte-for-byte identical. Dead duplication.

### P1 (important structural debt)
- `run_scheduled.sh` is a legacy scrape-only scheduler that coexists with newer full-pipeline wrappers. Operator confusion risk; can run silently without analysis/clustering.
- Cluster rebuild is a full DELETE with no atomic transaction or rollback — API returns empty cluster state on failed rebuild.
- `article_enrichment_runs` table is written on every enrichment but never read by API, frontend, or any operational surface. Dead write work.
- SQLite dialect branch (`_session_dialect_name`, `_explorer_published_at_sql`) lives in production `dbstore.py` to serve test infrastructure. Should be in test layer.

### P2 (cleanup/clarity debt)
- `entity_aliases` write path runs per enrichment but no API/read-side path consumes alias data.
- `ExplorerArticleDetail.semantic_summary` duplicates `point.analysis` in the API response.
- `cluster_key` is not a stable identifier — regenerated on each full rebuild, exposed in API/frontend.
- Enrichment score threshold defaults differ between Makefile (0.68) and `run_stories_refresh.sh` (0.45).
- `generate_comparison_summary.py` is an orphan script with no Makefile target and a hardcoded date.
- Frontend types are manually mirrored from Python contracts (acceptable now, needs tooling before growing).

## Tables classified

- Source-of-truth: `articles` only
- Semi-durable (expensive to rebuild): `article_embeddings`
- Reference/seed: `tags`
- Rebuild artifacts: everything else (story_clusters, cluster_members, cluster_entities, article_analysis, article_tags, entity_mentions, entities, article_projections, semantic_point_analysis, semantic_clusters)
- No read path: `article_enrichment_runs`, `entity_aliases`

## Story clustering vs semantic clustering

Confirmed: these are clearly different products. No schema overlap or conceptual confusion.

## Validation run in this implementation pass

- `~/.local/bin/uv run --project . python - <<'PY' ...` to verify both semantic schema renderers still emit identical SQL after deduplication.
- `~/.local/bin/uv run --project . pytest -q tests/test_story_clustering.py`
- `DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname' make scheduler-dry-run`
- `make help | grep -n "LEGACY" | head`

## Scope completed

### P0 — deduplicate SQL constants in `dbstore.py`
- Done.
- Replaced duplicate `INIT_SQL_TEMPLATE` / `ADDITIVE_SCHEMA_SQL` bodies with one canonical `SCHEMA_SQL_TEMPLATE`.
- Kept both render helpers for behavior compatibility.

### P1 — make cluster rebuild safer
- Done.
- `ClusterPipeline.build_clusters()` now explicitly rolls back on any failure during the destructive rebuild/persist phase before re-raising.
- Added a focused regression test that asserts rollback happens and commit does not happen on rebuild failure.

### P1 — reduce operator trap around old scheduler wrapper
- Done, without breaking legacy invocation.
- `scripts/run_scheduled.sh` now logs a loud deprecation warning stating that it is scrape-only and does not run enrichment/clustering.
- Makefile help text and operator docs now mark the wrapper as deprecated legacy behavior and point operators at `run_stories_refresh.sh`.

## Remaining architect backlog not tackled in this pass

- `article_enrichment_runs` still has no read path.
- SQLite compatibility branch in `src/semantic/dbstore.py` still exists.
- Other P2 cleanup items from the audit remain deferred.
