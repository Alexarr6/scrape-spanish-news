# RESULTS.md

## 2026-03-22 — raw editorial payload normalization implementation for `spain-news-bias-scraper`

**Role:** implementer  
**Outcome:** ✅ Complete  
**Scope:** decouple model-facing editorial generation from strict final persistence validation

### What I accomplished
Implemented the architect-approved contract split for editorial analysis:
- kept `ArticleEditorialAnalysisPayload` as the strict final persistence contract
- added `ArticleEditorialAnalysisRawPayload` as the bounded model-facing/raw contract
- added deterministic normalization in `src/analysis/editorial_normalization.py`
- changed the LLM client flow to:
  - parse raw JSON
  - normalize deterministically
  - validate the normalized result against the strict final payload
  - return/persist only the validated final payload
- changed the provider-facing JSON schema to a bounded raw schema that tolerates:
  - alias fields like `ideological_bias_framing`
  - nested `tone_dimensions`
  - top-level/global `confidence`
  - string-form `evidence_spans`
  - off-vocabulary article types and framing labels
- kept the conservative stance: ambiguous mappings degrade to `unclear` or safe defaults rather than fake certainty
- preserved debug visibility by recording normalization warnings in failure artifacts
- added regression coverage for representative raw payload shapes, including the captured minimax-style artifact form
- hotfixed the remaining article `2924` failure by accepting object-form `ideological_bias_framing` at the raw layer and normalizing the observed Spanish response shape (`noticia_accidente`, `bajo`/`baja`, `span`, `titular`/`hechos`) conservatively into the strict final payload

### Files changed
- `src/analysis/contracts.py`
- `src/analysis/editorial_normalization.py`
- `src/analysis/llm_client.py`
- `src/analysis/pipeline.py`
- `tests/test_editorial_analysis_contracts.py`
- `tests/test_editorial_analysis_pipeline.py`
- `tests/test_editorial_normalization.py`
- `STATUS.md`
- `RESULTS.md`

### Verification
Commands run:
- `~/.local/bin/uv run --project . ruff check src/analysis/contracts.py src/analysis/editorial_normalization.py src/analysis/llm_client.py src/analysis/pipeline.py tests/test_editorial_analysis_contracts.py tests/test_editorial_analysis_pipeline.py tests/test_editorial_normalization.py`
- `~/.local/bin/uv run --project . pytest -q tests/test_editorial_analysis_contracts.py tests/test_editorial_analysis_pipeline.py tests/test_editorial_normalization.py tests/test_api_editorial.py`
- `~/.local/bin/uv run --project . python - <<'PY' ... normalize captured article-2800 minimax artifact ... PY`

Results:
- `ruff check`: passed
- `pytest`: `16 passed`
- bounded manual artifact verification: passed
  - captured minimax payload normalized to `news_report`, `bias_label=unclear`, `tone_emotional=calm`, `sensationalism=low`, `3` evidence spans, with explicit normalization warnings for dropped unmapped framing labels

### Remaining risks / follow-ups
- deterministic mapping coverage is intentionally conservative; more provider quirks may still need explicit alias tables later
- the provider-facing raw schema is looser by design, so the normalizer is now the critical seam and should keep getting regression fixtures when new model drift appears
- this pass does not yet add provider/model allowlisting as an ops overlay
- I did not run a live `make analyze-editorial ...` call because that would depend on operator API credentials/runtime availability; the real captured artifact path was used instead for bounded manual verification

### Git / rollback
- Branch: `iter/004`
- Commit(s): pending final atomic commit(s)
- Rollback hint after commit: `git log --oneline -n 5`

## 2026-03-22 — architect review of editorial-analysis schema portability for `spain-news-bias-scraper`

**Role:** architect  
**Outcome:** ✅ Complete  
**Scope:** investigation/design only, no implementation

### What was accomplished
Performed a repo-grounded architecture/debug review of the repeated editorial-analysis validation failures still occurring after the robustness remediation pass.

