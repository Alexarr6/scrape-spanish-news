# UI_SPEC.md — iter/004 Frontend Architecture

**Role:** Frontend Architect (iter/004)
**Date:** 2026-03-20
**Status:** Complete — ready for `frontend.react` builder pass

---

## 1. Product thesis

This is a **media-intelligence workspace**, not a BI dashboard.

It answers two questions:
1. **Stories:** What stories exist in the coverage landscape, and how are Spanish outlets treating each one differently?
2. **Explorer:** How is a corpus of articles semantically arranged — which outlets cluster, which sit on the margin?

The UI should make those two questions legible, not bury them in symmetric panel soup.

---

## 2. Navigation model

### 2.1 Primary navigation

Two items only. No additions this iteration.

| Route | Label | Role |
|---|---|---|
| `/` | Stories | Default. Editorial front door. |
| `/explorer` | Explorer | Secondary. Specialist semantic desk. |

### 2.2 Navigation anatomy

Replace the current sidebar nav with a **top bar + minimal left rail** split.

**Stories route:** sidebar is hidden or collapsed by default. Filter drawer opens on demand.
**Explorer route:** no sidebar at all. Controls sit in a compact analytical header/rail system.

The current sidebar does three things: shows brand, shows nav, shows route-level copy. That is too many jobs for one column. Each concern gets its own place.

### 2.3 Brand block

Move brand out of the sidebar into a **top-bar wordmark**:
- Product name: `Spain News Bias Scraper` (or short form `Signal`) — left of top bar
- Nav items as plain links in top bar
- No sidebar sermon copy (the current "Serious story clustering..." paragraph is internal notes, not UI)

### 2.4 Top bar structure

```
[wordmark / logo]    [Stories]  [Explorer]          [dataset scope chip]
```

- Fixed/sticky at top
- Height: 48px
- No icons. Text-only nav.
- Active route: stronger weight, bottom border indicator (not a pill)
- Dataset scope chip (right): shows last dataset window if available, e.g. "15–20 Mar 2026 · 8 sources"

---

## 3. Route anatomy — Stories

### 3.1 Goal

Answer: **What is the story landscape right now, and how are different outlets treating each story?**

This is an editorial workflow, not a cluster browser admin screen.

### 3.2 Layout model (desktop)

```
┌──────────────────────────────────────────────────────────────────┐
│  TOP BAR                                                         │
├──────────────────────────────────────────────────────────────────┤
│  STORIES HEADER                                                  │
│  headline + count summary + filter trigger                       │
├────────────────────────┬─────────────────────────────────────────┤
│  STORY STREAM          │  STORY FOCUS PANEL                      │
│  (scrollable)          │  (scrollable, wider)                    │
│                        │                                         │
│  ranked story cards    │  — empty: editorial prompt              │
│  with editorial        │  — selected: brief + coverage + articles│
│  hierarchy             │                                         │
│                        │                                         │
└────────────────────────┴─────────────────────────────────────────┘
```

**Column widths (desktop ≥1280px):**
- Stream: `minmax(0, 1fr)` ~400–480px
- Focus: `min(480px, 37vw)` — wider and more intentional than today's right rail

**Filter access:**
- No permanent left filter panel (removes the symmetric three-panel look)
- Filters open as a **slide-over drawer** from a "Refine" button in the Stories header
- Filter state stays URL-encoded (same as today)

### 3.3 Stories header

A deliberate route header, not a page-header component recycled from the shell.

```
Stories                               [Refine ↓]  [n active filters]
n stories in current scope · n sources · last updated …
```

Elements:
- Route label (h1-weight, not eyebrow)
- Scope summary: story count, source count, data freshness (if available from API)
- "Refine" button: opens filter drawer
- Active filter count badge (only shown if > 0)

### 3.4 Story stream

**Purpose:** Let an analyst scan the story landscape quickly, rank by importance, and pick one.

Replaces `ClusterListPanel` and its nested hero card + results header + paginated list.

