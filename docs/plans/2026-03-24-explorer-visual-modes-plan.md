# Explorer visual modes plan — 2026-03-24

## Blunt read

The current Stories → Explorer handoff fixed the old lie (`sem_story_cluster` instead of fake text search), but it still defaults to the wrong product behavior for analysis.

Right now a story cluster opened from Stories becomes a **hard subset** in Explorer. That is useful sometimes, but it kills the main value of the semantic map: context. You can no longer see where that story sits inside the wider cloud.

So the missing product model is not “another filter.” It is a clean separation between:

1. **dataset scope** — what points are loaded at all
2. **match logic** — which points satisfy the active story/query/lens target
3. **visual treatment** — whether matches hide everything else or merely stand out
4. **color lens** — what hue encodes across the currently visible field

If those four things stay mashed together, Explorer keeps feeling clever-but-muddy.

---

## Recommended product model

## 1. Two visual modes, one target model

Explorer should support a single active **match target** plus a **visual mode**.

### Match target
A match target answers: *which points count as “the thing I care about”?*

Phase-1-supported targets:
- `story_cluster:<id>`
- `semantic_cluster:<id>`
- `search:<text>`
- `source:<slug>`

Phase-2+ targets:
- `editorial:bias_label=<label>`
- `editorial:tone_emotional=<label>`
- `editorial:opinionatedness=<label>`
- `editorial:review_flag=<flag>`
- compound targets / saved lenses

### Visual mode
A visual mode answers: *what happens to non-matching points?*

#### `highlight`
- keep the full dataset visible
- show matching points with stronger color/opacity/stroke
- keep non-matches receded but still readable
- this should be the default when opening from **Stories**

#### `filter`
- hide non-matching points entirely
- use when the user wants a narrow working set
- this is the current `sem_story_cluster` behavior and should remain available, just no longer the only move

That’s the right split. Anything else is muddled UX theater.

---

## 2. Separate “Visual mode” from “Color by”

Current Explorer already has `colorMode = neutral | source | cluster`. Keep that idea, but stop pretending it is the same as highlight/filter state.

### Recommended controls

#### Visual mode
- `Highlight`
- `Filter`

#### Color by
Phase 1:
- `Neutral`
- `Source`
- `Semantic cluster`
- `Active match`

Later:
- `Bias`
- `Tone`
- `Opinionatedness`
- `Review status`

### Why `Active match` matters
If the user searches “OnlyFans” or opens a story cluster, they often want “matched points in red, everything else blue/neutral.” That is **not** the same as color-by-source or color-by-cluster. It is a special color mode keyed off the current match target.

So the product needs:
- **visual mode** = highlight vs filter
- **color by** = neutral/source/cluster/active-match/editorial lens

Those are orthogonal.

---

## 3. Stories → Explorer default behavior

### When opening a story cluster from Stories
Default Explorer behavior should be:
- dataset scope: current Explorer dataset window (not just cluster members)
- active match target: `story_cluster:<id>`
- visual mode: `highlight`
- color by: `active-match`
- optional selected article preserved if launched from article detail

That gives the user the thing they actually want:
- **the cluster is visually obvious**
- **the rest of the cloud stays visible for context**
- the user can still toggle to `Filter` if they want a pure subset

### Suggested rail copy
- “Story cluster 412 highlighted in context”
- secondary action: `Switch to filter mode`
- tertiary action: `Clear story context`

This should feel like a lens, not a trap.

---

## 4. Query/search behavior

Search needs the same dual behavior.

### Example
Search `OnlyFans`:
- **Highlight mode**: all points remain visible; matches get strong color and larger emphasis
- **Filter mode**: only matches stay

### Match logic for Phase 1
Use the current search semantics:
- title
- summary

The frontend can display a “matches current search” emphasis without backend semantic search changes.

---

## 5. Editorial lens groundwork

Do **not** redesign the whole editorial ontology now. That would be classic scope-creep bullshit.

What Phase 1 should do is define the state model so future lenses plug in cleanly.

### Future lens model
```ts
type ExplorerMatchTarget =
  | { kind: 'story-cluster'; id: number }
  | { kind: 'semantic-cluster'; id: number }
  | { kind: 'search'; query: string }
  | { kind: 'source'; source: string }
  | { kind: 'editorial'; dimension: 'bias_label' | 'tone_emotional' | 'opinionatedness' | 'review_flag'; value: string }
```

