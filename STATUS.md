- State: DONE
- Current phase: implementer pass completed on `iter/004`; editorial-analysis now persists applicability + per-dimension diagnostics so `unclear` is explainable instead of a black box
- Last update: 2026-03-22 UTC

## Implementer completion — editorial diagnostics, applicability, and explainable `unclear`

Completed the bounded implementation pass approved in the architect review.

### Landed
- added first-class `editorial_applicability` and reason classification on persisted rows
- added per-dimension diagnostic statuses for article type / bias / tone / framing surfaces
- persisted diagnostics JSON on the editorial-analysis row so operators can inspect loss, abstention, provider omission, and preserved raw hints without opening raw failure artifacts first
- preserved non-canonical framing/tone hints inside diagnostics instead of silently discarding them
- extended run metrics / CLI JSON with aggregate unclear-reason and dimension-status counters
- exposed diagnostics/applicability/path through read-side + API detail/list responses
- added regression coverage for weak-signal abstention, mapping loss, provider-missing behavior, and out-of-domain article types

### Important constraint preserved
- the strict final editorial payload remains authoritative for filtering/aggregation
- diagnostics explain uncertainty/loss/applicability; they do not bypass validation

## Architect completion — editorial `unclear` semantics and explainability re-review

Completed a deeper architecture pass focused on the operator complaint that too many final fields end up as `unclear`.

### Main findings
- the current pipeline shape is directionally right, but it still hides too much of the middle
- `unclear` currently conflates at least four realities:
  - honest weak-signal abstention
  - mapping loss / dropped signal
  - provider omission / malformed output
  - out-of-domain or low-editorial-value article classes
- the final schema is only partly too ambitious; the main problem is not the existence of the fields but the lack of tiering and diagnostics around them
- `tone_target` and `framing_devices` are the shakiest first-pass dimensions and should be treated as compressed/derived summaries, not equally trustworthy peers of core fields
- strict/native structured output helpers are not a real architectural fix on the current OpenRouter mixed-model route; they may help ergonomics on allowlisted providers, but they do not solve compatibility drift or semantic compression

### Revised recommendation
Keep the current raw -> repair -> normalize -> strict flow, but add a second persistent product:
- canonical final row for filtering/aggregation
- diagnostics sidecar (or compact diagnostics JSON) preserving:
  - raw/repaired excerpts
  - dimension-level statuses
  - unmapped signals
  - dropped/truncated fields
  - provider path / fallback path
  - applicability / out-of-domain assessment

### Recommended next implementation scope
1. add `editorial_applicability` / reason classification
2. add per-dimension outcome statuses (`resolved`, `weak_signal_abstain`, `mapping_loss`, `provider_missing`, `out_of_domain`, `conflicted_signal`)
3. persist diagnostics as first-class DB/API-visible data
4. preserve unmapped framing/tone meaning instead of silently dropping it
5. extend metrics/CLI summaries so operators can see why `unclear` happened
6. add regression coverage for weak-signal vs mapping-loss vs provider-missing vs out-of-domain behavior

### Important explicit conclusion
Do **not** bet the next pass on LangChain/OpenAI-style `with_structured_output(...)` or direct Pydantic parsing as the primary fix.
On this provider route that would mostly move the same failures under a nicer helper API.
