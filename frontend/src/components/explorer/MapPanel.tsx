/**
 * MapPanel.tsx — DeckGL semantic canvas.
 *
 * Bug fixes applied in iter/005:
 *  BUG-1: flex/grid height chain — fixed in styles.css (min-height: 0)
 *  BUG-2: StrictMode double-mount — stable key="explorer-deck" on <DeckGL>
 *  BUG-4: Named view IDs mismatch — removed view IDs (unnamed single-view)
 *  BUG-5: Layer ID changes on every toggle — stable id: 'semantic-points'
 *  BUG-6: !important overrides — removed from styles.css
 *
 * Camera hardening:
 *  - Auto-fit only fires on first data load (null → data) or explicit fitAll()
 *  - Subsequent filter changes preserve the user's camera position
 *  - 3D orbit angles preserved across focusSelected() calls
 */

import { OrbitView, OrthographicView } from '@deck.gl/core'
import { ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { formatDate } from '../../lib/format'
import {
  CLUSTER_NULL_COLOR,
  CLUSTER_OUTLIER_COLOR,
  CLUSTER_PALETTE,
  POINT_DEFAULT_STROKE,
  POINT_DEFAULT_STROKE_WIDTH,
  POINT_HOVERED_FILL,
  POINT_HOVERED_RADIUS_2D,
  POINT_HOVERED_RADIUS_3D,
  POINT_HOVERED_STROKE,
  POINT_HOVERED_STROKE_WIDTH,
  POINT_NEIGHBOR_FILL,
  POINT_NEIGHBOR_RADIUS_2D,
  POINT_NEIGHBOR_RADIUS_3D,
  POINT_NEIGHBOR_STROKE,
  POINT_NEIGHBOR_STROKE_WIDTH,
  POINT_OUTLIER_ALPHA_NO_SELECTION,
  POINT_OUTLIER_ALPHA_UNDER_SELECTION,
  POINT_OUTLIER_RADIUS_2D,
  POINT_OUTLIER_RADIUS_3D,
  POINT_RECEDING_STROKE,
  POINT_RECEDING_STROKE_WIDTH,
  POINT_REGULAR_ALPHA_NO_SELECTION,
  POINT_REGULAR_ALPHA_UNDER_SELECTION,
  POINT_REGULAR_RADIUS_2D,
  POINT_REGULAR_RADIUS_3D,
  POINT_SELECTED_FILL,
  POINT_SELECTED_RADIUS_2D,
  POINT_SELECTED_RADIUS_3D,
  POINT_SELECTED_STROKE,
  POINT_SELECTED_STROKE_WIDTH,
  SOURCE_COLORS,
  SOURCE_FALLBACK_COLOR,
} from '../../lib/explorerColors'
import type {
  ExplorerColorMode,
  ExplorerPoint,
  ExplorerPointsResponse,
  ExplorerProjectionBounds,
  ExplorerViewMode,
} from '../../lib/types'

export type MapPanelHandle = {
  fitAll: () => void
  focusSelected: () => void
}

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

type TooltipState = { x: number; y: number; point: ExplorerPoint } | null
type PickingInfoLike = { object?: ExplorerPoint; x?: number; y?: number }
type ViewState2D = { target: [number, number, number]; zoom: number }
type ViewState3D = { target: [number, number, number]; zoom: number; rotationOrbit: number; rotationX: number }
type ViewStateMap = { '2d': ViewState2D; '3d': ViewState3D }
type PointBounds = {
  minX: number; maxX: number; minY: number; maxY: number; minZ: number; maxZ: number
}

const DEFAULT_3D_ORBIT = 28
const DEFAULT_3D_TILT = 32

// ─── Bounds helpers ──────────────────────────────────────────────────────────

function normalizeBounds(bounds: ExplorerProjectionBounds | null): PointBounds | null {
  if (!bounds) return null
  return {
    minX: bounds.min_x, maxX: bounds.max_x,
    minY: bounds.min_y, maxY: bounds.max_y,
    minZ: bounds.min_z, maxZ: bounds.max_z,
  }
}

function boundsFromPoints(items: ExplorerPoint[]): PointBounds | null {
  if (items.length === 0) return null
  return items.reduce<PointBounds>(
    (acc, p) => ({
      minX: Math.min(acc.minX, p.x), maxX: Math.max(acc.maxX, p.x),
      minY: Math.min(acc.minY, p.y), maxY: Math.max(acc.maxY, p.y),
      minZ: Math.min(acc.minZ, p.z), maxZ: Math.max(acc.maxZ, p.z),
    }),
    { minX: items[0].x, maxX: items[0].x, minY: items[0].y, maxY: items[0].y, minZ: items[0].z, maxZ: items[0].z },
  )
}

// ─── ViewState builders ──────────────────────────────────────────────────────

function build2dViewState(bounds: PointBounds | null): ViewState2D {
  if (!bounds) return { target: [0, 0, 0], zoom: 1.8 }
  const spanX = bounds.maxX - bounds.minX
  const spanY = bounds.maxY - bounds.minY
  const dominantSpan = Math.max(spanX, spanY)
  const paddedSpan = Math.max(dominantSpan * 1.45, 1.1)
  return {
    target: [(bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2, 0],
    zoom: Math.max(1.4, Math.min(7.2, Math.log2(3.2 / paddedSpan) + 1.4)),
  }
}

function build3dViewState(bounds: PointBounds | null, current?: ViewState3D): ViewState3D {
  if (!bounds) return {
    target: [0, 0, 0],
    zoom: 1.9,
    rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT,
    rotationX: current?.rotationX ?? DEFAULT_3D_TILT,
  }
  const spanX = bounds.maxX - bounds.minX
  const spanY = bounds.maxY - bounds.minY
  const spanZ = bounds.maxZ - bounds.minZ
  const dominantSpan = Math.max(spanX, spanY, spanZ)
  const paddedSpan = Math.max(dominantSpan * 1.6, 1.15)
  return {
    target: [(bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2, (bounds.minZ + bounds.maxZ) / 2],
    zoom: Math.max(1.55, Math.min(6.6, Math.log2(3.1 / paddedSpan) + 1.2)),
    rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT,
    rotationX: current?.rotationX ?? DEFAULT_3D_TILT,
  }
}

function buildInitialViewState(points: ExplorerPointsResponse | null, current?: ViewStateMap): ViewStateMap {
  const bounds = normalizeBounds(points?.meta.bounds ?? null)
  return {
    '2d': build2dViewState(bounds),
    '3d': build3dViewState(bounds, current?.['3d']),
  }
}

function buildSelectionBounds(selectedPoint: ExplorerPoint, items: ExplorerPoint[], neighborIds: Set<number>): PointBounds {
  const related = items.filter((item) =>
    item.article_id === selectedPoint.article_id || neighborIds.has(item.article_id),
  )
  const selectionBounds = boundsFromPoints(related.length > 0 ? related : [selectedPoint])
  if (!selectionBounds) {
    return {
      minX: selectedPoint.x, maxX: selectedPoint.x,
      minY: selectedPoint.y, maxY: selectedPoint.y,
      minZ: selectedPoint.z, maxZ: selectedPoint.z,
    }
  }
  return selectionBounds
}

// ─── Color helpers ───────────────────────────────────────────────────────────

function colorForPoint(point: ExplorerPoint, mode: ExplorerColorMode): [number, number, number] {
  if (mode === 'source') {
    return SOURCE_COLORS[point.source] ?? SOURCE_FALLBACK_COLOR
  }
  if (mode === 'cluster') {
    if (point.analysis.cluster_id == null) {
      return point.analysis.is_outlier ? CLUSTER_OUTLIER_COLOR : CLUSTER_NULL_COLOR
    }
    return CLUSTER_PALETTE[(point.analysis.cluster_id - 1) % CLUSTER_PALETTE.length]
  }
  // neutral
  return [67, 56, 202] // indigo-700
}

// ─── Component ───────────────────────────────────────────────────────────────

export const MapPanel = forwardRef<MapPanelHandle, Props>(function MapPanel(
  {
    points,
    loading,
    error,
    selectedArticleId,
    hoveredArticleId,
    neighborIds,
    viewMode,
    colorMode,
    onHoverArticle,
    onSelectArticle,
  },
  ref,
) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)
  const [viewState, setViewState] = useState<ViewStateMap>(() => buildInitialViewState(points))
  const [dataLoaded, setDataLoaded] = useState(false)
  const canvasRef = useRef<HTMLDivElement>(null)

  const neighborKey = Array.from(neighborIds).sort((a, b) => a - b).join(',')

  const selectedPoint = useMemo(
    () => points?.items.find((item) => item.article_id === selectedArticleId) ?? null,
    [points, selectedArticleId],
  )
  const hasSelection = selectedArticleId != null

  // ─── Camera auto-fit: ONLY fires on first data load (null → populated)
  // Subsequent filter changes preserve user camera position.
  const projectionSet = points?.meta.projection_set
  useEffect(() => {
    if (!points?.items.length) {
      setDataLoaded(false)
      return
    }
    if (!dataLoaded) {
      // First load or after a full reset — fit to all points
      setViewState((current) => buildInitialViewState(points, current))
      setDataLoaded(true)
    }
    // Subsequent filter changes: do NOT reset camera — user's pan/zoom is preserved
  }, [points?.items.length, projectionSet]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Imperative camera controls ──────────────────────────────────────────
  const fitAll = () => {
    setViewState((current) => buildInitialViewState(points, current))
  }

  const focusSelected = () => {
    if (!selectedPoint) return
    const selectionBounds = buildSelectionBounds(selectedPoint, points?.items ?? [], neighborIds)
    const focused2d = build2dViewState(selectionBounds)
    const focused3d = build3dViewState(selectionBounds, viewState['3d'])
    setViewState((current) => ({
      '2d': { ...focused2d, zoom: Math.min(focused2d.zoom + 0.25, 6.8) },
      '3d': {
        ...focused3d,
        zoom: Math.min(focused3d.zoom + 0.2, 6.2),
        // Preserve user's orbital angles — do not reset tilt/orbit on focus
        rotationOrbit: current['3d'].rotationOrbit,
        rotationX: current['3d'].rotationX,
      },
    }))
  }

  useImperativeHandle(ref, () => ({ fitAll, focusSelected }))

  // ─── Dev diagnostic (mount only) ─────────────────────────────────────────
  useEffect(() => {
    if (!import.meta.env.DEV) return
    const el = canvasRef.current
    // eslint-disable-next-line no-console
    console.debug(
      '[MapPanel] mount diagnostic:',
      '\n  canvas clientHeight:', el?.clientHeight ?? 'NOT FOUND',
      '\n  canvas clientWidth:', el?.clientWidth ?? 'NOT FOUND',
      '\n  points count:', points?.items.length ?? 0,
      '\n  viewState 2d:', viewState['2d'],
      '\n  bounds:', points?.meta.bounds,
    )
  }, []) // intentionally run once on mount only

  // ─── Layer ───────────────────────────────────────────────────────────────
  const layers = useMemo(() => {
    const items = points?.items ?? []
    const is3d = viewMode === '3d'

    return [
      new ScatterplotLayer<ExplorerPoint>({
        id: 'semantic-points', // stable ID — updateTriggers handle all changes (BUG-5 fix)
        data: items,
        pickable: true,
        filled: true,
        stroked: true,
        opacity: is3d ? 0.94 : 0.9,
        radiusUnits: 'pixels',
        lineWidthUnits: 'pixels',
        radiusMinPixels: 2,
        radiusMaxPixels: 18,

        getPosition: (point: ExplorerPoint) =>
          is3d ? [point.x, point.y, point.z] : [point.x, point.y],

        getRadius: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId)
            return is3d ? POINT_SELECTED_RADIUS_3D : POINT_SELECTED_RADIUS_2D
          if (neighborIds.has(point.article_id))
            return is3d ? POINT_NEIGHBOR_RADIUS_3D : POINT_NEIGHBOR_RADIUS_2D
          if (point.article_id === hoveredArticleId)
            return is3d ? POINT_HOVERED_RADIUS_3D : POINT_HOVERED_RADIUS_2D
          if (point.analysis.is_outlier)
            return is3d ? POINT_OUTLIER_RADIUS_3D : POINT_OUTLIER_RADIUS_2D
          return is3d ? POINT_REGULAR_RADIUS_3D : POINT_REGULAR_RADIUS_2D
        },

        getFillColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return POINT_SELECTED_FILL
          if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_FILL
          if (point.article_id === hoveredArticleId) return POINT_HOVERED_FILL
          const [r, g, b] = colorForPoint(point, colorMode)
          const alpha = hasSelection
            ? point.analysis.is_outlier
              ? POINT_OUTLIER_ALPHA_UNDER_SELECTION
              : POINT_REGULAR_ALPHA_UNDER_SELECTION
            : point.analysis.is_outlier
              ? POINT_OUTLIER_ALPHA_NO_SELECTION
              : POINT_REGULAR_ALPHA_NO_SELECTION
          return [r, g, b, alpha] as [number, number, number, number]
        },

        getLineColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return POINT_SELECTED_STROKE
          if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_STROKE
          if (point.article_id === hoveredArticleId) return POINT_HOVERED_STROKE
          if (hasSelection) return POINT_RECEDING_STROKE
          return POINT_DEFAULT_STROKE
        },

        getLineWidth: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return POINT_SELECTED_STROKE_WIDTH
          if (neighborIds.has(point.article_id)) return POINT_NEIGHBOR_STROKE_WIDTH
          if (point.article_id === hoveredArticleId) return POINT_HOVERED_STROKE_WIDTH
          if (hasSelection) return POINT_RECEDING_STROKE_WIDTH
          return POINT_DEFAULT_STROKE_WIDTH
        },

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
          getPosition: [viewMode],
          getRadius: [viewMode, selectedArticleId, hoveredArticleId, neighborKey],
          getFillColor: [viewMode, colorMode, selectedArticleId, hoveredArticleId, neighborKey],
          getLineColor: [selectedArticleId, neighborKey, hasSelection],
          getLineWidth: [selectedArticleId, neighborKey, hasSelection],
        },
      }),
    ]
  }, [points, viewMode, colorMode, selectedArticleId, hoveredArticleId, neighborIds, neighborKey, onHoverArticle, onSelectArticle, hasSelection])

  const activeViewState = viewState[viewMode]

  return (
    <div className="map-frame">
      {/* Initial load overlay */}
      {loading && !points && (
        <div className="map-loading-overlay">
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            Loading semantic projection…
          </div>
        </div>
      )}

      <div
        ref={canvasRef}
        className={`map-canvas${loading && points ? ' loading-update' : ''}`}
      >
        {/* BUG-2 fix: key="explorer-deck" prevents StrictMode double-mount identity loss.
            BUG-4 fix: OrthographicView/OrbitView with no id (unnamed single-view mode);
                       viewState is passed as a plain object — DeckGL handles it correctly. */}
        <DeckGL
          key="explorer-deck"
          views={viewMode === '3d' ? [new OrbitView()] : [new OrthographicView()]}
          controller={
            viewMode === '3d'
              ? { dragMode: 'rotate', inertia: true }
              : { dragRotate: false, doubleClickZoom: true, touchRotate: false }
          }
          layers={layers}
          viewState={activeViewState as never}
          onViewStateChange={({ viewState: nextViewState }) => {
            setViewState((current) => ({
              ...current,
              [viewMode]: nextViewState as ViewStateMap[typeof viewMode],
            }))
          }}
        >
          {error && (
            <div className="map-empty-state">
              <strong>Failed to load semantic projection</strong>
              <p>{error}</p>
            </div>
          )}
          {!loading && !error && (points?.items.length ?? 0) === 0 && (
            <div className="map-empty-state">
              <strong>No articles match the current filters</strong>
              <p>Broaden the source or date scope, or clear the cluster filter.</p>
            </div>
          )}
          {tooltip && (
            <Tooltip
              tooltip={tooltip}
              canvasWidth={canvasRef.current?.clientWidth ?? 9999}
              canvasHeight={canvasRef.current?.clientHeight ?? 9999}
            />
          )}
        </DeckGL>

        {/* Dev diagnostic overlay — stripped in production builds */}
        {import.meta.env.DEV && (
          <DevDiagnostic
            points={points}
            activeViewState={activeViewState}
            canvasEl={canvasRef.current}
          />
        )}
      </div>
    </div>
  )
})

