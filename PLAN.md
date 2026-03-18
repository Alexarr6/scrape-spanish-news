# PLAN.md — Phase 1: real 2D semantic explorer app shell

## Phase boundary
Phase 0 is done enough to stand on:
- FastAPI semantic explorer endpoints exist
- typed API contracts exist
- Vite/React/deck.gl frontend workspace exists
- the app shell layout exists
- the current UI is mostly placeholders

So Phase 1 is not “set up deck.gl” or “invent the API.” That part is already on the table.

**Phase 1 goal:** turn the current foundation into a genuinely usable **2D semantic explorer app shell** with bounded interaction, inspection, filtering, and selection behavior.

This phase must:
1. keep the existing semantic backend as the canonical source of truth
2. build on the existing explorer API instead of bypassing it
3. deliver one serious 2D interaction loop around the semantic map
4. stay small and sharp
5. use **atomic git commits per logical completed task**

Not in this phase: 3D, backend redesign, scraper changes, platform work, timeline/product sprawl, or a frontend rewrite because someone got bored.

## What exists now (repo reality after Phase 0)

### Backend/API already present
Relevant files already in place:
- `src/api/v1/semantic.py`
- `src/api/contracts/semantic.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`

Current API surface already gives us the basic contract we need:
- `GET /api/v1/semantic/explorer/points`
- `GET /api/v1/semantic/explorer/filters`
- `GET /api/v1/semantic/explorer/articles/{article_id}`

### Frontend foundation already present
Relevant files already in place:
- `frontend/src/App.tsx`
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/components/ExplorerLayout.tsx`
- `frontend/src/components/StatusBar.tsx`
- `frontend/src/components/FilterBar.tsx`
- `frontend/src/components/MapPanel.tsx`
- `frontend/src/components/InspectorPanel.tsx`
- `frontend/src/hooks/useExplorerBootstrap.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`

Current frontend state is basically a scaffold:
- it loads bootstrap data
- it renders the app layout
- deck.gl is wired but renders no actual semantic point layer
- filters are read-only lists
- inspector is a placeholder
- no real selection/highlight/query loop exists yet

That is exactly the right point to start Phase 1.

## Product outcome for Phase 1
After Phase 1, a human should be able to:
- open the explorer and see the semantic point cloud rendered as an actual 2D deck.gl view
- pan/zoom the map and understand what they are looking at
- hover a point for quick context
- click a point to select it and open a real inspector
- use bounded filters/search to narrow the dataset
- see selection/highlight behavior that makes semantic neighborhood exploration practical
- click neighbors in the inspector to move through the semantic graph

If the result still feels like a demo skeleton, Phase 1 failed.

## Chosen UX for this phase

### Single-screen explorer
Keep one screen with three areas:
1. **Status/header bar** — title, dataset counts, projection set, reset action
2. **Main 2D map panel** — deck.gl scatterplot interaction surface
3. **Inspector/filter side panels** — controls plus selected article detail

No extra routes unless a tiny `/ -> /explorer` redirect is already in place or nearly free.

### 2D map interaction
Bounded interaction model:
- render semantic points via `ScatterplotLayer`
- orthographic 2D view only
- pan + zoom enabled
- hover tooltip with: title, source, section/date, cluster/outlier hint
- click selects a point
- selected point gets clear visual emphasis
- optional neighbor highlighting is allowed **only** for the selected article’s nearest neighbors and only if it stays simple

No 3D. No pitch. No bearings. No basemap theater.

### Inspector/sidebar behavior
Inspector should answer: “what is this article, and why is it near these others?”

When nothing is selected:
- show concise instructions and current dataset summary

When a point is selected:
- article title, source, date, section
- summary or excerpt
- semantic summary block:
  - cluster id
  - cluster size
  - outlier flag
  - neighbor count
  - source neighbor diversity if available
- nearest neighbors list with similarity
- actions:
  - open source article
  - clear selection
  - click neighbor -> select that neighbor

No tabs. No mega-inspector. No report builder.

### Filters/search behavior
Bounded filter set for Phase 1:
- search text
- source select
- section select
- cluster select
- outlier-only toggle
- date from / date to
- reset all

Behavior rules:
- filter changes should trigger backend-backed refetch of points
- filters should be visible and editable, not just displayed as metadata
- active filters should be easy to clear
- empty results state must be explicit and useful

### Selection/highlight behavior
Keep it dead simple:
- one selected article at a time
- one hovered article at a time
- selected article persists across pan/zoom
- if filters remove the selected article from the current result set, clear selection and reset the inspector to empty state
- selected point uses stronger radius/stroke/opactity treatment than the rest
- hover should never visually compete with selection
- if neighbor highlighting is implemented, it should be a subtle secondary emphasis, not a rainbow mess

## Backend/API plan for Phase 1
The backend is mostly in place. Extend it only where the current contract is too thin for the real UI.

### Primary backend goal
Keep the backend as the sole owner of semantic truth and query shaping. The frontend should only own view state.

### Likely backend changes
Files likely to change:
- `src/api/v1/semantic.py`
- `src/api/contracts/semantic.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`
- maybe `tests/test_semantic_dbstore.py` if lower-level query coverage is cleaner there

### Backend work items
1. **Harden the points query contract for real filter usage**
   - confirm all intended Phase 1 filters work end-to-end: `source`, `section`, `cluster_id`, `outlier_only`, `date_from`, `date_to`, `search`, `limit`
   - ensure metadata remains coherent when filters are applied

2. **Ensure article detail is sufficient for the inspector**
   - confirm detail payload includes everything the inspector needs without additional hacks
   - if needed, add only small contract fields, not a giant detail object

3. **Optionally support selected-neighbor highlighting cleanly**
   - if the current detail response already includes enough neighbor ids, reuse it
   - do not add a separate graph API in this phase

### Backend non-goals
- no new persistence layer
- no semantic recomputation endpoint circus
- no backend redesign around frontend whims

## Frontend implementation plan for Phase 1

### State/data flow shape
Replace the current one-shot bootstrap mentality with a real explorer state flow.

Recommended owned frontend state:
- `filters`
- `selectedArticleId`
- `hoveredArticleId`
- `viewState`
- `colorMode` only if one bounded toggle is added

Recommended async data split:
- points query tied to current filters
- article detail query tied to `selectedArticleId`
- filter options query loaded once or reused from bootstrap

### Likely frontend file/module changes
Existing files likely to change heavily:
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/components/StatusBar.tsx`
- `frontend/src/components/FilterBar.tsx`
- `frontend/src/components/MapPanel.tsx`
- `frontend/src/components/InspectorPanel.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/styles.css`

