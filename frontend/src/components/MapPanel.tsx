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

function build2dViewState(bounds: ExplorerProjectionBounds | null): ViewState2D {
  if (!bounds) return { target: [0, 0, 0], zoom: 0 }
  const spanX = Math.max(bounds.max_x - bounds.min_x, 0.2)
  const spanY = Math.max(bounds.max_y - bounds.min_y, 0.2)
  const dominantSpan = Math.max(spanX, spanY)
  return {
    target: [(bounds.min_x + bounds.max_x) / 2, (bounds.min_y + bounds.max_y) / 2, 0],
    zoom: Math.max(0.35, Math.min(8, Math.log2(3.4 / dominantSpan))),
  }
}

function build3dViewState(bounds: ExplorerProjectionBounds | null): ViewState3D {
  if (!bounds) return { target: [0, 0, 0], zoom: 0.8, rotationOrbit: 28, rotationX: 32 }
  const spanX = Math.max(bounds.max_x - bounds.min_x, 0.2)
  const spanY = Math.max(bounds.max_y - bounds.min_y, 0.2)
  const spanZ = Math.max(bounds.max_z - bounds.min_z, 0.2)
  const dominantSpan = Math.max(spanX, spanY, spanZ)
  return {
    target: [(bounds.min_x + bounds.max_x) / 2, (bounds.min_y + bounds.max_y) / 2, (bounds.min_z + bounds.max_z) / 2],
    zoom: Math.max(0.45, Math.min(7, Math.log2(2.8 / dominantSpan))),
    rotationOrbit: 28,
    rotationX: 32,
  }
}

function buildInitialViewState(points: ExplorerPointsResponse | null): ViewStateMap {
  const bounds = points?.meta.bounds ?? null
  return { 'semantic-2d': build2dViewState(bounds), 'semantic-3d': build3dViewState(bounds) }
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
    setViewState(buildInitialViewState(points))
  }, [bounds?.min_x, bounds?.max_x, bounds?.min_y, bounds?.max_y, bounds?.min_z, bounds?.max_z, points?.meta.projection_set])

  useEffect(() => {
    if (!selectedPoint) return
    setViewState((current) => ({
      ...current,
      'semantic-2d': { ...current['semantic-2d'], target: [selectedPoint.x, selectedPoint.y, 0], zoom: Math.max(current['semantic-2d'].zoom, 4.2) },
      'semantic-3d': { ...current['semantic-3d'], target: [selectedPoint.x, selectedPoint.y, selectedPoint.z], zoom: Math.max(current['semantic-3d'].zoom, 3.8) },
    }))
  }, [selectedPoint?.article_id])

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

  const resetView = () => setViewState(buildInitialViewState(points))
  const focusSelection = () => {
    if (!selectedPoint) return
    setViewState((current) => ({
      ...current,
      'semantic-2d': { ...current['semantic-2d'], target: [selectedPoint.x, selectedPoint.y, 0], zoom: Math.max(current['semantic-2d'].zoom, 4.2) },
      'semantic-3d': { ...current['semantic-3d'], target: [selectedPoint.x, selectedPoint.y, selectedPoint.z], zoom: Math.max(current['semantic-3d'].zoom, 3.8) },
    }))
  }

  const activeViewState = viewState[viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']

  return (
    <div className="map-frame">
      <div className="map-overlay map-overlay-stack">
        <div className="map-toolbar">
          <div className="map-toolbar-row">
            <div>
              <div className="eyebrow">Explorer</div>
              <h2>{viewMode === '3d' ? '3D semantic view' : '2D semantic view'}</h2>
              <p className="muted">Points are articles. Color encodes source or cluster. Selection reveals the local semantic neighborhood.</p>
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
              <p className="muted">Keep the camera honest.</p>
              <div className="action-row">
                {selectedPoint ? <button className="ghost-button" type="button" onClick={focusSelection}>Focus selected</button> : null}
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
