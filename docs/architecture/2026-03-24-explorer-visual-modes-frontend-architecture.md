# Explorer visual modes — frontend architecture handoff (2026-03-24)

## Verdict

The current Explorer is close, but the product model is still mashed together in the wrong places.

Right now:
- `sem_story_cluster` means **backend subset filter**
- `colorMode` is local UI state only, not URL-backed
- the Stories → Explorer handoff always behaves like a trapdoor into a subset
- the context rail treats the story seed as a chip, not a first-class analysis lens

That is the core issue. The map is supposed to help users see **context**, not just a prettier filtered list.

This Phase 1 pass should cleanly separate four concepts:

1. **dataset scope** — what points are loaded
2. **active match target** — what counts as “the thing I care about”
3. **visual mode** — `highlight | filter`
4. **color lens** — `neutral | source | semantic-cluster | active-match`

Do not overengineer editorial lenses here. Just leave a sane path for them later.

---

## Files reviewed

Frontend:
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/components/explorer/ExplorerControlBar.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/components/explorer/MapPanel.tsx`
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/hooks/useExplorerData.ts`
- `frontend/src/lib/navigation.ts`
- `frontend/src/lib/query.ts`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/explorerColors.ts`

Backend/API:
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`
- `tests/test_semantic_dbstore.py`

Planning source:
- `docs/plans/2026-03-24-explorer-visual-modes-plan.md`

---

## Current repo behavior vs desired behavior

### What exists now

### Explorer query model
Current URL/query state supports:
- `search`
- `source`
- `section`
- `clusterId`
- `storyClusterId`
- `dateFrom`
- `dateTo`
- `outlierOnly`
- `limit`
- `selectedArticleId`

But:
- there is **no visual mode state**
- there is **no URL-backed color mode state**
- there is **no explicit match target abstraction**

### Stories → Explorer handoff
`buildSemanticExplorerHref()` currently clears most semantic filters, sets `view=semantic`, and writes:
- `sem_story_cluster=<id>`
- `sem_article=<id>` if present

That means opening from Stories currently lands in a **story-cluster-filtered dataset**, because the backend interprets `sem_story_cluster` as a subset filter.

### Backend points contract
Explorer points already expose enough for:
- neutral coloring
- source coloring
- semantic cluster coloring
- selection / hover / neighbor emphasis

But the points payload does **not** expose whether each visible point belongs to the active story cluster unless the backend filters the dataset down to only those members.

That blocks the desired behavior:
- full cloud visible
- active story cluster highlighted inside the full cloud

---

## Phase 1 product contract

## 1. Explorer state model

Use these repo-specific types.

```ts
type ExplorerVisualMode = 'highlight' | 'filter'

type ExplorerColorMode =
  | 'neutral'
  | 'source'
  | 'cluster'
  | 'active-match'

type ExplorerMatchTarget =
  | { kind: 'story-cluster'; id: number }
  | { kind: 'semantic-cluster'; id: number }
  | { kind: 'search'; query: string }
  | { kind: 'source'; source: string }
  | null
```

Important: Phase 1 does **not** require shipping `ExplorerMatchTarget` as a fully separate stored object in every component. But the code should behave as if that model is real.

That means:
- `storyClusterId` is the story-cluster match target
- `clusterId` is the semantic-cluster match target when present
- `search` is a search match target when non-empty
- `source` can also act as a match target when used intentionally

For Phase 1, the frontend can derive the effective active match target from the existing query fields plus precedence rules.

### Precedence rule
Use one active match target at a time for visual emphasis.

Priority:
1. `storyClusterId`
2. `clusterId`
3. non-empty `search`
4. `source`
5. none

This keeps the UI coherent and avoids fake multi-lens logic.

---

## 2. URL/state contract

### New URL params
Add:
- `sem_mode=highlight|filter`
- `sem_color=neutral|source|cluster|active-match`

