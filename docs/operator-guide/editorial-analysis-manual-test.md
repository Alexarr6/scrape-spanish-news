# Editorial Analysis — Manual Test Plan

## Goal

Validate that editorial analysis v1 is operationally sound and not saying obvious nonsense before Phase 3 adds rollups or comparison surfaces.

This is a **small-batch review**, not a full evaluation campaign.

## What to verify

For a small mixed set of articles, check:
- the pipeline runs without operational drama
- outputs persist correctly
- list/detail API works
- `review_flags` are useful
- `bias_label`, `bias_score`, `tone_*`, `rationale`, and `evidence_spans` feel defensible
- `unclear` is used when signal is weak
- the model is not obviously inheriting outlet stereotypes without textual support
- strict structured mode failures degrade honestly instead of pretending no request happened
- failure artifacts are written under `.artifacts/editorial-analysis/` when a row fails
- failure reasons start with a normalized class such as `provider_schema_rejected`, `json_parse_failed`, or `payload_validation_failed`

## Recommended order

### Step 0 — replay the offline corpus first
Before spending provider calls, run the captured replay corpus.

```bash
cd /path/to/spain-news-bias-scraper
PYTHONPATH=. uv run --project . python scripts/replay_editorial_corpus.py
```

Use this to check whether recent code changes altered:
- applicability buckets
- `unclear` reason mix
- dimension-level statuses
- preserved non-canonical signals
- known normalization failures

If the replay corpus moves in a surprising way, stop and inspect that first.

See also:
- `docs/operator-guide/editorial-analysis-replay-corpus.md`

### Step 1 — dry run first
Run a dry run on a small bounded slice.

Suggested examples:
- a single source
- a short date window
- small limit

Use dry run to confirm:
- selection logic is correct
- pending/failed targeting behaves as expected
- CLI flags behave sanely
- the reported `effective_status` matches operator intent
- `--reprocess` widens default `status=pending` runs to `status=any` unless explicit article ids are supplied
- `selection.status_counts` looks plausible before you spend tokens

### Step 2 — real small-batch run
Run a small real batch, ideally 10 to 20 articles.

Recommended mix:
- at least 3 different outlets
- mixture of politics, economics, migration/security, and institutional news if available
- mixture of likely straight reporting and more interpretive/opinion-like pieces

Avoid giant runs first. Small and inspectable beats noisy and useless.

### Step 3 — review API list surface
Use `GET /api/v1/editorial-analysis` with filters to inspect:
- `analysis_status`
- `bias_label`
- `min_bias_confidence`
- `tone_emotional`
- `opinionatedness`
- source/date filters

Confirm:
- pagination works
- sorting works
- missing rows behave as pending where expected
- review flags appear where they should

### Step 4 — inspect article detail cases
Pick 8-12 results and inspect detail payloads.

For each, check:
- article metadata is enough to identify the case quickly
- rationale is short and specific, not generic fluff
- evidence spans are real and relevant
- confidence roughly matches how arguable the classification is
- `needs_review` makes sense

## Recommended review sample categories

Try to include examples from each of these buckets:

1. **Easy / obvious framing**
   - articles where tone or ideological framing is fairly clear

2. **Hard / ambiguous framing**
   - straight reporting or explanatory pieces with weak ideological cues
   - these should often land near `unclear` or center with lower confidence

3. **Potentially inflammatory wording**
   - security, migration, corruption, or outrage-driven headlines

4. **Institutional / procedural coverage**
   - votes, courts, budgets, regulatory changes
   - useful for seeing if the system over-labels ideology

## What “good enough” looks like

You are not looking for perfection yet.
You are looking for this:
- no obvious schema failures
- no persistent broken statuses for normal articles
- evidence spans generally support the labels
- confidence is not absurdly inflated
- weak-signal articles do not get overconfident ideological labels
- review flags catch the sketchy cases

## Red flags

If you see these, stop before Phase 3:
- same outlet always getting same ideological label regardless of article text
- `bias_confidence` consistently too high
- empty or useless evidence spans
- rationale that sounds smart but is detached from text
- too many strong ideological labels on procedural/neutral reporting
- sensationalism/tone outputs collapsing into one default value across most articles

## Practical review checklist

For each article reviewed manually, answer:
- Is `article_type` plausible?
- Is `bias_label` defensible from the text itself?
- Is `bias_score` directionally sensible?
- Is `bias_confidence` too high, too low, or about right?
- Is `tone_emotional` fair?
- Is `opinionatedness` fair?
- Do `framing_devices` feel grounded or bullshit?
- Do `evidence_spans` actually support the output?
- Should `needs_review` be true?

## Suggested outcome after manual test

After the first review, classify the system state into one of three buckets:

### A. Good enough to proceed
- only minor prompt/schema tuning needed
- move to Phase 3 planning

### B. Needs prompt calibration first
- outputs are structurally fine but semantically noisy
- tune prompt/schema/thresholds before Phase 3

### C. Needs pipeline correction
- selection, persistence, validation, or API behavior is still shaky
- fix Phase 2/2.5 before any Phase 3 work

## Failure handling notes

### Generation modes
- `strict_json_schema`: preferred path using `response_format=json_schema`
- `fallback_json_text`: bounded retry path when strict mode is rejected or returns unusable content

### Current operator expectations
- `request_count` now reflects API-accepted provider attempts even if parse or validation later fails
- `provider_rejected_count` captures pre-generation schema rejection cases
- `parse_failed_count` captures empty/non-JSON/unexpected response content
- `validation_failed_count` captures local payload validation failures after JSON was parsed
- `strict_success_count` vs `fallback_success_count` now shows whether fallback actually saved the row
- warning-heavy successful rows should now increment `rows_with_warnings_count`
- truncation/data-loss cases should now be visible through metrics like `rows_with_truncated_evidence_count`, failure artifacts, and row-level warning details
- `unclear` should be interpreted with the new reason classes in artifacts (`semantic_weak_signal`, `mapping_unresolved`, `repair_data_loss`, etc.), not as a useless black-box shrug

### Artifact hygiene
- Artifacts are runtime debug files, not source docs
- Expected location: `.artifacts/editorial-analysis/`
- They should contain response/debug material, not full article bodies or secrets

## Recommendation

Do not start cluster rollups or media-comparison views until at least one manual batch review says this is in bucket **A** or near **B**.