// ─── Tooltip ─────────────────────────────────────────────────────────────────

const TOOLTIP_WIDTH = 288  // max-width: 18rem ≈ 288px
const TOOLTIP_HEIGHT = 120 // approximate

function Tooltip({
  tooltip,
  canvasWidth,
  canvasHeight,
}: {
  tooltip: NonNullable<TooltipState>
  canvasWidth: number
  canvasHeight: number
}) {
  const point = tooltip.point
  // Clamp tooltip so it doesn't overflow canvas edges
  const left = Math.min(tooltip.x + 14, canvasWidth - TOOLTIP_WIDTH - 8)
  const top = Math.min(tooltip.y + 14, canvasHeight - TOOLTIP_HEIGHT - 8)

  return (
    <div className="tooltip-card" style={{ left, top }}>
      <div className="tooltip-eyebrow">
        <span>{point.source}{point.section ? ` · ${point.section}` : ''}</span>
        {point.analysis.is_outlier && (
          <span className="tooltip-outlier-badge">Outlier</span>
        )}
      </div>
      <strong>{point.title}</strong>
      <div className="tooltip-meta">{formatDate(point.published_at)}</div>
      <div className="tooltip-cluster-meta">
        {point.analysis.cluster_id != null
          ? `Cluster ${point.analysis.cluster_id}`
          : 'No cluster'}
      </div>
      {point.summary_snippet && <p>{point.summary_snippet}</p>}
    </div>
  )
}

// ─── Dev diagnostic overlay ───────────────────────────────────────────────────

function DevDiagnostic({
  points,
  activeViewState,
  canvasEl,
}: {
  points: ExplorerPointsResponse | null
  activeViewState: { zoom: number; target: [number, number, number] }
  canvasEl: HTMLDivElement | null
}) {
  const b = points?.meta.bounds
  const boundsStr = b
    ? `[${b.min_x.toFixed(2)},${b.max_x.toFixed(2)},${b.min_y.toFixed(2)},${b.max_y.toFixed(2)}]`
    : 'null'

  return (
    <div className="map-debug-overlay">
      {`pts:${points?.items.length ?? 0} | canvas:${canvasEl?.clientWidth ?? '?'}×${canvasEl?.clientHeight ?? '?'} | zoom:${activeViewState.zoom.toFixed(2)} | bounds:${boundsStr}`}
    </div>
  )
}
