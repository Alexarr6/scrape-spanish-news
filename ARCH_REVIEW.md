# ARCH_REVIEW.md — Editorial analysis architecture re-review after operator concern about `unclear`

Status: architect recommendation for review before further implementation
Date: 2026-03-22
Branch: `iter/004`

## Executive summary

The current pipeline is no longer fundamentally broken.
It **is** fundamentally too opaque.

The operator’s complaint — “many columns end up as `unclear`” — is valid, and the current system still cannot answer the only question that matters:

**are those `unclear` values honest, or are we losing information on the way to persistence?**

Right now the answer is: **both happen, and the architecture still hides which is which.**
That is the real design failure.

My conclusion after re-reading the code, tests, docs, and failure artifacts is:

1. the strict raw/fallback/repair pipeline was the right move
2. strict provider-side structured outputs are still unreliable on this OpenRouter route
3. the final persisted schema is a bit too ambitious for first-pass article analysis **in how it is treated**, not in the existence of the fields themselves
4. the biggest remaining problem is not “bad JSON” anymore — it is that the system collapses multiple very different failure/abstention modes into the same final value: `unclear`
5. the next architecture must make **diagnostics first-class**, not just validation more tolerant

If you do not separate honest weak signal from dropped signal, the system can never be trusted, even when it is technically succeeding.

---

## What I inspected

Repo files reviewed:
- `AGENTS.md`
- `src/analysis/contracts.py`
- `src/analysis/editorial_normalization.py`
- `src/analysis/llm_client.py`
- `src/analysis/pipeline.py`
- `scripts/analyze_editorial.py`
- `Makefile`
- `docs/contracts/editorial-analysis-v1.md`
- `docs/contracts/editorial-analysis-prompt-v1.md`
- `docs/operator-guide/editorial-analysis-manual-test.md`
- `ARCH_REVIEW.md`
- `PLAN.md`
- `STATUS.md`
- `RESULTS.md`
- `tests/test_editorial_analysis_contracts.py`
- `tests/test_editorial_normalization.py`
- `tests/test_editorial_analysis_pipeline.py`
- `tests/test_llm_client_usage.py`

Artifacts reviewed:
- `.artifacts/editorial-analysis/20260322T170637Z-article-2924.json`
- `.artifacts/editorial-analysis/20260322T171315Z-article-2925.json`
- `.artifacts/editorial-analysis/20260322T172425Z-article-2928.json`
- prior artifact patterns referenced from current planner/results notes (`2926`, `2969`, `2927`)

External docs checked:
- OpenRouter structured outputs docs
- OpenAI structured outputs docs / SDK parsing helper guidance

---

## What is actually happening

## 1. Strict structured outputs are not trustworthy enough on this provider/model setup

This repo is using the OpenAI SDK against OpenRouter with mixed underlying providers/models.
That means `response_format=json_schema` only works when **all** of these line up:
- the route supports structured outputs
- the specific model supports them properly
- the provider’s schema validator accepts the exact schema flavor emitted
- the provider returns response content in the shape the SDK/client expects

That stack is too flaky to treat as the production contract.

The artifacts show exactly that:
- article `2924` / `2925`: provider-side `invalid_json_schema` complaints around nested `tone_dimensions`
- article `2928`: strict attempt accepted in some sense, but response shape came back unusable and then fallback produced the only meaningful content

So let’s say the quiet part out loud:

**strict structured outputs on this route are a probe, not a foundation.**

Keep them as an opportunistic first attempt if you want.
But building the whole architecture around them is wishful thinking.

---

## 2. The operator’s `unclear` complaint is not one bug — it is four different phenomena wearing the same hat

The code already tracks some `unclear_reasons`, but the final product still collapses too much into the final row.
At least four distinct realities are happening:

### A. Honest weak-signal abstention
Examples:
- accident / sports / travel-price / procedural coverage
- article is genuinely not ideologically rich
- output should often be `bias_label=unclear`, low confidence, calm tone, low sensationalism

This is good behavior.
It is not a failure.

### B. Mapping loss / dropped signal
Examples from artifacts and tests:
- useful framing descriptions returned but do not map into the narrow framing taxonomy
- nested tone keys like `government_assessment`, `emotional_charge`, `informational_balance` not captured semantically
- model offers clues in `classification_notes`, `source_treatment`, object rationale, or non-canonical framing labels, but the final payload has nowhere good to preserve them

This is **not** honest abstention.
This is information loss.