And:
```ts
type ExplorerVisualMode = 'highlight' | 'filter'
type ExplorerColorMode =
  | 'neutral'
  | 'source'
  | 'cluster'
  | 'active-match'
  | 'bias'
  | 'tone'
  | 'opinionatedness'
```

Phase 1 only has to fully implement the first four color modes. The editorial ones can be reserved/disabled until the points payload carries enough metadata.

---

## What the current repo already supports

## Already supported in backend/frontend contracts

### Backend
Current `/api/v1/semantic/explorer/points` already supports:
- `search`
- `source`
- `section`
- `cluster_id`
- `sem_story_cluster`
- `outlier_only`
- date window
- bounded point limit

Current points payload already includes enough for:
- neutral coloring
- source coloring
- semantic-cluster coloring
- selection / hover / neighbor emphasis

### Frontend
Current frontend already has:
- Stories → Explorer handoff builder in `frontend/src/lib/navigation.ts`
- URL state serialization in `useExplorerUrlState.ts`
- a top control bar with color mode state
- a context rail with seed chip / legend
- `MapPanel` emphasis tiers for selected / hovered / neighbor / receding points

That means the repo is **close**. It is missing the state separation and one crucial contract for story-cluster highlighting-in-context.

---

## Minimal contract changes needed

## Change A — add story-cluster membership metadata onto explorer points

### Why
For `highlight` mode, Explorer needs to know whether each visible point belongs to the seeded story cluster **without filtering the dataset down to that cluster**.

### Smallest useful addition
Add to each explorer point:
```json
{
  "analysis": {
    "story_cluster_ids": [412]
  }
}
```

Even if today that usually means zero-or-one ids, use an array. It keeps the contract honest if later membership modeling changes.

### Why this is the right minimal change
- it avoids shoving giant article-id lists into the URL
- it avoids requiring Explorer to fetch full cluster detail just to paint the map
- it lets the frontend compute both `highlight` and `filter` behavior from the same loaded dataset
- it also sets up future “color by active story cluster” behavior cleanly

## Change B — add lightweight editorial preview fields to explorer points (Phase 2, not required for Phase 1)

When you want color-by-bias/tone on the map, the points payload must expose a tiny per-point editorial preview. Something like:
```json
{
  "editorial_preview": {
    "analysis_status": "completed",
    "bias_label": "center_left",
    "tone_emotional": "elevated",
    "opinionatedness": "high",
    "needs_review": false
  }
}
```

Do **not** block Phase 1 on this.

## Change C — optional URL-state additions

Recommended new Explorer URL params:
- `sem_mode=highlight|filter`
- `sem_color=neutral|source|cluster|active-match`
- `sem_story_focus=<id>` or reuse `sem_story_cluster` as the active match target

Recommended semantics:
- `sem_story_cluster` should stop meaning only “backend filter the dataset”
- instead, treat it as “active story-cluster target”
- whether that target filters or highlights is determined by `sem_mode`

That avoids the current semantic confusion.

### Backend interpretation rule
- if `sem_story_cluster` is present **and** `sem_mode=filter`, backend applies membership filter
- if `sem_story_cluster` is present **and** `sem_mode=highlight`, backend does **not** filter dataset; it only returns membership metadata so frontend can highlight

That is the cleanest contract.

---

## Phase plan

## Phase 1 — ship the useful behavior now

### Product goal
Make Stories → Explorer feel right.

### Scope
1. add Explorer visual mode state: `highlight | filter`
2. add color mode `active-match`
3. default Stories handoff to:
   - `sem_story_cluster=<id>`
   - `sem_mode=highlight`
   - `sem_color=active-match`
4. add point-level story-cluster membership metadata
5. update `MapPanel` rendering logic:
   - matching points emphasized strongly in highlight mode
   - non-matching points receded, not hidden
   - filtered mode keeps current subset behavior
6. update rail/control copy so the difference is obvious

### Explicit non-goals
- no semantic backend rewrite
- no multi-select lens combinator UI
- no full editorial color map yet
- no ontology redesign

## Phase 2 — editorial lens plumbing

### Scope
1. add lightweight editorial preview onto points payload
2. add `Color by: Bias / Tone / Opinionatedness`
3. optionally add filter controls for editorial dimensions
4. define legend and unknown/pending handling

