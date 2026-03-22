# RESULTS.md

## 2026-03-22 — implementer pass for editorial diagnostics, applicability, and explainable `unclear`

**Role:** implementer  
**Outcome:** ✅ Complete  
**Scope:** bounded additive implementation of applicability, per-dimension statuses, diagnostics persistence, read-side exposure, aggregate metrics, and regression tests

### What I accomplished
- added persisted `editorial_applicability`, `editorial_applicability_reason`, `analysis_path`, and `diagnostics_json` fields on editorial-analysis rows
- extended normalization so the pipeline now classifies applicability, records per-dimension outcomes (`resolved`, `weak_signal_abstain`, `mapping_loss`, `provider_missing`, `out_of_domain`, `conflicted_signal`), and preserves non-canonical framing/tone hints in diagnostics
- threaded diagnostics through the LLM client success path and failure artifacts
- extended pipeline metrics so aggregate `unclear` can be explained by reason counts, dimension-status counts, applicability buckets, and preserved-signal summaries
- exposed diagnostics/applicability/path through read-side and API payloads
- added regression tests covering honest weak-signal abstention, mapping loss, provider-missing dimensions, fallback+mapping-loss persistence, and out-of-domain article classes

### Files changed
- `src/analysis/contracts.py`
- `src/analysis/editorial_normalization.py`
- `src/analysis/llm_client.py`
- `src/analysis/orm_models.py`
- `src/analysis/pipeline.py`
- `src/analysis/readside.py`
- `src/api/contracts/editorial.py`
- `scripts/analyze_editorial.py`
- `tests/test_editorial_normalization.py`
- `tests/test_editorial_analysis_pipeline.py`
- `tests/test_api_editorial.py`
- `STATUS.md`
- `RESULTS.md`

### Verification
Commands run:
- `~/.local/bin/uv run --project . ruff check src/analysis/contracts.py src/analysis/editorial_normalization.py src/analysis/llm_client.py src/analysis/pipeline.py src/analysis/readside.py src/api/contracts/editorial.py scripts/analyze_editorial.py tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py tests/test_editorial_analysis_pipeline.py tests/test_api_editorial.py`
- `~/.local/bin/uv run --project . pytest tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py tests/test_editorial_analysis_pipeline.py tests/test_api_editorial.py -q`

Results:
- `ruff check`: passed
- `pytest`: `20 passed`

### Remaining risks / follow-ups
- applicability heuristics are intentionally bounded and still heuristic; they likely need calibration on a larger reviewed corpus
- diagnostics are persisted in JSON on the main row rather than a separate table/child records; good enough now, but richer analytics may want normalization later
- repo still appears to have unrelated working-tree changes outside this task; commit only the bounded editorial-analysis slice

## 2026-03-22 — architect re-review of editorial `unclear` semantics, information loss visibility, and structured-output strategy

**Role:** architect  
**Outcome:** ✅ Complete  
**Scope:** design/review only, no implementation

### What I accomplished
Re-evaluated the editorial-analysis architecture against the operator’s real complaint: too many final fields land as `unclear`, and the system still does a poor job of showing whether that is honest abstention or pipeline loss.

Reviewed:
- `src/analysis/contracts.py`
- `src/analysis/editorial_normalization.py`
- `src/analysis/llm_client.py`
- `src/analysis/pipeline.py`
- `scripts/analyze_editorial.py`
- `Makefile`
- editorial contract/prompt/operator docs
- planner/status/result artifacts
- focused tests for contracts/normalization/pipeline/client usage
- failure artifacts including `2924`, `2925`, and `2928`
- OpenRouter/OpenAI structured-output docs relevant to provider compatibility and helper semantics

### Key findings
1. **The current problem is no longer mainly bad JSON.**  
   The pipeline now captures and repairs much more than before. The remaining trust problem is that the operator still cannot tell whether `unclear` is honest or lossy.

2. **`unclear` currently collapses four different realities.**  
   The system needs to distinguish:
   - honest weak-signal abstention
   - mapping loss / dropped signal
   - provider omission / malformed output
   - out-of-domain / low-editorial-value article classes

3. **The final schema is only partly too ambitious.**  
   The core fields are fine for first-pass article analysis. The unstable edge fields are mainly `tone_target` and `framing_devices`, which should be treated as compressed/derived summaries, not equally authoritative peers of the core dimensions.

4. **Diagnostics need to become first-class persisted data.**  
   Artifacts are helpful but insufficient. The system needs a diagnostics sidecar (or at least diagnostics JSON) preserving raw/repaired excerpts, dimension-level statuses, unmapped signals, dropped/truncated fields, applicability classification, and analysis path details.

