# COMPONENT_MAP.md — iter/006 Component Architecture

**Role:** Frontend Architect (iter/006)
**Date:** 2026-03-20

---

## Scope of this revision

This is an **incremental revision** of iter/004 COMPONENT_MAP.md.

**What changed:** Section 5 (Explorer route components) has been fully rewritten with:
- Precise render reliability fix targets in MapPanel
- Updated MapPanel prop contract
- New `ExplorerContextRail` details (seeded chip, onboarding guide, source swatches)
- New `explorerColors.ts` utility file
- Updated `ExplorerPage` composition reflecting the diagnosis

**What is unchanged from iter/004:** Sections 1–4 (App entry, Layout, Stories route, Stories page) and Sections 6–10 (shared utilities, preserved components, deletions, build notes).

---

## 1. App entry and routing

*(unchanged from iter/004)*

---

## 2. Layout components

*(unchanged from iter/004)*

---

## 3. Stories route components

*(unchanged from iter/004)*

---

## 4. Stories route page

*(unchanged from iter/004)*

---

## 5. Explorer route components (`components/explorer/`)

### New utility file: `lib/explorerColors.ts`

**Role:** Single source of truth for all Explorer point encoding constants. Removes inline magic constants from `MapPanel.tsx`.

**Content:**
```ts
// All point color/radius/alpha constants for the Explorer canvas
// These replace all inline color arrays in MapPanel.tsx
// See DESIGN_TOKENS.md Section 12.2 for the complete listing

export const POINT_SELECTED_FILL: [number, number, number, number]
export const POINT_SELECTED_STROKE: [number, number, number, number]
export const POINT_SELECTED_STROKE_WIDTH: number
export const POINT_SELECTED_RADIUS_2D: number
export const POINT_SELECTED_RADIUS_3D: number

export const POINT_NEIGHBOR_FILL: [number, number, number, number]
export const POINT_NEIGHBOR_STROKE: [number, number, number, number]
export const POINT_NEIGHBOR_STROKE_WIDTH: number
export const POINT_NEIGHBOR_RADIUS_2D: number
export const POINT_NEIGHBOR_RADIUS_3D: number

export const POINT_HOVERED_FILL: [number, number, number, number]
export const POINT_HOVERED_STROKE: [number, number, number, number]
export const POINT_HOVERED_STROKE_WIDTH: number
export const POINT_HOVERED_RADIUS_2D: number
export const POINT_HOVERED_RADIUS_3D: number

export const POINT_REGULAR_ALPHA_NO_SELECTION: number
export const POINT_REGULAR_ALPHA_UNDER_SELECTION: number
export const POINT_OUTLIER_ALPHA_NO_SELECTION: number
export const POINT_OUTLIER_ALPHA_UNDER_SELECTION: number
export const POINT_REGULAR_RADIUS_2D: number
export const POINT_REGULAR_RADIUS_3D: number
export const POINT_OUTLIER_RADIUS_2D: number
export const POINT_OUTLIER_RADIUS_3D: number

export const POINT_RECEDING_STROKE: [number, number, number, number]
export const POINT_RECEDING_STROKE_WIDTH: number
export const POINT_DEFAULT_STROKE: [number, number, number, number]
export const POINT_DEFAULT_STROKE_WIDTH: number

export const SOURCE_COLORS: Record<string, [number, number, number]>
export const SOURCE_COLORS_HEX: Record<string, string>
export const SOURCE_FALLBACK_COLOR: [number, number, number]

export const CLUSTER_PALETTE: Array<[number, number, number]>
export const CLUSTER_OUTLIER_COLOR: [number, number, number]
export const CLUSTER_NULL_COLOR: [number, number, number]
```

**Location:** `frontend/src/lib/explorerColors.ts`

---

### `MapPanel.tsx` (precision refactor)

**Role:** DeckGL canvas only. No controls. Exposes imperative camera handle.

**Props (unchanged contract from iter/004):**
```tsx
type Props = {
  points: ExplorerPointsResponse | null
  loading: boolean
  error: string | null
  selectedArticleId: number | null
  hoveredArticleId: number | null
  neighborIds: Set<number>
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  onHoverArticle: (articleId: number | null) => void
  onSelectArticle: (articleId: number | null) => void
}

export type MapPanelHandle = {
  fitAll: () => void
  focusSelected: () => void
}
```

**Implementation changes — render reliability fixes:**

**Fix BUG-1 (Container height):**
- `MapPanel` itself does not set its own height — it renders `<div className="map-frame">` → `<div className="map-canvas">` → `<DeckGL ...>`
- The fix is in CSS: add `min-height: 0` to `.explorer-workspace`, confirm the flex chain has no interruption
- Add a `useEffect` dev-diagnostic to confirm canvas `clientHeight > 0`