Keep existing params:
- `sem_search`
- `sem_source`
- `sem_section`
- `sem_cluster`
- `sem_story_cluster`
- `sem_from`
- `sem_to`
- `sem_outliers`
- `sem_limit`
- `sem_article`

### Required semantics

#### `sem_story_cluster`
Stop treating this as always meaning “filter the whole dataset.”

New meaning:
- it identifies the **active story-cluster target**
- whether it filters the dataset or only highlights it is controlled by `sem_mode`

#### `sem_mode`
- `highlight`: non-matching points stay visible
- `filter`: non-matching points are removed from the dataset

#### `sem_color`
- `neutral`: normal field coloring
- `source`: hue encodes source
- `cluster`: hue encodes semantic cluster
- `active-match`: hue encodes match vs non-match

### Defaults

#### Direct open of Explorer
If no semantic params are present:
- `sem_mode = highlight`
- `sem_color = neutral`

#### Stories → Explorer open
Default handoff should be:
- `sem_story_cluster=<id>`
- `sem_mode=highlight`
- `sem_color=active-match`
- preserve `sem_article=<id>` when launched from an article detail

That is the whole point of this pass.

---

## 3. UX behavior rules

## Stories → Explorer
When the user clicks “Open in Explorer” from Stories:
- keep the current Explorer dataset window semantics (date/source/limit/global dataset), not a forced story-only subset
- set active match target to the story cluster
- default to `highlight`
- default color to `active-match`

Expected experience:
- the full cloud remains visible
- story members stand out clearly
- user can flip to `Filter` if they want the isolated working set

### Rail copy
When a story seed is active and nothing is selected:
- primary chip/copy: `Story cluster {id} highlighted in context`
- secondary control: `Switch to filter mode`
- tertiary control: `Clear story context`

If `sem_mode=filter`, copy should say the user is viewing a filtered subset, not a highlight lens.

---

## Search behavior

Search follows the same model.

### Search + highlight
- full dataset visible
- articles whose title/summary match the current search are emphasized
- non-matches recede but remain readable

### Search + filter
- only matches remain visible

Important: Phase 1 search matching can stay client-side or backend-driven exactly as it is now. No semantic search rewrite. No bullshit reinvention.

---

## Manual filter mode

Users must be able to intentionally narrow to just the active match set.

This is the behavior of:
- story cluster + `sem_mode=filter`
- semantic cluster + `sem_mode=filter`
- search + `sem_mode=filter`
- source + `sem_mode=filter`

Phase 1 must make the mode switch obvious enough that the user understands whether they are seeing:
- a full-context highlight lens
- or a hard subset

---

## 4. Rendering contract for MapPanel

## Visual priority stack
Keep the existing semantic emphasis stack, with this order:
1. selected article
2. semantic neighbors
3. hovered article
4. active-match emphasis
5. normal field points
6. receding non-matches

Selection should still win over everything. If this pass breaks selected/neighbor readability, it failed.

## Highlight mode
In `highlight` mode:
- matching points stay fully visible and stronger
- non-matching points remain visible but recede in alpha/stroke
- selected/neighbor tiers still override base match styling

## Filter mode
In `filter` mode:
- only matching points should be passed through as the visible field
- the current behavior for story-cluster filtering can remain the backend path for Phase 1

## `active-match` color lens
In `active-match` mode:
- matching points get a strong accent hue
- non-matching points get a neutral/receded hue
- outliers still preserve their legibility
- selection and neighbor colors remain dominant overrides

This should not replace selection colors. It is a base encoding, not the top layer.

### Recommended palette behavior
Not a hard design token spec, but the implementation should behave roughly like this:
- active match = warm/high-contrast accent
- non-match field = slate/indigo neutral
- selected = sky blue (existing)
- neighbors = green (existing)

---

## 5. Minimal backend contract required

## Required change for Phase 1
Add story-cluster membership metadata onto explorer points.

### API shape
Add to `ExplorerSemanticSummary`:

```py
story_cluster_ids: list[int] = Field(default_factory=list)
```

Resulting point shape:

