# Semantic explorer / analysis second-pass architecture review

Date: 2026-03-17
Reviewer: architect second-pass audit
Scope: current `src/semantic/*`, `scripts/build_semantic_map.py`, semantic explorer HTML export, and related tests

## Verdict

This is **materially fixed** relative to the earlier broken state.

The current implementation is no longer doing the dumb thing of pretending the 2D projection *is* the semantic truth. The architecture now has a sane split:
- embeddings remain the semantic source of truth
- PCA projection is explicitly just a visualization layer
- semantic analysis runs off cosine distance in embedding space
- the explorer consumes analysis output instead of inventing its own semantics in the browser
- tests cover the important regressions that previously mattered

So the headline is simple:

**I would accept the current semantic explorer + semantic analysis work as structurally sound.**

No rewrite is justified. No grand roadmap is needed.

## What I checked

Code and tests reviewed:
- `src/semantic/analyze.py`
- `src/semantic/contracts.py`
- `src/semantic/dbstore.py`
- `src/semantic/project.py`
- `src/semantic/embed.py`
- `src/semantic/export.py`
- `src/semantic/load_articles.py`
- `scripts/build_semantic_map.py`
- `tests/test_semantic_analysis.py`
- `tests/test_semantic_build_cli.py`
- `tests/test_semantic_projection.py`
- `tests/test_semantic_dbstore.py`
- `tests/test_semantic_export.py`
- `tests/test_semantic_neighbors_cli.py`
- prior archive review note: `docs/archive/ARCH_REVIEW_legacy.md`

## Prior critical concerns: status

### 1) “Semantic grouping is being inferred from 2D layout instead of embeddings”
**Status: addressed well.**

Evidence:
- `src/semantic/analyze.py` computes pairwise cosine distance from full embeddings via `_cosine_distance()` and `_distance_matrix()`.
- `tests/test_semantic_analysis.py::test_analyze_points_ignores_misleading_2d_layout` explicitly proves clustering ignores misleading PCA coordinates.
- `AnalysisMetadataArtifact.distance_basis` is set to `embedding_cosine_distance`, which makes the contract explicit instead of hand-wavey.

This was the big one. It looks fixed in the actual implementation, not just in docs.

### 2) “Explorer has no grounded semantic metadata, just a pretty plot”
**Status: addressed well.**

Evidence:
- `analyze_points()` emits per-point analysis (`cluster_id`, `cluster_size`, outlier flag, local density distance, nearby source mix).
- `src/semantic/export.py` carries that analysis into point payloads and exposes it in the inspector UI.
- The browser UI now acts as a consumer of exported semantic metadata rather than a place where semantic logic is improvised.
- `tests/test_semantic_export.py` verifies the HTML contains the semantic inspector/filter affordances and serialized neighbor content.

That is the right direction: compute semantics in Python, inspect them in HTML.

### 3) “Build/export path can silently drift between embeddings and points”
**Status: meaningfully addressed.**

Evidence:
- `scripts/build_semantic_map.py::_canonicalize_semantic_records()` rejects point/embedding set drift and preserves canonical point order.
- `tests/test_semantic_build_cli.py::test_canonicalize_semantic_records_rejects_drift` covers the failure case.
- `analyze_points()` separately rejects misaligned article id sets.

This is boring defensive plumbing, which is exactly why it matters.

### 4) “Semantic artifacts are under-tested / easy to regress”
**Status: addressed enough for this scope.**

Evidence:
- semantic analysis tests cover clustering, outliers, misaligned ids, and cross-source summaries
- projection tests cover finite coordinates and single-row fallback
- export tests cover analysis JSON and semantic HTML shell
- dbstore tests cover model dimension handling, candidate selection, vector parsing/literals, and enriched neighbors
- neighbor CLI has output tests

For this feature area, the test net is now respectable.

## Current architecture assessment

## Good decisions now in place

### Embedding space is the authority
That should have been true from the start. It is true now.

`src/semantic/analyze.py` builds density, cluster seeds, attachment, and outlier labeling from embedding cosine distance, not from PCA geometry. That is the correct architectural center.

### Projection is demoted to what it actually is: a view
`src/semantic/project.py` is now just a projection step that turns embeddings into display coordinates. Nothing in there pretends PCA coordinates define semantic truth. Good.

