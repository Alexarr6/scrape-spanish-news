# ARCH_AUDIT.md — Architecture Audit: `spain-news-bias-scraper`

**Date:** 2026-03-20  
**Role:** architect (audit-only pass)  
**Status:** complete, no code changes made  
**Feeds:** post-audit cleanup/build phase

---

## Executive Summary

The repo is a layered system with real product surfaces: scraping, persistence, analysis/clustering, semantic/explorer, and API/frontend. The architecture is largely defensible for its current scope. The main risks are not dramatic — there is no structural rot — but there is meaningful accrual that will compound if scaled without cleanup.

**The five real problems, in order of urgency:**

1. `INIT_SQL_TEMPLATE` and `ADDITIVE_SCHEMA_SQL` in `dbstore.py` are **byte-for-byte identical**. This is a clear duplication bug.
2. The **SQLite dialect compatibility branch** in `dbstore.py` lives in production code to serve test infrastructure, which is the wrong arrangement.
3. **`article_enrichment_runs`** is written by the pipeline but never read by the API, frontend, or any operational surface. It is DB noise dressed as auditing.
4. **`cluster_key`** is generated with a non-deterministic index suffix on full cluster rebuilds, so it is not a stable identifier despite being exposed in the API and used by the frontend. This is a latent client-cache invalidation bug.
5. The **legacy `run_scheduled.sh`** coexists with two newer wrappers and has a different orchestration surface (no analysis, no clustering). Its continued existence creates operator confusion and divergent prod configs.

Everything else ranges from P2 (cleanup debt) to acceptable-for-now.

---

## Track 1 — DB/Schema Audit

### Data Model Decision Table

| Table | Owning subsystem | Write path | Read path | Rebuildable? | Justified? | Classification |
|---|---|---|---|---|---|---|
| `articles` | persistence | `crud.py` ingest/upsert | API, analysis, semantic | No | Yes | **source-of-truth** |
| `article_enrichment_runs` | analysis | `pipeline.py` enrichment | nowhere | Yes | Marginal | **operational log — no read path** |
| `tags` | analysis | `pipeline.py` seed_tags() | analysis, readside, API | Yes (idempotent seed) | Yes | **reference/seed data** |
| `article_analysis` | analysis | `pipeline.py` per-article | `pipeline.py` (cluster scoring) | Yes | Yes | **derived, rebuild artifact** |
| `entities` | analysis | `pipeline.py` per-article | `readside.py`, API cluster detail | Partly | Marginal at current scale | **derived, growing reference table** |
| `entity_aliases` | analysis | `pipeline.py` per-article | nowhere in API/read-side | Yes | Questionable | **derived, write-only in practice** |
| `entity_mentions` | analysis | `pipeline.py` per-article | `readside.py` (cluster detail/scoring) | Yes | Yes | **derived, rebuild artifact** |
| `article_tags` | analysis | `pipeline.py` per-article | `readside.py`, API | Yes | Yes | **derived, rebuild artifact** |
| `story_clusters` | analysis | `pipeline.py` full rebuild | API cluster list/detail | Yes — full delete/re-insert on each run | Yes | **derived, rebuild artifact** |
| `cluster_members` | analysis | `pipeline.py` full rebuild | `readside.py`, API | Yes | Yes | **derived, rebuild artifact** |
| `cluster_entities` | analysis | `pipeline.py` full rebuild | `readside.py`, API | Yes | Yes | **derived, rebuild artifact** |
| `article_embeddings` | semantic | `dbstore.py` upsert (content-hash gated) | `dbstore.py` projection + neighbor queries | No — embeddings cost API calls | Yes | **semi-durable, expensive to rebuild** |
| `article_projections` | semantic | `dbstore.py` destructive per-projection-set | API explorer points | Yes | Yes | **derived, rebuild artifact** |
| `semantic_point_analysis` | semantic | `dbstore.py` destructive per-projection-set | API explorer points page | Yes | Yes | **derived, rebuild artifact** |
| `semantic_clusters` | semantic | `dbstore.py` destructive per-projection-set | API explorer filters/summaries | Yes | Yes | **derived, rebuild artifact** |

### Source-of-Truth vs Derived

**True source-of-truth:** `articles` only.

**Expensive to rebuild (semi-durable):** `article_embeddings`. These cost real money to regenerate via OpenAI; treat them as durable even though they are technically re-derivable.

