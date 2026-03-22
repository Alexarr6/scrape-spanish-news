# UI_SPEC.md — iter/006 Explorer Framing, Axes & 3D Point Pass

**Role:** Frontend Architect (iter/006)
**Date:** 2026-03-20
**Status:** Complete — ready for `frontend.react` builder pass (Section 4.A added)

---

## iter/006 delta — three focused improvements

This is a **tightly-scoped addendum** to iter/005. Sections 1–11 from iter/005 remain valid.
Only the items below are new or changed.

---

### 4.A.1 — Pixel-aware initial framing (fix zoom formula)

**Problem:** The current `build2dViewState` / `build3dViewState` zoom formula is:
```ts
zoom = Math.max(1.4, Math.min(7.2, Math.log2(3.2 / paddedSpan) + 1.4))
```
This assumes world-space units on the order of 3.2 (geographic/meters scale).
Actual semantic projection coordinates live in **~[-1, 1]** (span ≈ 2 world units).
The formula produces zoom ≈ **1.5** but the user needs zoom ≈ **8–9** to read points.

**Fix: pixel-aware zoom formula.**

DeckGL `OrthographicView` zoom semantics: at zoom `Z`, one world unit renders as `2^Z` pixels.
To fit `paddedSpan` world units into the canvas width (or height, whichever is tighter):

```ts
// Read from canvasRef.current at the moment fitAll/build is called
const canvasW = canvasRef.current?.clientWidth ?? 900
const canvasH = canvasRef.current?.clientHeight ?? 600
const canvasPx = Math.min(canvasW, canvasH)    // use tighter dimension
const PADDING_FACTOR = 1.25                     // 25% padding on each axis (12.5% each side)
const paddedSpan = dominantSpan * PADDING_FACTOR

zoom = Math.max(1.0, Math.min(14.0, Math.log2(canvasPx / paddedSpan)))
```

For real data in `[-1, 1]`:
- `dominantSpan` ≈ 2.0, `paddedSpan` ≈ 2.5
- 900px canvas → zoom ≈ 8.5 ✓ (matches the user-observed "need zoom ~8")
- 1280px canvas → zoom ≈ 9.0 ✓

**Fallback (no bounds / no DOM element yet):**
```ts
zoom = 8.5  // sensible default for [-1,1] scale on a ~900px canvas
```
This replaces the existing `zoom: 1.8` / `zoom: 1.9` defaults.

**Changes needed in `MapPanel.tsx`:**
- `build2dViewState` must accept `canvasPx: number` (pass from component)
- `build3dViewState` must accept `canvasPx: number`
- `canvasPx = Math.min(canvasRef.current.clientWidth, canvasRef.current.clientHeight)` — read at call-site from `canvasRef`
- Both `fitAll()` and the initial mount effect must pass `canvasPx`
- The `PADDING_FACTOR` is `1.25` for 2D, `1.4` for 3D (slightly more padding for depth perception)
- Clamp: `Math.max(1.0, Math.min(14.0, computed))`
- Remove the hardcoded `3.2 / paddedSpan + 1.4` formula entirely

**No changes to UI** — this is a pure camera math fix.

---

### 4.A.2 — Visible axes for orientation

**Goal:** Give users a coordinate reference without cluttering the canvas.

**Design decision:**
- Use a **dedicated DeckGL layer**, not DOM/SVG overlay — keeps it in the same coordinate space as points
- Use `LineLayer` (already in `@deck.gl/layers`) — no new imports
- Axes should be **subtle, not dominant** — they serve orientation, not primary content
- Show axes in **both 2D and 3D**
- In 3D, add a faint XY-plane grid to enhance depth perception

**2D axes specification:**

```
X axis: horizontal line at Y=0, from X=-1.5 to X=1.5 (slightly beyond typical data bounds)
Y axis: vertical line at X=0, from Y=-1.5 to Y=1.5
Color: rgba(148, 163, 184, 0.35)  — slate-400 at 35% opacity (very subtle)
Width: 1.0px, widthUnits: 'pixels'
No tick marks, no labels (too complex for this pass)
Z: 0 for both 2D axis lines
```

**3D axes specification:**

```
X axis: [−1.5, 0, 0] → [1.5, 0, 0]
Y axis: [0, −1.5, 0] → [0, 1.5, 0]
Z axis: [0, 0, −1.5] → [0, 0, 1.5]
Colors (per axis, classic convention):
  X: rgba(220, 38, 38, 0.45)    — red-600, 45% opacity
  Y: rgba(34, 197, 94, 0.45)    — green-500, 45% opacity
  Z: rgba(59, 130, 246, 0.45)   — blue-500, 45% opacity
Width: 1.5px

XY plane faint grid (optional, adds depth):
  Grid lines from −1 to +1 at integer intervals on both axes
  Z=0 plane, horizontal and vertical lines
  Color: rgba(148, 163, 184, 0.12)  — very faint slate
  Width: 0.8px
  Only in 3D mode
```

**Axis extent:** The `[-1.5, 1.5]` range covers typical projection bounds.
The builder should extend to `Math.max(1.5, bounds.maxX * 1.1)` if bounds are available.

**Implementation in `MapPanel.tsx`:**