### Constraint
Only do this once the Phase 1 visual model is stable. Otherwise you are bolting metadata onto a confused UI.

## Phase 3 — richer lens composition

Potential later additions:
- combined filters + highlight targets
- saved lenses
- compare two sources within a story context
- multiple simultaneous highlight groups
- story-cluster vs semantic-cluster overlap mode

Not now.

---

## Recommended agent split

## Frontend architect — first
Use frontend architect for:
- state model cleanup
- URL semantics
- control bar / legend / rail interaction design
- exact highlight-vs-filter behavior rules
- match-target abstraction that can survive editorial lenses later

This is architect work because the hard part is product model integrity, not JSX typing.

## Frontend.react — second
Use frontend.react for:
- implementing the new controls and URL state
- `MapPanel` rendering changes
- rail/control/legend updates
- Stories handoff behavior update
- build verification

## Backend implementer — only if contract change is approved
Backend implementer is needed only for:
- point-level `story_cluster_ids` membership metadata
- later, point-level editorial preview metadata

Do **not** wake backend implementer for Phase 1 unless the team agrees on that exact tiny contract. Without it, frontend can still fake some behaviors, but the full-cloud story highlight will stay half-broken.

---

## Exact frontend architect handoff

Use this handoff verbatim:

> Design the Explorer interaction model for the repo’s existing React + FastAPI implementation so it supports two orthogonal controls: **visual mode** (`highlight` vs `filter`) and **color by** (`neutral`, `source`, `semantic cluster`, `active match`, with future editorial lens modes reserved). The immediate product requirement is that opening a story cluster from Stories should land in Explorer with the **full semantic cloud still visible** and the story-cluster members visually emphasized, not simply filtered down. Review current files including `frontend/src/routes/ExplorerPage.tsx`, `frontend/src/components/explorer/MapPanel.tsx`, `frontend/src/components/explorer/ExplorerControlBar.tsx`, `frontend/src/components/explorer/ExplorerContextRail.tsx`, `frontend/src/lib/navigation.ts`, `frontend/src/hooks/useExplorerUrlState.ts`, and the backend explorer contract in `src/api/v1/semantic.py` plus `src/api/contracts/semantic.py`. Produce a repo-specific architect handoff that defines: (1) final UX behavior for Stories handoff, search highlight, and manual filter mode; (2) the exact URL/state model; (3) the minimal backend contract needed, ideally point-level story-cluster membership metadata; (4) the component/file touch list for frontend.react; and (5) acceptance criteria + verification steps. Keep it Phase-1-first and do not propose a backend rewrite.

---

## Repo-specific implementation notes for frontend.react

Assuming the architect agrees with the model, frontend.react should likely touch:
- `frontend/src/lib/types.ts`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/lib/navigation.ts`
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/components/explorer/ExplorerControlBar.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/components/explorer/MapPanel.tsx`
- maybe `frontend/src/lib/explorerColors.ts`

If backend metadata lands, also touch:
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/dbstore.py`
- targeted tests in `tests/test_api_semantic_explorer.py` and `tests/test_semantic_dbstore.py`

---

## Verification plan

## Backend
If contract changes land:
```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper
pytest tests/test_api_semantic_explorer.py tests/test_semantic_dbstore.py
```

Add/verify cases for:
- `sem_story_cluster + sem_mode=filter` returns only members
- `sem_story_cluster + sem_mode=highlight` preserves broader dataset while exposing membership metadata
- points payload includes `analysis.story_cluster_ids`

## Frontend
```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper/frontend
npm run build
```

## Manual product checks
1. Open a story from Stories → Explorer
   - expect full cloud visible
   - expect story members emphasized
   - expect rail chip to describe highlighted story context
2. Toggle `Highlight` → `Filter`
   - expect non-matching points to disappear
3. Search for a term like `OnlyFans`
   - in highlight mode, expect matches emphasized and non-matches still visible
4. Change `Color by` from `Active match` to `Source`
   - expect hue encoding to swap without losing highlight/filter semantics
5. Select an article inside the highlighted cluster
   - expect selected/neighbor emphasis to still dominate correctly

---

## Strong recommendation

Phase 1 should be a **frontend-led iteration with one tiny backend contract change**.

That is the sweet spot.

Trying to do editorial color lenses before fixing the Explorer interaction model is backwards. You’d just be painting a confused product with more colors.