**Everything else is a rebuild artifact.** The schema correctly reflects this in practice (most tables are fully deleted and re-inserted on each pipeline run) but nothing documents this distinction explicitly. That creates operator confusion about what is safe to truncate.

### Finding 1.1 — `articles.tags` still exists alongside normalized tag system
**Severity: P2 | Confidence: high | Evidence: `orm_models.py`, `heuristics.py:115`, `pipeline.py:308`**

`articles.tags` is a raw text blob scraped from article metadata (RSS `article:tag`, `news_keywords`). It is still populated by the scraper and used by `heuristics.py` as an input signal for tag inference (`infer_tag_codes`). The normalized tag system (`article_tags` → `tags`) is the authoritative read surface.

**This is not dead code.** `articles.tags` feeds heuristic tag inference as a secondary source signal. Its continued existence is justified as a scraper-fidelity field.

**Recommendation:** `document` — add a code comment clarifying `articles.tags` is a raw scraper capture used only as heuristic input; it is not the canonical analysis-layer tag assignment. Prevents future "can I remove this?" confusion. No schema change needed.

### Finding 1.2 — `article_enrichment_runs` has no read path
**Severity: P1 | Confidence: high | Evidence: grepping all read paths in `src/api/`, `src/analysis/readside.py` — zero hits**

`ArticleEnrichmentRunORM` is written to on every enrichment run with run metadata (start/finish, model, token estimates, status). It is never read by the API, the frontend, the operator scripts, or any alerting surface. It doesn't appear in any query, reporting, or monitoring path.

This is operational logging masquerading as a schema table. If no one reads it, it is dead write work executed on every enrichment job.

**Recommendation:** `remove` (P1) — either wire it to an actual monitoring surface (admin endpoint, metrics export, operator CLI report) or drop it. If it exists for auditing intent, it needs a read path within 1 build cycle. Otherwise it is pure write overhead. The table itself has no foreign-key dependents; dropping it is a clean operation.

### Finding 1.3 — `entity_aliases` is written but never read in any API/read-side path
**Severity: P2 | Confidence: high | Evidence: grepping all `entity_aliases`/`EntityAlias` references in `src/api/` and `src/analysis/readside.py` — zero hits**

`entity_aliases` stores alternate names for entities (e.g., `PSOE` → `Partido Socialista Obrero Español`). The `EntityCanonicalizer` writes aliases during enrichment. No read-side query, API route, or frontend surface consumes them.

The intended use is likely entity disambiguation during mention matching, but the actual code uses `normalized_name` uniqueness constraints and alias lookup in `canonicalize()` — not alias table queries.

**Recommendation:** `defer` for now (P2) — but document what this table is waiting for. If entity disambiguation via alias lookup is not implemented in the next cycle, remove the table and the alias-write code. It is currently write-only infrastructure for a feature that does not exist yet.

### Finding 1.4 — `cluster_key` is not a stable identifier
**Severity: P1 | Confidence: high | Evidence: `pipeline.py:520`, `contracts/clusters.py:36`, `frontend/src/lib/types.ts:162`**

`cluster_key` is generated as:
```
story-{date}-{slug}-{index}
```
where `{index}` is the component's position in the sorted component list. Since clusters are **fully deleted and rebuilt** on every `build-story-clusters` run, the index suffix changes with each run when the set of articles or clustering result changes.

`cluster_key` is exposed in the API contract (`StoryClusterListItem`) and in the frontend TypeScript types. If any client code uses `cluster_key` as a stable bookmark/cache key across refreshes, it is wrong. The stable ID is the integer `id`, which also changes on full rebuild.

**In practice:** clusters are volatile across refreshes. The frontend should treat `id` as session-scoped only, and `cluster_key` should not be used as a durable reference. Nothing in the current UI code was found to cache cluster keys for later lookup, so this is currently latent — but one "share this cluster" feature would expose it.

**Recommendation:** `document` at minimum; `re-scope` if cluster persistence is ever intended to be stable. Either explicitly call `cluster_key` ephemeral in the contract, or design a stable cluster identity mechanism before adding any feature that relies on persistent cluster references.

### Finding 1.5 — Semantic tables use raw SQL DDL, not ORM models
**Severity: P2 | Confidence: high | Evidence: `dbstore.py` — `INIT_SQL_TEMPLATE`, `ADDITIVE_SCHEMA_SQL` strings; `db.py` — `Base.metadata.create_all` covers persistence + analysis ORM models but not semantic tables**