```ts
import { LineLayer } from '@deck.gl/layers'

function buildAxisLayers(viewMode: ExplorerViewMode, bounds: PointBounds | null) {
  const extent = Math.max(1.5, bounds ? Math.max(
    Math.abs(bounds.minX), Math.abs(bounds.maxX),
    Math.abs(bounds.minY), Math.abs(bounds.maxY),
  ) * 1.1 : 1.5)

  if (viewMode === '2d') {
    return [
      new LineLayer({
        id: 'axis-2d',
        data: [
          { from: [-extent, 0, 0], to: [extent, 0, 0] },   // X axis
          { from: [0, -extent, 0], to: [0, extent, 0] },   // Y axis
        ],
        getSourcePosition: (d) => d.from,
        getTargetPosition: (d) => d.to,
        getColor: [148, 163, 184, 90],  // slate-400 @ ~35%
        getWidth: 1.0,
        widthUnits: 'pixels',
        pickable: false,
      }),
    ]
  }

  // 3D mode — XYZ colored axes + XY grid
  const axisData = [
    { from: [-extent, 0, 0], to: [extent, 0, 0], color: [220, 38, 38, 115] as [number,number,number,number] },   // X red
    { from: [0, -extent, 0], to: [0, extent, 0], color: [34, 197, 94, 115] as [number,number,number,number] },   // Y green
    { from: [0, 0, -extent], to: [0, 0, extent], color: [59, 130, 246, 115] as [number,number,number,number] },  // Z blue
  ]

  // Optional XY plane grid (faint)
  const gridLines: { from: [number,number,number]; to: [number,number,number]; color: [number,number,number,number] }[] = []
  const gridExtent = Math.ceil(extent)
  for (let i = -gridExtent; i <= gridExtent; i++) {
    gridLines.push(
      { from: [-extent, i, 0], to: [extent, i, 0], color: [148, 163, 184, 30] as [number,number,number,number] },
      { from: [i, -extent, 0], to: [i, extent, 0], color: [148, 163, 184, 30] as [number,number,number,number] },
    )
  }

  return [
    new LineLayer({
      id: 'axis-grid-3d',
      data: gridLines,
      getSourcePosition: (d) => d.from,
      getTargetPosition: (d) => d.to,
      getColor: (d) => d.color,
      getWidth: 0.8,
      widthUnits: 'pixels',
      pickable: false,
    }),
    new LineLayer({
      id: 'axis-3d',
      data: axisData,
      getSourcePosition: (d) => d.from,
      getTargetPosition: (d) => d.to,
      getColor: (d) => d.color,
      getWidth: 1.5,
      widthUnits: 'pixels',
      pickable: false,
    }),
  ]
}
```

**Layer order:** Axis layers must be first in the `layers` array so points render on top:
```ts
layers={[...buildAxisLayers(viewMode, bounds), ...pointLayers]}
```

The `bounds` variable should be derived from `points?.meta.bounds` (already available in MapPanel).

**No new npm packages needed** — `LineLayer` is already in `@deck.gl/layers`.

---

### 4.A.3 — 3D points as volumetric spheres (not flat discs)

**Problem:** `ScatterplotLayer` in DeckGL renders points as **flat filled circles** — in 3D views, they look like flat discs lying in the XY plane rather than volumetric points. Under typical orbit angles (rotationX ≈ 32°), they appear oval/flat and lose depth presence.

**Fix: switch 3D mode to `PointCloudLayer`.**

`PointCloudLayer` (in `@deck.gl/layers`) renders points as **screen-aligned billboarded spheres** — they always face the camera and appear as true circles at any orbit angle, with consistent visual weight regardless of viewing angle.

**Approach: render two layers, switched by `viewMode`:**

```ts
import { PointCloudLayer } from '@deck.gl/layers'

// In the layers memo:
if (viewMode === '3d') {
  layers.push(new PointCloudLayer<ExplorerPoint>({
    id: 'semantic-points-3d',
    data: items,
    pickable: true,
    sizeUnits: 'pixels',
    pointSize: POINT_SIZE_MAP,    // see below
    getPosition: (p) => [p.x, p.y, p.z],
    getColor: (p) => getFillColorForPoint(p),
    getNormal: [0, 0, 1],         // unused for billboard, required by API
    material: false,              // disable Phong shading — pure color, clean look
    updateTriggers: {
      getColor: [colorMode, selectedArticleId, hoveredArticleId, neighborKey],
      pointSize: [selectedArticleId, hoveredArticleId, neighborKey],
    },
  }))
} else {
  layers.push(new ScatterplotLayer<ExplorerPoint>({ /* existing 2D layer */ }))
}
```

**Point size mapping for `PointCloudLayer`:**
`PointCloudLayer` has a single `pointSize` prop (not per-point) — it does NOT support `getRadius`.
Work around this limitation by rendering **multiple** `PointCloudLayer` instances, one per visual tier:

```ts
// Tier ordering: axis layers → regular → outlier → neighbor → hovered → selected
// Each layer has a fixed pointSize and filtered data

const items3d = {
  regular:  items.filter(p => !isHighlighted(p)),
  outlier:  items.filter(p => p.analysis.is_outlier && !isHighlighted(p)),
  neighbor: items.filter(p => neighborIds.has(p.article_id)),
  hovered:  hoveredArticleId != null ? items.filter(p => p.article_id === hoveredArticleId) : [],
  selected: selectedArticleId != null ? items.filter(p => p.article_id === selectedArticleId) : [],
}

// Point sizes (pixels) per tier
// These are bigger than 2D because PointCloudLayer renders as sphere diameter
const PC_SIZE_REGULAR  = 8   // ≈ POINT_REGULAR_RADIUS_3D * 2 = 9
const PC_SIZE_OUTLIER  = 10  // ≈ POINT_OUTLIER_RADIUS_3D * 2 = 12
const PC_SIZE_NEIGHBOR = 14  // ≈ POINT_NEIGHBOR_RADIUS_3D * 2 = 15
const PC_SIZE_HOVERED  = 12  // ≈ POINT_HOVERED_RADIUS_3D * 2 = 13
const PC_SIZE_SELECTED = 18  // ≈ POINT_SELECTED_RADIUS_3D * 2 = 20
```

**Where `isHighlighted(p)`:**
```ts
const isHighlighted = (p: ExplorerPoint) =>
  p.article_id === selectedArticleId ||
  neighborIds.has(p.article_id) ||
  p.article_id === hoveredArticleId
```

