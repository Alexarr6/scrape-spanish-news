# RESULTS.md — iter/029 analysis pipeline structural refactor phase 2

## Brief summary

iter/029 executed phase 2 of the structural refactor for `src/analysis/pipeline.py` with a real boundary cut and without touching the delicate heuristics. Story candidate generation and semantic-neighbor loading moved into `src/analysis/story_candidates.py`, and `ClusterPipeline` stayed as the thin orchestrator for that subsystem.

## Applied change

### New candidate module
- `src/analysis/story_candidates.py` (new)
  - introduces `StoryCandidateGenerator(session)`
  - moves, without functional redesign:
    - `generate_candidate_pairs()`
    - `load_semantic_neighbor_candidates()`
  - preserves the existing rules for:
    - source-priority ordering by `recall_mode`
    - per-source and per-seed limits
    - semantic-neighbor loading and filtering
    - `semantic_backfill` in `high_recall`
    - assembly of `pair.origins`, `pair.rank`, and `CandidateGenerationSummary`
    - safe fallback to `{}` when the semantic adapter fails

### Pipeline kept as orchestration
- `src/analysis/pipeline.py`
  - keeps `build_clusters()` unchanged at the public surface
  - keeps `score_pair()` and guarded closure where they already lived
  - delegates `_generate_candidate_pairs()` and `_load_semantic_neighbor_candidates()` to the extracted helper
  - keeps the old private method names as thin wrappers so tests and internal callers do not break

## Preserved invariants

- no change to candidate-pair inclusion or exclusion
- no change to `default` vs `high_recall` ordering
- no change to per-source limits or `high_recall` overrides
- no change to `semantic_backfill_limit`
- no change to semantic-neighbor fallback behavior (`{}`)
- no change to `max_days_delta` temporal filtering
- no change to `pair.origins` accumulation
- no change to `pair.rank` semantics
- no change to `CandidateGenerationSummary` fields or semantics
- no change to public `build_clusters()` behavior
- no change to pair scoring, guarded closure, or persistence

## Verification executed

1. `uv run python -m pytest tests/test_story_candidate_generation.py tests/test_story_clustering.py tests/test_story_matching_eval.py tests/test_story_review.py tests/test_story_pair_scoring.py`

## Verification result

- target suite: **40 passed**

## Honest residual risk

The refactor stopped exactly where it should have: split out the candidate-generation blob without pretending pair scoring was also ready to leave. Doing both at once would have been a pretty stupid idea.