Semantic tables (`article_embeddings`, `article_projections`, `semantic_point_analysis`, `semantic_clusters`) are created via raw SQL templates in `dbstore.py`, not via SQLAlchemy ORM models. This is a deliberate design choice — pgvector's `VECTOR(N)` type is not trivially handled by SQLAlchemy ORM at the time of writing.

**This is acceptable for now.** The raw SQL path works, schema evolution is gated by the model-dimension check, and the tables are rebuild artifacts anyway. But it means `Base.metadata.create_all()` does not cover semantic tables — they require the separate `make semantic-db-init` step. This is documented in the README and Makefile, so the operational risk is low.

**Recommendation:** `keep` — but document that semantic schema is managed separately from ORM-managed persistence/analysis schema. If a SQLAlchemy pgvector extension is ever adopted, migrating is straightforward.

### Finding 1.6 — `story_clusters` vs `semantic_clusters` are clearly different products
**Severity: low/informational | Confidence: high**

These are not overlapping concepts hiding in the schema. `story_clusters` (analysis layer) is editorial clustering: articles about the same news event, grouped by heuristic/entity/tag similarity. `semantic_clusters` (semantic layer) is geometric clustering: HDBSCAN groups in the PCA embedding space.

Both tables are rebuild artifacts. They serve different UI surfaces (story browser vs. semantic explorer). The naming and separation are correct.

**No action required.** Document this distinction once in the architecture docs if it continues to confuse.

---

## Track 2 — Codebase / Legacy Audit

### Cleanup Candidate Register

| # | Location | Why it looks legacy/dead | Still called? | Proof needed before removal |
|---|---|---|---|---|
| 1 | `scripts/run_scheduled.sh` | Scrape-only scheduler; does not run analysis, enrichment, or clustering. Newer wrappers (`run_stories_refresh.sh`, `run_explorer_refresh.sh`) replaced its function. README explicitly labels it "legacy". | Yes — `make scheduler-once`, `make scheduler-dry-run` | Confirm no production cron uses it; then remove Makefile targets and script |
| 2 | `src/semantic/dbstore.py` — `INIT_SQL_TEMPLATE` vs `ADDITIVE_SCHEMA_SQL` | Byte-for-byte identical strings. `INIT_SQL_TEMPLATE` is used only on fresh init; `ADDITIVE_SCHEMA_SQL` is used on subsequent runs. They are the same SQL. | Both are called | Remove one; use the other for both cases; `init_pgvector_schema()` already handles the conditional branch |
| 3 | `src/semantic/dbstore.py` — `_session_dialect_name()` + `_explorer_published_at_sql()` | SQLite compatibility branch exists to allow test infrastructure to use in-memory SQLite. Production is Postgres-only. This is test convenience leaking into production code. | Yes — called in `load_explorer_points_page` and `load_explorer_article_detail` | Refactor tests to use Postgres fixtures or a test double; then remove the dialect branch |
| 4 | `src/core/contracts.py` — backward-compat bridge in `RunMetricsModel` | The `strategy_metrics` field includes a backward-compat normalizer that converts old list-shape payloads to the current dict-shape. The list-shape is the legacy format. | Called by test suite | Check if any production data or external callers still emit the list format; if not, drop the compat branch |
| 5 | `scripts/generate_comparison_summary.py` | No Makefile target, not called by any scheduler or refresh wrapper. Has a hardcoded `DATE_DEFAULT = "2026-03-13"`. Used only by tests that exercise the contract. | Only by tests | Either give it a Makefile target and wire it to a real operational flow, or move the logic exclusively into tests and delete the standalone script |
| 6 | `src/core/comparison_summary.py` | Comparison summary infrastructure exists but has no live read path from the API or frontend. The comparison concept (baseline vs. current scrape counts) was meaningful for scraper QA but is not surfaced anywhere in the UI or API. | By test suite and the generate script | Decision needed: is this a deferred feature or dead weight? Tests are the only consumers. |

### Finding 2.1 — Legacy scheduler is a real operational risk
**Severity: P1 | Confidence: high | Evidence: `run_scheduled.sh` content; `Makefile` targets `scheduler-once`, `scheduler-dry-run`, `status`, `tail-log`**

`run_scheduled.sh` runs scrape + verify only. It does not run analysis enrichment or cluster building. If a production cron uses `scheduler-once` instead of `stories-refresh-once`, articles will be scraped and persisted but never enriched or clustered. The story browser will silently show stale or no clusters.

