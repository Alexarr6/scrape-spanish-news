# RESULTS.md

## 2026-03-21 — cleanup implementation for `spain-news-bias-scraper`

**Role:** implementer
**Outcome:** ✅ Complete for scoped items
**Scope:** P0 duplicate semantic schema SQL, P1 cluster rebuild safety, P1 legacy scheduler deprecation/guarding

---

## What changed

### 1) P0 — deduplicated semantic schema SQL
- Replaced the duplicated `INIT_SQL_TEMPLATE` and `ADDITIVE_SCHEMA_SQL` bodies in `src/semantic/dbstore.py` with a single canonical `SCHEMA_SQL_TEMPLATE`.
- Kept `render_init_sql()` and `render_additive_schema_sql()` as compatibility wrappers so call sites and behavior stay unchanged.

**Commit:** `refactor(db): deduplicate schema sql constants`

### 2) P1 — made cluster rebuild rollback explicit
- Tightened `ClusterPipeline.build_clusters()` so the destructive cluster rebuild persists inside an explicit `try/except` that calls `session.rollback()` on any failure before re-raising.
- This closes the operator trap where a failed rebuild could leave pending destructive work hanging around in the session and accidentally get committed later by a caller.
- Added a focused regression test covering rollback-on-failure.

**Commit:** `fix(clustering): make cluster rebuild transactional`

### 3) P1 — deprecated the legacy scrape-only scheduler wrapper
- Kept `scripts/run_scheduled.sh` callable for legacy usage, but made it loud and unmistakable:
  - logs a deprecation warning on dry-run and real execution
  - explicitly says it does **not** run `enrich-articles` or `build-story-clusters`
  - points operators to `scripts/run_stories_refresh.sh`
- Updated Makefile help text and operator-facing docs/README to mark the wrapper as legacy/deprecated.

**Commit:** `chore(ops): deprecate legacy scheduled wrapper`

---

## Validation run

- `~/.local/bin/uv run --project . python - <<'PY' ...` to confirm both semantic schema render helpers still emit the same SQL and the embedding dimension substitution still works.
- `~/.local/bin/uv run --project . pytest -q tests/test_story_clustering.py`
  - result: `3 passed`
- `DATABASE_URL='postgresql+psycopg://user:pass@host:5432/dbname' make scheduler-dry-run`
  - verified the legacy warning is written to `var/log/scheduler.log`
- `make help | grep -n "LEGACY" | head`
  - verified operator-facing legacy labeling in help output

---

## Blocked architect-level decisions

None for the scoped items completed here.

The remaining P1/P2 audit items (`article_enrichment_runs`, SQLite compatibility leakage, etc.) were intentionally left untouched because they were outside this implementation pass.

## 2026-03-20 — architect audit handoff for `spain-news-bias-scraper`

**Role:** architect
**Outcome:** ✅ Complete
**Scope:** audit-only, no implementation

---

## What was accomplished

A full, repo-grounded architecture audit has been completed and written to `ARCH_AUDIT.md`.

All five audit tracks from `PLAN.md` were executed:

1. **DB/schema audit** — every table classified by role (source-of-truth / derived / dead)
2. **Codebase/legacy audit** — cleanup candidate register with evidence and removal confidence
3. **Pipeline/data-flow audit** — end-to-end runtime map with risks annotated
4. **API/frontend contract audit** — Python/TypeScript alignment verified, issues identified
5. **Simplification/de-scope audit** — "remove tomorrow" and "not worth carrying yet" lists

---

## `ARCH_AUDIT.md` structure

The audit document contains:

- Executive summary with the five real problems in severity order
- **Deliverable A**: System audit memo (five tracks, each finding has severity/confidence/evidence/recommendation)
- **Deliverable B**: Data model decision table (all 15 tables)
- **Deliverable C**: Runtime/data-flow map (scrape to frontend, annotated with destructive/additive/risk markers)
- **Deliverable D**: Cleanup candidate register (6 items with proof requirements)
- **Deliverable E**: Recommended execution order (Phase 0/1/2/3)

---

## Summary findings by priority

### P0 — fix now
- **Duplicate SQL constants** (`INIT_SQL_TEMPLATE` == `ADDITIVE_SCHEMA_SQL` byte-for-byte): 5-minute fix, no behavior change

### P1 — important before scaling
- **Legacy `run_scheduled.sh`**: scrape-only scheduler coexists with newer full-pipeline wrappers; operator confusion risk; silent under-enrichment if wrong wrapper is used
- **Cluster rebuild has no transaction safety**: full DELETE before rebuild, no atomic swap; API returns empty cluster state on failed rebuild
- **`article_enrichment_runs`**: written every enrichment cycle, never read anywhere; dead write overhead dressed as auditing
- **SQLite dialect branch in production `dbstore.py`**: test infrastructure leaking into production code

### P2 — cleanup/clarity
- `entity_aliases`: write-only, no read path
- `ExplorerArticleDetail.semantic_summary` duplicates `point.analysis`
- `cluster_key` is not stable across rebuilds but is exposed in API/frontend types
- Threshold mismatch (0.68 in Makefile, 0.45 in stories refresh wrapper)
- `generate_comparison_summary.py` is an orphan script

---

## Table ownership summary

| Classification | Tables |
|---|---|
| Source-of-truth | `articles` |
| Semi-durable (expensive) | `article_embeddings` |
| Reference/seed | `tags` |
| Derived rebuild artifacts | `article_analysis`, `article_tags`, `entity_mentions`, `entities`, `story_clusters`, `cluster_members`, `cluster_entities`, `article_projections`, `semantic_point_analysis`, `semantic_clusters` |
| No read path (dead writes) | `article_enrichment_runs`, `entity_aliases` |

---

## What is not a problem

- Story clustering vs. semantic clustering: clearly different products, no schema overlap
- `articles.tags` raw field: still used as heuristic input signal, justified
- Semantic tables using raw SQL DDL instead of ORM: acceptable given pgvector constraints
- Frontend types manually mirrored from Python: acceptable at current scale
- `analysis-db-init` on every stories refresh: idempotent, harmless, low priority

---

## Previous result entries

### 2026-03-20 — planner handoff for serious repo audit

**Role:** planner
**Outcome:** ✅ Complete
**Scope:** planning only, no implementation

A full audit-planning handoff was placed in `PLAN.md` and this file. The planner established the five audit tracks, required deliverables, prioritization model, and architect workflow. See the earlier entry in git history for the full planner summary.
