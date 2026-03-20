import { OrbitView, OrthographicView } from '@deck.gl/core'
import { ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { forwardRef, useEffect, useImperativeHandle, useMemo, useState } from 'react'
import { formatDate } from '../../lib/format'
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
type ViewStateMap = { 'semantic-2d': ViewState2D; 'semantic-3d': ViewState3D }
type PointBounds = {
  minX: number; maxX: number; minY: number; maxY: number; minZ: number; maxZ: number
}

const DEFAULT_3D_ORBIT = 28
const DEFAULT_3D_TILT = 32

function normalizeBounds(bounds: ExplorerProjectionBounds | null): PointBounds | null {
  if (!bounds) return null
  return { minX: bounds.min_x, maxX: bounds.max_x, minY: bounds.min_y, maxY: bounds.max_y, minZ: bounds.min_z, maxZ: bounds.max_z }
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
  if (!bounds) return { target: [0, 0, 0], zoom: 1.9, rotationOrbit: current?.rotationOrbit ?? DEFAULT_3D_ORBIT, rotationX: current?.rotationX ?? DEFAULT_3D_TILT }
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
  return { 'semantic-2d': build2dViewState(bounds), 'semantic-3d': build3dViewState(bounds, current?.['semantic-3d']) }
}

function buildSelectionBounds(selectedPoint: ExplorerPoint, items: ExplorerPoint[], neighborIds: Set<number>): PointBounds {
  const related = items.filter((item) => item.article_id === selectedPoint.article_id || neighborIds.has(item.article_id))
  const selectionBounds = boundsFromPoints(related.length > 0 ? related : [selectedPoint])
  if (!selectionBounds) return { minX: selectedPoint.x, maxX: selectedPoint.x, minY: selectedPoint.y, maxY: selectedPoint.y, minZ: selectedPoint.z, maxZ: selectedPoint.z }
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
  [67, 56, 202, 220],
  [3, 105, 161, 220],
  [4, 120, 87, 220],
  [180, 83, 9, 220],
  [157, 23, 77, 220],
  [109, 40, 217, 220],
]

function colorForPoint(point: ExplorerPoint, mode: ExplorerColorMode): [number, number, number, number] {
  if (mode === 'source') return SOURCE_COLORS[point.source] ?? [100, 116, 139, 210]
  if (mode === 'cluster') {
    if (point.analysis.cluster_id == null)
      return point.analysis.is_outlier ? [220, 38, 38, 230] : [148, 163, 184, 200]
    return CLUSTER_PALETTE[(point.analysis.cluster_id - 1) % CLUSTER_PALETTE.length]
  }
  return [67, 56, 202, 200]
}

function withAlpha(color: [number, number, number, number], alpha: number): [number, number, number, number] {
  return [color[0], color[1], color[2], alpha]
}

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
  const neighborKey = Array.from(neighborIds).sort((a, b) => a - b).join(',')
  const bounds = points?.meta.bounds ?? null
  const selectedPoint = useMemo(
    () => points?.items.find((item) => item.article_id === selectedArticleId) ?? null,
    [points, selectedArticleId],
  )
  const hasSelection = selectedArticleId != null

  useEffect(() => {
    setViewState((current) => buildInitialViewState(points, current))
  }, [
    bounds?.min_x, bounds?.max_x, bounds?.min_y, bounds?.max_y, bounds?.min_z, bounds?.max_z,
    points?.meta.projection_set, points?.items.length,
  ])

  const fitAll = () => setViewState((current) => buildInitialViewState(points, current))

  const focusSelected = () => {
    if (!selectedPoint) return
    const selectionBounds = buildSelectionBounds(selectedPoint, points?.items ?? [], neighborIds)
    const focused2d = build2dViewState(selectionBounds)
    const focused3d = build3dViewState(selectionBounds, viewState['semantic-3d'])
    setViewState((current) => ({
      ...current,
      'semantic-2d': { ...focused2d, zoom: Math.max(current['semantic-2d'].zoom, Math.min(focused2d.zoom + 0.25, 6.8)) },
      'semantic-3d': { ...focused3d, zoom: Math.max(current['semantic-3d'].zoom, Math.min(focused3d.zoom + 0.2, 6.2)) },
    }))
  }

  // Expose imperative handle for ExplorerPage to wire to ExplorerControlBar
  useImperativeHandle(ref, () => ({ fitAll, focusSelected }))

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
        opacity: is3d ? 0.94 : 0.9,
        radiusUnits: 'pixels',
        getPosition: (point: ExplorerPoint) => (is3d ? [point.x, point.y, point.z] : [point.x, point.y]),
        getRadius: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return is3d ? 10 : 8.8
          if (neighborIds.has(point.article_id)) return is3d ? 7.6 : 6.8
          if (point.article_id === hoveredArticleId) return is3d ? 6.4 : 5.8
          if (point.analysis.is_outlier) return is3d ? 5.6 : 5.1
          return is3d ? 4.4 : 3.9
        },
        radiusScale: is3d ? 1 : 1.1,
        radiusMinPixels: 3,
        radiusMaxPixels: 18,
        lineWidthUnits: 'pixels',
        getLineWidth: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return 2.8
          if (neighborIds.has(point.article_id)) return 1.5
          return 0.8
        },
        getFillColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return [14, 165, 233, 255]
          if (neighborIds.has(point.article_id)) return [34, 197, 94, 235]
          if (point.article_id === hoveredArticleId) return [125, 211, 252, 235]
          const base = colorForPoint(point, colorMode)
          if (!hasSelection) return base
          if (point.analysis.is_outlier) return withAlpha(base, 150)
          return withAlpha(base, 78)
        },
        getLineColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return [255, 255, 255, 255]
          if (neighborIds.has(point.article_id)) return [236, 253, 245, 240]
          return hasSelection ? [226, 232, 240, 90] : [248, 250, 252, 190]
        },
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
          getLineColor: [selectedArticleId, neighborKey],
        },
      }),
    ]
  }, [points, viewMode, colorMode, selectedArticleId, hoveredArticleId, neighborIds, neighborKey, onHoverArticle, onSelectArticle, hasSelection])

  const activeViewState = viewState[viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']

  return (
    <div className="map-frame">
      {loading && (
        <div className="map-loading-overlay">
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            Loading semantic projection…
          </div>
        </div>
      )}

      <div className="map-canvas">
        <DeckGL
          views={
            viewMode === '3d'
              ? [new OrbitView({ id: 'semantic-3d' })]
              : [new OrthographicView({ id: 'semantic-2d' })]
          }
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
              [viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']:
                nextViewState as ViewStateMap[keyof ViewStateMap],
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
          {tooltip && <Tooltip tooltip={tooltip} />}
        </DeckGL>
      </div>
    </div>
  )
})

function Tooltip({ tooltip }: { tooltip: NonNullable<TooltipState> }) {
  return (
    <div className="tooltip-card" style={{ left: tooltip.x + 14, top: tooltip.y + 14 }}>
      <strong>{tooltip.point.title}</strong>
      <div className="tooltip-meta">{tooltip.point.source} · {tooltip.point.section || 'no section'}</div>
      <div className="tooltip-meta">{formatDate(tooltip.point.published_at)}</div>
      {tooltip.point.summary_snippet && (
        <p>{tooltip.point.summary_snippet}</p>
      )}
    </div>
  )
}