**Color function for `PointCloudLayer`** (same logic as `getFillColor`, minus stroke):
```ts
function getPointCloudColor(point: ExplorerPoint): [number,number,number,number] {
  if (point.article_id === selectedArticleId) return POINT_SELECTED_FILL
  if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_FILL
  if (point.article_id === hoveredArticleId) return POINT_HOVERED_FILL
  const [r, g, b] = colorForPoint(point, colorMode)
  const alpha = hasSelection
    ? (point.analysis.is_outlier ? POINT_OUTLIER_ALPHA_UNDER_SELECTION : POINT_REGULAR_ALPHA_UNDER_SELECTION)
    : (point.analysis.is_outlier ? POINT_OUTLIER_ALPHA_NO_SELECTION : POINT_REGULAR_ALPHA_NO_SELECTION)
  return [r, g, b, alpha]
}
```

**Important:** `PointCloudLayer` does NOT support `stroked` — no outline. This is fine for 3D; in 3D mode the depth separation and color are the primary differentiators.

**`material: false`** disables Phong lighting, which would distort the encoding colors unpredictably. Keep it false — pure flat color is correct for this use case.

**No new npm packages** — `PointCloudLayer` is already in `@deck.gl/layers`.

**Final 3D layer stack (order matters):**
```ts
// 3D mode layers (bottom → top)
[
  ...axisGridLayers,         // XY grid (faint)
  ...axisLineLayers,         // XYZ colored axes
  regularPointCloud,         // regular points (behind)
  outlierPointCloud,         // outliers (slightly in front)
  neighborPointCloud,        // neighbor highlight tier
  hoveredPointCloud,         // hover tier
  selectedPointCloud,        // selected — always on top
]
```

---

### 4.A.4 — Axis constants to add to `explorerColors.ts`

```ts
// Axis and grid colors — add to explorerColors.ts
export const AXIS_COLOR_2D: [number, number, number, number] = [148, 163, 184, 90]   // slate-400 @35%
export const AXIS_X_COLOR_3D: [number, number, number, number] = [220, 38, 38, 115]   // red-600 @45%
export const AXIS_Y_COLOR_3D: [number, number, number, number] = [34, 197, 94, 115]   // green-500 @45%
export const AXIS_Z_COLOR_3D: [number, number, number, number] = [59, 130, 246, 115]  // blue-500 @45%
export const AXIS_GRID_COLOR_3D: [number, number, number, number] = [148, 163, 184, 30] // very faint

export const PC_SIZE_REGULAR  = 8   // PointCloudLayer 3D point sizes (pixel diameter)
export const PC_SIZE_OUTLIER  = 10
export const PC_SIZE_NEIGHBOR = 14
export const PC_SIZE_HOVERED  = 12
export const PC_SIZE_SELECTED = 18
```

---

### 4.A.5 — What the builder must NOT do for this pass

- Do not migrate to `react-three-fiber` or `three.js`
- Do not add axis labels / tick marks (too complex, out of scope)
- Do not apply `material: true` (Phong) to `PointCloudLayer` — it distorts encoding colors
- Do not replace `ScatterplotLayer` in 2D — only 3D switches to `PointCloudLayer`
- Do not change the context rail, control bar, or filter drawer
- Do not redesign the zoom/pan UX — only fix the formula

---

---

## Scope of this revision

This document covers two iterations:

**iter/005 (prior):** Section 4 — Explorer render reliability diagnosis + full Explorer UX rewrite.

**iter/006 (this pass — Section 4.A above):**
Three tightly-bounded improvements to the Explorer visualization:
- 4.A.1: Pixel-aware zoom formula (fixes `[-1,1]` framing)
- 4.A.2: Visible axes via `LineLayer` in both 2D and 3D
- 4.A.3: 3D points switch to `PointCloudLayer` (volumetric billboarded spheres)
- 4.A.4: New axis/PC constants for `explorerColors.ts`

**What is unchanged from iter/005:** Sections 1–3, 4.1–4.15, 5–11 all remain valid.

---

## 1. Product thesis

*(unchanged from iter/004)*

This is a **media-intelligence workspace**, not a BI dashboard.

Two questions:
1. **Stories:** What stories exist in the coverage landscape, and how are Spanish outlets treating each one differently?
2. **Explorer:** How is a corpus of articles semantically arranged — which outlets cluster, which sit on the margin?

Explorer is a **specialist secondary surface** — not the editorial front door, not a 3D art piece.

---

## 2. Navigation model

*(unchanged from iter/004)*

---

## 3. Route anatomy — Stories

*(unchanged from iter/004)*

---

## 4. Route anatomy — Explorer

### 4.0 The real problem statement

The Explorer currently exhibits **render unreliability**: the map container appears but the DeckGL canvas does not paint points. This section addresses that failure first, then specifies the product/UX improvements once a reliable baseline exists.

**Do not add new features until the render failure is fixed.**

---

### 4.1 Render reliability diagnosis

After reading the full codebase — `MapPanel.tsx`, `ExplorerPage.tsx`, `useExplorerData.ts`, `styles.css` — the following are the **most likely causes** of blank-canvas behavior, ranked by probability:

---

#### BUG-1 (Highest risk): DeckGL canvas gets zero computed height

**Root cause:** DeckGL requires its container to have an explicit pixel height. The current CSS achieves this via `flex: 1` on nested flex children, which requires every ancestor in the flex chain to have `min-height: 0` and proper flex expansion.

**Suspects in current CSS:**
```css
/* .explorer-layout: flex column, flex: 1 ✓ */
/* .explorer-workspace: flex: 1 + grid — but no min-height: 0 ✗ */
/* .explorer-canvas-area: flex column, min-height: 0 ✓ */
/* .map-frame: position: relative, flex: 1, min-height: 0 ✓ */
/* .map-canvas: flex: 1, position: relative, min-height: 0 ✓ */
```

The `explorer-workspace` div uses `display: grid` and `align-items: stretch` but is missing `min-height: 0`. In some browser contexts, this can prevent the grid from actually expanding inside a flex parent, collapsing the canvas to zero height.