The Makefile still exposes `scheduler-once` as a named target at the same level of visibility as `stories-refresh-once`. There is nothing to distinguish them for an operator scanning the help text except reading the comments.

**Recommendation:** `remove` (P1) — deprecate `run_scheduled.sh` and its Makefile targets. If someone needs a scrape-only (no analysis) mode, make that a named parameter of `run_stories_refresh.sh`, not a separate legacy wrapper.

### Finding 2.2 — Duplicate SQL strings in `dbstore.py`
**Severity: P0 | Confidence: high | Evidence: programmatic comparison — `INIT_SQL_TEMPLATE == ADDITIVE_SCHEMA_SQL` is True**

`INIT_SQL_TEMPLATE` (used for fresh schema creation) and `ADDITIVE_SCHEMA_SQL` (used when schema already exists) are identical strings. The logic that uses them is different (one-time init vs. idempotent `CREATE TABLE IF NOT EXISTS` run), but the SQL itself is the same because both already use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.

This means `render_init_sql()` and `render_additive_schema_sql()` do the same thing. The two-constant design implies they were intended to diverge (perhaps `INIT_SQL_TEMPLATE` was going to be a destructive `DROP + CREATE` at some point), but they never did.

**Recommendation:** `merge` (P0) — remove one constant, use the other everywhere. This is a small fix with no behavior change but eliminates a permanently misleading code structure.

### Finding 2.3 — SQLite dialect branch is test infrastructure leaking into production code
**Severity: P1 | Confidence: high | Evidence: `_session_dialect_name()`, `_explorer_published_at_sql()` in `dbstore.py`; `test_api_semantic_explorer.py` uses `sqlite+pysqlite:///:memory:`**

The semantic explorer tests use SQLite in-memory because `article_embeddings` cannot be expressed as a proper ORM model (pgvector dependency). To work around this, `dbstore.py` detects the session's dialect and emits different SQL for `published_at` formatting depending on whether the DB is SQLite or Postgres.

This is backwards. Production code should not contain SQLite compatibility branches. The right fix is to isolate the SQLite workaround to the test layer (e.g., a test-specific session wrapper or mock, or switching to testcontainers/Postgres fixtures for semantic tests).

**Recommendation:** `fix` (P1) — move the dialect detection and SQLite SQL variant into the test layer only. Production `dbstore.py` should emit Postgres SQL unconditionally.

### Finding 2.4 — `entity_aliases` write path runs on every enrichment but has no read path
Already documented in Track 1 (Finding 1.3). From a codebase perspective: the alias-write loop in `pipeline.py` runs on every article enrichment, hitting the DB multiple times per entity per article. It accumulates aliases over time with no corresponding read logic. This is pure write overhead.

### Finding 2.5 — `generate_comparison_summary.py` is an orphan script
**Severity: P2 | Confidence: high | Evidence: not in Makefile, not in any scheduler, hardcoded date**

`scripts/generate_comparison_summary.py` generates a JSON comparison of baseline vs. current scrape counts. It has a hardcoded `DATE_DEFAULT = "2026-03-13"` (a past date). It is not wired to any Makefile target or refresh wrapper. The tests in `test_comparison_summary_contract.py` exercise the contract directly without calling the script.

The module itself (`src/core/comparison_summary.py`) and its contract (`src/core/contracts.py`) are live code, but the script is a standalone artifact from an earlier QA workflow that has not been integrated into current operations.

**Recommendation:** `remove` the script (P2), keep the module if comparison logic is still intended for future use. Add a Makefile target or remove the module entirely if the comparison concept is not on the roadmap.

---

## Track 3 — Pipeline / Data-Flow Audit

### End-to-End Runtime Map

