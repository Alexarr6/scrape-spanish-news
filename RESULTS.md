# RESULTS.md

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

### Remaining risks / follow-ups
- warning details are currently surfaced in artifacts and run metrics, not persisted as first-class DB columns
- `unclear` reasoning is now much more explainable, but API/read-side exposure of those reason classes is still a possible next slice if operators want them outside artifacts
- strict structured-output mode is still an opportunistic first attempt rather than a reliable foundation on this route
- I did not run a live provider-backed editorial batch because that would require real API credentials plus a real Postgres target; pretending otherwise would be bullshit

### Git / rollback
- Branch: `iter/004`
- Commit(s): pending final atomic commit(s)
- Rollback hint after commit: `git log --oneline -n 5`

## 2026-03-22 — architect re-review of editorial-analysis pipeline after real operator testing

**Role:** architect  
**Outcome:** ✅ Complete  
**Scope:** investigation/design only, no implementation

### What I accomplished
Performed a second architecture pass using the updated code, tests, and the new real operator artifacts from `.artifacts/editorial-analysis/`.

Reviewed:
- `src/analysis/contracts.py`
- `src/analysis/editorial_normalization.py`
- `src/analysis/llm_client.py`
- `src/analysis/pipeline.py`
- `scripts/analyze_editorial.py`
- `Makefile`
- editorial contracts/docs/operator guide
- planner/status/result artifacts
- focused editorial tests
- real failure artifacts for articles `2924`, `2925`, `2926`, `2969`, `2927`, `2928`
- relevant OpenAI structured-output/docs behavior for schema requirements and content-shape assumptions

### Key findings
1. **The raw layer is still too strict.**  
   The repo correctly separated raw generation from final persistence, but the current raw contract still rejects ordinary provider variation before repair/normalization can act.

2. **Most remaining failures are shape-repair failures, not useless-model failures.**  
   Real artifacts show parseable, semantically useful JSON failing because of:
   - overlong `evidence_spans`
   - string confidence labels like `moderate`
   - object-form `rationale`
   - object-form `ideological_bias_framing`
   - object-form `framing_devices`

3. **`unclear` is overloaded.**  
   The operator currently cannot tell whether `unclear` means the article truly had weak editorial signal, or the pipeline lost information during mapping/repair.

4. **`REPROCESS` semantics are confusing.**  
   With default `status=pending`, `reprocess` changes skip behavior but does not widen selection, so operator expectation and actual behavior diverge.

5. **Reporting is still too shallow.**  
   Current metrics say pass/fail, but they do not explain fallback success, truncation, dropped fields, normalization warnings, or why rows degraded to `unclear`.

### Revised architecture recommendation
Recommended pipeline:

`raw capture -> shape repair/coercion -> semantic normalization -> strict final validation -> persistence/reporting`

Specific recommendations:
- widen raw capture to accept bounded but variable provider shapes
- add an explicit repair/coercion stage before semantic normalization
- move list-length enforcement like `evidence_spans <= 6` out of raw capture and into repair/final stages
- coerce confidence labels conservatively instead of failing rows
- extract text from rationale objects and framing/bias objects before normalization
- keep the final strict payload authoritative for persistence
- report whether `unclear` came from weak signal or mapping/data-loss degradation
- fix `--reprocess` semantics so selection behavior matches human expectations

### Files changed
- `ARCH_REVIEW.md`
- `PLAN.md`
- `STATUS.md`
- `RESULTS.md`

### Recommended implementation scope and order
1. widen `ArticleEditorialAnalysisRawPayload`
2. add explicit shape-repair/coercion stage
3. make normalization emit warning classes and `unclear` reasons
4. fix CLI/pipeline `REPROCESS` + effective selection behavior
5. extend metrics/artifacts for fallback success, truncation, dropped fields, warning-heavy rows, and `unclear` causes
6. add regression tests from the observed artifacts

### Critical tradeoffs / unresolved choices
- raw capture should be loose on shape variability but still bounded on total size and pathological junk
- strict structured outputs can remain a first attempt, but they should not be treated as the trusted production path on this route
- DB persistence of repair warnings is optional for the next slice; artifacts + run summaries are enough to unblock the architecture fix
- sports/non-political content may still legitimately normalize to many `unclear` values, but the operator must be able to distinguish that from mapping loss

### Verification
No code implementation was performed. Verification was architectural and artifact-based:
- repo code/docs/test inspection
- artifact inspection of real failing rows
- lightweight external docs review for structured-output/schema behavior

---

## Previous result entries

## 2026-03-22 — minimal raw-payload hotfix for article-2925-style editorial fallback payloads

**Role:** implementer  
**Outcome:** ✅ Complete  
**Scope:** accept and conservatively normalize the newly observed fallback raw shape without redesigning the pipeline

### What I accomplished
Implemented a minimal hotfix for the observed raw payload validation failure in the editorial normalization flow:
- widened the raw contract so `rationale` can arrive as either a string or an object
- normalized object-form `rationale` conservatively using summary/description-style text fields
- taught the normalizer to extract bias labels from object-form `ideological_bias_framing` payloads that use keys like `bias`
- taught the normalizer to accept object-form `framing_devices` entries and map their `device`/`description` content conservatively into the existing framing taxonomy
- added narrow support for the exact nested tone variants observed (`emotional_valence.valence`, `sensationalism.level`, `alarmism.level`)
- added focused regression coverage for an article-2925-style payload shape
- updated status notes without changing the broader architecture

### Files changed
- `src/analysis/contracts.py`
- `src/analysis/editorial_normalization.py`
- `tests/test_editorial_analysis_contracts.py`
- `tests/test_editorial_normalization.py`
- `STATUS.md`
- `RESULTS.md`

### Verification
Commands run:
- `~/.local/bin/uv run --project . ruff check src/analysis/contracts.py src/analysis/editorial_normalization.py tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py`
- `~/.local/bin/uv run --project . pytest -q tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py`

Results:
- `ruff check`: passed
- `pytest`: `12 passed`

### Remaining risks / follow-ups
- this is intentionally narrow and only covers the exact newly observed shapes, not arbitrary nested provider ontologies
- rationale object extraction is conservative and text-first; if providers start returning more exotic structured rationales, more aliases may be needed later
- framing-device object handling prefers `device` and then `description`; unmapped variants still drop safely rather than guessing

### Git / rollback
- Branch: `iter/004`
- Commit(s): pending final atomic commit
- Rollback hint after commit: `git log --oneline -n 5`

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