**Fix BUG-4 (Named view + viewState mismatch):**
```tsx
// BEFORE (broken):
views={[new OrthographicView({ id: 'semantic-2d' })]}
viewState={activeViewState as never}  // not keyed to 'semantic-2d'

// AFTER (fixed — Option A: remove ids from views):
views={[viewMode === '3d' ? new OrbitView() : new OrthographicView()]}
viewState={activeViewState}

// OR Option B: key the viewState (keep named views):
views={[viewMode === '3d'
  ? new OrbitView({ id: 'semantic-3d' })
  : new OrthographicView({ id: 'semantic-2d' })
]}
viewState={viewMode === '3d'
  ? { 'semantic-3d': viewState['semantic-3d'] }
  : { 'semantic-2d': viewState['semantic-2d'] }
}
```

**Recommendation:** Use Option A (remove view IDs) — simpler, less surface area for bugs. `onViewStateChange` handler must be updated to use the string key from `viewId` if ids are kept; with unnamed views it just returns the state directly.

```tsx
// With unnamed views:
onViewStateChange={({ viewState: nextViewState }) => {
  setViewState((current) => ({
    ...current,
    [viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']: nextViewState,
  }))
}}
```

**Fix BUG-5 (Stable layer ID):**
```tsx
// BEFORE:
id: `semantic-points-${viewMode}-${colorMode}`  // changes on every mode toggle

// AFTER:
id: 'semantic-points'  // stable — let updateTriggers handle all changes
```

**Fix BUG-2 (StrictMode isolation):**
```tsx
// Wrap DeckGL in a stable key — prevents identity loss on StrictMode double-mount
<DeckGL
  key="explorer-deck"  // ADD THIS
  views={...}
  ...
/>
```

**Fix BUG-6 (Remove CSS !important overrides):**
- Remove from `styles.css`: `.map-canvas > div, .map-canvas canvas { width: 100% !important; height: 100% !important; }`
- DeckGL should control its own canvas size; parent flex layout should give it the dimensions

**Updated ScatterplotLayer encoding:**

Import from `explorerColors.ts` instead of inline constants.

```tsx
import {
  POINT_SELECTED_FILL, POINT_SELECTED_STROKE, POINT_SELECTED_STROKE_WIDTH,
  POINT_SELECTED_RADIUS_2D, POINT_SELECTED_RADIUS_3D,
  POINT_NEIGHBOR_FILL, POINT_NEIGHBOR_STROKE, POINT_NEIGHBOR_STROKE_WIDTH,
  POINT_NEIGHBOR_RADIUS_2D, POINT_NEIGHBOR_RADIUS_3D,
  POINT_HOVERED_FILL, POINT_HOVERED_STROKE, POINT_HOVERED_STROKE_WIDTH,
  POINT_HOVERED_RADIUS_2D, POINT_HOVERED_RADIUS_3D,
  POINT_REGULAR_ALPHA_NO_SELECTION, POINT_REGULAR_ALPHA_UNDER_SELECTION,
  POINT_OUTLIER_ALPHA_NO_SELECTION, POINT_OUTLIER_ALPHA_UNDER_SELECTION,
  POINT_REGULAR_RADIUS_2D, POINT_REGULAR_RADIUS_3D,
  POINT_OUTLIER_RADIUS_2D, POINT_OUTLIER_RADIUS_3D,
  POINT_RECEDING_STROKE, POINT_RECEDING_STROKE_WIDTH,
  POINT_DEFAULT_STROKE, POINT_DEFAULT_STROKE_WIDTH,
} from '../../lib/explorerColors'
```

**Updated getRadius:**
```tsx
getRadius: (point) => {
  const is3d = viewMode === '3d'
  if (point.article_id === selectedArticleId)
    return is3d ? POINT_SELECTED_RADIUS_3D : POINT_SELECTED_RADIUS_2D
  if (neighborIds.has(point.article_id))
    return is3d ? POINT_NEIGHBOR_RADIUS_3D : POINT_NEIGHBOR_RADIUS_2D
  if (point.article_id === hoveredArticleId)
    return is3d ? POINT_HOVERED_RADIUS_3D : POINT_HOVERED_RADIUS_2D
  if (point.analysis.is_outlier)
    return is3d ? POINT_OUTLIER_RADIUS_3D : POINT_OUTLIER_RADIUS_2D
  return is3d ? POINT_REGULAR_RADIUS_3D : POINT_REGULAR_RADIUS_2D
}
```