**Card anatomy (StoryCard):**

```
┌─────────────────────────────────────────────────┐
│  [cluster_type label]        [article_count]    │
│                                                 │
│  HEADLINE (large, bold)                         │
│                                                 │
│  Summary text (2 lines max, truncated)          │
│                                                 │
│  [coverage bar: source icons/pills]  [date range]│
└─────────────────────────────────────────────────┘
```

Rules:
- Headline is the dominant element. Not a `h3` — use `h2` sizing at 1.1rem bold.
- Summary: 2 lines max, `line-clamp: 2`. Not an essay.
- Source pills at bottom: only source names, not tags/entities (those go in the focus panel)
- Article count and source count are data-points, not pills — formatted as `12 articles · 5 sources`
- Date range: right-aligned, subtle, `Apr 3–7`
- No entity chips on the card. They're noise here.
- Selected state: left border accent (4px) + subtle background, not a box-shadow ring

**Pagination:**
- Retain numeric pagination controls
- Position: below the stream, not inside a card header
- Copy: `← Previous` / `Next →` with page info `Showing 1–20 of 47`

### 3.5 Story focus panel

This is the most important surface change. Currently this is a cramped right rail. It should become a **first-class story workspace panel** that can actually hold content.

**States:**

#### Empty state
```
┌──────────────────────────────────────┐
│  Select a story                      │
│                                      │
│  Pick any cluster from the stream    │
│  to inspect its source coverage      │
│  and article detail.                 │
│                                      │
│  [→ Explorer]  (secondary action)    │
└──────────────────────────────────────┘
```

No decorative illustrations. Plain and direct.

#### Selected state — sections

**Section 1: Story brief**
```
[cluster_type · status]
HEADLINE
Summary text (full, not truncated)
Articles · Sources · Date window
[↗ Open in Explorer]
```
The Explorer link stays, but styled as a secondary action, not a primary button.

**Section 2: Coverage composition**
A compact visual bar or list showing source share:
```
El País     ████████░░░  4 articles (40%)
El Mundo    ████░░░░░░░  2 articles (20%)
ABC         ██░░░░░░░░░  2 articles (20%)
...
```
This is currently absent. It turns source coverage into a readable signal, not a chip cloud.

Implementation note: this can be built purely from existing `members` array — no new backend needed. Group by source, count, compute shares.

**Section 3: Articles by source**

Grouped by source (preserves current `groupMembersBySource` logic).

Article row anatomy:
```
SOURCE NAME  (2 articles)
  Title of article 1                              [score]  date
  Summary snippet
  [tag · tag]

  Title of article 2                              [score]  date
  ...
```

Reduce visual noise vs current `member-card`:
- Remove entity chips from article rows entirely
- Keep only 1–2 tag chips maximum
- Membership score: right-aligned, subtle, formatted as `92%` not `0.92`

**Section 4: Selected article detail**

Shown when an article is selected within the focus panel:
```
[BACK ←]
SOURCE · SECTION · DATE
TITLE
Summary (full)
Excerpt (collapsible or truncated at 4 lines)
[Open article ↗]  [Open in Explorer →]

Semantic context:
  Cluster: n  |  Neighbors: n  |  Outlier: Yes/No
  
  Nearby articles (max 4):
  [article title — source — similarity]
```

Back button returns to the source-grouped article list (not to empty state).

### 3.6 Filter drawer

Slides in from left (or right on mobile) over the content. Not a permanent panel.

Content (same fields as current `ClusterFilterPanel`):
- Search by headline/summary
- Source select
- Tag select
- Entity select
- Date range
- Results per page

Close: click outside or explicit Close button.
Apply on change (no submit button needed — current behavior).

### 3.7 Stories states

