- State: DONE
- Current phase: frontend.react pass completed for iter/005 editorial-analysis product integration on `iter/005`
- Last update: 2026-03-23 UTC

## Frontend.react completion — editorial layer now visible in Stories + Explorer

Completed the approved frontend slice using the shaped editorial payloads.

### What shipped
- built shared editorial UI primitives for status, dimensions, evidence, and article-level rendering:
  - `frontend/src/components/editorial/EditorialStatusBadge.tsx`
  - `frontend/src/components/editorial/EditorialDimensionGrid.tsx`
  - `frontend/src/components/editorial/EditorialEvidenceList.tsx`
  - `frontend/src/components/editorial/EditorialAnalysisCard.tsx`
  - `frontend/src/components/editorial/editorialFormat.ts`
- added `frontend/src/components/stories/EditorialLensSection.tsx` for cluster-scoped comparison in Stories
- wired `StoryFocusPanel` to show:
  - new `Editorial lens` section between Coverage and Articles by source
  - article-card preview badges from `member.editorial_preview`
  - full article-level editorial card inside selected article detail
- wired `ExplorerContextRail` to show a compact article-level editorial card before cluster context
- added sober editorial styling in `frontend/src/styles.css` with muted status tones, comparison grids, evidence blocks, and restrained chips/callouts

### UX constraints preserved
- confidence, applicability, review state, and evidence are visible in the main UI
- cluster comparison is framed as story-scoped source behavior, not universal outlet ideology
- no raw operator/debug diagnostics dump in the main product surfaces
- no giant ideology toy nonsense

### Verification
- `cd frontend && npm run build`
  - result: passed
  - note: existing Vite/loaders.gl warning remains about `spawn` browser external and chunk size, but production build succeeds