**Diagnosis:** The DeckGL canvas calculates its own size from its container's `offsetWidth`/`offsetHeight`. If those are 0 at mount time and DeckGL does not re-check on resize, the canvas is blank even when points exist.

**Fix:**
```css
.explorer-workspace {
  min-height: 0;  /* ADD THIS */
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--explorer-context-width);
  align-items: stretch;
}

/* Also guard the full flex chain */
.app-main {
  min-height: 0; /* ADD THIS if not present */
}
```

**Verification:** Add `data-debug-height` attribute in dev mode and confirm `offsetHeight > 0` on `.map-canvas` before DeckGL mount.

---

#### BUG-2 (High risk): DeckGL React StrictMode double-mount drops the canvas

**Root cause:** React 18 StrictMode runs effects twice in development. DeckGL 9.x's React wrapper may not handle double-mount/unmount cleanly — the Deck instance can be destroyed on the simulated unmount and not reliably reinstated.

**Evidence:** `main.tsx` wraps in `<React.StrictMode>`. DeckGL 9.x has known interactions with React 18 strict mode.

**Fix options (pick one):**
1. Confirm DeckGL 9.1.x handles StrictMode — if not, temporarily disable StrictMode in dev builds (not in production) to isolate the bug.
2. Alternatively, add an `id` key to `<DeckGL>` that is stable (not changing on re-render) to prevent remounting.

**Verification strategy:** Remove `<React.StrictMode>` wrapper temporarily. If points appear, this is confirmed. Re-enable StrictMode with DeckGL key stabilization.

---

#### BUG-3 (Medium risk): ViewState mismatch causing points to render outside visible bounds

**Root cause:** `build2dViewState` and `build3dViewState` compute zoom from `log2(3.2 / paddedSpan)`. If the semantic projection's coordinate space has `paddedSpan` significantly smaller or larger than 3.2, the zoom formula produces a value that maps points far outside the visible canvas area.

**Current zoom formula:**
```ts
zoom: Math.max(1.4, Math.min(7.2, Math.log2(3.2 / paddedSpan) + 1.4))
```

If `paddedSpan ≈ 0.001` (very compact projection), zoom = ~11 (clamped to 7.2, but still wrong centering). If `paddedSpan ≈ 100`, zoom goes negative (clamped to 1.4, but points may be at wrong target).

**Current target formula:**
```ts
target: [midX, midY, 0]
```
This is correct for centering, but only if the projection coordinate space is symmetric around the midpoint.

**Diagnosis:** The projection API returns `min_x, max_x, min_y, max_y`. The zoom formula is hardcoded to a specific scale assumption (3.2 world units ≈ one screenful). This needs to be verified against real data.

**Fix:** Add a diagnostic log in dev mode:
```ts
console.debug('[MapPanel] computed viewState', viewState, 'from bounds', bounds)
```
Check whether the resulting zoom and target place points within [−1, 1] of the viewport center in screen space.

**Alternative fix:** Use `OrthographicView`'s native zoom-to-fit approach by computing zoom from canvas pixel dimensions and projection span directly:
```ts
// Approximate: assume canvas is W×H pixels
// zoom such that paddedSpan world units = W pixels
// DeckGL OrthographicView: 1 zoom unit ≈ 2^zoom pixels per world unit
const CANVAS_REF_SIZE = 900 // approximate canvas px
zoom = Math.log2(CANVAS_REF_SIZE / paddedSpan)
```

---

#### BUG-4 (Medium risk): viewState passed to DeckGL as single object but views array expects multi-view keyed state

**Root cause:** `MapPanel` passes `viewState={activeViewState as never}` — a single view state object. DeckGL's multi-view model (`views={[new OrthographicView({ id: 'semantic-2d' })]}`) expects viewState to be **either** a plain object (if single view, no id needed) or a `{ [viewId]: viewState }` map (if multiple views or named views).

With named views (`id: 'semantic-2d'`), DeckGL may not match the unkeyed `activeViewState` to the view, resulting in no camera being applied.

**Fix:** Ensure viewState structure matches DeckGL's named-view expectation:
```tsx
// Option A: Remove view ids (simpler, matches current single-view usage)
views={
  viewMode === '3d'
    ? [new OrbitView({})]   // no id
    : [new OrthographicView({})]  // no id
}
viewState={activeViewState}

// Option B: Pass keyed viewState matching the view id
viewState={{ [viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']: activeViewState }}
```

Option A is safer and simpler for single-view usage. The current code uses named view IDs but does not pass a keyed viewState — this is a concrete bug.

---

#### BUG-5 (Medium risk): Layer key forcing full re-create on every viewMode/colorMode change

**Current layer id:**
```ts
id: `semantic-points-${viewMode}-${colorMode}`
```

Every time `viewMode` or `colorMode` changes, DeckGL gets a new layer ID. DeckGL treats a changed ID as a new layer — it destroys and recreates the GPU buffers. This is correct when the data geometry changes (2D vs 3D does change `getPosition`), but it also resets all internal GPU state including the render pipeline.

This is not a blank-canvas bug by itself, but it means that transitions between modes are guaranteed to cause a brief flash/blank frame.

**Fix:** Keep the ID stable, rely on `updateTriggers` to signal changes:
```ts
id: 'semantic-points'  // stable
updateTriggers: {
  getPosition: [viewMode],
  getRadius: [viewMode, selectedArticleId, hoveredArticleId, neighborKey],
  getFillColor: [viewMode, colorMode, selectedArticleId, hoveredArticleId, neighborKey],
  getLineColor: [selectedArticleId, neighborKey],
}
```
This is already partially done — but the ID is still changing. Fix: use a stable ID.

---

#### BUG-6 (Lower risk): CSS `!important` override on DeckGL canvas may conflict