**Updated getFillColor:**
```tsx
getFillColor: (point) => {
  if (point.article_id === selectedArticleId) return POINT_SELECTED_FILL
  if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_FILL
  if (point.article_id === hoveredArticleId) return POINT_HOVERED_FILL
  const base = colorForPoint(point, colorMode)
  const alpha = hasSelection
    ? (point.analysis.is_outlier
        ? POINT_OUTLIER_ALPHA_UNDER_SELECTION
        : POINT_REGULAR_ALPHA_UNDER_SELECTION)
    : (point.analysis.is_outlier
        ? POINT_OUTLIER_ALPHA_NO_SELECTION
        : POINT_REGULAR_ALPHA_NO_SELECTION)
  return [...base, alpha] as [number, number, number, number]
}
```

**Updated getLineColor:**
```tsx
getLineColor: (point) => {
  if (point.article_id === selectedArticleId) return POINT_SELECTED_STROKE
  if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_STROKE
  if (point.article_id === hoveredArticleId) return POINT_HOVERED_STROKE
  if (hasSelection) return POINT_RECEDING_STROKE
  return POINT_DEFAULT_STROKE
}
```

**Updated getLineWidth:**
```tsx
getLineWidth: (point) => {
  if (point.article_id === selectedArticleId) return POINT_SELECTED_STROKE_WIDTH
  if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_STROKE_WIDTH
  if (point.article_id === hoveredArticleId) return POINT_HOVERED_STROKE_WIDTH
  if (hasSelection) return POINT_RECEDING_STROKE_WIDTH
  return POINT_DEFAULT_STROKE_WIDTH
}
```

**Updated tooltip (add cluster + outlier info):**
```tsx
function Tooltip({ tooltip }: { tooltip: NonNullable<TooltipState> }) {
  const point = tooltip.point
  return (
    <div className="tooltip-card" style={{ left: tooltip.x + 14, top: tooltip.y + 14 }}>
      <div className="tooltip-eyebrow">
        {point.source}
        {point.section ? ` · ${point.section}` : ''}
        {point.analysis.is_outlier && (
          <span className="tooltip-outlier-badge">Outlier</span>
        )}
      </div>
      <strong>{point.title}</strong>
      <div className="tooltip-meta">{formatDate(point.published_at)}</div>
      <div className="tooltip-meta">
        {point.analysis.cluster_id != null
          ? `Cluster ${point.analysis.cluster_id}`
          : 'No cluster'}
      </div>
      {point.summary_snippet && <p>{point.summary_snippet}</p>}
    </div>
  )
}
```

**Dev diagnostic hook (add to MapPanel, dev only):**
```tsx
useEffect(() => {
  if (!import.meta.env.DEV) return
  const el = document.querySelector('.map-canvas') as HTMLElement | null
  console.debug(
    '[MapPanel] mount diagnostic:',
    '\n  canvas clientHeight:', el?.clientHeight ?? 'NOT FOUND',
    '\n  canvas clientWidth:', el?.clientWidth ?? 'NOT FOUND',
    '\n  points count:', points?.items.length ?? 0,
    '\n  viewState:', activeViewState,
    '\n  bounds:', points?.meta.bounds,
  )
}, [])  // run only on mount
```

**Camera behavior:**
- `fitAll()`: recompute from `points?.meta.bounds` — same as current
- `focusSelected()`: same logic as current, preserve 3D angles
- Add: do not call `fitAll` or `focusSelected` inside the `useEffect` that fires on bounds change — that auto-reset is a UX anti-pattern. The `useEffect` that calls `buildInitialViewState` on bounds change should ONLY fire on the first time data loads (when previous bounds were null), not on every filter refinement.

**Camera view-state fix — suppress eager resets:**
```tsx
// BEFORE: fires on every bounds change, resetting user camera
useEffect(() => {
  setViewState((current) => buildInitialViewState(points, current))
}, [bounds?.min_x, bounds?.max_x, /* ... */ points?.items.length])

// AFTER: only reset if the data went from null → populated (i.e., first load or full reset)
const [dataLoaded, setDataLoaded] = useState(false)
useEffect(() => {
  if (!points?.items.length) {
    setDataLoaded(false)
    return
  }
  if (!dataLoaded) {
    // First load or after a reset — fit all
    setViewState((current) => buildInitialViewState(points, current))
    setDataLoaded(true)
  }
  // Subsequent filter changes: do NOT reset camera
}, [points?.items.length, points?.meta.projection_set])
```

This preserves camera position when the user refines filters. Only explicit "Fit all" or a complete data reset reframes the view.

---

### `ExplorerControlBar.tsx` (minor update)

**Role:** Compact horizontal control bar — same as iter/004.

**Changes in this pass:**
1. Color mode labels: `'By source'` instead of `'source'`, `'By cluster'` instead of `'cluster'`
2. Add `title` attribute to 2D/3D buttons:
   ```tsx
   <button ... title="2D: flat layout for broad comparison">2D</button>
   <button ... title="3D: depth view for cluster overlap inspection">3D</button>
   ```
