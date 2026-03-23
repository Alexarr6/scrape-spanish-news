- State: DONE
- Current phase: iter/007 Phase B implementer anti-bridge pass completed; ready for Phase C scrape coverage architect review
- Last update: 2026-03-23 UTC

## iter/007 Phase B implementer status
- shipped the bounded anti-bridge clustering pass recommended by `ARCH_REVIEW.md`
- tightened risky pair handling in `ClusterPipeline.score_pair()` with explicit penalties/diagnostics for:
  - follow-up drift
  - secondary-form article pairs (`analysis`, `explainer`, `feature`, `interview`)
  - entity-glue pairs that share actors but lack enough event-specific lexical support
- replaced raw permissive connected components with a guarded incremental merge path that:
  - grows from strongest edges first
  - blocks risky bridge pairs from fusing components cheaply
  - requires stronger multi-edge support before attaching articles to an existing cluster
- expanded persisted/read-side member diagnostics via `membership_reason_json` and cluster detail payloads so support edge counts, best/mean support, supporting article ids, risky-bridge flags, and penalties are inspectable
- added explicit regression coverage for:
  - bridge-article false merges
  - follow-up separation
  - same-event/different-headline matching
  - analysis/explainer bridge contamination
- exact touched files and verification are now recorded in `RESULTS.md`

## iter/007 Phase A architect review summary
- verdict: mostly real fix, not just a relocated title-search hack
- real improvement: Stories now hands Explorer a true story-cluster scope via `sem_story_cluster`, and backend filtering resolves membership through `cluster_members`
- original review flaw is now fixed: `useExplorerUrlState()` now serializes and clears `sem_story_cluster`, so the Explorer URL/state contract round-trips cleanly again
- object-boundary cleanup: the misleading Explorer → Stories reverse link that treated a semantic cluster id like a story cluster id has been removed rather than papered over
- test read: backend tests are meaningful for membership filtering, but frontend state-contract coverage is missing exactly where the remaining bug lives
- cleanup patch landed: `sem_story_cluster` now participates in Explorer URL serialization/reset, and the misleading Explorer → Stories reverse link that treated semantic cluster ids like story cluster ids was removed
- frontend note: the repo still lacks a dedicated frontend unit-test harness, so this cleanup was verified with targeted build/typecheck rather than new browser-side regression tests
- exact next move into Phase B: do the clustering deep review focused on connected-component bridge merges / false same-story merges

## iter/007 planner completion — phased route locked

Planned a dependency-aware four-phase route for iter/007:

### Phase A — real Stories → Explorer handoff
- replace the current seeded title-search behavior with explicit **story-cluster-scoped** Explorer navigation
- recommended primary route/query key: `sem_story_cluster`
- preserve `sem_article` when opening Explorer from a selected article
- do **not** misuse semantic `cluster_id` for story-cluster identity
- smallest shippable slice: backend Explorer membership filter + Stories link update + Explorer URL/state + honest context chip/copy

### Phase B — same-story clustering deep review + bounded improvement
Clustering architect must inspect:
- candidate article windowing and limits
- pair scoring weights and penalties in `ClusterPipeline.score_pair()`
- connected-components/transitive merge risk
- persistence/read-side diagnostics and representative selection
- false merge / false split evidence in current tests and runtime assumptions

### Phase C — scrape coverage/source imbalance deep review + bounded improvement
Scrape architect must inspect:
- per-source adapter/feed/discovery differences
- refresh-window and scheduler asymmetry between story and explorer refresh flows
- where coverage attrition happens: discovery, extraction, persistence, enrichment, clustering, semantic sync/project
- whether imbalance is real publisher behavior or a pipeline defect

### Phase D — final whole-project architect review + bounded implementer follow-up
Final architect review must assess:
- navigation integrity across Stories and Explorer
- same-story clustering credibility after the bounded fix
- scrape/source operational credibility after the bounded fix
- cross-surface analytical UX and remaining overclaim/confusion risks

### Verification route by phase
- Phase A: `pytest tests/test_api_semantic_explorer.py tests/test_api_clusters.py` + `frontend npm run build`
- Phase B: clustering/unit/API slice + targeted ruff on analysis files
- Phase C: adapter/discovery tests + targeted ruff on adapter/runtime surfaces; full wrappers only if env is present
- Phase D: full `pytest` + `frontend npm run build`

## Key planning decision
The repo currently conflates two different concepts:
- Stories **same-story clusters**
- Explorer **semantic clusters**

That is the core reason the current handoff is weak.
iter/007 should fix that first by making Explorer able to open in a real story-cluster scope instead of pretending that a title search is equivalent.