| State | Behavior |
|---|---|
| Loading (first load) | Stream shows skeleton cards (3–4 placeholders). Focus panel shows nothing. |
| Loading (paginating) | Stream goes slightly dimmed (opacity), not fully replaced. Preserves layout. |
| Error (list) | Stream replaced by error card with recovery hint. |
| Error (detail) | Focus panel shows error inline. Stream stays usable. |
| Empty results | Stream shows empty state with filter reset suggestion. |
| No selection | Focus panel shows editorial prompt + Explorer secondary action. |
| Story selected, no article | Focus panel shows brief + coverage + article list + empty article section. |
| Story selected + article selected | Focus panel shows full detail in section 4. |

---

## 4. Route anatomy — Explorer

### 4.1 Goal

Answer: **How is the current article corpus semantically arranged? Which outlets cluster? Which sit on the margin?**

This is a specialist tool. It assumes the analyst already has a question in mind.

### 4.2 Layout model (desktop)

```
┌──────────────────────────────────────────────────────────────────┐
│  TOP BAR                                                         │
├──────────────────────────────────────────────────────────────────┤
│  ANALYST CONTROL BAR (compact)                                   │
│  [view mode]  [color lens]  [fit all]  [n points]  [filters ↓]  │
├────────────────────────────────────┬─────────────────────────────┤
│                                    │  CONTEXT RAIL               │
│  SEMANTIC CANVAS                   │                             │
│  (DeckGL / full height)            │  — no selection: guide      │
│                                    │  — selected: article detail │
│                                    │                             │
│                                    │                             │
└────────────────────────────────────┴─────────────────────────────┘
```

**Column widths (desktop ≥1280px):**
- Canvas: `minmax(0, 1fr)`
- Context rail: `320px` (narrower than today — the canvas should dominate)

No permanent left filter panel for Explorer either. Filters open from the control bar.

### 4.3 Analyst control bar

A single compact horizontal bar between the top bar and the canvas. Replaces the current floating overlay toolbar inside the map.

```
[2D / 3D]  [Neutral / Source / Cluster]  [Fit all]  [Focus selected]
                                                          n points visible  [Refine ↓]
```

Rules:
- No floating cards inside the map canvas for controls
- Control bar is outside the canvas frame — clean separation between control surface and semantic surface
- `Fit all` and `Focus selected` remain as framing actions
- `Refine` opens a filter sheet (same pattern as Stories)
- Point count: `482 points` displayed as passive metadata, not in a pill

### 4.4 Semantic canvas

The map stays central. DeckGL behavior unchanged.

Remove from the canvas:
- The current `.map-toolbar` overlay card (controls move to control bar above)
- The guide text overlay inside the canvas

Keep in the canvas:
- Hover tooltip
- Click-to-select behavior
- 2D/3D camera logic unchanged

The canvas should be visually clean — semantic signal only, no chrome inside it.

### 4.5 Context rail

**Width:** 320px. Fixed. Not resizable in this iteration.

#### State: no selection

```
┌──────────────────────────────┐
│  Semantic workspace           │
│                               │
│  Click any point to inspect   │
│  an article and its semantic  │
│  neighborhood.                │
│                               │
│  ─────────────────────────── │
│  LEGEND                       │
│  [color encoding key]         │
│                               │
│  ─────────────────────────── │
│  DATASET SUMMARY              │
│  n clusters · n outliers      │
│  Sources: El País, El Mundo…  │
└──────────────────────────────┘
```

No tabs when nothing is selected. Just structured sections.

#### State: point selected

```
┌──────────────────────────────┐
│  [✕ clear]                    │
│                               │
│  SOURCE · SECTION · DATE      │
│  TITLE                        │
│  Summary snippet              │
│                               │
│  [Open article ↗]             │
│  [Open in Stories →]          │  ← back-link to Stories route
│                               │
│  ─────────────────────────── │
│  CLUSTER CONTEXT              │
│  Cluster n · n articles       │
│  Source mix: ...              │
│  Date span: ...               │
│                               │
│  ─────────────────────────── │
│  SEMANTIC NEIGHBORHOOD        │
│  n neighbors found            │
│  [neighbor title — source — score]  │
│  ...                          │
└──────────────────────────────┘
```