### C. Provider omission / malformed output
Examples:
- strict mode returns unusable response shape
- fallback JSON lacks enough usable evidence spans
- content cannot be parsed or extracted reliably

This is transport/provider failure, not article ambiguity.

### D. Out-of-domain or low-editorial-value article class
Examples:
- sports match recap
- accident bulletin
- travel price roundup
- pure market/consumer price report

These are not malformed and not necessarily weak-signal in a generic sense.
They are often just the wrong content class for detailed ideological editorial analysis.

Right now the system treats a lot of D like A, and some B like A too.
That’s why the operator cannot tell whether the system is being careful or just confused.

---

## 3. The final schema is only partly too ambitious

The common lazy diagnosis would be “too many fields, simplify the schema.”
That’s not quite right.

My view:

### The core fields are fine for first pass
These should stay as first-pass persisted outputs:
- `article_type`
- `article_type_confidence`
- `bias_label`
- `bias_score`
- `bias_confidence`
- `tone_emotional`
- `opinionatedness`
- `sensationalism`
- `rhetorical_certainty`
- `evidence_spans`
- `rationale`

These are coherent first-pass dimensions.

### The current schema becomes too ambitious at the edges
The trouble spots are:
- `tone_target`
- `framing_devices`
- demanding a strong ideological interpretation on low-editorial-value content
- treating all fields as equally “must-decide” on first pass

`tone_target` is especially slippery because many articles have:
- multiple actors
- quoted criticism without clear narrator endorsement
- procedural coverage with no single stable target

`framing_devices` is also lossy because the taxonomy is narrow while model outputs are broader and more descriptive.
The model often provides **useful non-canonical frame descriptions** that are currently dropped instead of preserved.

### Recommendation
Do **not** delete these fields.
Instead, re-tier them:

#### Tier 1 — primary first-pass fields
Persist as today, operator-facing:
- article type
- ideological direction
- intensity/confidence
- broad tone/opinionatedness
- evidence/rationale

#### Tier 2 — derived/narrow-taxonomy summaries
Persist, but explicitly as compressed/derived summaries from richer intermediate analysis:
- `tone_target`
- `framing_devices`

#### Tier 3 — diagnostic / audit fields
Persist separately so lost meaning does not disappear:
- raw framing candidates
- unmapped tone hints
- dropped field reasons
- out-of-domain assessment
- abstention classification

That is the real fix.
Not pretending the model will magically become more certain.

---

## 4. The current normalization is still too destructive for operator understanding

The code now does:
- raw capture
- repair
- semantic normalization
- strict final validation

That pipeline is directionally correct.
But from an operator perspective, the middle still disappears too quickly.

What is missing is a **first-class intermediate analysis record**.
Right now the success path keeps the strict final row and throws most of the interesting audit story into ephemeral warnings/artifacts.
That is too little.

### Real examples
- `2924`: useful object-form ideological explanation and emergency-response framing survive in raw content, but final taxonomy will flatten much of that nuance
- `2925`: the model is basically saying “this is a travel/price report, not ideological,” which is useful and honest, but the final system mostly expresses that as a bland cloud of `unclear`/calm/low
- `2928`: the model leaks outlet prior (`ABC, a center-right outlet`) into rationale, which is bad semantically, but it also contains useful signals about quoted criticism and headline emphasis; the current system risks mixing those together without making the contamination visible

The operator needs to see:
- what the model said
- what was salvaged
- what was discarded
- why the final row looks thinner than the raw analysis

Without that, you cannot debug or trust the pipeline.

---

## Recommended architecture

## Final recommendation

Keep the current high-level pipeline, but split the product into **two outputs**, not one:

```text
LLM raw response
  -> capture
  -> shape repair
  -> semantic normalization
  -> strict final record
  -> diagnostic/audit record
```

The missing piece is the second output.

### Output A — strict canonical row
This remains the DB/API row for filtering, rollups, and dashboards.
It should stay conservative and narrow.

### Output B — diagnostic/audit row
This is where you preserve the story of what happened.
It should include, at minimum:
- raw parsed JSON excerpt or hash-linked stored artifact
- repaired intermediate values
- unmapped candidates
- dropped/truncated fields
- abstention classification per dimension
- out-of-domain flag and reason
- provider/mode path (`strict`, `fallback`, etc.)

If you only keep Output A, the operator will keep staring at `unclear` and asking whether the machine ate their homework.
Because sometimes it did.

---