Likely new files/modules:
- `frontend/src/hooks/useExplorerPoints.ts`
- `frontend/src/hooks/useArticleDetail.ts`
- `frontend/src/lib/query.ts` or equivalent query-string helper
- `frontend/src/lib/format.ts` for date/label formatting
- `frontend/src/state/explorerState.ts` or `frontend/src/hooks/useExplorerState.ts`
- optional `frontend/src/components/Tooltip.tsx` if keeping tooltip rendering separate stays cleaner

### Task 1 — replace bootstrap-only loading with real explorer state and query flow
Work:
- separate filters/options/points/detail fetching concerns
- add typed query building for points endpoint
- make selection and filters first-class UI state
- keep state local and boring; no state-management cosplay unless clearly needed

Done when:
- filters drive point queries
- selecting a point drives detail queries
- loading/error state is specific and understandable

### Task 2 — turn `MapPanel` into a real 2D semantic map
Work:
- add `ScatterplotLayer` backed by actual point data
- compute stable view state from bounds
- implement hover + click handlers
- encode selected vs unselected points clearly
- add tooltip rendering with bounded article context

Done when:
- the map is the real product surface, not a “deck.gl wired” badge of shame

### Task 3 — implement real filter/search controls
Work:
- make `FilterBar` interactive instead of informational
- wire controls to backend query params
- include reset-all action
- show active filter summary or obvious applied-state affordances

Done when:
- filtering materially changes the dataset and is pleasant enough to use twice in a row

### Task 4 — implement the real inspector workflow
Work:
- fetch selected article detail on click
- render selected article metadata and semantic summary
- render neighbors list and neighbor click-to-select behavior
- support clear selection and open source article action
- show honest empty/loading/error states