Rules:
- No tabs in the context rail for Explorer. Tabs in iter/003 helped organize, but the content is not complex enough to warrant tab switching. Sections with dividers are cleaner.
- "Open in Stories" link: if the article belongs to a cluster, link to `/` with `clusterId` pre-selected in URL. This closes the Stories↔Explorer loop.
- Neighbor list: max 5, same as today.

### 4.6 Explorer filter sheet

Same slide-over pattern as Stories.

Fields:
- Source
- Section
- Cluster select
- Date range
- Outlier only toggle
- Point limit

### 4.7 Explorer states

| State | Behavior |
|---|---|
| Loading (first) | Canvas shows loading overlay. Context rail shows minimal text. |
| Loading (filter change) | Canvas dims briefly. Control bar shows spinner indicator. |
| Error | Canvas replaced by error message. Control bar stays. |
| Empty (no points) | Canvas shows empty state centered. Context rail shows filter reset prompt. |
| No selection | Context rail: guide + legend + dataset summary. |
| Point selected (loading detail) | Context rail shows point title immediately (from `selectedPoint`), loading spinner for detail section. |
| Point selected (detail loaded) | Full context rail content. |
| Point selected (detail error) | Article section shows inline error. Neighborhood section empty. |

---

## 5. App shell changes

### 5.1 What the shell must do

1. Render top bar with wordmark and nav
2. Route to Stories or Explorer
3. Stay out of the way

### 5.2 What the shell must NOT do

- Impose a shared three-panel layout on both routes
- Carry semantic content (sidebar copy, route descriptions)
- Force symmetric layout structure

### 5.3 New shell structure

```tsx
// AppShell.tsx — new contract
type Props = {
  navItems: NavItem[]
  children: ReactNode
}
// Renders: <TopBar> + <main>{children}</main>
```

Routes compose their own layout internally. The shell provides top bar + base structure only.

Remove from shell:
- `section`, `title`, `description`, `summary`, `filters`, `filtersTitle`, `detail`, `detailTitle`, `status`
- `workspace-grid` / `workspace-panel` layout responsibility
- `app-sidebar` entirely
- `sidebar-note` entirely
- `page-header` (moves into route-specific headers)

### 5.4 Top bar anatomy

```tsx
// TopBar.tsx — new component
// Left: wordmark
// Center: nav items (Stories, Explorer)
// Right: dataset scope chip (optional, from API or empty)
```

---

## 6. Responsive behavior

### 6.1 Priority

Desktop ≥1280px: full layout as specified.
Tablet 768–1279px: adapted but functional.
Mobile <768px: usable, not the primary target.

### 6.2 Stories responsive rules

| Breakpoint | Behavior |
|---|---|
| ≥1280px | Stream + focus side by side. Filter drawer. |
| 900–1279px | Stream full width. Focus panel drops below stream. Filter drawer. |
| <900px | Stack: header → stream → focus (collapsed by default, expands on selection). |
| <640px | Focus panel is full-screen overlay when story selected. |

### 6.3 Explorer responsive rules

| Breakpoint | Behavior |
|---|---|
| ≥1280px | Control bar → canvas + context rail side by side. |
| 900–1279px | Control bar → canvas (full width) → context rail below. |
| <900px | Control bar → canvas (min-height: 60vh) → context rail below. |
| <640px | Context rail becomes a bottom sheet on selection. |

### 6.4 Top bar responsive rules

| Breakpoint | Behavior |
|---|---|
| ≥768px | Full top bar with wordmark + nav + scope chip. |
| <768px | Wordmark + hamburger menu. Nav items in dropdown sheet. |

---

## 7. States and microcopy direction

### 7.1 Principles

- Loading states name what is loading and why it matters to the user
- Empty states suggest the next meaningful action, not a generic "no results"
- Error states state the failure plainly + one recovery action
- No emoji in error states, no exclamation marks in empty states