Reviewed:
- current client/pipeline/contracts
- operator/docs/planning artifacts
- focused tests
- the captured failure artifact for article `2800` on `minimax/minimax-m2.7`
- OpenRouter structured-output compatibility guidance

### Main finding
The remaining failures are **not primarily a parsing bug anymore**.

The real blocker is architectural:
- the pipeline currently asks OpenRouter-routed models/providers to emit the **final persistence schema directly**
- multiple providers/models instead emit parseable JSON in their **own analysis schema/ontology**
- the repo has no deterministic normalization layer between raw LLM output and the strict final `ArticleEditorialAnalysisPayload`
- result: semantically useful outputs are discarded as `payload_validation_failed`

### Recommendation
Add a two-layer editorial contract:
- **raw/model-facing payload** for portable generation
- **strict final normalized payload** for persistence/API use

Recommended flow:
- raw LLM payload
- deterministic normalization/mapping
- final strict validation
- persistence

Keep provider/model allowlisting only as an operational guardrail, not as the main fix.

### Files changed
- `ARCH_REVIEW.md`
- `STATUS.md`
- `RESULTS.md`

### Explicit next implementation scope
1. add a raw editorial payload model
2. add deterministic normalization code for field aliases, vocab mapping, evidence shaping, and conservative abstention to `unclear`
3. update the pipeline to normalize before final validation/persistence
4. add regression tests, especially for the captured article-2800 minimax artifact shape
5. update docs/runbook to explain raw-vs-final flow

### Important “do not do this” guidance
- do **not** just weaken the final schema until junk slips through
- do **not** rely on prompt tightening alone
- do **not** hide normalization inside another fuzzy LLM call by default

---

## 2026-03-22 — editorial analysis robustness remediation for `spain-news-bias-scraper`

**Role:** implementer  
**Outcome:** ✅ Complete  
**Scope:** bounded backend hardening for editorial-analysis provider reliability

### What I accomplished
Implemented the approved robustness pass for the editorial-analysis pipeline:
- added a structured attempt/result envelope around OpenRouter editorial calls
- introduced normalized failure classes for provider rejection, parse failures, validation failures, refusals, and unknown response shapes
- made `request_count` honest by counting API-accepted attempts before parse/validation
- added additive failure counters for provider rejection, parse failure, and validation failure
- added a bounded fallback from strict `response_format=json_schema` to prompt-only JSON text mode
- persisted failed-response debug artifacts under `.artifacts/editorial-analysis/`
- kept failure reasons operator-visible by prefixing them with the normalized failure class
- added focused regression tests for the new failure paths and fallback behavior

### Files changed
- `src/analysis/llm_client.py`
- `src/analysis/pipeline.py`
- `src/analysis/contracts.py`
- `tests/test_editorial_analysis_pipeline.py`
- `docs/operator-guide/editorial-analysis-manual-test.md`
- `STATUS.md`

### 2026-03-22 — post-pass hotfix for OpenRouter/OpenAI SDK usage objects

**Outcome:** ✅ Complete  
**Scope:** minimal regression fix after the editorial robustness pass

What changed:
- normalized `response.usage` handling in `src/analysis/llm_client.py`
- editorial/enrichment usage parsing now accepts:
  - plain dicts
  - pydantic-like objects exposing `model_dump()`
  - SDK-style objects with `prompt_tokens` / `completion_tokens` / `total_tokens` attributes
  - missing / `None`
- added focused regression coverage in `tests/test_llm_client_usage.py`
- updated `STATUS.md` for the hotfix slice

Verification:
- `~/.local/bin/uv run --project . pytest -q tests/test_llm_client_usage.py tests/test_editorial_analysis_pipeline.py` → passed (`6 passed`)
- `~/.local/bin/uv run --project . ruff check src/analysis/llm_client.py tests/test_llm_client_usage.py` → passed

### Verification run
Commands run:
- `PYTHONPATH=.venv/lib/python3.11/site-packages .venv/bin/ruff check src/analysis/llm_client.py src/analysis/pipeline.py tests/test_editorial_analysis_pipeline.py`
- `PYTHONPATH=.venv/lib/python3.11/site-packages python3 -m pytest -q tests/test_api_editorial.py tests/test_editorial_analysis_pipeline.py`