```
SCRAPE INPUTS
  └─ adapters/{source}.py (RSS + HTML extraction)
     └─ src/core/models.py Article dataclass
        └─ src/core/contracts.py NewsItemModel validation

SCRAPE-ONLY MODE (make run-source / make smoke)
  └─ output: data/{prefix}_{source}_{date}.json
  └─ output: logs/{prefix}_{source}_{date}_metrics.json

PERSIST MODE (make run-source-persist / make run-all-persist)
  └─ src/persistence/crud.py ArticleCRUD.upsert()
     └─ WRITES: articles (source-of-truth, additive/upsert)

ANALYSIS FLOW (make enrich-articles)
  └─ src/analysis/pipeline.py AnalysisPipeline.enrich_articles()
     ├─ READS: articles (bounded window by published_at)
     ├─ READS: tags (taxonomy lookup)
     ├─ WRITES: article_enrichment_runs (write-only, no read path)
     ├─ WRITES: article_analysis (upsert, content-hash gated)
     ├─ WRITES: article_tags (delete + re-insert per article)
     ├─ WRITES: entities (upsert on normalized_name)
     ├─ WRITES: entity_aliases (additive per entity)
     └─ WRITES: entity_mentions (delete + re-insert per article)

CLUSTER FLOW (make build-story-clusters)
  └─ src/analysis/pipeline.py ClusterPipeline.build_clusters()
     ├─ READS: articles + article_analysis (enriched window)
     ├─ READS: article_tags, entity_mentions
     ├─ DESTROYS: cluster_entities, cluster_members, story_clusters (full DELETE)
     └─ WRITES: story_clusters, cluster_members, cluster_entities (full rebuild)

SEMANTIC SYNC (make semantic-sync)
  └─ src/semantic/dbstore.py select_embedding_candidates() + upsert_embeddings()
     ├─ READS: articles (window filter)
     ├─ READS: article_embeddings (content-hash check)
     └─ WRITES: article_embeddings (upsert, content-hash gated, expensive)

SEMANTIC PROJECT (make semantic-project)
  └─ src/semantic/dbstore.py refresh_projection_set()
     ├─ READS: article_embeddings (all or windowed)
     ├─ DESTROYS: article_projections, semantic_point_analysis, semantic_clusters (per projection_set)
     └─ WRITES: article_projections, semantic_point_analysis, semantic_clusters (rebuild)

SEMANTIC BUILD (make semantic-build)
  └─ scripts/build_semantic_map.py
     ├─ READS: article_embeddings, article_projections (from DB)
     └─ WRITES: data/semantic/*.json, data/semantic/*.html (file exports only)

API READ PATHS
  └─ /api/v1/articles → persistence layer (ArticleCRUD)
  └─ /api/v1/clusters → analysis readside (readside.py)
  └─ /api/v1/semantic/explorer → semantic dbstore (load_explorer_*) 
```

### Finding 3.1 — Cluster rebuild is fully destructive with no atomic swap
**Severity: P1 | Confidence: high | Evidence: `pipeline.py:500-502`**

```python
self.session.execute(delete(ClusterEntityORM))
self.session.execute(delete(ClusterMemberORM))
self.session.execute(delete(StoryClusterORM))
```

These are naked DELETEs — no WHERE clause — that wipe **all** cluster data before rebuilding. If the rebuild fails mid-flight (e.g., OOM, LLM timeout, DB connection drop), the API returns an empty cluster list until the next successful run. There is no fallback, no atomic swap, no partial-success handling.

The current code does wrap this in a session that commits at the end, so a Python exception before the final `commit()` would leave the DB in the pre-delete state. But any error after the DELETE flush and before the commit will still result in a committed empty state on some paths.

**Recommendation:** `fix` (P1) — either (a) wrap the entire cluster rebuild in a single transaction with explicit rollback on failure, or (b) use a staging approach (write new clusters to temp rows, then swap). Option (a) is simpler and sufficient given current scale.

### Finding 3.2 — `analysis-db-init` runs on every stories refresh
**Severity: P2 | Confidence: high | Evidence: `run_stories_refresh.sh:96-100`**

`run_stories_refresh.sh` calls `make analysis-db-init` on every run. `init_analysis_schema.py` calls `Base.metadata.create_all()` (which is idempotent for existing tables) and `AnalysisPipeline.seed_tags()`. `seed_tags()` upserts all CANONICAL_TAGS on every run.

This is harmless but wasteful. The tag seed is only necessary on first run or when the taxonomy changes. Running it on every 6-hour refresh is overhead.

**Recommendation:** `keep` for now (P2) — it is idempotent and the cost is minimal. But if the pipeline scales to higher frequency, extract the init step to a one-time setup command.

### Finding 3.3 — `select_embedding_candidates()` over-fetches by 4x
**Severity: P2 | Confidence: high | Evidence: `dbstore.py` — `query.limit(limit * 4)`**

The semantic sync candidate selection loads `limit * 4` article rows in Python, then filters out articles with unchanged content hashes and insufficient text length. This is an in-Python filter on a 4x over-fetch.

