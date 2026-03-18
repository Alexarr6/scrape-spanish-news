import { OrbitView, OrthographicView } from '@deck.gl/core'
import { ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { useEffect, useMemo, useState } from 'react'
import { formatDate } from '../lib/format'
import type {
  ExplorerColorMode,
  ExplorerPoint,
  ExplorerPointsResponse,
  ExplorerProjectionBounds,
  ExplorerViewMode,
} from '../lib/types'

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

type TooltipState = {
  x: number
  y: number
  point: ExplorerPoint
} | null

type PickingInfoLike = {
  object?: ExplorerPoint
  x?: number
  y?: number
}

type ViewState2D = { target: [number, number, number]; zoom: number }
type ViewState3D = { target: [number, number, number]; zoom: number; rotationOrbit: number; rotationX: number }
type ViewStateMap = { 'semantic-2d': ViewState2D; 'semantic-3d': ViewState3D }

const MIN_SPAN_EPSILON = 1e-6
const VIEW_PADDING = 0.12

function clampZoom(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function paddedSpan(span: number): number {
  return Math.max(span, MIN_SPAN_EPSILON) * (1 + VIEW_PADDING * 2) + MIN_SPAN_EPSILON
}

function build2dViewState(bounds: ExplorerProjectionBounds | null): ViewState2D {
  if (!bounds) return { target: [0, 0, 0], zoom: 0 }
  const spanX = paddedSpan(bounds.max_x - bounds.min_x)
  const spanY = paddedSpan(bounds.max_y - bounds.min_y)
  const dominantSpan = Math.max(spanX, spanY)
  return {
    target: [(bounds.min_x + bounds.max_x) / 2, (bounds.min_y + bounds.max_y) / 2, 0],
    zoom: clampZoom(Math.log2(2.8 / dominantSpan), -1.2, 7),
  }
}

function build3dViewState(bounds: ExplorerProjectionBounds | null): ViewState3D {
  if (!bounds) return { target: [0, 0, 0], zoom: 0, rotationOrbit: 28, rotationX: 32 }
  const spanX = paddedSpan(bounds.max_x - bounds.min_x)
  const spanY = paddedSpan(bounds.max_y - bounds.min_y)
  const spanZ = paddedSpan(bounds.max_z - bounds.min_z)
  const dominantSpan = Math.max(spanX, spanY, spanZ)
  return {
    target: [(bounds.min_x + bounds.max_x) / 2, (bounds.min_y + bounds.max_y) / 2, (bounds.min_z + bounds.max_z) / 2],
    zoom: clampZoom(Math.log2(2.25 / dominantSpan), -1, 6),
    rotationOrbit: 28,
    rotationX: 32,
  }
}

function buildInitialViewState(points: ExplorerPointsResponse | null): ViewStateMap {
  const bounds = points?.meta.bounds ?? null
  return {
    'semantic-2d': build2dViewState(bounds),
    'semantic-3d': build3dViewState(bounds),
  }
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
  [56, 189, 248, 220],
  [74, 222, 128, 220],
  [250, 204, 21, 220],
  [244, 114, 182, 220],
  [192, 132, 252, 220],
  [248, 113, 113, 220],
]

function colorForPoint(point: ExplorerPoint, mode: ExplorerColorMode): [number, number, number, number] {
  if (mode === 'source') return SOURCE_COLORS[point.source] ?? [148, 163, 184, 210]
  if (mode === 'cluster') {
    if (point.analysis.cluster_id == null) return point.analysis.is_outlier ? [248, 113, 113, 230] : [148, 163, 184, 190]
    return CLUSTER_PALETTE[(point.analysis.cluster_id - 1) % CLUSTER_PALETTE.length]
  }
  return [96, 165, 250, 205]
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
    setViewState(buildInitialViewState(points))
  }, [bounds?.min_x, bounds?.max_x, bounds?.min_y, bounds?.max_y, bounds?.min_z, bounds?.max_z, points?.meta.projection_set])

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
        opacity: is3d ? 0.9 : 0.82,
        radiusUnits: 'pixels',
        getPosition: (point: ExplorerPoint) => (is3d ? [point.x, point.y, point.z] : [point.x, point.y]),
        getRadius: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return is3d ? 9 : 8
          if (neighborIds.has(point.article_id)) return is3d ? 7 : 6
          if (point.article_id === hoveredArticleId) return is3d ? 6 : 5.5
          if (point.analysis.is_outlier) return is3d ? 5.5 : 5
          return is3d ? 4.5 : 4
        },
        radiusScale: is3d ? 1 : 1.2,
        radiusMinPixels: is3d ? 3 : 2.5,
        radiusMaxPixels: is3d ? 18 : 14,
        lineWidthUnits: 'pixels',
        getLineWidth: (point: ExplorerPoint) => (point.article_id === selectedArticleId ? 2.5 : 1),
        getFillColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return [250, 204, 21, 255]
          if (neighborIds.has(point.article_id)) return [34, 197, 94, 230]
          if (point.article_id === hoveredArticleId) return [125, 211, 252, 235]
          return colorForPoint(point, colorMode)
        },
        getLineColor: (point: ExplorerPoint) => point.article_id === selectedArticleId ? [255, 255, 255, 255] : [15, 23, 42, 150],
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

  const resetView = () => setViewState(buildInitialViewState(points))
  const focusSelection = () => {
    if (!selectedPoint) return
    setViewState((current) => ({
      ...current,
      'semantic-2d': { ...current['semantic-2d'], target: [selectedPoint.x, selectedPoint.y, 0], zoom: Math.max(current['semantic-2d'].zoom, 3.5) },
      'semantic-3d': { ...current['semantic-3d'], target: [selectedPoint.x, selectedPoint.y, selectedPoint.z], zoom: Math.max(current['semantic-3d'].zoom, 3.2) },
    }))
  }

  const activeViewState = viewState[viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']

  return (
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
        <div className="map-overlay map-overlay-stack">
          <div className="panel-header compact">
            <div>
              <strong>{viewMode === '3d' ? '3D semantic explorer' : '2D semantic explorer'}</strong>
              <p>{loading ? 'Loading projection…' : error ? error : `${points?.items.length ?? 0} visible points · ${points?.meta.available_clusters.length ?? 0} clusters.`}</p>
            </div>
            <div className="segmented-control" role="tablist" aria-label="Explorer view mode">
              <button className={viewMode === '2d' ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onViewModeChange('2d')}>2D</button>
              <button className={viewMode === '3d' ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onViewModeChange('3d')}>3D</button>
            </div>
          </div>
          <div className="panel-header compact">
            <span className="muted">Visual mode</span>
            <div className="segmented-control" role="tablist" aria-label="Explorer color mode">
              {(['neutral', 'source', 'cluster'] as ExplorerColorMode[]).map((mode) => (
                <button key={mode} className={colorMode === mode ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onColorModeChange(mode)}>
                  {mode}
                </button>
              ))}
            </div>
          </div>
          <div className="hint-row">
            <span>{viewMode === '3d' ? 'Drag to orbit, scroll to zoom, right-drag to pan.' : 'Drag to pan, scroll to zoom, click for the inspector.'}</span>
            <div className="action-row">
              {selectedPoint ? <button className="ghost-button" type="button" onClick={focusSelection}>Focus selected</button> : null}
              <button className="ghost-button" type="button" onClick={resetView}>Reset view</button>
            </div>
          </div>
        </div>
        {!loading && !error && (points?.items.length ?? 0) === 0 ? <div className="empty-state">No points match the current filters.</div> : null}
        {tooltip ? <Tooltip tooltip={tooltip} /> : null}
      </DeckGL>
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
