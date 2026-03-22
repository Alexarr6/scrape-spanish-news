# DESIGN_TOKENS.md — iter/006 Visual System

**Role:** Frontend Architect (iter/006)
**Date:** 2026-03-20

---

## Scope of this revision

Sections 1–9 from iter/004 are **unchanged and remain valid**.

This revision adds **Section 12: Explorer-specific visual additions** covering:
- Explorer canvas background and depth cue tokens
- Point encoding state palette (consolidates MapPanel inline constants)
- Seeded context chip visual treatment

---

## 1–11: Base visual system

*(All content from iter/004 DESIGN_TOKENS.md remains unchanged)*

See iter/004 for:
- Design principles (Section 1)
- Color palette (Section 2)
- Typography (Section 3)
- Spacing scale (Section 4)
- Border and radius (Section 5)
- Elevation / shadow (Section 6)
- Surface hierarchy rules (Section 7)
- Interactive states (Section 8)
- Component visual rules (Section 9)
- Layout-level tokens (Section 10)
- CSS architecture notes (Section 11)

---

## 12. Explorer-specific visual additions

These tokens augment the base system for the Explorer canvas and its point encoding. They belong in the Explorer-specific CSS section or in a future `explorer.css` split.

---

### 12.1 Explorer canvas background

```css
/* Explorer canvas area */
.explorer-canvas-area {
  background: var(--color-bg);     /* same as page — no special canvas color */
}

/* No grid overlay, no axes in this iteration */
/* The semantic projection does not have a meaningful coordinate origin to label */
```

The canvas background should match the page background. Do not use a dark canvas background in light mode — it creates a jarring visual mode switch. If a dark canvas treatment is desired later, it should be a separate dark-canvas design token, not a CSS hack.

---

### 12.2 Explorer point encoding palette (authoritative source)

These values **replace** the inline constants in `MapPanel.tsx`. The builder should define them as named constants in a dedicated `explorerColors.ts` file and import from there.

**Selection states:**

```ts
// frontend/src/lib/explorerColors.ts

export const POINT_SELECTED_FILL: [number, number, number, number] = [14, 165, 233, 255]   // sky-500 full
export const POINT_SELECTED_STROKE: [number, number, number, number] = [255, 255, 255, 255]  // white
export const POINT_SELECTED_STROKE_WIDTH = 2.8
export const POINT_SELECTED_RADIUS_2D = 9
export const POINT_SELECTED_RADIUS_3D = 10

export const POINT_NEIGHBOR_FILL: [number, number, number, number] = [34, 197, 94, 235]    // green-500
export const POINT_NEIGHBOR_STROKE: [number, number, number, number] = [220, 252, 231, 240] // green-100
export const POINT_NEIGHBOR_STROKE_WIDTH = 1.5
export const POINT_NEIGHBOR_RADIUS_2D = 7
export const POINT_NEIGHBOR_RADIUS_3D = 7.5

export const POINT_HOVERED_FILL: [number, number, number, number] = [125, 211, 252, 235]   // sky-300
export const POINT_HOVERED_STROKE: [number, number, number, number] = [224, 242, 254, 235] // sky-100
export const POINT_HOVERED_STROKE_WIDTH = 0.8
export const POINT_HOVERED_RADIUS_2D = 6
export const POINT_HOVERED_RADIUS_3D = 6.5

// Regular and outlier points — base alpha
export const POINT_REGULAR_ALPHA_NO_SELECTION = 210
export const POINT_REGULAR_ALPHA_UNDER_SELECTION = 65
export const POINT_OUTLIER_ALPHA_NO_SELECTION = 230
export const POINT_OUTLIER_ALPHA_UNDER_SELECTION = 100

export const POINT_REGULAR_RADIUS_2D = 4
export const POINT_REGULAR_RADIUS_3D = 4.5
export const POINT_OUTLIER_RADIUS_2D = 5.5
export const POINT_OUTLIER_RADIUS_3D = 6

// Stroke for receding points — effectively invisible
export const POINT_RECEDING_STROKE: [number, number, number, number] = [226, 232, 240, 0]  // transparent
export const POINT_RECEDING_STROKE_WIDTH = 0

// Stroke for visible regular points (no selection)
export const POINT_DEFAULT_STROKE: [number, number, number, number] = [248, 250, 252, 190] // slate-50 semi
export const POINT_DEFAULT_STROKE_WIDTH = 0.6
```

**Source color palette:**

```ts
export const SOURCE_COLORS: Record<string, [number, number, number]> = {
  elpais:       [59, 130, 246],    // blue-500
  elmundo:      [16, 185, 129],    // emerald-500
  abc:          [249, 115, 22],    // orange-500
  eldiario:     [168, 85, 247],    // purple-500
  lavanguardia: [236, 72, 153],    // pink-500
  '20minutos':  [251, 191, 36],    // amber-400
}
export const SOURCE_FALLBACK_COLOR: [number, number, number] = [100, 116, 139]  // slate-500

// Source colors for CSS swatches in the legend (hex)
export const SOURCE_COLORS_HEX: Record<string, string> = {
  elpais:       '#3b82f6',
  elmundo:      '#10b981',
  abc:          '#f97316',
  eldiario:     '#a855f7',
  lavanguardia: '#ec4899',
  '20minutos':  '#fbbf24',
}
```