Results:
- `ruff check`: passed
- `pytest`: `7 passed`

### Operator-facing behavior changes
- strict structured mode is still preferred first
- if strict mode is schema-rejected or returns unusable content, the client now retries once in fallback JSON-text mode
- failed rows now write a debug artifact in `.artifacts/editorial-analysis/`
- `failure_reason` now starts with the normalized failure class and includes the artifact path when present
- metrics now distinguish:
  - `request_count`
  - `provider_rejected_count`
  - `parse_failed_count`
  - `validation_failed_count`

### Remaining risks / notes
- the fallback path depends on provider willingness to return plain JSON text; it is bounded and safer, but not magic
- artifact paths are stored in truncated `failure_reason`, so very long provider errors may lose some tail detail; the artifact is the real debug source
- this pass did not add DB columns like `failure_class`; taxonomy remains visible through `failure_reason` plus artifact contents
- manual verification against the three reported real-world models is still recommended before calling any provider “stable”

### Git / rollback
- Branch: `iter/004`
- Commit(s): pending final atomic commit for this remediation pass
- Rollback hint after commit: `git log --oneline -n 5`

## 2026-03-21 — editorial analysis phase 1 implementation for `spain-news-bias-scraper`

**Role:** implementer  
**Outcome:** ✅ Complete for scoped phase 1  
**Scope:** dedicated article-level editorial analysis only

---

## What was added

### Persistence / ORM
- Added new dedicated ORM model and table: `article_editorial_analysis`
- Kept this additive and separate from existing `article_analysis`
- Stored bounded JSON payloads in:
  - `framing_devices_json`
  - `evidence_spans_json`
- Included operational/versioning fields for status, model, prompt/schema version, content hash, and timestamps

### Contracts / validation
- Added strict editorial contracts in `src/analysis/contracts.py`
- Added dedicated evidence span model
- Added semantic guards beyond raw JSON parsing, including:
  - score/confidence bounds
  - no duplicate framing devices
  - at least one evidence span
  - `unclear` bias requiring near-neutral/low-confidence outputs
  - pragmatic consistency checks for tone/opinionatedness/certainty

### Prompt / schema / OpenRouter client
- Added dedicated prompt builder: `build_editorial_analysis_prompt(...)`
- Added dedicated strict JSON schema builder: `editorial_analysis_json_schema()`
- Added dedicated OpenRouter client method: `analyze_editorial(...)`
- Kept this path separate from the existing enrichment prompt/schema/client flow

### Pipeline / job
- Added dedicated `EditorialAnalysisPipeline`
- Added `scripts/analyze_editorial.py`
- Added Make target: `make analyze-editorial DATABASE_URL=...`
- Implemented:
  - recent article loading
  - content-hash skip behavior
  - OpenRouter call
  - strict payload validation
  - persistence into the new table
  - simple failed/completed status handling

### Read surface
- Added minimal article-level read endpoint:
  - `GET /api/v1/editorial-analysis/{article_id}`
- Did **not** add cluster-level ideological summaries

---

## Validation run

Ran focused checks only:
- `ruff check src/analysis/contracts.py src/analysis/llm_client.py src/analysis/orm_models.py src/analysis/pipeline.py src/analysis/readside.py src/api/app.py src/api/contracts/editorial.py src/api/v1/editorial.py scripts/analyze_editorial.py tests/test_editorial_analysis_contracts.py tests/test_editorial_analysis_pipeline.py tests/test_api_editorial.py`
- `pytest -q tests/test_editorial_analysis_contracts.py tests/test_editorial_analysis_pipeline.py tests/test_api_editorial.py tests/test_api_articles.py tests/test_openrouter_extraction_contract.py`

Result:
- `13 passed`
- lint passed on touched files

---

## Caveats / deferred items

Still intentionally out of scope:
- cluster/story ideological rollups
- media-level comparison endpoints
- replacing or refactoring current `article_analysis.article_type`
- frontend polish for this feature
- migration framework overhaul

