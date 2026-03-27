# Semantic Wave 5 Audit

## Status

Wave 5 did a conservative cleanup of `semantic`:

- removed dead wrappers and duplicate helpers with zero in-repo callers
- kept metrics and exported fields that still feed scripts, JSON artifacts, or tests
- avoided changing API payloads, explorer behavior, or export formats

## Removed

- `src/semantic/load_articles.py`
  - no callers in `src/`, `scripts/`, or `tests`
- duplicate private helpers in `src/semantic/dbstore.py`
  - `_load_available_clusters`
  - `_load_cluster_summaries`
  - `_analysis_for_row`
  - `_build_editorial_review_flags`
  - `_parse_json_list`
  - `_parse_json_scalar_list`
  - all had been superseded by `src/semantic/explorer_readside.py`

## Kept Intentionally

- `SemanticMetrics` fields such as `fetched_rows`, `eligible_rows`, `embedding_dimensions`, and `projection_method`
  - still written to metrics JSON and covered by scripts/tests
- explorer read-side helpers in `src/semantic/explorer_readside.py`
  - actively consumed by `src/semantic/dbstore.py`
- large orchestration blocks in `src/semantic/dbstore.py`
  - still live and need a structural split rather than dead-code deletion

## Next Structural Candidates

- `src/semantic/dbstore.py`
  - split write-side persistence from explorer/read-side SQL shaping
- `src/semantic/export.py`
  - separate artifact serialization from HTML rendering
- `scripts/build_semantic_map.py`
  - isolate metrics/reporting from export orchestration