**Cluster color palette:**

```ts
export const CLUSTER_PALETTE: Array<[number, number, number]> = [
  [67, 56, 202],     // indigo-700
  [3, 105, 161],     // sky-700
  [4, 120, 87],      // emerald-700
  [180, 83, 9],      // amber-700
  [157, 23, 77],     // rose-800
  [109, 40, 217],    // violet-700
]

export const CLUSTER_OUTLIER_COLOR: [number, number, number] = [220, 38, 38]  // red-600
export const CLUSTER_NULL_COLOR: [number, number, number] = [148, 163, 184]   // slate-400
```

---

### 12.3 Seeded context chip visual treatment

A chip shown at the top of the context rail (no-selection state) when the Explorer was opened with pre-applied filters from Stories.

```css
/* Seeded context chip */
.context-seed-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-accent-light);
  border: 1px solid var(--color-accent-border);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--color-accent);
  font-weight: 500;
  margin-bottom: var(--space-3);
}

.context-seed-chip-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.context-seed-chip-clear {
  background: none;
  border: none;
  color: var(--color-accent);
  cursor: pointer;
  font-size: var(--text-xs);
  padding: 0;
  opacity: 0.7;
  transition: opacity 120ms ease;
}

.context-seed-chip-clear:hover {
  opacity: 1;
}
```

Usage: shown only when `query.clusterId !== ''` or `query.search.trim() !== ''` on mount (i.e., Explorer was launched with a pre-applied filter from Stories).

---

### 12.4 Explorer loading state visual treatment

The loading overlay during initial data fetch is distinct from the loading state during filter changes.

**Initial load:**
```css
.map-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(244, 246, 249, 0.72);
  z-index: 10;
  backdrop-filter: blur(1px);  /* optional — subtle */
}
```

**Filter change (refetch with existing data):**
Do not show the full overlay. Instead, dim the canvas slightly via a CSS class:
```css
.map-canvas.loading-update {
  opacity: 0.6;
  transition: opacity 180ms ease;
}
```

This preserves the map's spatial context while indicating that data is refreshing. The control bar point count shows "Loading…" during this state.

---

### 12.5 Dev diagnostic overlay

For dev builds only. Positioned as an absolute overlay in the top-left corner of the canvas, low z-index (below tooltip).

```css
/* Dev only — strip from production builds */
.map-debug-overlay {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
  z-index: 5;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  font-size: 11px;
  font-family: monospace;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  pointer-events: none;
  line-height: 1.6;
}
```

Content: `points: N | canvas: W×H px | zoom: Z.ZZ | bounds: [minX,maxX,minY,maxY]`

Visible only when `import.meta.env.DEV === true`.

---

## 13. iter/006 additions — axis colors and PointCloud sizes

These constants extend `explorerColors.ts`. Add them to the bottom of that file.

### 13.1 Axis layer colors

```ts
// Axis line and grid colors — used by buildAxisLayers() in MapPanel.tsx

// 2D mode: single subtle grey for both axes
export const AXIS_COLOR_2D: [number, number, number, number] = [148, 163, 184, 90]    // slate-400 @35%

// 3D mode: RGB convention for XYZ
export const AXIS_X_COLOR_3D: [number, number, number, number] = [220, 38, 38, 115]   // red-600 @45%
export const AXIS_Y_COLOR_3D: [number, number, number, number] = [34, 197, 94, 115]   // green-500 @45%
export const AXIS_Z_COLOR_3D: [number, number, number, number] = [59, 130, 246, 115]  // blue-500 @45%
export const AXIS_GRID_COLOR_3D: [number, number, number, number] = [148, 163, 184, 30] // slate-400 @12%, very faint
```

**Opacity rationale:**
- 2D axes: 35% — visible but clearly secondary to points
- 3D axes: 45% — slightly more prominent to help depth orientation
- 3D grid: 12% — barely there, just enough to read the XY plane

---

### 13.2 PointCloudLayer sizes

`PointCloudLayer.pointSize` is a single per-layer value (pixel diameter), not per-point.
Use one layer per tier, each with its own fixed `pointSize`:

```ts
// frontend/src/lib/explorerColors.ts — add these
// PointCloudLayer point diameters (pixels) — 3D mode only
export const PC_SIZE_REGULAR  = 8    // regular field points
export const PC_SIZE_OUTLIER  = 10   // outlier field points
export const PC_SIZE_NEIGHBOR = 14   // semantic neighbors (highlighted)
export const PC_SIZE_HOVERED  = 12   // hovered (unselected) point
export const PC_SIZE_SELECTED = 18   // selected article — always dominant
```

**Sizing rationale:**
- These are diameters; `POINT_*_RADIUS_3D` values from Section 12.2 were radii.
- `PC_SIZE = POINT_*_RADIUS_3D * 2` approximately, then rounded to even px.
- `PC_SIZE_REGULAR = 8` gives a readable point that won't crowd at typical zoom.

---

*Design tokens complete. See UI_SPEC.md for layout and component specs.*
