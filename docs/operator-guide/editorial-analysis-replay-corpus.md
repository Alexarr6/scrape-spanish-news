# Editorial Analysis Replay Corpus

This is the cheap calibration loop.

Use it before burning more provider calls.

## Why it exists

The replay corpus lets us push **real captured model outputs** back through the current local pipeline:

- raw payload parse
- repair / coercion
- semantic normalization
- strict final validation
- diagnostics inspection

That means we can answer the question that actually matters:

**is `unclear` honest, or did the pipeline lose something?**

## Fixture location

Fixtures live under:

- `tests/fixtures/editorial_replay/*.json`

Each fixture is a representative article-family case, not a runtime special-case.

## Fixture shape

Each JSON fixture includes, as relevant:

- `fixture_id`
- `family`
- `source_artifact`
- `notes`
- `article` metadata / source context
- `provider` metadata
- `raw_provider_output`
- `parsed_json`
- `repaired_payload`
- `final_payload`
- `diagnostics`
- `expectation`

The expectation block records what the current pipeline should do for that family:

- success vs normalization error
- expected applicability
- expected applicability reason
- expected unclear reasons
- expected final canonical payload
- expected dimension statuses
- expected preserved-signal groups
- expected warning fragments

## Run it

```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper
PYTHONPATH=. ~/.local/bin/uv run --project . python3 scripts/replay_editorial_corpus.py
```

If you want the test gate too:

```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper
PYTHONPATH=. ~/.local/bin/uv run --project . pytest -q tests/test_editorial_replay.py
```

## What the report tells you

The replay report is intentionally blunt.

For each fixture it shows:

- article family
- success/fail
- applicability
- a summary bucket
- unclear reasons
- per-dimension statuses
- preserved signal groups
- any mismatches

Summary buckets are there to separate the major failure/abstention modes fast:

- `out_of_domain`
- `limited`
- `mapping_loss`
- `provider_missing`
- `honest_abstention`
- `resolved_or_mixed`
- `normalization_error`

## How to use it during iteration

When changing editorial normalization or diagnostics:

1. run the replay corpus first
2. inspect any changed buckets, not just pass/fail
3. confirm whether a shift is good calibration or accidental regression
4. only then do a bounded live provider check if needed

If a live run finds a new interesting family, add a new replay fixture from the captured artifact.

## Important rules

- do **not** add article-id-specific runtime logic
- fixtures are evaluation coverage, not production exceptions
- prefer representative article families over one-off curiosities
- if the pipeline changes intentionally, update fixture expectations explicitly and explain why in `RESULTS.md`