## The key architectural change: dimension-level outcome status

Stop treating each final field as just “value or `unclear`.”
That is too dumb.

For at least the major dimensions, persist a status alongside the final value.

Suggested dimensions:
- article type
- bias
- tone
- opinionatedness
- sensationalism
- rhetorical certainty
- framing

Suggested per-dimension status enum:
- `resolved`
- `weak_signal_abstain`
- `mapping_loss`
- `provider_missing`
- `out_of_domain`
- `conflicted_signal`

Example:
- `bias_label=unclear` + `bias_status=weak_signal_abstain`
- `framing_devices=[]` + `framing_status=mapping_loss`
- `tone_target=unclear` + `tone_target_status=provider_missing`
- `bias_label=unclear` + `bias_status=out_of_domain`

That one change would answer the operator’s core question more honestly than any amount of prompt tweaking.

---

## Out-of-domain must become explicit

Right now out-of-domain content is handled indirectly through low-signal conservative outputs.
That is not enough.

Add an explicit normalization decision:
- `editorial_applicability`: `full`, `limited`, `out_of_domain`
- `editorial_applicability_reason`: short enum/string

Suggested reasons:
- `procedural_hard_news`
- `sports_recap`
- `accident_crime_bulletin`
- `consumer_price_roundup`
- `weather_or_service_info`
- `insufficient_text`

This does two important things:
1. explains why many ideological fields are `unclear`
2. prevents operators from reading those rows as model failure when the content itself is a bad fit for rich editorial labeling

For article classes like sports and accidents, this is massively better than making the model fake nuance.

---

## Make information loss visible in DB/API, not just artifacts

Artifacts are useful for debugging.
They are not enough for operations.

### Minimum recommendation
Persist a compact diagnostics JSON column on `article_editorial_analysis`, something like:
- `analysis_diagnostics_json`

Suggested content:
```json
{
  "provider_path": "strict_failed_fallback_succeeded",
  "editorial_applicability": "limited",
  "dimension_status": {
    "bias": "weak_signal_abstain",
    "framing": "mapping_loss"
  },
  "repair_warnings": ["repair_confidence_label_mapped"],
  "normalization_warnings": ["dropped framing_device='comparacion_cuantitativa'"],
  "dropped_fields": ["framing_devices"],
  "truncated_fields": ["evidence_spans"],
  "unmapped_signals": {
    "framing_candidates": ["comparacion_cuantitativa"],
    "tone_hints": ["government_assessment=critical"]
  }
}
```

### Better recommendation
If you want this genuinely debuggable and explainable, add a side table:
- `article_editorial_analysis_diagnostics`

Why a side table is cleaner:
- avoids bloating the canonical row
- lets you store larger JSON safely
- separates read paths: dashboard vs audit
- easier to evolve without destabilizing the public contract

### API/read-side recommendation
Expose diagnostics in one of two ways:
- optional include on detail endpoint (`?include_diagnostics=1`)
- separate diagnostics endpoint for a given article/analysis id

Do **not** force all consumers to ingest the diagnostics blob by default.
But make it easily available.

---

## Structured output strategy: honest evaluation of `with_structured_output(...)` / Pydantic helpers

The user explicitly raised LangChain/OpenAI-style native structured output helpers.
Here’s the honest answer:

## Short version
**No, this probably does not materially solve the current problem on the current OpenRouter-routed mixed-model setup.**

It may improve ergonomics in code.
It does not change the weakest link.

## Why not
Helpers like:
- `client.responses.parse(..., text_format=MyPydanticModel)`
- LangChain `with_structured_output(...)`
- Pydantic schema wrappers

are mainly convenience layers over one of these mechanisms:
- provider-native structured outputs / `json_schema`
- tool/function calling
- post-hoc parsing and validation of text output

In this repo’s current environment, the hard problems are:
1. provider/model compatibility over OpenRouter
2. mixed response-shape behavior across routes
3. semantic loss during mapping into a narrow canonical schema
4. operator visibility into loss/abstention

A helper wrapper does not fix any of those.
It just moves the failure boundary.

### Specifically
- If the helper uses provider-native structured outputs underneath, you still hit the same OpenRouter/provider compatibility failures.
- If the helper falls back to prompt-and-parse, you still need the same repair/normalization architecture.
- If the helper validates into Pydantic directly, it can actually make the current lossy behavior worse by failing earlier unless you still maintain a permissive raw model and repair stage.

So the brutal truth is:

**`with_structured_output(...)` would mostly be lipstick on the same pig unless you also keep the raw->repair->normalize->validate pipeline.**

## Where helpers could still help
I’m not saying “never use them.”
They could be useful for:
- a provider-specific fast path on known-good models
- cleaner code when talking directly to OpenAI-native structured-output models
- experiments on a fixed allowlisted model family

But that is a **narrow optimization path**, not the architecture.

## Recommendation
- keep the current portable raw JSON contract as the default architecture
- optionally add a provider-specific structured-output fast path behind feature flags/allowlists
- never let helper-based direct validation replace the permissive raw capture stage on mixed OpenRouter routing

That is the honest tradeoff.

---

## Concrete recommended data model changes

## Keep canonical row, add diagnostics

### Canonical row (`article_editorial_analysis`)
Keep current fields, but add minimal operator-facing explainability:
- `editorial_applicability` (`full|limited|out_of_domain`)
- `analysis_path` (`strict`, `fallback`, `fallback_after_strict_reject`, etc.)
- maybe `has_diagnostics` boolean if side table is used

### Diagnostics sidecar (`article_editorial_analysis_diagnostics`)
Suggested columns:
- `article_id` / FK to analysis row
- `raw_payload_json`
- `repaired_payload_json`
- `dimension_status_json`
- `unmapped_signals_json`
- `repair_warnings_json`
- `normalization_warnings_json`
- `dropped_fields_json`
- `truncated_fields_json`
- `provider_failure_summary_json`
- `created_at`

If full raw payload persistence is too heavy, store:
- artifact path
- payload hashes
- compact excerpts

But something persistent needs to exist besides transient artifact files.

---

## Concrete normalization policy changes

## 1. Distinguish article suitability before ideology
Run an explicit early normalization question:
- is this article a good fit for fine-grained editorial analysis?

If not, mark `editorial_applicability=limited|out_of_domain` before over-interpreting the ideological dimensions.

## 2. Preserve unmapped meaning
When framing/tone signals are useful but non-canonical:
- do not silently drop them
- persist them into diagnostics as `unmapped_signals`

## 3. Make `tone_target` secondary
Continue computing it, but treat it as a derived/narrow field.
It should not be allowed to dominate operator trust because it is one of the least stable first-pass dimensions.

## 4. Make framing taxonomy explicitly lossy
Do not pretend the final framing enum is the full truth.
Treat it as a compressed operator-facing summary derived from richer raw descriptions.

## 5. Add dimension-level abstention reasoning
This matters more than global `unclear_reasons`.
The operator needs to know which field was unclear for which reason.

---

## Metrics and reporting changes

Current metrics are not useless anymore, but they still stop short of the real question.

Add at least:
- `out_of_domain_count`
- `limited_applicability_count`
- `bias_weak_signal_count`
- `bias_mapping_loss_count`
- `framing_mapping_loss_count`
- `provider_missing_dimension_count`
- `rows_with_unmapped_signals_count`
- `fallback_after_strict_reject_count`

And expose a sample summary in CLI output, not just raw counts:
- top dropped framing candidates
- top unmapped tone hints
- how many `unclear` rows were honest abstentions vs mapping/provider issues

That’s the difference between observability and ritual.

---

## Recommended implementation order

## Phase 1 — persist diagnostics as first-class data
Add sidecar diagnostics persistence or compact diagnostics JSON.
This is the highest-value change.

## Phase 2 — dimension-level status classification
Replace coarse/global `unclear_reasons` with per-dimension outcome status.

## Phase 3 — explicit editorial applicability classification
Mark content as `full|limited|out_of_domain` before over-reading ideological dimensions.

## Phase 4 — re-tier the read side
Keep canonical row slim, diagnostics optional, and expose both clearly in API/operator tools.

## Phase 5 — optional provider-specific fast path
Only after the above, consider model/provider allowlists or helper-based structured-output fast paths for known-good routes.

---

## Explicit implementer scope

Next implementer should focus on:
- `src/analysis/contracts.py`
  - add diagnostics and applicability contracts
- `src/analysis/editorial_normalization.py`
  - produce dimension-level outcome statuses
  - classify applicability / out-of-domain
  - preserve unmapped signals
- `src/analysis/pipeline.py`
  - persist diagnostics sidecar or diagnostics JSON
  - add new metrics
- `src/analysis/llm_client.py`
  - preserve analysis path details cleanly
- `scripts/analyze_editorial.py`
  - expose new summary counts
