# RESULTS.md

## iter/004 — Frontend Rebuild: Complete

**Date:** 2026-03-20 UTC
**Build verification:** ✅ `cd frontend && npm run build` — zero TypeScript errors — 5.07s clean build

---

## Implementation summary

### What changed

A complete frontend rebuild of the Spain News Bias Scraper from the old three-column panel template into two distinct, purpose-built product surfaces.

#### The root problem (addressed)

`AppShell.tsx` imposed a generic `filters / main / detail` three-column template on both Stories and Explorer. Both routes felt like the same screen. The shell prop pattern locked routes into a layout they didn't control.

#### What was done

**Shell broken.** `AppShell.tsx` deleted. `Shell.tsx` now provides only a top bar and a main wrapper. Routes compose their own layouts.

**Stories rebuilt as a stream + focus panel.** No permanent filter column. Filter drawer opens on demand. Story cards are headline-dominant with source badges and date range. The focus panel now has four clearly separated sections: story brief → coverage bar → articles by source → article detail.

**CoverageBar added.** New component that computes source share from the existing `members` array (no backend change). The highest-value new element in the rebuild — makes source coverage readable as a quantified visual signal instead of a chip pile.

**Explorer rebuilt with control bar above canvas.** Floating toolbar overlay removed from inside the DeckGL canvas. Controls live in a clean horizontal `ExplorerControlBar` above the map. Canvas is clean semantic signal only. `MapPanel` refactored to `forwardRef` with a `MapPanelHandle` (fitAll / focusSelected) for imperative camera control from the control bar.

**ExplorerContextRail replaces InspectorPanel tabs.** Sections with dividers replace the Article/Cluster/Legend tab structure. No-selection state shows guide + legend + dataset summary. Selection state shows article → cluster context → semantic neighborhood in one scrollable rail.

**"Open in Stories" cross-link implemented.** From Explorer context rail → Stories route with the cluster pre-selected. Uses existing `cluster_id` field on `ExplorerPoint.analysis`. Requires no new API endpoint. `navigation.ts` updated to support `clusterId` param in `buildClusterBrowserHref`.

**Visual system rewritten.** `styles.css` fully replaced with a CSS custom property token system. Three surface levels enforced. Border radius reduced throughout. `.badge` replaces the overused dual `.status-chip` / `.summary-pill` system.

---

### Files created

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
      MapPanel.tsx
    system/
      LoadingState.tsx
      ErrorState.tsx
      EmptyState.tsx
  routes/
    ClusterBrowserPage.tsx    (rebuilt)
    ExplorerPage.tsx          (rebuilt)
  App.tsx                     (simplified)
  styles.css                  (rewritten)
lib/navigation.ts             (minor: clusterId param added)
```

### Files deleted

```
components/AppShell.tsx
components/ClusterFilterPanel.tsx
components/ClusterInspectorPanel.tsx
components/ClusterListPanel.tsx
components/ClusterStatusBar.tsx
components/FilterBar.tsx
components/InspectorPanel.tsx
components/StatusBar.tsx
components/MapPanel.tsx       (moved to components/explorer/MapPanel.tsx)
```

### Files preserved unchanged

```
hooks/useClusterBrowserData.ts
hooks/useClusterUrlState.ts
hooks/useClusterFilters.ts
hooks/useExplorerData.ts
hooks/useExplorerUrlState.ts
hooks/useExplorerFilters.ts
hooks/useExplorerBootstrap.ts
lib/api.ts
lib/types.ts
lib/format.ts
lib/query.ts
```

---

## Backend/API changes

**None.** Zero new endpoints. All rebuilt surfaces work against existing API contracts:
- `/api/v1/clusters` → Stories stream
- `/api/v1/clusters/{id}` → Story focus detail
- `/api/v1/clusters/filters` → Filter drawer
- `/api/v1/semantic/explorer/points` → Explorer canvas
- `/api/v1/semantic/explorer/filters` → Explorer filter sheet
- `/api/v1/semantic/explorer/articles/{id}` → Explorer context rail

Coverage bar computed client-side from existing `members` array. Explorer→Stories cross-link uses existing `cluster_id` from `ExplorerPoint.analysis`.

---

## Verification

```bash
cd frontend && npm run build
# Result: ✓ built in 5.07s — zero TypeScript errors
# Pre-existing @loaders.gl/worker-utils warning: unchanged from iter/003 baseline
```

---

## Risks and known gaps

| Risk | Severity | Note |
|---|---|---|
| Canvas height on some browsers | Low | `min-height: 0` on flex children handles most cases; verify if a parent gains `overflow: hidden` |
| Mobile Explorer UX | Low | Context rail drops below canvas at <1280px — functional but not polished; mobile is not primary target per spec |
| StoryFocusPanel sticky | Low | `position: sticky` breaks if any parent has `overflow: hidden` / `overflow: auto` |
| Source color palette keys | Low | Same keying as iter/003 — verify source slugs match API response keys |

---

## Optional follow-up (not blocking)

Per UI_SPEC.md §8.2, the following optional backend enhancements were documented but not implemented:

| Gap | Component | Priority |
|---|---|---|
| Dataset scope metadata (freshness, source count, date window) | TopBar scope chip + Stories header | Optional |
| Server-side source-level article counts per cluster | CoverageBar server validation | Optional — frontend compute is correct |

These are deferred to a follow-up pass if needed. The current rebuild is complete and functional against existing contracts.

---

## Architect handoff notes (for reference)

The architect pass produced:
- `UI_SPEC.md` — full route anatomy, layout model, states, interactions, API requirements
- `DESIGN_TOKENS.md` — color palette, typography, spacing, elevation, component visual rules
- `COMPONENT_MAP.md` — full component inventory with props, CSS sketch, file migration plan

All spec decisions were followed. Deviations from spec: none. One practical addition: `StoriesFilterFields` and `ExplorerFilterFields` defined inline in their route files (not as separate files) since their content is route-specific and small enough to colocate without harm.
