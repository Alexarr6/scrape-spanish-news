# RESULTS.md

## iter/006 — Explorer framing, axes & 3D point implementation

**Date:** 2026-03-20 UTC
**Iteration:** iter/006
**Role:** `frontend.react` builder 👷
**Outcome:** ✅ Complete — build passes, 3 improvements implemented

---

### Problem statement

Three UX issues observed after iter/005 render fix:

1. **Zoom too low** — points in `[-1, 1]` space require manual zoom to ~8 to read; initial view shows them as a tiny dot cluster
2. **No orientation** — no visual reference for the coordinate space; users can't tell left from right or up from down
3. **3D points look flat** — `ScatterplotLayer` renders flat discs; at orbit angles they appear as distorted ovals, not volumetric points

---

### Decisions

| Issue | Fix | Key constraint |
|---|---|---|
| Zoom | Pixel-aware formula: `log2(canvasPx / paddedSpan)` | No hardcoded scale assumption |
| Axes | `LineLayer` in both 2D + 3D | No new npm packages; `LineLayer` already in `@deck.gl/layers` |
| 3D points | `PointCloudLayer` tiers by priority | `material: false`; no 2D changes; 5 layers for per-tier sizing |

---

### What was implemented

**File: `frontend/src/lib/explorerColors.ts`**
Appended 10 new constants: axis colors × 5 (AXIS_COLOR_2D, AXIS_X/Y/Z_COLOR_3D, AXIS_GRID_COLOR_3D) and PC sizes × 5 (PC_SIZE_REGULAR/OUTLIER/NEIGHBOR/HOVERED/SELECTED).

**File: `frontend/src/components/explorer/MapPanel.tsx`**
Three changes implemented:

1. **Pixel-aware zoom formula** — `build2dViewState(bounds, canvasPx)` and `build3dViewState(bounds, canvasPx, current?)` now compute `zoom = log2(canvasPx / paddedSpan)`. Helper `getCanvasPx(canvasRef)` reads real DOM size at call time. Default zoom 8.5 (was 1.8/1.9). Clamp changed from [1.4,7.2] to [1.0,14.0]. `buildInitialViewState`, `fitAll()`, `focusSelected()` all updated to pass `canvasPx`.

2. **`buildAxisLayers(viewMode, bounds)`** — produces `LineLayer`-based axis layers. 2D: one layer with two grey lines. 3D: faint XY grid layer + RGB XYZ axis layer. Always prepended to layer stack.

3. **3D PointCloudLayer tiers** — `viewMode === '3d'` branch in `layers` useMemo creates 5 `PointCloudLayer` instances (regular/outlier/neighbor/hovered/selected) with fixed `pointSize` per tier, `material: false`, billboarded normals. `ScatterplotLayer` retained for 2D only.

**Build:**
```
✓ tsc -b — 0 type errors
✓ vite build — 711 modules transformed, 0 build errors
dist/assets/index-CRIiqvoD.js  936.66 kB (was 903.68 — +33KB from PointCloudLayer)
✓ built in 4.99s
```

**Commit:** `feat(explorer): iter/006 — pixel-aware zoom, axes, 3D PointCloudLayer`

---

### Files changed in this pass

| File | Change |
|---|---|
| `frontend/src/lib/explorerColors.ts` | Appended 10 new constants (axis colors + PC sizes) |
| `frontend/src/components/explorer/MapPanel.tsx` | New zoom formula, buildAxisLayers, 3D PointCloudLayer tiers |
| `STATUS.md` | Updated to BUILD_PASS |
| `RESULTS.md` | This entry |

No other files modified.

---

## Previous pass

## Explorer improvement pass — implementation handoff

**Date:** 2026-03-20 UTC
**Iteration:** iter/005
**Role:** `frontend.react` builder 👷
**Outcome:** ✅ Complete — all bug fixes applied, UX improvements implemented, build passes

---

## One-line summary

**Five concrete render bugs fixed, all planned UX improvements implemented, build passes clean. Points should render reliably on next browser load.**

---

## What was implemented

### Phase 1 — CSS render reliability (BUG-1, BUG-6)

**File:** `frontend/src/styles.css`

- Added `overflow: hidden` to `.explorer-workspace` — prevents grid from collapsing inside flex parent (BUG-1)
- Removed `!important` overrides on `.map-canvas > div, canvas` (BUG-6) — DeckGL must control its own canvas dimensions
- Added explicit `height: 100%` to `.map-canvas` — ensures `offsetHeight > 0` at DeckGL mount time
- Added all new CSS classes for new UX additions (seed chip, guide explainer, tooltip enhancements, legend additions, dev overlay)

**Commit:** `fix(explorer): restore render reliability — CSS height chain and BUG-6`

---

### Phase 2 — DeckGL stabilization and encoding (BUG-2, BUG-4, BUG-5)

**Files:** `frontend/src/lib/explorerColors.ts` (new), `frontend/src/components/explorer/MapPanel.tsx`

**explorerColors.ts (new):**
- Authoritative constants for all point encoding: fill colors, stroke colors, stroke widths, radii (2D/3D), alpha values by selection state
- Source color palette (RGB + HEX), cluster palette, outlier/null colors
- Imported by MapPanel — no more inline magic arrays