**Current CSS:**
```css
.map-canvas > div,
.map-canvas canvas {
  width: 100% !important;
  height: 100% !important;
}
```

This is meant to force the DeckGL container to fill its parent. However, DeckGL 9.x may set its own `width`/`height` on the wrapper `div` via inline styles that conflict with this. In some cases, DeckGL needs to control its own container size to calculate device pixel ratio and canvas resolution.

**Fix:** Remove the `!important` rule. Instead, ensure the `.map-canvas` container has a correct explicit size via flex layout (the real fix is BUG-1). DeckGL should size itself from its container.

---

#### BUG-7 (Low risk): Missing `useExplorerBootstrap` — double data fetch race condition

`useExplorerBootstrap.ts` exists but is **not used** in the current `ExplorerPage.tsx`. Instead, `useExplorerData` fetches data independently. The bootstrap hook was presumably meant to pre-warm data, but it appears orphaned.

This is not a blank-canvas bug, but the double fetch could cause a state race on mount:
- `useExplorerData` fetches points with current `query`
- Simultaneously triggers `setSelectedArticleId(null)` if the selected article is not in the result set

If the first render happens before the API returns, `pointsState.data` is `null`, so `points?.items.length === 0` renders the empty state overlay inside DeckGL — this overlay may visually mask the canvas even when data loads later, if it stays mounted.

**Fix:** Ensure the empty state overlay is only shown when `!loading && !error && (points?.items.length ?? 0) === 0`. The current code does this correctly, but verify that the loading state is set to `true` at mount so the empty overlay never shows during initial load.

---

### 4.2 Render reliability hardening plan

**Hardening steps for the builder (ordered):**

**Step 1: Fix flex/grid height chain (BUG-1)**
- Add `min-height: 0` to `.explorer-workspace` and `.app-main`
- Remove `!important` from `.map-canvas > div, .map-canvas canvas` (BUG-6)
- Add explicit `height: 100%` to `.map-canvas` (not just `flex: 1`)
- Verify canvas `offsetHeight > 0` in browser DevTools before any other debugging

**Step 2: Stabilize layer ID (BUG-5)**
- Change layer id to `'semantic-points'`
- Verify `updateTriggers` cover all dynamic properties (they do in current code)

**Step 3: Fix named-view viewState mismatch (BUG-4)**
- Remove `id` from `OrthographicView` and `OrbitView` to use unnamed single-view mode
- Or pass viewState as `{ 'semantic-2d': activeViewState }` / `{ 'semantic-3d': activeViewState }`
- Single-view unnamed is simpler and correct for the current architecture

**Step 4: Validate viewState bounds formula (BUG-3)**
- Add a dev-mode `console.debug` of the computed viewState and raw bounds
- Verify zoom places points within visible canvas area
- If zoom is wrong: implement pixel-based zoom formula using canvas element `clientWidth`

**Step 5: Verify StrictMode interaction (BUG-2)**
- In dev: temporarily disable StrictMode and check if points appear
- If confirmed: add stable `key` to `<DeckGL>` to prevent identity loss on simulated remount

**Step 6: Add dev diagnostic banner**
- In dev builds only (`import.meta.env.DEV`), add a small diagnostic overlay:
  ```
  [DEV] points: {N} | canvas: {W}×{H}px | zoom: {Z} | bounds: {minX,maxX,minY,maxY}
  ```
- Remove before any production build

---

### 4.3 Canvas diagnostic instrumentation (dev only)

Add a `useEffect` in `MapPanel` (dev-only):
```ts
useEffect(() => {
  if (!import.meta.env.DEV) return
  const el = document.querySelector('.map-canvas')
  if (el) {
    console.debug('[MapPanel] canvas size', el.clientWidth, 'x', el.clientHeight)
  }
  console.debug('[MapPanel] points count', points?.items.length ?? 0)
  console.debug('[MapPanel] active viewState', activeViewState)
  console.debug('[MapPanel] bounds', bounds)
}, [points, activeViewState, bounds])
```

This log should be the first thing checked when the map appears blank.

---

### 4.4 Goal

Answer: **How is the current article corpus semantically arranged? Which outlets cluster? Which sit on the margin?**

The Explorer is a **specialist analytical tool**. It assumes the analyst already has a question in mind. 2D is the primary analytical mode. 3D is an intentional depth-inspection overlay.

---

### 4.5 Layout model (desktop ≥ 1280px)

```
┌──────────────────────────────────────────────────────────────────┐
│  TOP BAR                                                         │
├──────────────────────────────────────────────────────────────────┤
│  ANALYST CONTROL BAR                                             │
│  [2D/3D]  [Neutral/Source/Cluster]  [Fit all]  [Focus]          │
│                              n points  [n filters]  [Refine ↓]  │
├──────────────────────────────┬───────────────────────────────────┤
│                              │  CONTEXT RAIL (320px)            │
│  SEMANTIC CANVAS             │                                   │
│  (DeckGL, fills remaining    │  — no selection:                  │
│   height and width)          │    guide + legend + dataset       │
│                              │                                   │
│  [dev diagnostic overlay]   │  — selected:                      │
│  [hover tooltip]            │    article + cluster + neighbors  │
│                              │                                   │
│  [empty state if no pts]    │  — seeded context chip            │
│                              │    (if arriving from Stories)     │
└──────────────────────────────┴───────────────────────────────────┘
```

**Column widths:**
- Canvas: `minmax(0, 1fr)` — greedy, takes all remaining space
- Context rail: `--explorer-context-width: 320px` — fixed

**Height allocation:**
- Top bar: `--topbar-height: 3rem` (48px)
- Control bar: `3rem` (48px) — flex-shrink: 0
- Workspace (canvas + rail): `flex: 1`, `min-height: 0`

The entire height chain must be explicit. See BUG-1.

---

### 4.6 Analyst control bar specification

A compact horizontal bar between the top bar and the canvas.

