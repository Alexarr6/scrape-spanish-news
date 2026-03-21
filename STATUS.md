- State: EDITORIAL_PHASE1_IMPLEMENTED
- Current phase: article-level editorial analysis phase 1 implemented for `spain-news-bias-scraper`
- Last update: 2026-03-21 UTC

## Editorial analysis phase 1 implementation

### What landed
- New dedicated ORM table/model: `article_editorial_analysis`
- New strict editorial Pydantic contracts with semantic validation guards
- New dedicated editorial prompt builder + strict JSON schema generator
- New dedicated OpenRouter client method: `analyze_editorial(...)`
- New separate editorial pipeline/job: `EditorialAnalysisPipeline`
- New CLI entrypoint: `scripts/analyze_editorial.py`
- New Make target: `make analyze-editorial DATABASE_URL=...`
- New minimal read API: `GET /api/v1/editorial-analysis/{article_id}`
- Focused tests for contracts, persistence/pipeline behavior, and API read path

### Hard constraints respected
- Editorial analysis was **not** folded into the existing enrichment flow
- Existing `article_analysis.article_type` usage was left in place for clustering
- No cluster/story ideological aggregation was added
- No unrelated cleanup/refactor was bundled into this slice

### Validation run
- `ruff check` on touched editorial files: passed
- `pytest -q tests/test_editorial_analysis_contracts.py tests/test_editorial_analysis_pipeline.py tests/test_api_editorial.py tests/test_api_articles.py tests/test_openrouter_extraction_contract.py`: passed (`13 passed`)

### Deferred by design
- Cluster/story ideological rollups
- Media-level comparison endpoints
- Unifying editorial `article_type` with current `article_analysis.article_type`
- Frontend/editorial UI polish
- Broader migration framework changes

## Scope completed in this planning pass

Prepared an implementation-ready plan for adding **article-level editorial analysis** using OpenRouter, based on:
- `docs/contracts/editorial-analysis-v1.md`
- `docs/contracts/editorial-analysis-prompt-v1.md`
- existing analysis / ORM / OpenRouter / API stack

## Planner recommendations

### Recommended persistence shape
- Add a new dedicated ORM table: `article_editorial_analysis`
- Keep **one row per article** in v1
- Do **not** overload existing `article_analysis`
- Keep `framing_devices` and `evidence_spans` as bounded JSON fields in v1

### Recommended OpenRouter integration
- Add a separate editorial payload contract and JSON schema
- Add a dedicated prompt builder and client method
- Use strict OpenRouter `json_schema` response mode plus Pydantic validation
- Treat the prompt/template as versioned infrastructure, not inline glue text

### Recommended pipeline shape
- Add a **new dedicated editorial-analysis job/pipeline**
- Do not fold it directly into current topical enrichment flow in v1
- Use content-hash skip logic and explicit status/failure handling
- Do not invent a heuristic fallback for bias/tone classification

### Recommended API shape
- Start with article-level read access:
  - `GET /api/v1/articles/{article_id}/editorial-analysis`
- Add optional list/filter endpoints later if needed
- Defer cluster-level ideological aggregation; it is underspecified and easy to get wrong

## Migration / schema call

- The repo currently uses ORM registration + `Base.metadata.create_all()` via init scripts, not Alembic
- Plan assumes additive schema evolution in that style
- No full historical backfill should happen by default on first implementation

## Key open design calls resolved by planner

1. **Naming**: recommend `article_editorial_analysis` over alternatives because `article_analysis` already means enrichment/taxonomy work in this repo
2. **Pipeline placement**: recommend a separate job, not silent expansion of existing enrichment payload
3. **Evidence modeling**: keep as JSON in v1, normalize later only if there is a proven read/write need
4. **Prompt handling**: prompt/template must be explicit, versioned, and test-covered
5. **Cluster rollups**: defer; article-level output is the real v1 contract

## Atomic implementation slices proposed

1. editorial contract models + validators
2. prompt/template infrastructure
3. dedicated OpenRouter client method
4. ORM model + schema init coverage
5. editorial pipeline/CLI target
6. article-level read API
7. optional cluster detail integration
8. later operator/backfill controls

## Files updated in this pass
- `PLAN.md`
- `STATUS.md`
- `RESULTS.md`