**MapPanel.tsx:**
- `key="explorer-deck"` on `<DeckGL>` — fixes React 18 StrictMode double-mount (BUG-2)
- Removed view IDs from `OrthographicView`/`OrbitView` (unnamed single-view) — fixes viewState mismatch (BUG-4)
- Stable `id: 'semantic-points'` on ScatterplotLayer (BUG-5) — `updateTriggers` handle all dynamic changes
- ViewState keyed by `'2d'`/`'3d'` (simpler than old `'semantic-2d'`/`'semantic-3d'`)
- Camera hardening: `dataLoaded` guard — auto-fit only on first load, not on every filter refetch
- 3D orbit angles preserved in `focusSelected()` — no tilt/orbit reset on selection change
- Updated `getFillColor`, `getRadius`, `getLineColor`, `getLineWidth` using `explorerColors.ts` constants
- Updated `Tooltip` component: cluster ID, outlier badge, edge-clamping (won't overflow canvas)
- Dev diagnostic overlay (DEV only): canvas dimensions × point count × zoom × bounds
- Dev diagnostic `console.debug` on mount (DEV only)

**Commit:** `fix(explorer): stabilize DeckGL viewport and layer rendering (BUGs 2,4,5)`

---

### Phase 3 — Context rail, control bar, ExplorerPage (UX improvements)

**Files:**
- `frontend/src/components/explorer/ExplorerContextRail.tsx`
- `frontend/src/components/explorer/ExplorerControlBar.tsx`
- `frontend/src/routes/ExplorerPage.tsx`

**ExplorerContextRail:**
- New props: `seedContext: SeedContext`, `onClearSeed: () => void`
- Seeded context chip in no-selection state (Stories→Explorer handoff visibility)
- "How to read this space" onboarding guide block (3 sentences, below guide text)
- Mode-sensitive `ColorLegend`: neutral dot / source outlet swatches / cluster color list
- Outlier badge (`context-outlier-badge`) in selection rail header

**ExplorerControlBar:**
- Labels: `'By source'`, `'By cluster'` instead of raw `'source'`/`'cluster'`
- `title` hints on 2D/3D buttons
- Loading label: `'N points (updating)'` during filter-change refetch

**ExplorerPage:**
- `seedContext = useMemo(...)` derived from `query.clusterId`/`query.search`
- Passed to `ExplorerContextRail` with `onClearSeed={resetQuery}`

**Commit:** `feat(explorer): context rail polish, seeded chip, and control bar improvements`

---

## Build verification

```
cd frontend && npm run build
✓ tsc -b — 0 type errors
✓ vite build — 711 modules transformed, 0 build errors
dist/assets/index-CbzGlOTe.css  23.45 kB
dist/assets/index-t3NwS3ti.js  903.68 kB
✓ built in 4.90s
```

---

## What was NOT done (deferred)

| Item | Reason |
|---|---|
| BUG-7: `useExplorerBootstrap.ts` orphan | Not a render bug; cleanup-only change, safe to defer |
| BUG-3: Verify zoom formula against real API data | Requires live API; diagnostic log added for developer to check on first load |
| Mobile bottom-sheet CSS transform | Out of scope for this pass per spec |
| `useExplorerData` selected-article race cleanup | Minor UX; not a render bug |

---

## Risks remaining

| Risk | Status |
|---|---|
| BUG-3: zoom formula may need tuning for real projection scale | Dev diagnostic log added — developer should check `[MapPanel] mount diagnostic` on first load with data |
| Safari flex/grid `min-height: 0` | `.explorer-workspace` has `min-height: 0` from iter/004; `overflow: hidden` added this pass. Standard fix — should hold |
| StrictMode test in dev mode | `key="explorer-deck"` is the standard mitigation; test in both dev and preview |

---

## Files changed in this pass

| File | Change |
|---|---|
| `frontend/src/styles.css` | CSS fixes + new Explorer additions |
| `frontend/src/lib/explorerColors.ts` | **NEW** — authoritative encoding constants |
| `frontend/src/components/explorer/MapPanel.tsx` | Render bug fixes + encoding improvements |
| `frontend/src/components/explorer/ExplorerContextRail.tsx` | Seeded chip + guide + legend improvements |
| `frontend/src/components/explorer/ExplorerControlBar.tsx` | Label + tooltip improvements |
| `frontend/src/routes/ExplorerPage.tsx` | seedContext derivation + prop pass |
| `STATUS.md` | Updated |
| `RESULTS.md` | This file |

---

## Previous pass

### iter/005 — architecture/diagnosis pass (preceding this)

**Date:** 2026-03-20 UTC
**Role:** `frontend` architect 🏗️
**Outcome:** ✅ Spec complete

Seven concrete render-reliability bugs diagnosed. Three key UX improvements specified. Implementation slices defined. Build order was: fix canvas first, improve encoding second, add context polish third.

See the architecture pass entries in this file for the full diagnosis record.

---

*Implementation complete. Next: verify in browser with real API data. Check `[MapPanel] mount diagnostic` log for canvas dimensions and zoom.*