```
LEFT:
  [2D | 3D]                    ← segmented control, 2D default
  [Neutral | Source | Cluster] ← segmented control, Neutral default
  [Fit all]                    ← ghost button, always visible
  [Focus selected]             ← ghost button, only if selectedArticleId != null

RIGHT:
  n points                     ← passive metadata text
  [n filters]                  ← accent badge, only if activeFilterCount > 0
  [Refine ↓]                   ← ghost button, opens filter drawer
```

**Behavior rules:**
- No floating controls inside the canvas
- "Fit all": resets camera to show all visible points, preserving current viewMode
- "Focus selected": zooms to selected point + its neighbors (padded bounds)
- Point count: `{N} points` when loaded; `Loading…` when `loading && pointCount === 0`
- No loading spinner in the control bar — the canvas loading overlay handles that

**Label improvements from iter/004 segmented controls:**
- 2D label: `2D` *(unchanged)* with tooltip hint `"Compare layout"` (HTML title attr)
- 3D label: `3D` *(unchanged)* with tooltip hint `"Inspect depth / overlap"`
- Neutral label: `Neutral` — keep
- Source label: `By source` — more descriptive than `source`
- Cluster label: `By cluster` — more descriptive than `cluster`

---

### 4.7 Semantic canvas

The DeckGL canvas fills all remaining height and width of `explorer-canvas-area`.

**What lives inside the canvas:**
- The DeckGL render surface
- Hover tooltip (positioned by `info.x`, `info.y`)
- Empty state overlay (centered, absolute) — only when points exist but are zero
- Error state overlay — only when API error
- Loading overlay (semi-transparent) — only during initial load, not on filter changes

**What must NOT live inside the canvas:**
- Controls (moved to control bar — already done in iter/004 build)
- Guide text (moved to context rail — already done)
- Legend (moved to context rail — already done)

**Canvas background:**
- Light mode: `var(--color-bg)` — page background
- Do not add a visible grid or coordinate axes in 2D mode
- In 3D mode: no extra visual chrome needed for this iteration

---

### 4.8 2D mode behavior specification

**Purpose:** Fast layout scanning, broad pattern recognition, cluster topology.

**Camera defaults:**
- `OrthographicView` (no `id` needed for single-view usage)
- Controller: `{ dragRotate: false, doubleClickZoom: true, touchRotate: false }`
- Initial zoom: fit all points with 25% padding
- No roll/tilt — orthographic flat view only

**On "Fit all":**
- Recompute `build2dViewState` from `points.meta.bounds`
- Apply immediately to `viewState['semantic-2d']`
- Preserve any zoom level the user was at — do NOT force reset unless explicitly called

**On "Focus selected":**
- Compute bounds from selected point + all neighbor points
- Apply zoomed `build2dViewState` with +0.25 zoom boost
- Maintain current `target[2] = 0` (flat)

**Scroll/zoom:** standard pan/zoom, no inertia needed in 2D

---

### 4.9 3D mode behavior specification

**Purpose:** Inspect depth separation, cluster overlap in Z axis, article density.

**Camera defaults:**
- `OrbitView` (no `id` needed for single-view usage)
- Controller: `{ dragMode: 'rotate', inertia: true }`
- Default tilt: `rotationX: 32` (slightly above horizon)
- Default orbit: `rotationOrbit: 28`
- Initial zoom: same computation as 2D but with Z span factored in

**On switching from 2D → 3D:**
- Preserve the camera `target` (same center point)
- Apply default `rotationX` and `rotationOrbit` if not previously set
- Do NOT jump to a different center

**On switching from 3D → 2D:**
- Preserve the camera `target`
- Reset rotation (orthographic ignores it anyway)
- Do NOT force a fit-all — stay at current zoom center

**On "Fit all" in 3D:**
- Compute bounds including Z axis span
- Apply `build3dViewState` preserving current `rotationOrbit` and `rotationX`

**On "Focus selected" in 3D:**
- Zoom to selection+neighbor bounds including Z
- Preserve current orbit angles (do not reset tilt)

**User rotation in 3D:**
- Preserve user's orbital angle when selection changes
- Do not auto-reset orbit on every `setSelectedArticleId`

---

### 4.10 Visual encoding hierarchy specification

The encoding must convey priority clearly. The following hierarchy is absolute:

```
PRIORITY 1: Selected point       — always visible, always dominant
PRIORITY 2: Semantic neighbors   — clearly distinguished, never confused with unselected
PRIORITY 3: Outlier points       — distinct when no selection; recede under selection priority
PRIORITY 4: Regular points       — the semantic field, recedes on selection
```

**Point states and their visual treatment:**

| State | Fill color | Stroke color | Stroke width | Radius (2D) | Radius (3D) | Alpha |
|---|---|---|---|---|---|---|
| Selected | `#0ea5e9` (sky-500) | `#ffffff` | 2.8px | 9px | 10px | 255 |
| Neighbor | `#22c55e` (green-500) | `#dcfce7` | 1.5px | 7px | 7.5px | 235 |
| Hovered (unselected) | `#7dd3fc` (sky-300) | `#e0f2fe` | 0.8px | 6px | 6.5px | 235 |
| Outlier (no selection) | base color | `#fef2f2` | 1px | 5.5px | 6px | 230 |
| Regular (no selection) | base color | `rgba(248,250,252,0.75)` | 0.6px | 4px | 4.5px | 210 |
| Regular (under selection) | base color | `rgba(226,232,240,0.35)` | 0px | 4px | 4.5px | 65 |
| Outlier (under selection) | base color | `rgba(226,232,240,0.35)` | 0px | 5px | 5.5px | 100 |

**Rules:**
- Selected point ALWAYS renders at max alpha (255), regardless of other state
- Neighbor ring ALWAYS renders at high alpha (235) to be clearly readable
- When a point is selected, regular points drop to alpha ~65 — still visible but receding
- Outliers under selection drop to alpha ~100 — slightly more visible than regular to preserve their structural signal
- Stroke on regular/receding points: zero width (no stroke) — reduces visual noise at low alpha