- docs/operator guide
  - teach operators how to interpret `unclear`, `limited`, and `out_of_domain`
- tests
  - add cases proving the system distinguishes weak signal vs mapping loss vs provider omission vs out-of-domain

---

## Final proposed end-state architecture

This system should do **first-pass editorial analysis**, not pretend to be a final political-theory oracle.

### What it should do
- decide whether an article is suitable for editorial analysis at all
- classify broad editorial posture proportionate to the available signal
- distinguish strong signal from weak signal from pipeline loss
- store one conservative canonical result in the DB
- store enough traceability that an operator can understand **why** the result looks that way
- stay portable across providers by assuming raw-shape variability is normal, not exceptional

### What it should not overclaim
- it should not infer ideology from outlet reputation alone
- it should not force fine-grained ideological labels onto low-editorial-value content
- it should not treat all article categories as equally analyzable
- it should not pretend that an empty or narrow framing taxonomy fully captures what the model saw
- it should not treat `unclear` as one monolithic outcome

## Recommended end-state flow

```text
article text
  -> pre-classify editorial applicability
  -> provider call strategy (portable raw JSON default)
  -> raw response capture
  -> shape repair / coercion
  -> semantic normalization
  -> strict canonical validation
  -> DB persistence of:
       A) canonical row
       B) diagnostics / audit payload
```

### 1. Pre-classify applicability before ideology
Make the first question:

**is this article even a good candidate for ideological/editorial analysis?**

Persist:
- `editorial_applicability`: `full | limited | out_of_domain`
- `editorial_applicability_reason`: bounded reason enum

Recommended category policy:

#### `full`
Use for:
- politics
- governance
- migration/security when the article itself contains editorial framing
- economics when the article contains evaluative framing
- ideology-rich analysis/opinion/editorial pieces

#### `limited`
Use for:
- procedural hard news
- neutral institutional updates
- explainers with some frame hints but weak ideological signal
- consumer/economic service articles that may contain mild framing but are not mainly editorial objects

Expected behavior:
- core fields still filled when defensible
- many dimensions may honestly abstain
- operator should read result as “lightweight editorial read,” not “deep ideology score”

#### `out_of_domain`
Use for:
- sports recaps
- accident/crime bulletins
- weather/service information
- pure price roundups / travel deal coverage
- extremely short/incomplete text

Expected behavior:
- do not chase fake nuance
- store conservative defaults plus explicit out-of-domain diagnostics
- do not let these rows poison later calibration of ideological fields

This is the cleanest way to prevent misleading blankets of `unclear`.

### 2. Provider/call strategy
Default architecture should remain:
- `strict_json_schema` probe first
- portable fallback JSON-text attempt when strict path is rejected or unusable
- always preserve raw content and parsed JSON when available

Reason: on this OpenRouter route, provider-native schema support is not stable enough to be the foundation.
OpenAI’s native structured output stack promises strong schema adherence on supported models, and OpenRouter documents structured outputs only for compatible models, which is exactly the catch here: compatibility is conditional, not universal. In this repo’s actual evidence, the route is mixed and flaky enough that raw capture plus local repair is still the production-grade path.

### 3. Structured-output strategy
Be explicit:

#### Default path
- ask for a **portable raw JSON object**
- accept shape variation
- validate locally in two stages:
  - permissive raw contract
  - strict canonical contract

#### Optional fast path
Use `with_structured_output(...)` / SDK parse helpers / native Pydantic structured parsing only as:
- an allowlisted provider-model optimization
- a convenience wrapper on top of the same diagnostic architecture

Do **not** let helper-based direct parsing replace the raw -> repair -> normalize flow.
If the helper works, great. If not, the portable path must still be the real contract.

### 4. Canonical output shape
Keep the current canonical row largely intact, but re-tier the semantics.

#### Tier 1: first-pass trustworthy fields
- `article_type`
- `article_type_confidence`
- `bias_label`
- `bias_score`
- `bias_confidence`
- `tone_emotional`
- `opinionatedness`
- `sensationalism`
- `rhetorical_certainty`
- `evidence_spans`
- `rationale`
- `editorial_applicability`
- `editorial_applicability_reason`

#### Tier 2: compressed summaries
- `tone_target`
- `framing_devices`

These should stay, but operator tooling should present them as narrower derived summaries rather than equal peers of the core fields.

