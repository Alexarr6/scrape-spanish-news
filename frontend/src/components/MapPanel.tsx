import { OrbitView, OrthographicView } from '@deck.gl/core'
import { ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { useEffect, useMemo, useState } from 'react'
import { formatDate } from '../lib/format'
import type { ExplorerColorMode, ExplorerPoint, ExplorerPointsResponse, ExplorerProjectionBounds, ExplorerViewMode } from '../lib/types'

type Props = {
  points: ExplorerPointsResponse | null
  loading: boolean
  error: string | null
  selectedArticleId: number | null
  hoveredArticleId: number | null
  neighborIds: Set<number>
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  onViewModeChange: (mode: ExplorerViewMode) => void
  onColorModeChange: (mode: ExplorerColorMode) => void
  onHoverArticle: (articleId: number | null) => void
  onSelectArticle: (articleId: number | null) => void
}

type TooltipState = { x: number; y: number; point: ExplorerPoint } | null
type PickingInfoLike = { object?: ExplorerPoint; x?: number; y?: number }
type ViewState2D = { target: [number, number, number]; zoom: number }
type ViewState3D = { target: [number, number, number]; zoom: number; rotationOrbit: number; rotationX: number }
type ViewStateMap = { 'semantic-2d': ViewState2D; 'semantic-3d': ViewState3D }
type PointBounds = {
  minX: number
  maxX: number
  minY: number
  maxY: number
  minZ: number
  maxZ: number
}

const DEFAULT_3D_ORBIT = 28
const DEFAULT_3D_TILT = 32

function normalizeBounds(bounds: ExplorerProjectionBounds | null): PointBounds | null {
  if (!bounds) return null
  return {
    minX: bounds.min_x,
    maxX: bounds.max_x,
    minY: bounds.min_y,
    maxY: bounds.max_y,
    minZ: bounds.min_z,
    maxZ: bounds.max_z,
  }
}

function boundsFromPoints(items: ExplorerPoint[]): PointBounds | null {
  if (items.length === 0) return null
  return items.reduce<PointBounds>(
    (acc, point) => ({
      minX: Math.min(acc.minX, point.x),
      maxX: Math.max(acc.maxX, point.x),
      minY: Math.min(acc.minY, point.y),
      maxY: Math.max(acc.maxY, point.y),
      minZ: Math.min(acc.minZ, point.z),
      maxZ: Math.max(acc.maxZ, point.z),
    }),
    {
      minX: items[0].x,
      maxX: items[0].x,
      minY: items[0].y,
      maxY: items[0].y,
      minZ: items[0].z,
      maxZ: items[0].z,
    },
  )
}

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
  if (!bounds) {
    return {
      target: [0, 0, 0],
      zoom: 1.9,
      rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT,
      rotationX: current?.rotationX ?? DEFAULT_3D_TILT,
    }
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
    'semantic-2d': build2dViewState(bounds),
    'semantic-3d': build3dViewState(bounds, current?.['semantic-3d']),
  }
}

function buildSelectionBounds(selectedPoint: ExplorerPoint, items: ExplorerPoint[], neighborIds: Set<number>): PointBounds {
  const related = items.filter((item) => item.article_id === selectedPoint.article_id || neighborIds.has(item.article_id))
  const selectionBounds = boundsFromPoints(related.length > 0 ? related : [selectedPoint])
  if (!selectionBounds) {
    return {
      minX: selectedPoint.x,
      maxX: selectedPoint.x,
      minY: selectedPoint.y,
      maxY: selectedPoint.y,
      minZ: selectedPoint.z,
      maxZ: selectedPoint.z,
    }
  }
  return selectionBounds
}

const SOURCE_COLORS: Record<string, [number, number, number, number]> = {
  elpais: [59, 130, 246, 220],
  elmundo: [16, 185, 129, 220],
  abc: [249, 115, 22, 220],
  eldiario: [168, 85, 247, 220],
  lavanguardia: [236, 72, 153, 220],
  '20minutos': [251, 191, 36, 220],
}

const CLUSTER_PALETTE: Array<[number, number, number, number]> = [
  [79, 70, 229, 220],
  [14, 165, 233, 220],
  [34, 197, 94, 220],
  [245, 158, 11, 220],
  [244, 63, 94, 220],
  [168, 85, 247, 220],
]