For small limits (100–500) this is acceptable. At larger scale, this should move to a subquery that excludes already-embedded articles with matching content hashes at the SQL level.

**Recommendation:** `defer` (P2) — acceptable now, flag for optimization before scaling sync limits beyond ~1000.

### Finding 3.4 — Enrichment pipeline skips articles by content hash, but cluster rebuild does not
**Severity: P2 | Confidence: medium | Evidence: `pipeline.py:163-167` (enrichment skip), `pipeline.py:500-502` (cluster full delete)**

Enrichment is incremental (skip if content hash matches). Cluster rebuild is always full. This means even a single new article triggers a full cluster delete-and-rebuild of the entire window. If `CLUSTER_LIMIT=1000` and most articles are unchanged, this is unnecessary work.

The full-rebuild approach is correct for correctness (cluster membership can shift due to new articles even for old content), but it means the cluster table is always transiently empty during rebuild, which feeds Finding 3.1.

**Recommendation:** `document` the reasoning explicitly. Full rebuild is correct for correctness; the risk is the downtime window.

### Finding 3.5 — Story scoring is heuristic-heavy with undocumented threshold behavior
**Severity: P2 | Confidence: high | Evidence: `pipeline.py:403-438`**

The pair-scoring formula is:
```
score = semantic_similarity * 0.30 + title_sim * 0.20 + shared_entity_score * 0.25
      + tag_overlap_score * 0.10 + keyphrase_overlap_score * 0.10
      + temporal_proximity_score * 0.05
```
With penalties for `analysis_pair_penalty` (-0.15) and `followup_penalty` (-0.12).

The default threshold in `run_stories_refresh.sh` is `SCORE_THRESHOLD=0.45`, but the Makefile default is `SCORE_THRESHOLD=0.68`. These differ by 0.23 — a substantial gap that means the scheduler runs with much looser clustering than `make build-story-clusters`. This is not necessarily wrong, but it is undocumented and produces different cluster shapes depending on which entrypoint is used.

**Recommendation:** `document` (P2) — either standardize the threshold across all entrypoints or explicitly document why they differ. An operator should not need to read both the Makefile and the script to know what threshold the system is using.

### Finding 3.6 — Pipeline parameters are scattered across too many surfaces
**Severity: P2 | Confidence: high**

`DAYS_BACK`, `ENRICH_LIMIT`, `CLUSTER_LIMIT`, `SCORE_THRESHOLD`, `EMBEDDING_MODEL`, `PROJECTION_SET`, `SEMANTIC_LIMIT` are defined in:
- `Makefile` (defaults)
- `run_stories_refresh.sh` (overrides)
- `run_explorer_refresh.sh` (overrides)
- `scripts/enrich_articles.py` etc. (argparse defaults)

Three layers of defaults for the same parameters. The effective value for any parameter depends on which entrypoint was used. This is not a blocking problem but it will bite the next person who tries to tune production behavior.

**Recommendation:** `re-scope` (P2) — designate one canonical location for pipeline tuning parameters (the shell wrappers are the right place for prod values) and document that Makefile defaults are for local dev convenience only.

---

## Track 4 — API / Frontend Contract Audit

### Finding 4.1 — Frontend TypeScript types are manually mirrored from Python Pydantic models
**Severity: P2 | Confidence: high | Evidence: `src/api/contracts/semantic.py` vs `frontend/src/lib/types.ts`**

Python Pydantic models and TypeScript types are manually kept in sync. For the semantic explorer:
- `ExplorerSemanticSummary` (Python) ↔ `ExplorerSemanticSummary` (TS)
- `ExplorerPoint` (Python) ↔ `ExplorerPoint` (TS)
- `ExplorerMeta` (Python) ↔ `ExplorerMeta` (TS)
- etc.

The current sync is clean — field names and types match. This is acceptable at this scale and better than many projects handle it.

**Risk:** Any Python contract change requires a corresponding TS update. No tooling enforces this.

**Recommendation:** `keep` for now (P2) — at this scale, manual sync is fine. If the contract surface grows significantly, consider a code-gen step (FastAPI → OpenAPI → TS types via `openapi-typescript`). Flag this before adding more than 5 new fields to any contract.

### Finding 4.2 — `ExplorerArticleDetail.semantic_summary` duplicates `ExplorerArticleDetail.point.analysis`
**Severity: P2 | Confidence: high | Evidence: `src/api/v1/semantic.py:_to_article_detail_response()`**