**Color lens behavior:**

*Neutral mode:*
- All non-selected, non-neighbor points: `#4338ca` (accent indigo) with alpha from table
- Calm, uniform field — makes spatial structure visible without source noise

*Source mode:*
- Color by `point.source`, using stable source → color mapping
- Source palette (consistent with `DESIGN_TOKENS.md`):
  ```ts
  const SOURCE_COLORS = {
    elpais:      [59, 130, 246],   // blue-500
    elmundo:     [16, 185, 129],   // emerald-500
    abc:         [249, 115, 22],   // orange-500
    eldiario:    [168, 85, 247],   // purple-500
    lavanguardia:[236, 72, 153],   // pink-500
    '20minutos': [251, 191, 36],   // amber-400
  }
  const FALLBACK_SOURCE_COLOR = [100, 116, 139]  // slate-500
  ```
- Alpha table applies same as neutral mode (selection dims all non-selected)

*Cluster mode:*
- Color by `point.analysis.cluster_id`
- Cluster palette (6 hues, cycles): same as current `CLUSTER_PALETTE` (adequate for now)
- Outliers in cluster mode: `[220, 38, 38]` (red-600) — preserved
- Unclustered/null cluster_id: `[148, 163, 184]` (slate-400)

**Outlier marker:**
Outliers are NOT given a special shape (diamond, square) in this iteration — shape encoding requires custom vertex shaders. Use the radius and alpha differences from the table above. Outlier `is_outlier: true` points get:
- Slightly larger radius than regular (+1.5px in 2D)
- Slightly higher alpha than regular under selection (+35 alpha)
- In the legend: explicitly labeled with a warning-color dot

---

### 4.11 Hover tooltip specification

**Trigger:** `onHover` on ScatterplotLayer, existing behavior.

**Position:** `left: info.x + 14, top: info.y + 14` — existing behavior is correct. Consider clamping to canvas bounds to prevent overflow at edges.

**Content spec:**
```
┌─────────────────────────────────────────────────┐
│  [SOURCE] · [SECTION]           [OUTLIER badge?] │
│  TITLE (max 2 lines, font-weight 600)            │
│  Published: DATE                                 │
│  [Cluster N]  or  [No cluster]                   │
│  Summary snippet (max 2 lines, muted)            │
└─────────────────────────────────────────────────┘
```

**Current tooltip only shows:** title, source, section, date, summary snippet.

**Add:**
- Cluster ID badge: `Cluster N` or `No cluster` (styled as `.badge.muted`)
- Outlier flag: `Outlier` badge in red if `point.analysis.is_outlier`

**Tooltip overflow protection:**
```ts
// Clamp tooltip so it doesn't go off canvas right/bottom edge
const { x, y } = info
const maxX = canvasWidth - TOOLTIP_WIDTH - 20
const maxY = canvasHeight - TOOLTIP_HEIGHT - 20
const left = Math.min(x + 14, maxX)
const top = Math.min(y + 14, maxY)
```

Canvas dimensions can be read from the containing element via a ref.

---

### 4.12 Context rail specification

**Width:** 320px. Fixed. Scrollable.

**No-selection state:**

```
┌──────────────────────────────┐
│  Click any point to inspect  │
│  an article and its semantic │
│  neighborhood.               │
│                              │
│  ─── Legend ─────────────── │
│  ● Selected article          │
│  ● Semantic neighbors        │
│  ● Outlier                   │
│  ● [Color mode explanation]  │
│                              │
│  How to read this space:     │
│  [Short 2–3 sentence guide]  │
│                              │
│  ─── Dataset ─────────────  │
│  N clusters · N sources      │
│  N clustered articles        │
│  2D: compare layout          │
│  3D: inspect depth           │
└──────────────────────────────┘
```

**Legend entries (always shown, context-sensitive):**
1. `● Selected article` — sky-500 dot
2. `● Semantic neighbors` — green-500 dot
3. `● Outliers` — red-600 dot
4. `● [Mode-specific]`:
   - Neutral: "Neutral field (structural baseline)"
   - Source: "Color by source outlet" + mini source swatches (El País, El Mundo, ABC…)
   - Cluster: "Color by cluster" + cluster count

**How to read this space (onboarding microcopy, no-selection state only):**
> Proximity = semantic similarity. Points near each other discuss similar topics. Clusters (color groups) indicate articles that the model grouped together. Outliers (red) sit outside all clusters.

This copy is shown only in the no-selection state as a single collapsed block. Max 3 sentences. Does not repeat on every open.

**Seeded context chip (if arriving from Stories):**
If `query.clusterId` or `query.search` is non-empty on mount, show a visible chip at the top of the context rail:

```
┌──────────────────────────────┐
│  📍 Filtered by: Cluster 3   │  ← or "Filtered by: 'energy'"
│  [Clear filter ×]            │
├──────────────────────────────┤
│  Click any point to inspect… │
│  ...                         │
└──────────────────────────────┘
```

This makes the Stories → Explorer handoff visible instead of magical.

**Selection state:**

```
┌──────────────────────────────┐
│  [← Clear]                   │
│                              │
│  SOURCE · SECTION            │
│  Date: DD Mon YYYY           │
│  [Outlier badge if applicable]│
│                              │
│  ARTICLE TITLE               │
│  Summary / excerpt           │
│                              │
│  [Open article ↗]            │
│  [Open in Stories →]         │  ← only if cluster_id exists
│                              │
│  ─── Cluster context ─────  │
│  Cluster N · N articles      │
│  Sources: El País, El Mundo… │
│  [metrics grid]              │
│                              │
│  ─── Semantic neighbors ─── │
│  [neighbor list, max 5]      │
└──────────────────────────────┘
```