function colorForPoint(point: ExplorerPoint, mode: ExplorerColorMode): [number, number, number, number] {
  if (mode === 'source') return SOURCE_COLORS[point.source] ?? [100, 116, 139, 210]
  if (mode === 'cluster') {
    if (point.analysis.cluster_id == null) return point.analysis.is_outlier ? [220, 38, 38, 230] : [148, 163, 184, 200]
    return CLUSTER_PALETTE[(point.analysis.cluster_id - 1) % CLUSTER_PALETTE.length]
  }
  return [79, 70, 229, 200]
}

export function MapPanel({
  points,
  loading,
  error,
  selectedArticleId,
  hoveredArticleId,
  neighborIds,
  viewMode,
  colorMode,
  onViewModeChange,
  onColorModeChange,
  onHoverArticle,
  onSelectArticle,
}: Props) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)
  const [viewState, setViewState] = useState<ViewStateMap>(() => buildInitialViewState(points))
  const neighborKey = Array.from(neighborIds).sort((a, b) => a - b).join(',')
  const bounds = points?.meta.bounds ?? null
  const selectedPoint = useMemo(() => points?.items.find((item) => item.article_id === selectedArticleId) ?? null, [points, selectedArticleId])

  useEffect(() => {
    setViewState((current) => buildInitialViewState(points, current))
  }, [bounds?.min_x, bounds?.max_x, bounds?.min_y, bounds?.max_y, bounds?.min_z, bounds?.max_z, points?.meta.projection_set, points?.items.length])

  const focusSelection = () => {
    if (!selectedPoint) return
    const selectionBounds = buildSelectionBounds(selectedPoint, points?.items ?? [], neighborIds)
    setViewState((current) => ({
      ...current,
      'semantic-2d': {
        ...build2dViewState(selectionBounds),
        zoom: Math.max(current['semantic-2d'].zoom, Math.min(build2dViewState(selectionBounds).zoom + 0.25, 6.8)),
      },
      'semantic-3d': {
        ...build3dViewState(selectionBounds, current['semantic-3d']),
        zoom: Math.max(current['semantic-3d'].zoom, Math.min(build3dViewState(selectionBounds, current['semantic-3d']).zoom + 0.2, 6.2)),
      },
    }))
  }

  const layers = useMemo(() => {
    const items = points?.items ?? []
    const is3d = viewMode === '3d'
    return [
      new ScatterplotLayer<ExplorerPoint>({
        id: `semantic-points-${viewMode}-${colorMode}`,
        data: items,
        pickable: true,
        filled: true,
        stroked: true,
        opacity: is3d ? 0.92 : 0.86,
        radiusUnits: 'pixels',
        getPosition: (point: ExplorerPoint) => (is3d ? [point.x, point.y, point.z] : [point.x, point.y]),
        getRadius: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return is3d ? 9.5 : 8.5
          if (neighborIds.has(point.article_id)) return is3d ? 7.5 : 6.5
          if (point.article_id === hoveredArticleId) return is3d ? 6.5 : 5.7
          if (point.analysis.is_outlier) return is3d ? 5.7 : 5.2
          return is3d ? 4.8 : 4.2
        },
        radiusScale: is3d ? 1 : 1.15,
        radiusMinPixels: 3,
        radiusMaxPixels: 18,
        lineWidthUnits: 'pixels',
        getLineWidth: (point: ExplorerPoint) => (point.article_id === selectedArticleId ? 2.5 : 1),
        getFillColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return [14, 165, 233, 255]
          if (neighborIds.has(point.article_id)) return [34, 197, 94, 235]
          if (point.article_id === hoveredArticleId) return [125, 211, 252, 235]
          return colorForPoint(point, colorMode)
        },
        getLineColor: (point: ExplorerPoint) => (point.article_id === selectedArticleId ? [255, 255, 255, 255] : [248, 250, 252, 190]),
        onHover: (info: PickingInfoLike) => {
          const point = info.object
          onHoverArticle(point?.article_id ?? null)
          if (point && info.x != null && info.y != null) setTooltip({ x: info.x, y: info.y, point })
          else setTooltip(null)
        },
        onClick: (info: PickingInfoLike) => onSelectArticle(info.object?.article_id ?? null),
        updateTriggers: {
          getPosition: [viewMode],
          getRadius: [viewMode, selectedArticleId, hoveredArticleId, neighborKey],
          getFillColor: [viewMode, colorMode, selectedArticleId, hoveredArticleId, neighborKey],
          getLineColor: [selectedArticleId],
        },
      }),
    ]
  }, [points, viewMode, colorMode, selectedArticleId, hoveredArticleId, neighborIds, neighborKey, onHoverArticle, onSelectArticle])

  const resetView = () => setViewState((current) => buildInitialViewState(points, current))

  const activeViewState = viewState[viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']

  return (
    <div className="map-frame">
      <div className="map-overlay map-overlay-stack">
        <div className="map-toolbar">
          <div className="map-toolbar-row">
            <div>
              <div className="eyebrow">Explorer</div>
              <h2>{viewMode === '3d' ? '3D semantic view' : '2D semantic view'}</h2>
              <p className="muted">Auto-fit keeps the visible subset framed on load. Select an article when you want to inspect its local semantic neighborhood.</p>
            </div>
            <div className="status-chip-row compact-row">
              <span className="status-chip emphasis">{loading ? 'Loading projection…' : `${points?.items.length ?? 0} visible points`}</span>
              <span className="status-chip">{points?.meta.available_clusters.length ?? 0} clusters</span>
            </div>
          </div>
          <div className="map-toolbar-row">
            <div className="control-group">
              <h3>View</h3>
              <p className="muted">Switch between flat and spatial inspection.</p>
              <div className="segmented-control" role="tablist" aria-label="Explorer view mode">
                <button className={viewMode === '2d' ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onViewModeChange('2d')}>2D</button>
                <button className={viewMode === '3d' ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onViewModeChange('3d')}>3D</button>
              </div>
            </div>
            <div className="control-group">
              <h3>Color encoding</h3>
              <p className="muted">Choose the lens, not just the paint.</p>
              <div className="segmented-control" role="tablist" aria-label="Explorer color mode">
                {(['neutral', 'source', 'cluster'] as ExplorerColorMode[]).map((mode) => (
                  <button key={mode} className={colorMode === mode ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onColorModeChange(mode)}>
                    {mode}
                  </button>
                ))}
              </div>
            </div>
            <div className="control-group">
              <h3>Focus</h3>
              <p className="muted">Fit the whole subset or tighten around the selected neighborhood.</p>
              <div className="action-row">
                <button className="ghost-button" type="button" onClick={focusSelection} disabled={!selectedPoint}>Focus selected</button>
                <button className="ghost-button" type="button" onClick={resetView}>Fit all</button>
              </div>
            </div>
          </div>
          <div className="legend-row">
            <span className="muted">{viewMode === '3d' ? 'Drag to orbit, scroll to zoom, right-drag to pan.' : 'Drag to pan, scroll to zoom, click a point for context.'}</span>
            <span className="muted">{error ? error : `Projection set: ${points?.meta.projection_set ?? 'loading'}`}</span>
          </div>
        </div>
      </div>

      <div className="map-canvas">
        <DeckGL
          views={viewMode === '3d' ? [new OrbitView({ id: 'semantic-3d' })] : [new OrthographicView({ id: 'semantic-2d' })]}
          controller={viewMode === '3d' ? { dragMode: 'rotate', inertia: true } : { dragRotate: false, doubleClickZoom: true, touchRotate: false }}
          layers={layers}
          viewState={activeViewState as never}
          onViewStateChange={({ viewState: nextViewState }) => {
            setViewState((current) => ({ ...current, [viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']: nextViewState as ViewStateMap[keyof ViewStateMap] }))
          }}
        >
          {!loading && !error && (points?.items.length ?? 0) === 0 ? (
            <div className="map-empty-state">
              <strong>No points match the current scope</strong>
              <p className="muted">Widen the date range, remove one filter, or go back to Stories if what you need is coverage comparison.</p>
            </div>
          ) : null}
          {tooltip ? <Tooltip tooltip={tooltip} /> : null}
        </DeckGL>
      </div>
    </div>
  )
}

function Tooltip({ tooltip }: { tooltip: NonNullable<TooltipState> }) {
  return (
    <div className="tooltip-card" style={{ left: tooltip.x + 14, top: tooltip.y + 14 }}>
      <strong>{tooltip.point.title}</strong>
      <div className="muted">{tooltip.point.source} · {tooltip.point.section || 'no section'}</div>
      <div className="muted">{formatDate(tooltip.point.published_at)}</div>
      <p>{tooltip.point.summary_snippet || 'No summary snippet available.'}</p>
      <div className="muted point-coords">x {tooltip.point.x.toFixed(2)} · y {tooltip.point.y.toFixed(2)} · z {tooltip.point.z.toFixed(2)}</div>
      <div className="muted point-coords">{tooltip.point.analysis.cluster_id == null ? (tooltip.point.analysis.is_outlier ? 'Outlier' : 'Unclustered') : `Cluster ${tooltip.point.analysis.cluster_id} · ${tooltip.point.analysis.cluster_size} items`}</div>
    </div>
  )
}