```python
semantic_summary = (
    point_model.analysis if point_model is not None else ExplorerSemanticSummary()
)
return ExplorerArticleDetail(
    ...
    point=point_model,
    semantic_summary=semantic_summary,  # same object as point.analysis
    ...
)
```

`semantic_summary` in the response is the same data as `point.analysis` when the point exists. This means the JSON payload contains the same data twice for articles that have projections.

**Recommendation:** `simplify` (P2) — remove `semantic_summary` from the contract and have the frontend read `point.analysis` directly. The frontend currently has both fields in `ExplorerArticleDetail` type. This is a clean breaking change on a single detail endpoint; low risk.

### Finding 4.3 — Cluster API contracts are mature; semantic API contracts are slightly ad hoc
**Severity: P2 | Confidence: medium**

The cluster API (`src/api/contracts/clusters.py`) is well-structured with proper Pydantic models for every response type. The semantic API (`src/api/contracts/semantic.py`) is also Pydantic-based, but the translation in `_to_point_model()` does a manual `model_dump() / setdefault()` dance instead of a clean mapping:

```python
def _to_point_model(item, *, neighbor_count: int = 0) -> ExplorerPoint:
    payload = item.model_dump()
    analysis = payload.pop("analysis", {}) or {}
    analysis.setdefault("neighbor_count", neighbor_count)
    return ExplorerPoint(**payload, analysis=ExplorerSemanticSummary(**analysis))
```

This works but is fragile — it relies on `item.model_dump()` having the right keys and not having extra keys that `ExplorerPoint.__init__` won't accept.

**Recommendation:** `tighten` (P2) — use a typed constructor instead of dict unpacking. `PointArtifact` should map to `ExplorerPoint` via explicit field assignments, not blind dict spreading.

### Finding 4.4 — `StoryClusterDetail` contains `cluster_key` which is not stable
Already documented in Finding 1.4. From the contract perspective: `cluster_key` is in the API response model and the frontend type. Nothing in the API documentation warns consumers that this key is ephemeral and regenerated on each cluster rebuild. If any client builds a link or bookmark using `cluster_key`, it will silently break after the next cluster rebuild.

**Recommendation:** `document` in the API contract comment that `cluster_key` is not a stable external identifier.

### Finding 4.5 — Test coverage is adequate for happy path, weak on contract guarantees
**Severity: P2 | Confidence: medium | Evidence: `test_api_clusters.py`, `test_api_semantic_explorer.py`**

The API tests use SQLite in-memory with seeded fixture data and exercise the happy path well. They do not:
- Test response schema stability (no JSON schema validation against OpenAPI spec)
- Test empty results for each filter combination
- Test error cases (invalid cluster_id, missing projection data)
- Assert that all required response fields are present with the correct types

The semantic explorer tests recreate table DDL manually in SQLite (bypassing the ORM entirely) which means schema drift between test setup and production init SQL is possible and undetected.

**Recommendation:** `tighten` (P2) — add at minimum: (a) tests for 404 paths, (b) a schema-validation check against the contract models for at least one full response payload per endpoint, (c) consider testcontainers for semantic tests to use real Postgres.

---

## Track 5 — Simplification / De-scope Opportunities

### "Could remove tomorrow if disciplined"

| Item | Evidence | Risk of removal |
|---|---|---|
| `INIT_SQL_TEMPLATE` (keep `ADDITIVE_SCHEMA_SQL` or vice versa) | Byte-for-byte identical | Zero |
| `scripts/run_scheduled.sh` + Makefile targets `scheduler-once`, `scheduler-dry-run`, `status`, `tail-log` | Legacy scrape-only wrapper; newer wrappers cover the same ground plus analysis | Low — needs cron audit first |
| `ExplorerArticleDetail.semantic_summary` field in API response | Duplicates `point.analysis` | Low — single endpoint change |
| `scripts/generate_comparison_summary.py` | Orphan script, no Makefile target, hardcoded date | Low — tests use the module directly |

### "Not worth carrying yet"

| Item | Evidence | Why |
|---|---|---|
| `entity_aliases` table + write path | Write-only; no read path in API or clustering | Premature infrastructure for disambiguation that doesn't exist |
| `article_enrichment_runs` table | Write-only; no operational read path | DB noise; if needed, replace with metrics file logging |
| Comparison summary module (`src/core/comparison_summary.py`) | Only consumed by tests; no operational surface | Valid concept but not integrated into any live flow |
| Per-article entity alias accumulation loop | O(entities × aliases) DB writes per enrichment, serves no current read | Can be deferred until alias-based disambiguation is implemented |