### Contracts are explicit enough for artifacts
The dataclass contracts in `src/semantic/contracts.py` are boring and readable. For this repo, that’s fine. They clearly separate:
- raw embedding artifacts
n- projected point artifacts
- per-point analysis
- cluster summaries
- build metrics

That makes the export pipeline comprehensible.

### The explorer is a consumer, not the source of truth
`src/semantic/export.py` serializes analysis results into the page and the JS sticks mostly to filtering, selection, and display. That is the right boundary.

## Remaining issues worth fixing now

There are only **two** things I’d put in the “fix now” bucket.

### 1) Neighbor export currently does an N+1 query pattern
**Priority: medium**

`load_projected_points(..., include_neighbors=True)` calls `load_neighbors_for_articles()`, which loops article ids and calls `nearest_neighbors()` once per article.

For the current default map size this probably won’t explode, but it is still the one architectural inefficiency in the feature path that is worth caring about now because it sits directly on the semantic explorer build.

Evidence:
- `src/semantic/dbstore.py::load_projected_points()`
- `src/semantic/dbstore.py::load_neighbors_for_articles()`
- `src/semantic/dbstore.py::nearest_neighbors()`

Why it matters:
- map export cost grows linearly in extra DB round-trips
- it is avoidable
- it will get annoying before the actual clustering code does

### Recommended implementation
Replace per-article neighbor lookup with one set-based query using a seed article list and a window function.

Concrete approach:
1. Pass the article id list into a SQL CTE like `seed_articles(article_id)`.
2. Join `article_embeddings seed` against `article_embeddings other` once.
3. Rank neighbors with `row_number() over (partition by seed.article_id order by other.embedding <=> seed.embedding)`.
4. Filter to `row_number <= :limit`.
5. Group rows back into `dict[int, list[NeighborArtifact]]` in Python.

That keeps the existing artifact contract intact while removing the N+1 shape.

### 2) The semantic HTML export mixes serialization, layout, and app logic in one giant function
**Priority: medium-low**

`src/semantic/export.py::_post_script()` is now doing a lot:
- payload injection
- CSS shell construction
- filter wiring
- inspector rendering
- highlight behavior
- plot updates

This is still acceptable today, but it is the likeliest place to become miserable if the explorer gets one more round of feature work.

Why it is worth a small cleanup now:
- the current feature is already past “tiny helper string” size
- reviewing or changing explorer behavior is harder than it should be
- this is a local refactor, not a redesign

### Recommended implementation
Do **not** rewrite the explorer. Just split `_post_script()` into small helpers in Python that emit named JS blocks, or move the browser code into a versioned static template string/file and inject only the JSON payload.

Minimal acceptable step:
- extract CSS shell markup
- extract inspector JS
- extract filtering/redraw JS
- keep the final `write_html(... post_script=...)` contract unchanged

That preserves behavior while making future review less annoying.

## Things I do **not** think need action now

### The O(n²) distance matrix in `analyze_points()`
For the current scale and usage, this is fine.

Yes, it is quadratic. No, that is not automatically a problem here. The feature appears aimed at small offline exploration slices, not million-row clustering. Don’t optimize this out of boredom.

### The dataclass contract style in `src/semantic/contracts.py`
Also fine for now.

If the whole repo later standardizes on Pydantic everywhere, sure, revisit it. But in this semantic slice the contracts are simple, readable, and stable. This is not where the pain is.

### PCA specifically
PCA is acceptable as a first-pass projection for an offline semantic map. If someone later wants UMAP/t-SNE as an option, that’s a product decision, not a current architecture defect.

## Bottom line

The previous critical semantic problems appear **meaningfully resolved**.

What exists now is coherent:
- semantic truth comes from embeddings
- analysis artifacts are explicit
- export path checks alignment
- explorer surfaces semantic metadata instead of inventing it
- tests cover the important failure modes

That’s enough to stop treating this feature as shaky.

## Recommended next step

Make **only** these two follow-up changes if there is another implementation pass:
1. remove the neighbor-query N+1 pattern
2. split the giant explorer script/export function into smaller reviewable pieces

If there is no immediate follow-up pass, I would still consider the current implementation acceptable to ship/use as-is.

## Acceptance judgment

**Accepted with two modest follow-ups, not blockers.**