One practical caveat:
- failed editorial rows are persisted with `analysis_status="failed"` plus `failure_reason`, using placeholder `unclear` values for required classification columns so the row stays storable without inventing fake successful analysis

---

## Previous result entries

### 2026-03-21 — planner handoff for editorial analysis feature

**Role:** planner  
**Outcome:** ✅ Complete  
**Scope:** planning only, no implementation

---

## What was accomplished

Created a concrete implementation plan for adding **LLM-driven article editorial analysis** to `spain-news-bias-scraper`.

The plan was grounded in:
- `docs/contracts/editorial-analysis-v1.md`
- `docs/contracts/editorial-analysis-prompt-v1.md`
- the current OpenRouter client path in `src/analysis/llm_client.py`
- the current analysis ORM/contracts/pipeline stack
- current FastAPI read-side structure and CRUD style

Updated:
- `PLAN.md`
- `STATUS.md`
- `RESULTS.md`

No implementation work was performed.

---

## Planner recommendations in one shot

### 1) Persistence / naming
- Add a new dedicated table and ORM model: **`article_editorial_analysis`**
- Keep **one row per article** in v1
- Do **not** stuff editorial bias/tone fields into the existing `article_analysis` table
- Keep `framing_devices` and `evidence_spans` as bounded JSON fields in v1

### 2) OpenRouter integration
- Add a separate editorial payload contract and schema instead of extending `ArticleEnrichmentPayload`
- Add a dedicated prompt builder + client method for editorial analysis
- Reuse OpenRouter `response_format={type: json_schema}` style, then validate with Pydantic and extra semantic guards
- Treat the prompt/template as **versioned core infrastructure**

### 3) Pipeline design
- Build a **new dedicated editorial-analysis pipeline/job**
- Do not fold it into the current enrichment job in v1
- Use content-hash skip logic and explicit status/failure fields
- Do **not** add a heuristic fallback for ideology/tone classification

### 4) Schema evolution
- The repo currently relies on ORM registration + `Base.metadata.create_all()` via init scripts
- Plan assumes additive schema evolution in that existing style
- No default full-corpus backfill on first release; start with bounded recent windows

### 5) API surface
- Start with article-level read access:
  - `GET /api/v1/articles/{article_id}/editorial-analysis`
- Optionally add list/filter reads later
- Defer cluster-level ideological rollups; they need explicit aggregation rules and are easy to bullshit

### 6) Testing / validation
- Add contract tests, JSON schema tests, prompt/version tests, client parsing tests, DB persistence tests, and API route tests
- Add manual review fixtures for ambiguous vs obvious cases before any broader backfill

---

## Recommended atomic implementation order

1. editorial Pydantic models + validators
2. prompt/template runtime infrastructure
3. dedicated OpenRouter client method
4. ORM model + schema init support
5. dedicated editorial pipeline/CLI target
6. article-level read API
7. optional cluster detail integration
8. later operator/backfill controls

---

## Important decisions locked by this planner pass

- **Best table name:** `article_editorial_analysis`
- **Best v1 architecture:** dedicated pipeline, not enrichment-job overloading
- **Best evidence modeling:** JSON in v1, not child-table normalization yet
- **Best prompt handling:** explicit versioned asset/module, not ad hoc inline strings
- **Best read-side scope:** article-level first, cluster aggregation later if ever justified

---

## Relevant repo details for implementer

- Existing OpenRouter integration already uses strict JSON schema mode in `src/analysis/llm_client.py`
- Existing topical enrichment uses `ArticleEnrichmentPayload` and writes to `article_analysis`
- Existing schema init is driven by `Base.metadata.create_all()` via `scripts/init_analysis_schema.py`
- Existing CRUD style is explicit, lightweight, and a good fit for article-level editorial reads
- Current clustering depends on existing `article_analysis.article_type`, so any unification of article-type sources should be treated as a later deliberate follow-up, not part of the first feature slice

---

## Previous result entries

### 2026-03-21 — cleanup implementation for `spain-news-bias-scraper`

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