3. Loading indicator in point count:
   ```tsx
   <span className="explorer-point-count">
     {loading
       ? (pointCount === 0 ? 'Loading…' : `${pointCount} points (updating)`)
       : `${pointCount} points`}
   </span>
   ```

**Props:** unchanged from iter/004.

---

### `ExplorerContextRail.tsx` (updated)

**Role:** Right context rail for Explorer. Sections with dividers. No tabs.

**Props (unchanged from iter/004):**
```tsx
type ExplorerContextRailProps = {
  selectedPoint: ExplorerPoint | null
  detail: ExplorerArticleDetail | null
  loading: boolean
  error: string | null
  clusterSummaries: ExplorerClusterSummary[]
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  onClearSelection: () => void
  onSelectArticle: (articleId: number) => void
}
```

**New prop to add:**
```tsx
type ExplorerContextRailProps = {
  // ... existing ...
  seedContext: { type: 'cluster'; clusterId: number } | { type: 'search'; query: string } | null
  onClearSeed: () => void
}
```

`seedContext` is derived in `ExplorerPage` from `query`:
```tsx
const seedContext = useMemo(() => {
  if (query.clusterId) return { type: 'cluster' as const, clusterId: Number(query.clusterId) }
  if (query.search.trim()) return { type: 'search' as const, query: query.search.trim() }
  return null
}, [query.clusterId, query.search])
```

`onClearSeed` calls `resetQuery()` from `useExplorerUrlState`.

**No-selection state (updated):**
```tsx
<div className="context-rail">
  {/* Seeded context chip — only when filter active from Stories */}
  {seedContext && (
    <div className="context-seed-chip">
      <span className="context-seed-chip-label">
        {seedContext.type === 'cluster'
          ? `📍 Cluster ${seedContext.clusterId}`
          : `🔍 "${seedContext.query}"`}
      </span>
      <button className="context-seed-chip-clear" onClick={onClearSeed}>
        Clear ×
      </button>
    </div>
  )}

  {/* Guide text */}
  <p className="context-guide-text">
    Click any point to inspect an article and its semantic neighborhood.
  </p>

  {/* How to read this space — onboarding */}
  <div className="context-guide-explainer">
    <p className="context-guide-explainer-text">
      Proximity = semantic similarity. Clusters group articles the model found coherent.
      Outliers (red) sit outside all clusters.
    </p>
  </div>

  <SectionDivider label="Legend" />
  <ColorLegend colorMode={colorMode} clusterSummaries={clusterSummaries} />

  <SectionDivider label="Dataset" />
  <DatasetSummary clusterSummaries={clusterSummaries} viewMode={viewMode} />
</div>
```

**Updated `ColorLegend` component:**
```tsx
function ColorLegend({
  colorMode,
  clusterSummaries,
}: {
  colorMode: ExplorerColorMode
  clusterSummaries: ExplorerClusterSummary[]
}) {
  return (
    <ul className="legend-list">
      <li className="legend-item">
        <span className="legend-dot" style={{ background: '#0ea5e9' }} />
        <span>Selected article</span>
      </li>
      <li className="legend-item">
        <span className="legend-dot" style={{ background: '#22c55e' }} />
        <span>Semantic neighbors</span>
      </li>
      <li className="legend-item">
        <span className="legend-dot" style={{ background: '#dc2626' }} />
        <span>Outliers</span>
      </li>

      {/* Mode-specific legend entries */}
      {colorMode === 'neutral' && (
        <li className="legend-item">
          <span className="legend-dot" style={{ background: '#4338ca' }} />
          <span>Articles (neutral field)</span>
        </li>
      )}

      {colorMode === 'source' && (
        <>
          <li className="legend-item legend-item-header">Color by source</li>
          {Object.entries(SOURCE_COLORS_HEX).map(([source, color]) => (
            <li key={source} className="legend-item legend-item-indent">
              <span className="legend-dot" style={{ background: color }} />
              <span>{source}</span>
            </li>
          ))}
        </>
      )}

      {colorMode === 'cluster' && (
        <>
          <li className="legend-item legend-item-header">Color by cluster</li>
          {clusterSummaries.slice(0, 6).map((cluster, idx) => {
            const [r, g, b] = CLUSTER_PALETTE[idx % CLUSTER_PALETTE.length]
            return (
              <li key={cluster.cluster_id} className="legend-item legend-item-indent">
                <span className="legend-dot" style={{ background: `rgb(${r},${g},${b})` }} />
                <span>Cluster {cluster.cluster_id} · {cluster.size}</span>
              </li>
            )
          })}
        </>
      )}
    </ul>
  )
}
```

**Selection state (unchanged from iter/004 core, minor additions):**
- Add outlier badge next to article eyebrow if `selectedPoint.analysis.is_outlier`
- Show article source at top of cluster context: "Cluster N · N articles" + top sources as badges

