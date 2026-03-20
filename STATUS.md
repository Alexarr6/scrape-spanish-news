- State: BUILD_PASS
- Current phase: Explorer visualization refinement — iter/006 implementation complete
- Last update: 2026-03-20 UTC

## Completed deliverables (iter/006 — this pass)

Architecture spec only. No code written yet — ready for `frontend.react` builder.

- **UI_SPEC.md §4.A**: Three focused improvements specified:
  - 4.A.1: Pixel-aware zoom formula (replaces broken `log2(3.2/span)+1.4`)
  - 4.A.2: Axis layers via `LineLayer` (2D: grey X+Y; 3D: RGB XYZ + faint XY grid)
  - 4.A.3: 3D mode switches to `PointCloudLayer` (billboarded spheres, 5 tiers)
  - 4.A.4: New constants for `explorerColors.ts`
  - 4.A.5: What NOT to do (no new libraries, no 2D changes, no labels/ticks)
- **DESIGN_TOKENS.md §13**: Axis colors + PC sizes documented
- **COMPONENT_MAP.md §5.A**: Full implementation handoff with code-ready snippets:
  - `build2dViewState` / `build3dViewState` signatures updated
  - `buildAxisLayers()` function ready to paste
  - `PointCloudLayer` tier pattern ready to paste
  - `explorerColors.ts` additions listed

## Key technical decisions (architect rationale)

### 1. Zoom formula
- **Problem:** `log2(3.2/span)+1.4` assumes geographic/meter scale; projection is in `[-1,1]`
- **Fix:** `zoom = log2(canvasPx / paddedSpan)` — reads actual DOM canvas size at call time
- **Impact:** zoom goes from ~1.5 to ~8.5 for 900px canvas and `[-1,1]` data ✓
- **Fallback:** `zoom=8.5` when no DOM element yet (first `useState` call)

### 2. Axes
- **Layer type:** `LineLayer` (already in `@deck.gl/layers`, zero new deps)
- **2D:** single grey X+Y, slate-400 @35% — subtle, not dominant
- **3D:** RGB XYZ convention (X=red, Y=green, Z=blue) @45% + faint XY grid @12%
- **Extent:** `max(1.5, maxAbsBound * 1.1)` — extends just past data
- **Placement:** always first in layer stack so points render on top

### 3. 3D points
- **Problem:** `ScatterplotLayer` renders flat discs; looks planar at orbit angles
- **Fix:** `PointCloudLayer` — billboarded, always faces camera, appears as sphere
- **Pattern:** 5 separate layers (one per tier) with fixed `pointSize` per tier
- **`material: false`:** disables Phong lighting that would corrupt encoding colors
- **Picking:** each tier has `pickable: true`; topmost layer wins at cursor position
- **2D unchanged:** `ScatterplotLayer` stays for 2D (stroked circles are correct there)

## Not done (deferred)
- Axis tick marks / labels (complex, out of scope)
- Mobile bottom-sheet CSS (prev deferred, still deferred)
- `useExplorerBootstrap.ts` cleanup (prev deferred, still deferred)

## Build status
- iter/005 build: ✅ PASS (carried forward)
- iter/006 build: ✅ PASS — tsc 0 errors, vite 711 modules, 4.99s

## Pending verification (browser)
- Zoom should frame points on first load without manual zoom (~8.5 for [-1,1] data)
- Axes visible in 2D (grey) and 3D (RGB) without obscuring points
- 3D points appear as round spheres at all orbit angles (no flat disc artifacts)