### 5. Diagnostics / operator trust contract
A row should be explainable without opening random artifact files.
Persist diagnostics with at least:
- provider path / attempt path
- applicability classification
- dimension-level status
- repair warnings
- normalization warnings
- dropped/truncated fields
- preserved non-canonical signals
- provider failure classes
- global unclear reasons

Dimension-level status is the real trust mechanism:
- `resolved`
- `weak_signal_abstain`
- `mapping_loss`
- `provider_missing`
- `out_of_domain`
- `conflicted_signal`

The operator should be able to see, for example:
- `bias_label=unclear` because `weak_signal_abstain`
- `framing_devices=[]` because `mapping_loss`
- `tone_target=unclear` because `provider_missing`
- all dimensions limited because `out_of_domain`

### 6. Schema change decision
My recommendation is **no major contraction of the final canonical schema right now**.
That would be the wrong fix.

What should change is:
- treat `tone_target` and `framing_devices` as explicitly secondary/compressed
- keep diagnostics first-class
- preserve richer intermediate meaning in diagnostics instead of bloating the canonical enum space

So the answer is:
- **keep most fields**
- **change their trust model and operator presentation**
- **do not pretend first-pass analysis can resolve every dimension equally well**

### 7. Explicit view on `with_structured_output(...)` / native structured helpers
Blunt answer:

**useful tool, wrong foundation.**

#### When it helps
- direct OpenAI-native or otherwise known-good providers/models
- internal ergonomics
- code simplification on allowlisted reliable routes
- faster success path when the provider truly honors schemas

#### When it does not help
- mixed OpenRouter routing with inconsistent schema support
- response-shape variability across providers
- semantic compression into a narrow taxonomy
- cases where you still need salvage/repair after provider output

#### Recommendation
- optional fast path only
- provider/model allowlist only
- never the sole persistence contract

If someone proposes “just switch everything to Pydantic/native structured outputs,” the honest answer is: no, that’s mostly cosmetic here.

### 8. Explicit view on offline calibration corpus
This idea is not optional fluff.
It should become a core part of how this system improves.

#### Yes — build it
Use real captured model outputs and real article cases as an offline corpus.

#### What it should contain
For each fixture:
- article metadata
- article text excerpt or stable fixture copy
- raw provider output(s), ideally from multiple models/providers when available
- repaired payload
- final canonical payload
- diagnostics
- expected applicability classification
- expected dimension statuses
- optional human review notes

Cover article families deliberately:
- ideology-rich opinion/editorial
- interpretive analysis
- procedural hard news
- neutral explainers
- migration/security stories
- economic policy stories
- sports / accidents / service info / price roundups
- malformed/provider-weird outputs

#### How it should be used
- regression tests for normalization and diagnostics
- offline replay harness: run raw outputs through repair/normalize/validate without spending tokens
- calibration review: inspect where `unclear` is honest vs lossy
- taxonomy review: decide which signals deserve new aliases/mappings and which should remain diagnostics only
- model comparison: same article, different model raw outputs, same normalization expectations where possible

That is how you improve this system without hallucinating progress from one-off prompt tweaks.

## Recommended next implementation scope / order

1. **Add offline replay + fixture corpus tooling**
   - scripts/tests that replay captured raw outputs through normalization only
   - golden expectations for applicability, dimension status, and preserved signals

2. **Refine applicability classification using the corpus**
   - reduce false `full` on low-editorial-value content
   - ensure `limited` is used for procedural hard news rather than defaulting to generic `unclear`

3. **Rework operator read-side presentation**
   - make detail/list endpoints surface tiering and dimension-status meaning more clearly
   - highlight why a value is `unclear`, not just that it is

4. **Promote structured-output helpers to an optional allowlisted fast path only if proven on a fixed model route**
   - measure strict success rate, salvage rate, and semantic quality before adopting

5. **Only then consider taxonomy expansion**
   - especially framing aliases and narrow tone-target semantics
   - driven by corpus evidence, not vibes

## Final verdict

The current system is not mainly failing because the model can’t emit JSON.
That was yesterday’s problem.

Today’s problem is sharper:

**the system still compresses “honest abstention,” “mapping loss,” “provider omission,” and “out-of-domain article” into the same operator experience.**

That is why `unclear` feels suspicious.
Because sometimes it is honest, and sometimes it is a tombstone for lost information.

The next architecture should not primarily chase better formatting.
It should make the loss visible, classify abstention honestly, and preserve the middle of the pipeline as first-class diagnostic data.

That is how this becomes reliable instead of merely tolerant.