### 7.2 Copy direction by state

**Stories stream loading:**
> "Loading story clusters…"
> Grouping coverage by shared event.

**Stories stream empty:**
> "No stories match the current filters."
> [Clear all filters] or widen the date window.

**Story focus empty:**
> "Select a story to inspect its coverage."
> Pick any cluster to see how different outlets covered the same event.

**Explorer loading:**
> "Loading semantic projection…"
> Mapping article embeddings into 2D/3D space.

**Explorer empty:**
> "No articles match the current filters."
> Broaden the source or date scope, or clear the cluster filter.

**Explorer no selection:**
> "Click any point to inspect an article."
> Colors show [encoding]. Clusters group by semantic similarity.

**Error recovery:**
> "Failed to load [thing]. Check the API connection or try again."
> [Try again] (reload action where feasible)

---

## 8. Backend/API requirements

### 8.1 Required for the rebuild (no new endpoints needed)

The rebuilt UI can work against **existing API contracts** for the initial implementation:
- `/api/v1/clusters` → Stories stream
- `/api/v1/clusters/{id}` → Story focus detail
- `/api/v1/clusters/filters` → Filter drawer
- `/api/v1/semantic/explorer/points` → Explorer canvas
- `/api/v1/semantic/explorer/filters` → Explorer filter sheet
- `/api/v1/semantic/explorer/articles/{id}` → Explorer article detail

The coverage composition bar in Story focus (Section 2) is computed from existing `members` array — no new endpoint needed.

The "Open in Stories" link from Explorer can use the existing `cluster_id` on `ExplorerPoint.analysis.cluster_id` to construct a URL — no new endpoint needed.

### 8.2 Nice to have (optional, for a follow-up pass)

| Gap | Why | Priority |
|---|---|---|
| Dataset scope metadata (freshness, source count, date window) | Feeds top bar scope chip and Stories header count. Currently not in any response. | Optional but useful |
| Source-level article count normalized in cluster detail | Would confirm coverage bar percentages server-side | Optional — frontend can compute |
| Representative article IDs per cluster for stream preview | Could enrich story card with first article title/snippet | Optional |

### 8.3 Explicitly not needed

- No new backend endpoint for coverage bar (derived client-side)
- No cluster summary enrichment required for this iteration
- No auth, no user model
- No search endpoint changes
- No semantic algorithm changes

---

## 9. Interaction model

### 9.1 Story selection

- Click story card → set selectedClusterId in URL
- Story focus panel shows story brief immediately (from list data)
- Article detail section loads async in focus panel
- Browser back button works (URL state)

### 9.2 Article selection in Stories

- Click article row in focus panel → set selectedArticleId in URL
- Article detail section expands in focus panel
- Source-grouped article list remains visible above
- "Back" in article detail returns to article list (clears `selectedArticleId`)

### 9.3 Story→Explorer handoff

- "Open in Explorer" link in Story focus: navigates to `/explorer?clusterId=n&articleId=m` (current behavior preserved)
- Opened story/article should be selected on Explorer load (current `useExplorerBootstrap` hook handles this)

### 9.4 Explorer→Stories handoff (new)