### Files updated in this pass
- `frontend/src/components/editorial/EditorialStatusBadge.tsx`
- `frontend/src/components/editorial/EditorialDimensionGrid.tsx`
- `frontend/src/components/editorial/EditorialEvidenceList.tsx`
- `frontend/src/components/editorial/EditorialAnalysisCard.tsx`
- `frontend/src/components/editorial/editorialFormat.ts`
- `frontend/src/components/stories/EditorialLensSection.tsx`
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/styles.css`
- `STATUS.md`
- `RESULTS.md`

## Implementer completion — shaped editorial payloads now land in Stories + Explorer contracts

Completed the bounded backend/read-model slice the frontend architect asked for.

### What changed
- added shaped product-facing editorial data to `ExplorerArticleDetail.editorial`
- added shaped cluster-scoped comparison data to `StoryClusterDetail.editorial_summary`
- added lightweight `StoryClusterMemberItem.editorial_preview` for list/badge use
- kept the raw operator/audit editorial API separate; product surfaces do **not** need to consume raw editorial rows
- updated frontend TS types so the next `frontend.react` pass can wire shared editorial components without inventing contracts

### Payload design choices
- uncertainty/applicability are first-class, not hidden:
  - `analysis_status`
  - `editorial_applicability`
  - `editorial_applicability_reason`
  - `review_flags`
  - compact evidence spans
  - cluster `confidence_note` + `scope_note`
- no fake one-number bias abstraction; the shaped payload still carries article type, bias label/score/confidence, tone, opinionatedness, sensationalism, rhetorical certainty, framing devices, evidence, and review semantics
- cluster-level shaping is conservative:
  - source-by-source breakdowns
  - applicability/article-type/bias/tone/opinionatedness counts
  - top framing devices with example article ids
  - cluster signals only when support clears a minimal threshold
  - explicit mixed/contested signal note when bias labels diverge

### Files updated in this implementer pass
- `src/api/contracts/semantic.py`
- `src/api/contracts/clusters.py`
- `src/api/v1/semantic.py`
- `src/analysis/readside.py`
- `frontend/src/lib/types.ts`
- `tests/test_api_semantic_explorer.py`
- `tests/test_api_clusters.py`
- `STATUS.md`
- `RESULTS.md`

### Verification
- `PYTHONPATH=.venv/lib/python3.11/site-packages python3 -m pytest tests/test_api_semantic_explorer.py tests/test_api_clusters.py`
  - result: `10 passed`
- `PYTHONPATH=.venv/lib/python3.11/site-packages .venv/bin/ruff check --fix src/api/contracts/semantic.py src/api/contracts/clusters.py src/api/v1/semantic.py src/analysis/readside.py`
  - result: passed for touched backend source files

### Handoff readiness
Repo is now ready for `frontend.react` to:
1. build shared editorial display components
2. wire **Stories first** against `StoryClusterDetail.editorial_summary` and member previews
3. wire **Explorer** against `ExplorerArticleDetail.editorial`

That’s the useful slice. Raw rows stay in the audit lane where they belong.


## Frontend architect completion — editorial analysis as a first-class UI layer

Completed the repo-specific frontend architecture pass for integrating persisted editorial analysis into the existing product surfaces.

### What was inspected
- planning docs:
  - `PROJECT_BRIEF.md`
  - `TASK_CONTRACT.md`
  - `PLAN.md`
  - prior `STATUS.md`
- frontend surfaces:
  - `frontend/src/components/stories/StoryFocusPanel.tsx`
  - `frontend/src/components/explorer/ExplorerContextRail.tsx`
  - `frontend/src/routes/ClusterBrowserPage.tsx`
  - `frontend/src/routes/ExplorerPage.tsx`
  - `frontend/src/lib/types.ts`
  - `frontend/src/lib/api.ts`
- backend/UI contracts:
  - `src/api/contracts/semantic.py`
  - `src/api/contracts/clusters.py`
  - `src/api/contracts/editorial.py`
  - `src/api/v1/semantic.py`
  - `src/api/v1/clusters.py`
  - `src/analysis/readside.py`

### Main architecture decisions
- **StoryFocusPanel is the highest-value editorial surface.**
  - Add a first-class `Editorial lens` section between Coverage and Articles-by-source.
  - Keep story cluster as the main comparison scope.
- **Article-level editorial analysis should appear in both Stories and Explorer.**
  - Stories article detail gets the full card.
  - ExplorerContextRail gets a compact variant.
- **User-facing analytical surfaces must stay separate from operator/debug surfaces.**
  - Product surfaces get shaped summaries.
  - Raw diagnostics stay in the existing editorial API / audit flows.
- **Applicability, evidence, confidence, and uncertainty are non-optional UI fields.**
  - No one-number bias toy.
  - No fake certainty.

### Files updated in this architect pass
- `UI_SPEC.md`
- `COMPONENT_MAP.md`
- `STATUS.md`

### Implementer handoff — required backend contracts
The next implementation pass should provide:

1. `ExplorerArticleDetail.editorial`
   - compact article-level editorial summary for product use
2. `StoryClusterDetail.editorial_summary`
   - cluster-scoped comparison payload with source summaries, applicability coverage, cluster signals, and confidence/scope notes
3. optional `StoryClusterMemberItem.editorial_preview`
   - minimal badge-oriented preview for article list items

These should be shaped read models, not raw diagnostics dumps.

### Recommended frontend build sequence after contract work
1. create shared editorial components:
   - `EditorialStatusBadge`
   - `EditorialDimensionGrid`
   - `EditorialEvidenceList`
   - `EditorialAnalysisCard`
2. create `EditorialLensSection` for StoryFocusPanel
3. wire StoryFocusPanel:
   - editorial lens section
   - article detail editorial card
   - optional member preview badges
4. wire ExplorerContextRail compact editorial card

### Minimum acceptable shipped slice
- StoryFocusPanel shows cluster-level editorial comparison
- selected article in Stories shows evidence-backed editorial card
- selected article in Explorer shows compact editorial card
- pending / failed / limited / out_of_domain / low-confidence states are visible
- no surface reduces the output to a single ideology score

### Recommendation: what the implementer must build next
**Build the backend/read-model contract slice first**:
- extend semantic article detail payload with `editorial`
- extend cluster detail payload with `editorial_summary`
- preserve example article ids and uncertainty states in those payloads
- then hand off to frontend.react for bounded UI construction

That is the next real move. Anything else is lipstick on the database row.