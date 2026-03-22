- State: DONE
- Current phase: editorial-analysis reliability remediation implemented on `iter/004`
- Last update: 2026-03-22 UTC

## Why this new planning pass exists

Recent operator testing exposed that the editorial-analysis pipeline is not robust across OpenRouter model/provider combinations.

Observed failures to carry forward into implementation:
- `minimax/minimax-m2.7` via OpenRouter: billed requests, but pipeline ended with `failed_count=3`, `request_count=0`, `analyzed_count=0`; DB `failure_reason` was `Expecting value: line 1 column 1 (char 0)`
- GPT-5.4 nano route via OpenRouter: provider returned `400 invalid schema for response_format article_editorial_analysis`, pointing at `properties.framing_devices`
- `openai/gpt-4.1-mini` via OpenRouter: operator reports same parse-failure pattern as minimax

## Planning conclusion

The current code path is too brittle because it:
- assumes `message.content` is directly parseable JSON text
- increments `request_count` only after successful parse
- collapses transport/schema/parse/validation failures into the same generic failed path
- does not preserve raw failed-response artifacts for debugging
- has no fallback mode when strict `response_format=json_schema` is rejected or returns unusable content

## Approved next implementation scope

Implement the bounded remediation plan now captured in `PLAN.md`:

1. response capture + normalized failure taxonomy
2. robust response parsing + honest request accounting
3. fallback mode when strict structured outputs are rejected or malformed
4. focused regression tests + operator runbook notes

## Explicit handoff to implementer

Touch backend/integration files only for this pass. Do not drift back into unrelated frontend work.

Priority order:
1. `src/analysis/llm_client.py`
2. `src/analysis/pipeline.py`
3. `scripts/analyze_editorial.py`
4. focused tests
5. small contract/docs updates only as needed

Key expected outcomes:
- billed attempts reflected in metrics
- failure class visible and truthful
- raw failed-response artifacts available for diagnosis
- schema rejection can fall back to JSON-text mode instead of hard failing immediately

## Implementer progress update

Completed in code:
- normalized failure classes + multi-attempt result envelope in `src/analysis/llm_client.py`
- honest request accounting and failure bucket counters in `src/analysis/pipeline.py`
- bounded fallback from strict schema mode to JSON-text mode
- failed-response artifact writing under `.artifacts/editorial-analysis/`
- focused regression coverage for parse failure, schema rejection fallback, validation failure, and unchanged-row skipping

Pending before closure:
- final docs/results sync
- commit(s)

## Notes on previous Phase 2 status

The earlier Phase 2 usability/read-side work is still valid.
This new pass does **not** replace that work; it fixes the backend reliability gap discovered during operator testing.