Done when:
- the inspector explains the selected point instead of apologizing for not existing yet

### Task 5 — shell polish and practical UX cleanup
Work:
- improve `StatusBar` so it reflects active dataset state, selection count, and reset affordance
- make layout resilient for typical laptop screen widths
- ensure empty/error/loading states do not destroy the page structure
- keep styling clean and functional, not ornate

Done when:
- the app feels like a tool, not a pile of independently working widgets

## Verification plan

### 1) Existing repo gate
```bash
make check
```
Expected:
- existing backend/test gate remains green

### 2) Semantic explorer API tests
```bash
uv run python -m pytest -q tests/test_api_semantic_explorer.py tests/test_semantic_dbstore.py
```
Expected:
- points endpoint supports the actual Phase 1 filter set
- detail endpoint supports inspector needs
- selection-related contract assumptions are covered

### 3) Frontend type/build check
```bash
cd frontend
npm install
npm run build
```
Expected:
- clean build
- no type errors

### 4) Practical app smoke check
Run backend + frontend locally and verify manually:
- explorer page loads
- semantic points render as real scatterplot points
- hover tooltip works
- click selection updates highlight and inspector
- filters refetch and narrow points
- clearing filters works
- neighbor click changes selection
- empty results state is clear
- network/API failures produce sane UI feedback

### 5) Canonical-backend sanity check
Verify that:
- the map point count reflects backend-filtered results, not client-side fakery
- inspector content matches the canonical backend response
- neighbor list comes from existing semantic neighbor logic/path

### 6) Commit granularity check
```bash
git log --oneline --decorate -n 15
```
Expected:
- atomic commits per logical completed task
- no giant “phase1 ui” landfill commit

## Required git discipline for the later implementer
This is mandatory, not aspirational.

The implementer must use **atomic git commits per logical completed task**.

Minimum expected commit boundaries:
1. explorer state/query-flow refactor
2. real deck.gl map rendering + hover/select behavior
3. interactive filters/search wired to backend
4. real inspector + neighbor navigation
5. shell polish, docs, and verification updates

Rules:
- each commit must leave the repo coherent
- each commit should correspond to one completed logical step
- do not bury unrelated backend and frontend work together if they are not part of the same finished task
- no “misc fixes” garbage truck commit at the end

If the commit history looks like one panic dump, the implementer ignored the contract.

## Risks and mitigations

### Risk: Phase 1 bloats into a frontend architecture project
Mitigation:
- reuse the existing scaffold
- keep one route, one map, one inspector, one filter set
- avoid adding framework furniture unless a real problem forces it

### Risk: frontend starts inventing semantic behavior client-side
Mitigation:
- backend owns semantic truth and query shaping
- frontend owns only view state and presentation
- no client-side neighbor/clustering reinvention

### Risk: map interaction is technically present but ergonomically useless
Mitigation:
- prioritize hover/select/tooltip/highlight quality over decorative extras
- ship fewer controls, but make them actually work

### Risk: inspector becomes a dumping ground
Mitigation:
- keep it article-centric
- only include fields that explain the selected point and its nearest neighbors

### Risk: filter/query flow becomes brittle
Mitigation:
- centralize query param construction
- keep filter state explicit and typed
- test the real supported filter set, not just happy-path bootstrap

## Explicit deferred items
Absolutely not part of Phase 1:
- 3D explorer modes
- timeline animation/playback
- compare-two-articles or compare-two-clusters workflows
- advanced full-text search system
- cross-source comparison dashboards
- saved views/share links/annotations
- auth or multi-user features
- deployment/platform work
- backend semantic redesign
- scraper/provider redesign
- frontend platform rewrite

## Recommended implementation order
1. refactor explorer state and API query flow around real filters + selection
2. implement real deck.gl scatterplot rendering and interaction
3. implement interactive filters/search
4. implement inspector + neighbor navigation
5. polish shell, verify behavior, document run/smoke steps

## Bottom line
Phase 0 proved the wiring. Phase 1 needs to prove the product. Build one bounded, actually usable 2D semantic explorer on top of the current backend truth. No 3D clownery, no backend detour, no frontend philosophy retreat. Just make the thing properly usable, and commit it atomically like an adult.