- "Open in Stories" link in Explorer context rail: navigates to `/?clusterId=n` (new URL param Stories doesn't currently support by cluster ID — see API notes below)
- This requires Stories to accept a `clusterId` URL param and auto-select it on load
- Currently Stories uses `selectedClusterId` in URL state — verify this already works or add it

### 9.5 Point hover in Explorer

- Hover tooltip behavior unchanged
- Tooltip: title + source + date (current behavior preserved)

---

## 10. File/component migration plan

### 10.1 Components to delete

| Component | Reason |
|---|---|
| `AppShell.tsx` | Replaced by leaner `Shell.tsx` + `TopBar.tsx` |
| `ClusterStatusBar.tsx` | Merged into Stories header |
| `StatusBar.tsx` (Explorer) | Merged into Explorer control bar |
| `ClusterFilterPanel.tsx` | Replaced by `FilterDrawer.tsx` (shared) |
| `FilterBar.tsx` (Explorer) | Replaced by `FilterDrawer.tsx` (shared) |

### 10.2 Components to heavily refactor

| Component | Change |
|---|---|
| `ClusterListPanel.tsx` | Becomes `StoryStream.tsx` — removes hero card, tighter card anatomy |
| `ClusterInspectorPanel.tsx` | Becomes `StoryFocusPanel.tsx` — adds coverage bar, better section hierarchy |
| `MapPanel.tsx` | Controls moved out of canvas, cleaner canvas surface |
| `InspectorPanel.tsx` | Becomes `ExplorerContextRail.tsx` — sections replace tabs |

### 10.3 New components

| Component | Role |
|---|---|
| `TopBar.tsx` | Global top bar (wordmark + nav + scope chip) |
| `Shell.tsx` | Leaner app shell (top bar + main area) |
| `StoryStream.tsx` | Stories route main column |
| `StoryCard.tsx` | Individual story card |
| `StoryFocusPanel.tsx` | Stories route right panel |
| `CoverageBar.tsx` | Source share visualization in Story focus |
| `FilterDrawer.tsx` | Shared filter slide-over (Stories + Explorer) |
| `ExplorerControlBar.tsx` | Compact horizontal controls for Explorer |
| `ExplorerContextRail.tsx` | Explorer right panel (replaces InspectorPanel) |
| `SectionDivider.tsx` | Lightweight semantic divider between content sections |

### 10.4 Components to keep mostly as-is

| Component | Notes |
|---|---|
| `MapPanel.tsx` (canvas core) | DeckGL internals unchanged; only chrome moved out |
| `useClusterBrowserData.ts` | Logic preserved; adapt to new component interfaces |
| `useClusterUrlState.ts` | Preserved |
| `useClusterFilters.ts` | Preserved |
| `useExplorerData.ts` | Preserved |
| `useExplorerUrlState.ts` | Preserved |
| `useExplorerFilters.ts` | Preserved |
| `useExplorerBootstrap.ts` | Preserved |
| `lib/api.ts` | Preserved — no new endpoints needed |
| `lib/types.ts` | Preserved — no new types needed for initial pass |
| `lib/format.ts` | Preserved |
| `lib/query.ts` | Preserved |
| `lib/navigation.ts` | Add `buildClusterBrowserHref` with clusterId param |

### 10.5 Recommended file structure

```
frontend/src/
  components/
    layout/
      Shell.tsx
      TopBar.tsx
      FilterDrawer.tsx
      SectionDivider.tsx
    stories/
      StoryStream.tsx
      StoryCard.tsx
      StoryFocusPanel.tsx
      CoverageBar.tsx
    explorer/
      ExplorerControlBar.tsx
      ExplorerContextRail.tsx
      MapPanel.tsx          ← keep here, it's already a canvas component
    system/
      LoadingState.tsx
      ErrorState.tsx
      EmptyState.tsx
  routes/
    ClusterBrowserPage.tsx  ← keep filename, heavy refactor
    ExplorerPage.tsx        ← keep filename, heavy refactor
  hooks/           ← unchanged
  lib/             ← unchanged
  styles.css       ← rewrite (see DESIGN_TOKENS.md)
  App.tsx          ← simplify (shell no longer a prop)
```

---

## 11. What the builder must NOT do

- Do not add a third top-level route
- Do not add tabs to the Stories stream
- Do not make Stories look like Explorer or vice versa
- Do not add decorative illustrations or icon sets
- Do not keep the sidebar (it is gone)
- Do not keep the symmetric three-panel `workspace-grid` template for both routes
- Do not add animation libraries
- Do not change the DeckGL projection/rendering logic
- Do not add any backend endpoints — start against existing API contracts

---

*Handoff complete. Next pass: `frontend.react` constructor 👷*
