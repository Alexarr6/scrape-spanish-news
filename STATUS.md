- State: DONE
- Current phase: implementer pass completed on `iter/004`; editorial analysis now uses explicit raw capture -> shape repair/coercion -> semantic normalization -> strict final validation, with saner `reprocess` selection semantics and warning-aware reporting
- Last update: 2026-03-22 UTC

## Implementer completion — editorial-analysis robustness pass landed

Implemented the architect-approved hardening slice without article-id hacks.

### What changed
- widened `ArticleEditorialAnalysisRawPayload` so recoverable provider drift does not die at the raw boundary
- added an explicit shape-repair/coercion stage in `src/analysis/editorial_normalization.py`
- kept semantic normalization separate from repair and preserved the strict final payload as the authority
- added repair/normalization warning classes plus explicit `unclear` reason signals
- expanded run metrics/artifact detail for fallback success, dropped fields, truncation, and warning-heavy successful rows
- fixed `--reprocess` semantics so default pending selection widens to `status=any` unless the operator explicitly targets article ids
- updated CLI dry-run reporting to show effective selection status and counts by current row status
- added regression coverage for object rationale, object ideological bias, confidence-label coercion, overlong evidence, framing-device objects, nested tone structures, and fallback-success warning reporting

### Bounded verification completed
- `~/.local/bin/uv run --project . ruff check src/analysis/contracts.py src/analysis/editorial_normalization.py src/analysis/llm_client.py src/analysis/pipeline.py scripts/analyze_editorial.py tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py tests/test_editorial_analysis_pipeline.py`
- `~/.local/bin/uv run --project . pytest -q tests/test_api_editorial.py tests/test_editorial_analysis_contracts.py tests/test_editorial_normalization.py tests/test_editorial_analysis_pipeline.py`

Result:
- `ruff check`: passed
- `pytest`: `19 passed`
- bounded operator-style CLI verification against a temp sqlite URL: intentionally failed fast with `ValueError("Postgres-only mode: db URL must start with 'postgresql'")`, which is expected under the repo's DB policy and therefore not a valid end-to-end operator path without a real Postgres target

## Architect re-review completion — remaining editorial failures are now well-localized

A deeper architecture pass has been completed using the new real operator artifacts and recent hotfix/test state.

### Main conclusion
The repo fixed the first half of the problem, but not the second.

What is now clearly true:
- separating raw generation from strict final persistence was the right move
- honest request accounting and strict->fallback retry were also correct
- **but the current raw layer is still too narrow**
- it is rejecting recoverable provider variation before repair/normalization can salvage it

That is why the pipeline now shows this awkward behavior:
- single runs sometimes succeed
- fallback often returns parseable, useful JSON
- batch runs still fail on raw validation details like overlong evidence lists, object rationales, object framing structures, and string confidence labels
- successful rows often land in `unclear`, but operator reporting does not explain whether that is genuine abstention or mapping/data-loss degradation

### Real operator/artifact findings carried into the revised recommendation
Observed directly in `.artifacts/editorial-analysis/`:
- article `2924`: object-form `ideological_bias_framing`
- article `2925`: object-form `rationale`
- article `2926`: 9-item `evidence_spans`
- article `2969`: 7-item `evidence_spans`
- article `2927`: 10-item string `evidence_spans`
- article `2928`: fallback JSON with `confidence="moderate"` and useful but off-ontology political framing

Interpretation:
- these are mostly **shape-repair** cases, not semantic nonsense cases
- the raw layer should capture them
- a distinct repair/coercion phase should handle them
- only then should semantic normalization and final validation decide what survives

### Revised architecture recommendation
The recommended editorial pipeline is now:

`raw capture -> shape repair/coercion -> semantic normalization -> strict final validation -> persistence/reporting`

Key policy implications:
- raw capture should accept bounded but variable shapes
- overlong evidence lists should truncate with warnings, not fail at capture time
- confidence labels like `moderate` should coerce conservatively
- object rationales / ideological framing / framing devices should be repaired before semantic mapping
- final strict payload remains the persistence gatekeeper

### Operator-facing conclusion
Two operator issues are now explicit design targets, not incidental annoyances:

1. **`REPROCESS` semantics are confusing**
   - current default `status=pending` means `reprocess` does not widen selection
   - that makes `REPROCESS=1` appear ineffective unless the operator already knows the internal selection model
   - recommended fix: `--reprocess` should imply `status=any` unless status was explicitly passed

2. **`unclear` is overloaded**
   - some rows are genuinely weak-signal
   - others become `unclear` because mapping/repair dropped information
   - reporting must distinguish these cases

### Updated planning direction
`ARCH_REVIEW.md` and `PLAN.md` now call for the next implementer slice to focus on:
1. widening the raw editorial contract
2. adding an explicit shape-repair/coercion stage
3. making normalization warning-aware and reason-aware
4. fixing `REPROCESS` / selection semantics
5. improving metrics and artifacts so fallback success, truncation, dropped fields, and `unclear` reasons are visible
6. locking the observed failures into regression coverage

### Important non-recommendation
Do **not** spend the next pass mostly on prompt tweaks.
That would be cargo-cult nonsense.
The artifacts already show the model often returns usable JSON; the remaining issue is where the pipeline draws its boundaries and how little it tells the operator.