```json
{
  "article_id": 123,
  "analysis": {
    "cluster_id": 9,
    "is_outlier": false,
    "story_cluster_ids": [412]
  }
}
```

### Why this tiny change matters
Without this, the frontend cannot cleanly highlight story-cluster membership in the full cloud. It would be forced to:
- fetch extra cluster detail and reconcile article IDs client-side, or
- keep using backend filtering and fake the rest

Both options are dumb.

### Backend interpretation rule
For `/api/v1/semantic/explorer/points`:
- if `sem_story_cluster` is present **and** `sem_mode=filter`, backend filters dataset to cluster members
- if `sem_story_cluster` is present **and** `sem_mode=highlight`, backend does **not** filter the dataset, but includes `analysis.story_cluster_ids` on each visible point

This is the right contract because it keeps one URL param for the active story target and makes mode decide visibility behavior.

## Optional-but-not-required backend extension
No editorial preview metadata is required for Phase 1 Explorer visual modes.

Do not block this pass on bias/tone map coloring.

---

## 6. Repo-specific frontend implementation plan

## What frontend.react can implement cleanly now

### A. URL/state plumbing
Touch:
- `frontend/src/lib/types.ts`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/lib/navigation.ts`
- `frontend/src/lib/query.ts`

Changes:
- extend `ExplorerColorMode` with `'active-match'`
- add `ExplorerVisualMode = 'highlight' | 'filter'`
- add URL parsing/serialization for `sem_mode` and `sem_color`
- keep color mode in URL state, not local component state only
- preserve Stories handoff defaults: `sem_mode=highlight`, `sem_color=active-match`

### B. Explorer route orchestration
Touch:
- `frontend/src/routes/ExplorerPage.tsx`
- maybe `frontend/src/hooks/useExplorerData.ts`

Changes:
- derive `activeMatchTarget` from query via precedence rules
- pass `visualMode`, `activeMatchTarget`, and URL-backed `colorMode` into map + rail + control bar
- keep `viewMode` as local UI state for now unless there is a strong reason to URL-back it later

### C. Control bar
Touch:
- `frontend/src/components/explorer/ExplorerControlBar.tsx`

Changes:
- add a segmented control for `Highlight | Filter`
- extend color options with `Active match`
- copy should clearly separate:
  - visual mode
  - color by

If these are mashed into one control, the UI stays muddy.

### D. Context rail
Touch:
- `frontend/src/components/explorer/ExplorerContextRail.tsx`

Changes:
- evolve `SeedContext` into a proper active context display
- show mode-aware copy:
  - highlighted in context
  - filtered subset
- add action button to toggle highlight/filter when a seed exists
- add legend support for `active-match`
- keep clear action scoped to the active lens, not necessarily a full reset of all query fields unless the current UX intentionally wants that

### E. Map rendering
Touch:
- `frontend/src/components/explorer/MapPanel.tsx`
- maybe `frontend/src/lib/explorerColors.ts`

Changes:
- derive `isMatch(point)` from the active match target
- use match state in both 2D and 3D layers
- implement `active-match` base coloring
- recede non-matches in highlight mode
- preserve selected / neighbor / hovered dominance

### F. Stories handoff
Touch:
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- `frontend/src/lib/navigation.ts`

Changes:
- handoff URLs should include `sem_mode=highlight` and `sem_color=active-match`
- preserve selected article when relevant

---

## 7. What should wait

Do **not** add in this phase:
- editorial map color lenses
- compound lens logic
- multiple simultaneous active match groups
- saved views/lenses
- backend semantic search changes
- frontloaded abstraction theater that makes simple work harder

Phase 1 is about making the map tell the truth.

---

## 8. Tiny backend pass handoff

Backend implementer should make the smallest possible change.

### Files to touch
- `src/api/contracts/semantic.py`
- `src/api/v1/semantic.py`
- `src/semantic/dbstore.py`
- `tests/test_api_semantic_explorer.py`
- `tests/test_semantic_dbstore.py`

### Required backend tasks
1. Extend `ExplorerSemanticSummary` with `story_cluster_ids: list[int]`
2. Extend `ExplorerFilters` with `visual_mode: str | None = None` or a tighter enum-friendly value
3. Update request handling in `src/api/v1/semantic.py` to accept `sem_mode`
4. Update DB read-side logic so:
   - filter mode applies story-cluster subset filtering
   - highlight mode keeps dataset broad and adds story membership metadata per point
5. Add tests for:
   - `sem_story_cluster + sem_mode=filter` ⇒ only members returned
   - `sem_story_cluster + sem_mode=highlight` ⇒ broader dataset returned with point membership metadata
   - points payload includes `analysis.story_cluster_ids`

### Constraint
No backend rewrite. No new endpoint. No giant join circus if a tight membership lookup or aggregation does the job.

---

## 9. Exact frontend.react handoff

Implement Explorer Phase 1 visual modes using the existing React route/components without changing the overall page structure.

### Goals
1. Separate **visual mode** from **color by**
2. Make Stories → Explorer open in **highlight-in-context** by default
3. Preserve the existing selected/neighbor semantic inspection behavior

### Files to touch
- `frontend/src/lib/types.ts`
- `frontend/src/hooks/useExplorerUrlState.ts`
- `frontend/src/lib/navigation.ts`
- `frontend/src/lib/query.ts`
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/components/explorer/ExplorerControlBar.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/components/explorer/MapPanel.tsx`
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- optionally `frontend/src/lib/explorerColors.ts`