5. **Structured-output helpers are not the main fix here.**  
   LangChain/OpenAI-style `with_structured_output(...)` / Pydantic helpers may improve code ergonomics or support allowlisted provider-specific fast paths, but they do not solve the main current issues on an OpenRouter mixed-model route. They would mostly move the same compatibility and semantic-compression failures somewhere else.

### Recommended architecture
Keep the existing broad pipeline:
- strict attempt
- fallback JSON text
- raw capture
- repair/coercion
- semantic normalization
- strict final validation

But add a second persistent product:
- **canonical final row** for filtering and aggregation
- **diagnostics sidecar** for auditability and operator trust

### Recommended next implementation order
1. add `editorial_applicability` (`full|limited|out_of_domain`) plus reason classification
2. add per-dimension outcome statuses such as `resolved`, `weak_signal_abstain`, `mapping_loss`, `provider_missing`, `out_of_domain`, `conflicted_signal`
3. persist diagnostics sidecar or compact diagnostics JSON
4. preserve unmapped framing/tone meaning instead of silently dropping it
5. extend metrics/CLI summaries so `unclear` is explainable in aggregate
6. add regression coverage proving the system distinguishes weak signal vs mapping loss vs provider omission vs out-of-domain

### Files changed
- `ARCH_REVIEW.md`
- `PLAN.md`
- `STATUS.md`
- `RESULTS.md`

### Explicit view on structured-output helper alternative
Blunt version:
- **No, switching to `with_structured_output(...)` / direct Pydantic native helpers is not the architectural answer here.**
- On this OpenRouter-routed mixed-model setup, provider compatibility is still flaky enough that helper-based native structured output would mostly wrap the same problems in nicer syntax.
- If used at all, it should be a future allowlisted fast path for known-good providers/models, not the default portable architecture.

### Verification
Verification was design/artifact/test-code based, not implementation-based:
- repo code/docs/tests inspected
- real failure artifacts inspected
- external documentation checked for structured-output compatibility assumptions

---

## Previous result entries

## 2026-03-22 — implementer pass for editorial-analysis shape repair, warning-aware normalization, and reprocess semantics

**Role:** implementer  
**Outcome:** ✅ Complete  
**Scope:** raw-shape permissiveness, explicit repair/coercion, operator-visible warning reporting, and `--reprocess` semantics cleanup

### What I accomplished
Implemented the architect-approved robustness slice for editorial analysis:
- widened the raw editorial contract to accept recoverable shape variation without failing too early
- added an explicit repair/coercion phase before semantic normalization
- kept semantic normalization separate from repair and left final strict validation intact
- added repair warnings, normalization warnings, dropped/truncated field reporting, and explicit `unclear` reason classes
- expanded run metrics so fallback success and warning-heavy successful rows are visible
- improved failure artifacts so each attempt can show repair warnings, truncation, dropped fields, fallback success, and final unclear reasons
- fixed `--reprocess` behavior so the effective default selection becomes `status=any` unless the operator is explicitly targeting article ids
- improved CLI selection output with effective status and per-status counts
- added regression tests covering the real observed shape families rather than article-specific hacks

### Files changed
- `src/analysis/contracts.py`
- `src/analysis/editorial_normalization.py`
- `src/analysis/llm_client.py`
- `src/analysis/pipeline.py`
- `scripts/analyze_editorial.py`
- `tests/test_editorial_analysis_contracts.py`
- `tests/test_editorial_normalization.py`
- `tests/test_editorial_analysis_pipeline.py`
- `docs/operator-guide/editorial-analysis-manual-test.md`
- `STATUS.md`
- `RESULTS.md`

### Verification
Commands run:
- `~/.local/bin/uv run --project . ruff check src/analysis/contracts.py src/analysis/editorial_normalization.py src/analysis/llm_client.py src/analysis/pipeline.py scripts/analyze_editorial.py tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py tests/test_editorial_analysis_pipeline.py`
- `~/.local/bin/uv run --project . pytest -q tests/test_api_editorial.py tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py tests/test_editorial_analysis_pipeline.py`
- `tmpdb=$(mktemp /tmp/editorial-cli-XXXXXX.db) && ~/.local/bin/uv run --project . python3 scripts/analyze_editorial.py --db-url sqlite:///$tmpdb --dry-run --days-back 2 --limit 5 --reprocess`

Results:
- `ruff check`: passed
- `pytest`: `19 passed`
- bounded CLI verification: expected fast failure with `ValueError("Postgres-only mode: db URL must start with 'postgresql'")`; this confirms the repo still enforces Postgres-only operator paths, so a true operator-style dry run needs a real Postgres target