### What the leanest credible architecture looks like right now

If you stripped the project to what it actually needs to deliver its current product value:

**Keep as-is:**
- `articles` table and CRUD (source of truth)
- `tags`, `article_analysis`, `article_tags`, `entity_mentions` (enrichment pipeline)
- `entities` table (referenced by cluster read-side)
- `story_clusters`, `cluster_members`, `cluster_entities` (the cluster product)
- `article_embeddings` (expensive to rebuild; keep)
- `article_projections`, `semantic_point_analysis`, `semantic_clusters` (semantic explorer)
- `run_stories_refresh.sh`, `run_explorer_refresh.sh` (the two real scheduler paths)
- All API contracts and frontend

**Remove or defer:**
- `article_enrichment_runs` (no read path)
- `entity_aliases` write path (no read path)
- `run_scheduled.sh` and its Makefile targets (legacy)
- Duplicate `INIT_SQL_TEMPLATE` constant
- SQLite compat branch in `dbstore.py`
- `ExplorerArticleDetail.semantic_summary` duplication
- `generate_comparison_summary.py` script

This gives you a tighter codebase with no functional regression.

---

## Recommended Execution Order (Post-Audit)

### Phase 0 — Immediate (P0)

1. **Merge `INIT_SQL_TEMPLATE` and `ADDITIVE_SCHEMA_SQL`** — same SQL, one constant. 5-minute fix.

### Phase 1 — Important structural fixes (P1)

2. **Wrap cluster rebuild in a transaction with explicit rollback** — prevents empty cluster state on failed rebuild.
3. **Remove `run_scheduled.sh` and its Makefile targets** — but first: audit any production cron configs to ensure nothing is using `scheduler-once`. Replace with a comment pointing to `stories-refresh-once`.
4. **Remove `article_enrichment_runs` or wire it to a real read path** — if monitoring enrichment cost/history is a real need, add a `make enrichment-report` target or admin API endpoint. Otherwise drop the table.
5. **Move SQLite compat branch to test layer** — `_session_dialect_name()` and `_explorer_published_at_sql()` should not exist in production code.

### Phase 2 — Cleanup / clarity (P2)

6. **Document `articles.tags` as raw scraper capture** — add a code comment.
7. **Defer or remove `entity_aliases` write path** — document what triggers its re-introduction.
8. **Standardize `SCORE_THRESHOLD` across Makefile and `run_stories_refresh.sh`** — or document why they differ.
9. **Remove `ExplorerArticleDetail.semantic_summary`** — simplify the article detail response.
10. **Remove `generate_comparison_summary.py`** — or give it a Makefile target and a real operational home.
11. **Document `cluster_key` as ephemeral** — in both the API contract and the frontend type.

### Phase 3 — Optional improvements (P3)

12. Add testcontainers/Postgres fixtures for semantic API tests (remove SQLite workaround entirely).
13. Consider OpenAPI → TS codegen to enforce contract sync.
14. Add enrichment run metrics to a file-based metrics export (replace the DB table with a logs file if the operational need is real).
15. Consider explicit `published_at` indexing on the `articles` table for analysis pipeline window queries (not currently an issue, worth tracking if article volume grows significantly).

---

## Definition of Success

After implementing Phase 0 + Phase 1, the following questions should have clean answers:

- **Why does each DB table exist?** — All remaining tables have documented roles. `article_enrichment_runs` is either read-wired or removed.
- **Which tables are durable truth and which are rebuild artifacts?** — Documented above; `articles` and `article_embeddings` are durable, everything else is rebuildable.
- **Which codepaths are legacy and safe to kill?** — `run_scheduled.sh`, `INIT_SQL_TEMPLATE` duplicate, SQLite branch.
- **Where are the real pipeline boundaries?** — Scrape → Persist → Enrich → Cluster (stories) | Embed → Project → Analyze (semantic). No hidden coupling beyond the shared `articles` table.
- **Which API/frontend contracts are stable?** — All except `cluster_key` (document as ephemeral) and `semantic_summary` (remove).
- **What should be simplified before scaling?** — Cluster rebuild transaction safety, legacy scheduler removal, dead write paths.