### Exact implementation requirements
- Add URL-backed `sem_mode` and `sem_color`
- Add `ExplorerVisualMode = 'highlight' | 'filter'`
- Extend `ExplorerColorMode` with `'active-match'`
- In Stories handoff, default to:
  - `sem_story_cluster=<id>`
  - `sem_mode=highlight`
  - `sem_color=active-match`
  - optional `sem_article=<id>`
- Derive a single effective `activeMatchTarget` from query using priority:
  1. story cluster
  2. semantic cluster
  3. search
  4. source
- In `MapPanel`, implement match-aware rendering for both 2D and 3D
- In highlight mode, non-matching points remain visible but recede
- In filter mode, preserve current narrow working-set behavior
- Add `Active match` legend/copy support in the rail
- Add visual-mode toggle in the control bar
- Do not break selection, hover, neighbor emphasis, fit-all, or focus-selected

### Frontend assumptions
- If backend ships `analysis.story_cluster_ids`, use that for story-cluster matching in highlight mode
- For search/source/semantic-cluster matching, frontend can derive match state from current point payload + query
- If backend has not landed yet, frontend can still wire the state model and UI, but the full-cloud story highlight behavior will remain incomplete

---

## 10. Acceptance criteria

## Product checks
1. Open a story from Stories → Explorer
   - full cloud visible
   - story members visually emphasized
   - mode defaults to `Highlight`
   - color defaults to `Active match`
2. Toggle to `Filter`
   - only matching points remain
3. Run a search in highlight mode
   - matches stand out
   - non-matches remain visible
4. Change `Color by` from `Active match` to `Source`
   - hue encoding changes
   - highlight/filter behavior still works
5. Select an article within highlighted context
   - selected and neighbor tiers still dominate visually

## URL checks
1. Refresh preserves `sem_mode` and `sem_color`
2. Shared Explorer links preserve the lens behavior
3. Stories handoff URL explicitly encodes the intended default state

## Verification

Backend:
```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper
pytest tests/test_api_semantic_explorer.py tests/test_semantic_dbstore.py
```

Frontend:
```bash
cd /home/node/.openclaw/workspace/repos/spain-news-bias-scraper/frontend
npm run build
```

---

## Bottom line

Phase 1 should be:
- **frontend-led**
- with **one tiny backend contract change**
- and absolutely no editorial-lens scope creep

That is the clean move. Everything else is decorative chaos.