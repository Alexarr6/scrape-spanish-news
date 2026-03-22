# Architect review — explorer clustering phase (2026-03-18)

## Verdict
Direction is good. The repo is still using the right stack, the explorer remains bounded, and the new semantic clustering work moves fake UI affordances into real persisted behavior. That is the correct kind of progress.

The weak spots are mostly follow-through, not architecture collapse.

## What is working
- **Deck.gl stays in place.** Correct. No pointless stack churn.
- **Clustering is now based on embeddings, not projected coordinates.** Also correct. Anything else would be semantic cosplay.
- **Persistence is keyed by `projection_set`.** Good call. Keeps analysis traceable to the projection being viewed.
- **Frontend additions are bounded.** Color modes + focus/reset are useful and do not blow scope.
- **API shape remains coherent.** The explorer still has one main surface instead of five half-overlapping endpoints.

## Immediate improvements worth doing now

### 1) Fix the remaining operator defaults that still point at `pca_2d_latest`
Some Makefile/help text still defaults semantic build/project/smoke to the old 2D set. That is stale and will confuse anyone trying to reproduce the current explorer workflow.

**Do now:**
- switch `semantic-project`, `semantic-build`, and `semantic-smoke` defaults to `pca_3d_latest`
- update nearby help/copy accordingly

### 2) Silence the HDBSCAN warning explicitly
The current tests emit scikit-learn’s future-warning about the `copy` parameter. That’s minor, but leaving noisy warnings around is lazy.

**Do now:**
- set `copy=` explicitly on the estimator construction

### 3) Attach persisted analysis in generic projected-point loads
`load_projected_points()` still returns points without the persisted semantic analysis attached. That means some offline/export paths can drift from the explorer API path unless analysis is reapplied elsewhere.

**Do now:**
- join `semantic_point_analysis` in `load_projected_points()` and hydrate `point.analysis`

## Future suggestions, not for this pass
- Split explorer query/persistence code into a dedicated semantic-explorer module if the file keeps growing.
- Add snapshot-ish frontend tests once the UI surface stabilizes a bit more.
- Consider exposing cluster summary cards or legend UI, but only after real usage shows the current controls are not enough.
- If clustering becomes operationally important, persist richer analysis metadata/versioning rather than only point/cluster outputs.

## Bottom line
No rewrite needed. Just tighten the last 10% so the repo defaults, warning surface, and generic load path match the direction the feature already took.