**"Open in Stories" link:**
```tsx
// In ExplorerContextRail — remains from iter/004
// Only shown if cluster_id is non-null
const storiesHref = buildStoriesHref(detail?.semantic_summary.cluster_id ?? selectedPoint?.analysis.cluster_id ?? null)
```

**Additional CSS additions for rail:**
```css
.context-guide-explainer {
  margin-top: var(--space-2);
  padding: var(--space-3);
  background: var(--color-surface-muted);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.context-guide-explainer-text {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

.legend-item-header {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: var(--space-2);
  list-style: none;
}

.legend-item-indent {
  padding-left: var(--space-3);
}
```

---

### `ExplorerPage.tsx` (updated)

**Changes from iter/004:**
1. Derive `seedContext` from `query`
2. Pass `seedContext` and `onClearSeed` to `ExplorerContextRail`
3. Pass `hasSelection={selectedArticleId !== null}` to `ExplorerControlBar` (already done)

```tsx
export function ExplorerPage() {
  const [viewMode, setViewMode] = useState<ExplorerViewMode>('2d')  // 2D default
  const [colorMode, setColorMode] = useState<ExplorerColorMode>('neutral')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const mapRef = useRef<MapPanelHandle>(null)

  const {
    query,
    selectedArticleId,
    activeFilterCount,
    updateQuery,
    resetQuery,
    setSelectedArticleId,
  } = useExplorerUrlState()

  const {
    pointsState,
    filtersState,
    detailState,
    selectedPoint,
    hoveredArticleId,
    neighborIds,
    clearSelectedArticle,
    setHoveredArticleId,
  } = useExplorerData(query, selectedArticleId, setSelectedArticleId)

  // Seeded context: visible chip when Explorer was opened from Stories with a filter
  const seedContext = useMemo(() => {
    if (query.clusterId) return { type: 'cluster' as const, clusterId: Number(query.clusterId) }
    if (query.search.trim()) return { type: 'search' as const, query: query.search.trim() }
    return null
  }, [query.clusterId, query.search])

  return (
    <div className="explorer-layout">
      <ExplorerControlBar
        viewMode={viewMode}
        colorMode={colorMode}
        pointCount={pointsState.data?.meta.returned ?? 0}
        activeFilterCount={activeFilterCount}
        loading={pointsState.loading}
        hasSelection={selectedArticleId !== null}
        onViewModeChange={setViewMode}
        onColorModeChange={setColorMode}
        onFitAll={() => mapRef.current?.fitAll()}
        onFocusSelected={() => mapRef.current?.focusSelected()}
        onOpenFilters={() => setFiltersOpen(true)}
      />

      <div className="explorer-workspace">
        <div className="explorer-canvas-area">
          <MapPanel
            ref={mapRef}
            points={pointsState.data}
            loading={pointsState.loading}
            error={pointsState.error}
            selectedArticleId={selectedArticleId}
            hoveredArticleId={hoveredArticleId}
            neighborIds={neighborIds}
            viewMode={viewMode}
            colorMode={colorMode}
            onHoverArticle={setHoveredArticleId}
            onSelectArticle={setSelectedArticleId}
          />
        </div>

        <ExplorerContextRail
          selectedPoint={selectedPoint}
          detail={detailState.data}
          loading={detailState.loading}
          error={detailState.error}
          clusterSummaries={
            pointsState.data?.meta.cluster_summaries ??
            filtersState.data?.cluster_summaries ??
            []
          }
          viewMode={viewMode}
          colorMode={colorMode}
          onClearSelection={clearSelectedArticle}
          onSelectArticle={setSelectedArticleId}
          seedContext={seedContext}
          onClearSeed={resetQuery}
        />
      </div>

      <FilterDrawer
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        title="Refine Explorer"
        activeCount={activeFilterCount}
        onReset={resetQuery}
      >
        <ExplorerFilterFields
          filters={filtersState.data}
          query={query}
          onQueryChange={updateQuery}
          disabled={pointsState.loading && !pointsState.data}
        />
      </FilterDrawer>
    </div>
  )
}
```

---

## 5.A iter/006 — MapPanel changes for framing, axes, and 3D points

All changes are in `frontend/src/components/explorer/MapPanel.tsx` and `frontend/src/lib/explorerColors.ts`.
No other files change in this pass.

---

### 5.A.1 Zoom formula — replace `build2dViewState` and `build3dViewState`

**Signature change:** both functions now take `canvasPx: number` as a second parameter.

