- State: DONE
- Current phase: iter/007 Phase A implemented — Stories → Explorer now uses real story-cluster scope via `sem_story_cluster`
- Last update: 2026-03-23 UTC

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