**Article summary display:** use `article.summary` if available; fall back to `article.article_text_excerpt`; fall back to `selectedPoint.summary_snippet`. Don't show blank sections.

**"Open in Stories" link:** Only shown if `selectedPoint.analysis.cluster_id != null`. Navigates to `/?clusterId={cluster_id}`.

**Cluster context metrics grid:**
```
Outlier   │ Neighbor count
Src diversity │ Density dist.
```
Show all 4 metrics in a 2×2 grid. Use `--` for null values.

---

### 4.13 Filter drawer specification

*(Same pattern as Stories — already implemented in iter/004)*

**Fields (in order):**
1. Search: title or summary text
2. Source: select from `available_sources`
3. Section: select from `available_sections`
4. Cluster: select from `cluster_summaries` — label: `Cluster N · N articles`
5. Date from / Date to: side-by-side date inputs
6. Outlier only: checkbox
7. Point limit: select `[100, 250, 500]`

**On open:** show current active filters pre-populated.
**On change:** immediate — no submit button.
**Reset:** "Clear all" button calls `resetQuery()`.

---

### 4.14 Explorer states table

| State | Canvas | Context rail | Control bar |
|---|---|---|---|
| Loading (initial) | Semi-transparent overlay: "Loading semantic projection…" | "Loading…" minimal text | Point count: "Loading…" |
| Loading (filter change) | Canvas dims to 60% opacity; no overlay text | Unchanged | Point count: "Loading…" spinner dot |
| API error | Error overlay: "Failed to load projection" | Brief error hint | Point count hidden |
| Empty (0 points) | Centered empty state: "No articles match filters" + "Clear filters" action | Filter reset prompt | "0 points" |
| No selection (points loaded) | Points rendered | Guide + legend + dataset | Full controls, no "Focus selected" |
| Point selected (loading detail) | Points rendered, selected highlighted | Article title + source (from `selectedPoint`) + loading spinner for detail | "Focus selected" shown |
| Point selected (detail loaded) | Full point hierarchy rendered | Full detail: article + cluster + neighbors | "Focus selected" shown |
| Point selected (detail error) | Points rendered | Inline error in article section | "Focus selected" shown |

---

### 4.15 Responsive behavior

| Breakpoint | Canvas | Context rail | Control bar |
|---|---|---|---|
| ≥ 1280px | Side by side with context rail | 320px fixed right column | Single-row horizontal bar |
| 900–1279px | Full width, context rail below | Below canvas, max-height 50vh, scrollable | Single-row (may wrap) |
| < 900px | Full width, min-height 60vh | Below canvas, collapsible | May wrap to 2 rows |
| < 640px | Full width, 55vh | Bottom sheet on selection (via CSS only — no JS modal) | Wraps, font-size xs |

**Mobile consideration:**
- On `< 640px`, the context rail should act as a sliding bottom panel (CSS transform only, no JS modal framework)
- The filter drawer remains full-width overlay on mobile
- Touch pan/zoom work natively via DeckGL controller — no additional touch handling needed

---

## 5. App shell changes

*(unchanged from iter/004)*

---

## 6. Responsive behavior — Stories

*(unchanged from iter/004)*

---

## 7. States and microcopy

*(unchanged from iter/004)*

**Explorer additions to microcopy:**

**Loading (filter change):**
> `{N} points` (count shown immediately from prior data, refreshing)

**Seeded context chip:**
> "Filtered by: Cluster N" / "Filtered by: '{search term}'"

**Legend — How to read this space:**
> "Proximity = semantic similarity. Clusters group articles the model found coherent. Outliers (red) sit outside all clusters."

**No-selection guide:**
> "Click any point to inspect an article and its semantic neighborhood."

---

## 8. Backend/API requirements

*(unchanged from iter/004)*

All render reliability fixes are purely frontend. No new endpoints are required for this iteration.

---

## 9. Interaction model

*(unchanged from iter/004, with one addition)*

### 9.6 Seeded context from Stories

When the Explorer is opened from a "Open in Explorer" link in Stories, the URL contains `?clusterId=N&articleId=M` (or similar). The context rail should:

1. Show a visible context chip at the top of the no-selection state:
   `"Filtered by: Cluster N"` with a `[Clear ×]` button that calls `resetQuery()`
2. If `articleId` is present, auto-select that article on mount (existing `useExplorerBootstrap` behavior)
3. The chip disappears when the filter is cleared

This makes the Explorer → Stories ← Explorer navigation loop feel intentional, not accidental.

---

## 10. File/component migration plan

*(largely unchanged from iter/004)*

**Additional Explorer-specific changes in this pass:**

| File | Change |
|---|---|
| `MapPanel.tsx` | Fix BUGs 1-5 (height chain, layer ID, view naming, viewState); add dev diagnostic; update tooltip with cluster/outlier info; stabilize camera transitions |
| `styles.css` (explorer section) | Add `min-height: 0` to `.explorer-workspace`, `.app-main`; remove `!important` from `.map-canvas > div, canvas` |
| `ExplorerContextRail.tsx` | Add seeded context chip; add "How to read this space" onboarding block; improve legend with source swatches in source mode |
| `ExplorerControlBar.tsx` | Improve color mode label copy ("By source", "By cluster"); add tooltip hints on 2D/3D buttons |

---

## 11. What the builder must NOT do

*(unchanged from iter/004, plus)*

- Do NOT migrate to React Three Fiber for the main Explorer
- Do NOT introduce new npm packages to fix the rendering issues — they are CSS/DeckGL config problems
- Do NOT add a DeckGL resize observer library — fix the flex chain instead (the correct approach)
- Do NOT refactor `useExplorerData` while fixing the render bug — isolate changes to `MapPanel.tsx` and CSS first
- Do NOT skip the dev diagnostic step — confirm the bug before adding polish

---

*Spec complete. Next pass: `frontend.react` builder — implement the deck.gl Explorer stabilization and UX improvement plan.*