```ts
// PADDING_FACTOR: percentage of canvas the data span should occupy (inverted)
// 1.25 means the span occupies 100/1.25 = 80% of the canvas (10% margin each side)
const PADDING_2D = 1.25
const PADDING_3D = 1.4   // slightly more padding in 3D for depth comfort

function build2dViewState(bounds: PointBounds | null, canvasPx: number): ViewState2D {
  if (!bounds) return { target: [0, 0, 0], zoom: 8.5 }  // sensible default for [-1,1]
  const spanX = bounds.maxX - bounds.minX
  const spanY = bounds.maxY - bounds.minY
  const dominantSpan = Math.max(spanX, spanY)
  const paddedSpan = Math.max(dominantSpan * PADDING_2D, 0.01)  // guard against 0
  const zoom = Math.max(1.0, Math.min(14.0, Math.log2(canvasPx / paddedSpan)))
  return {
    target: [(bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2, 0],
    zoom,
  }
}

function build3dViewState(bounds: PointBounds | null, canvasPx: number, current?: ViewState3D): ViewState3D {
  if (!bounds) return {
    target: [0, 0, 0],
    zoom: 8.5,
    rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT,
    rotationX: current?.rotationX ?? DEFAULT_3D_TILT,
  }
  const spanX = bounds.maxX - bounds.minX
  const spanY = bounds.maxY - bounds.minY
  const spanZ = bounds.maxZ - bounds.minZ
  const dominantSpan = Math.max(spanX, spanY, spanZ)
  const paddedSpan = Math.max(dominantSpan * PADDING_3D, 0.01)
  const zoom = Math.max(1.0, Math.min(14.0, Math.log2(canvasPx / paddedSpan)))
  return {
    target: [
      (bounds.minX + bounds.maxX) / 2,
      (bounds.minY + bounds.maxY) / 2,
      (bounds.minZ + bounds.maxZ) / 2,
    ],
    zoom,
    rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT,
    rotationX: current?.rotationX ?? DEFAULT_3D_TILT,
  }
}
```

**Reading `canvasPx` at call-site:**
```ts
// Helper — call wherever build2d/3dViewState is invoked
function getCanvasPx(canvasRef: React.RefObject<HTMLDivElement>): number {
  const el = canvasRef.current
  if (!el) return 900  // safe fallback
  return Math.min(el.clientWidth, el.clientHeight)
}
```

Update `buildInitialViewState`, `fitAll()`, and `focusSelected()` to pass `getCanvasPx(canvasRef)`.
The initial `useState` call happens before the ref is populated, so the fallback `900` will apply there —
that's acceptable; the `useEffect` on first data load will re-fit with real dimensions.

---

### 5.A.2 Axis layer builder — add `buildAxisLayers` to MapPanel

Add the following function inside `MapPanel.tsx` (not exported, module-level):

```ts
import { LineLayer } from '@deck.gl/layers'
import {
  AXIS_COLOR_2D,
  AXIS_X_COLOR_3D, AXIS_Y_COLOR_3D, AXIS_Z_COLOR_3D, AXIS_GRID_COLOR_3D,
} from '../../lib/explorerColors'

function buildAxisLayers(viewMode: ExplorerViewMode, bounds: PointBounds | null) {
  const extent = bounds
    ? Math.max(1.5, Math.max(
        Math.abs(bounds.minX), Math.abs(bounds.maxX),
        Math.abs(bounds.minY), Math.abs(bounds.maxY),
      ) * 1.1)
    : 1.5

  if (viewMode === '2d') {
    return [
      new LineLayer({
        id: 'axis-2d',
        data: [
          { from: [-extent, 0, 0], to: [extent, 0, 0] },
          { from: [0, -extent, 0], to: [0, extent, 0] },
        ] as { from: [number,number,number]; to: [number,number,number] }[],
        getSourcePosition: (d) => d.from,
        getTargetPosition: (d) => d.to,
        getColor: AXIS_COLOR_2D,
        getWidth: 1.0,
        widthUnits: 'pixels',
        pickable: false,
      }),
    ]
  }

  // 3D axes + XY grid
  const gridExtent = Math.ceil(extent)
  const gridLines: { from: [number,number,number]; to: [number,number,number]; color: [number,number,number,number] }[] = []
  for (let i = -gridExtent; i <= gridExtent; i++) {
    gridLines.push(
      { from: [-extent, i, 0], to: [extent, i, 0], color: AXIS_GRID_COLOR_3D },
      { from: [i, -extent, 0], to: [i, extent, 0], color: AXIS_GRID_COLOR_3D },
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
      data: [
        { from: [-extent, 0, 0], to: [extent, 0, 0], color: AXIS_X_COLOR_3D },
        { from: [0, -extent, 0], to: [0, extent, 0], color: AXIS_Y_COLOR_3D },
        { from: [0, 0, -extent], to: [0, 0, extent], color: AXIS_Z_COLOR_3D },
      ] as { from: [number,number,number]; to: [number,number,number]; color: [number,number,number,number] }[],
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

**Wire up in the `layers` useMemo:**
```ts
const bounds = normalizeBounds(points?.meta.bounds ?? null)  // derive this in the memo too

