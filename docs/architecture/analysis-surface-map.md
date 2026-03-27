# Analysis Surface Map

This note records the intended module boundaries after the `analysis` refactor waves.

## Public Stable

- `src.analysis.pipeline`
- `src.analysis.llm_client`
- `src.analysis.editorial_normalization`
- `src.analysis.readside`
- `src.analysis.matching_corpus`
- `src.analysis.story_eval`
- `src.analysis.story_review`
- `src.analysis.editorial_replay`

These modules remain import-safe for scripts, tests, and any external callers while the internal
structure keeps evolving.

## Compat Only

- `src.analysis.__init__`

This package root stays intentionally narrow and only preserves the historical pipeline exports.

## Internal Live

- `src.analysis.enrichment.*`
- `src.analysis.editorial.*`
- `src.analysis.clustering.*`
- `src.analysis.readside.*`
- cross-cutting helpers such as `contracts`, `types`, `taxonomy`, `heuristics`, and `normalization`

Internal analysis code should import from these concrete modules directly.

## Removed Wrappers

- `src.analysis.readside_editorial`
- `src.analysis.story_candidates`
- `src.analysis.story_closure`

These wrappers were deleted in Wave 3 after confirming zero callers in `src/`, `scripts/`, and
`tests/`.

## Deadcode Note

`deadcode` is useful here as an advisory tool, but not as a deletion oracle. Pydantic models,
SQLAlchemy ORM fields, CLI entrypoints, and test-only/public compatibility surfaces produce false
positives and must still be verified with real caller searches before removal.