const layers = useMemo(() => {
  const items = points?.items ?? []
  const bounds = normalizeBounds(points?.meta.bounds ?? null)
  const axisLayers = buildAxisLayers(viewMode, bounds)

  if (viewMode === '3d') {
    // ... PointCloudLayer tiers (see 5.A.3) ...
    return [...axisLayers, ...pcLayers]
  }

  // 2D: existing ScatterplotLayer
  return [
    ...axisLayers,
    new ScatterplotLayer<ExplorerPoint>({ /* unchanged */ }),
  ]
}, [/* same deps + viewMode in axis trigger */])
```

**updateTriggers for axis layers:** not needed — axis layers have no dynamic data. They re-create naturally on `viewMode` change because `buildAxisLayers` is called in the same `useMemo`.

---

### 5.A.3 3D PointCloudLayer tiers — replace OrbitView ScatterplotLayer

**Import:**
```ts
import { PointCloudLayer } from '@deck.gl/layers'
import {
  PC_SIZE_REGULAR, PC_SIZE_OUTLIER, PC_SIZE_NEIGHBOR, PC_SIZE_HOVERED, PC_SIZE_SELECTED,
} from '../../lib/explorerColors'
```

**Inside the `layers` useMemo, 3D branch:**

```ts
if (viewMode === '3d') {
  const isHighlighted = (p: ExplorerPoint) =>
    p.article_id === selectedArticleId ||
    neighborIds.has(p.article_id) ||
    p.article_id === hoveredArticleId

  const getPC3dColor = (p: ExplorerPoint): [number,number,number,number] => {
    if (p.article_id === selectedArticleId) return POINT_SELECTED_FILL
    if (neighborIds.has(p.article_id)) return POINT_NEIGHBOR_FILL
    if (p.article_id === hoveredArticleId) return POINT_HOVERED_FILL
    const [r, g, b] = colorForPoint(p, colorMode)
    const alpha = hasSelection
      ? (p.analysis.is_outlier ? POINT_OUTLIER_ALPHA_UNDER_SELECTION : POINT_REGULAR_ALPHA_UNDER_SELECTION)
      : (p.analysis.is_outlier ? POINT_OUTLIER_ALPHA_NO_SELECTION : POINT_REGULAR_ALPHA_NO_SELECTION)
    return [r, g, b, alpha]
  }

  const colorTrigger = [colorMode, selectedArticleId, hoveredArticleId, neighborKey, hasSelection]

  const pcLayer = (id: string, data: ExplorerPoint[], size: number) =>
    new PointCloudLayer<ExplorerPoint>({
      id,
      data,
      pickable: true,
      sizeUnits: 'pixels',
      pointSize: size,
      getPosition: (p) => [p.x, p.y, p.z],
      getColor: getPC3dColor,
      getNormal: [0, 0, 1],
      material: false,
      onHover: (info: PickingInfoLike) => {
        const point = info.object
        onHoverArticle(point?.article_id ?? null)
        if (point && info.x != null && info.y != null) {
          setTooltip({ x: info.x, y: info.y, point })
        } else {
          setTooltip(null)
        }
      },
      onClick: (info: PickingInfoLike) => onSelectArticle(info.object?.article_id ?? null),
      updateTriggers: {
        getColor: colorTrigger,
      },
    })

  const regular  = items.filter(p => !isHighlighted(p) && !p.analysis.is_outlier)
  const outlier  = items.filter(p => !isHighlighted(p) && p.analysis.is_outlier)
  const neighbor = items.filter(p => neighborIds.has(p.article_id))
  const hovered  = hoveredArticleId != null ? items.filter(p => p.article_id === hoveredArticleId) : []
  const selected = selectedArticleId != null ? items.filter(p => p.article_id === selectedArticleId) : []

  const pcLayers = [
    pcLayer('pc-regular',  regular,  PC_SIZE_REGULAR),
    pcLayer('pc-outlier',  outlier,  PC_SIZE_OUTLIER),
    pcLayer('pc-neighbor', neighbor, PC_SIZE_NEIGHBOR),
    pcLayer('pc-hovered',  hovered,  PC_SIZE_HOVERED),
    pcLayer('pc-selected', selected, PC_SIZE_SELECTED),
  ]

  return [...axisLayers, ...pcLayers]
}
```

**Picking note:** Each `PointCloudLayer` tier has `pickable: true` with the same `onHover`/`onClick` handlers. This is correct — DeckGL picks from the topmost rendered layer at the cursor position, so the selected/neighbor tiers correctly win picking over regular tiers.

**No tooltip changes needed** — `setTooltip` / `Tooltip` component is unchanged.

---

### 5.A.4 `explorerColors.ts` additions

Append to the bottom of `frontend/src/lib/explorerColors.ts`:

```ts
// ─── Axis and grid colors (iter/006) ────────────────────────────────────────
export const AXIS_COLOR_2D: [number, number, number, number] = [148, 163, 184, 90]
export const AXIS_X_COLOR_3D: [number, number, number, number] = [220, 38, 38, 115]
export const AXIS_Y_COLOR_3D: [number, number, number, number] = [34, 197, 94, 115]
export const AXIS_Z_COLOR_3D: [number, number, number, number] = [59, 130, 246, 115]
export const AXIS_GRID_COLOR_3D: [number, number, number, number] = [148, 163, 184, 30]

// ─── PointCloudLayer sizes (iter/006) — 3D mode only ────────────────────────
export const PC_SIZE_REGULAR  = 8
export const PC_SIZE_OUTLIER  = 10
export const PC_SIZE_NEIGHBOR = 14
export const PC_SIZE_HOVERED  = 12
export const PC_SIZE_SELECTED = 18
```

---

### 5.A.5 Files changed in iter/006

| File | Change |
|---|---|
| `frontend/src/lib/explorerColors.ts` | Append axis + PC size constants |
| `frontend/src/components/explorer/MapPanel.tsx` | New zoom formula, `buildAxisLayers`, 3D `PointCloudLayer` tiers |
| `UI_SPEC.md` | Section 4.A added (this pass spec) |
| `DESIGN_TOKENS.md` | Section 13 added (axis colors, PC sizes) |
| `COMPONENT_MAP.md` | Section 5.A added (this section) |
| `STATUS.md` | Updated |
| `RESULTS.md` | Updated |

No other files change.

---

## 6. Shared utility components

*(unchanged from iter/004)*

---

## 7. Preserved components

*(unchanged from iter/004)*

**Additional verification for this pass:**

`useExplorerData.ts` — The `useEffect` that watches `[query, selectedArticleId]` and calls `setSelectedArticleId(null)` when the selected article is not in the new result set may cause a brief flash. Consider:
- Debouncing the query change by 200ms before firing the API call
- Or: only clear selectedArticleId after the API response arrives, not during loading

This is a minor UX issue, not a render bug. Address in a cleanup commit after the render is confirmed working.

---

## 8. Components to delete

*(unchanged from iter/004)*

---

## 9. CSS changes summary for this pass

**File: `frontend/src/styles.css` — Explorer section**

Changes needed:

```css
/* ADD: min-height: 0 to workspace grid to fix flex height chain (BUG-1) */
.explorer-workspace {
  min-height: 0;   /* ADD */
  /* rest unchanged */
}

/* ADD: explicit height to app-main to support flex chain */
.app-main {
  min-height: 0;   /* ADD */
}

/* REMOVE: !important override that conflicts with DeckGL canvas sizing (BUG-6) */
/* DELETE these lines: */
/* .map-canvas > div, */
/* .map-canvas canvas { */
/*   width: 100% !important; */
/*   height: 100% !important; */
/* } */

/* ADD: explicit height on map-canvas */
.map-canvas {
  flex: 1;
  position: relative;
  min-height: 0;
  height: 100%;   /* ADD: explicit height for DeckGL reference */
}

/* ADD: loading-update dimming class */
.map-canvas.loading-update {
  opacity: 0.6;
  transition: opacity 180ms ease;
}

/* ADD: tooltip eyebrow and outlier badge */
.tooltip-eyebrow {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.65);
}

.tooltip-outlier-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 5px;
  background: rgba(220, 38, 38, 0.25);
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
  color: #fca5a5;
}

/* ADD: seed chip styles */
.context-seed-chip {
  /* see DESIGN_TOKENS.md Section 12.3 */
}

/* ADD: guide explainer styles */
.context-guide-explainer {
  /* see DESIGN_TOKENS.md Section 12.3 */
}

/* ADD: legend header/indent styles */
.legend-item-header { /* ... */ }
.legend-item-indent { /* ... */ }

/* ADD: dev diagnostic overlay */
.map-debug-overlay {
  /* see DESIGN_TOKENS.md Section 12.5 */
}
```

---

## 10. Build-level notes

*(unchanged from iter/004, plus)*

- After fixing BUGs 1 and 4, verify the canvas renders points in a fresh browser profile (to avoid cached state)
- Run `cd frontend && npm run build` and `npm run preview` to test against a real API after each major fix
- Do NOT run `npm run dev` with StrictMode as the only test environment for DeckGL — preview mode is more representative
- The dev diagnostic log (`console.debug`) must be gated on `import.meta.env.DEV` and must not appear in production builds

---

*Component map complete. See UI_SPEC.md for layout and interaction specs. See DESIGN_TOKENS.md for visual system.*
