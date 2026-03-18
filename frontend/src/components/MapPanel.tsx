import { OrbitView, OrthographicView } from '@deck.gl/core'
import { ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { useEffect, useMemo, useState } from 'react'
import { formatDate } from '../lib/format'
import type {
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
  onViewModeChange: (mode: ExplorerViewMode) => void
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

type ViewStateMap = {
  'semantic-2d': {
    target: [number, number, number]
    zoom: number
  }
  'semantic-3d': {
    target: [number, number, number]
    zoom: number
    rotationOrbit: number
    rotationX: number
  }
}

function build2dViewState(bounds: ExplorerProjectionBounds | null): ViewStateMap['semantic-2d'] {
  if (!bounds) {
    return { target: [0, 0, 0], zoom: 0 }
  }
  const spanX = Math.max(bounds.max_x - bounds.min_x, 1)
  const spanY = Math.max(bounds.max_y - bounds.min_y, 1)
  const dominantSpan = Math.max(spanX, spanY)
  return {
    target: [(bounds.min_x + bounds.max_x) / 2, (bounds.min_y + bounds.max_y) / 2, 0],
    zoom: Math.max(-1.5, Math.min(7, Math.log2(2.6 / dominantSpan))),
  }
}

function build3dViewState(bounds: ExplorerProjectionBounds | null): ViewStateMap['semantic-3d'] {
  if (!bounds) {
    return { target: [0, 0, 0], zoom: 0, rotationOrbit: 35, rotationX: 35 }
  }
  const spanX = Math.max(bounds.max_x - bounds.min_x, 1)
  const spanY = Math.max(bounds.max_y - bounds.min_y, 1)
  const spanZ = Math.max(bounds.max_z - bounds.min_z, 1)
  const dominantSpan = Math.max(spanX, spanY, spanZ)
  return {
    target: [
      (bounds.min_x + bounds.max_x) / 2,
      (bounds.min_y + bounds.max_y) / 2,
      (bounds.min_z + bounds.max_z) / 2,
    ],
    zoom: Math.max(-1.2, Math.min(6, Math.log2(2.1 / dominantSpan))),
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

export function MapPanel({
  points,
  loading,
  error,
  selectedArticleId,
  hoveredArticleId,
  neighborIds,
  viewMode,
  onViewModeChange,
  onHoverArticle,
  onSelectArticle,
}: Props) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)
  const [viewState, setViewState] = useState<ViewStateMap>(() => buildInitialViewState(points))
  const neighborKey = Array.from(neighborIds).sort((a, b) => a - b).join(',')
  const bounds = points?.meta.bounds ?? null

  useEffect(() => {
    setViewState(buildInitialViewState(points))
  }, [bounds?.min_x, bounds?.max_x, bounds?.min_y, bounds?.max_y, bounds?.min_z, bounds?.max_z, points?.meta.projection_set])

  const layers = useMemo(() => {
    const items = points?.items ?? []
    const is3d = viewMode === '3d'
    return [
      new ScatterplotLayer<ExplorerPoint>({
        id: `semantic-points-${viewMode}`,
        data: items,
        pickable: true,
        filled: true,
        stroked: true,
        opacity: is3d ? 0.88 : 0.78,
        radiusUnits: 'pixels',
        getPosition: (point: ExplorerPoint) => (is3d ? [point.x, point.y, point.z] : [point.x, point.y]),
        getRadius: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return is3d ? 9 : 8
          if (neighborIds.has(point.article_id)) return is3d ? 7 : 6
          if (point.article_id === hoveredArticleId) return is3d ? 6 : 5.5
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
          return is3d ? [96, 165, 250, 205] : [59, 130, 246, 165]
        },
        getLineColor: (point: ExplorerPoint) =>
          point.article_id === selectedArticleId ? [255, 255, 255, 255] : [15, 23, 42, 150],
        onHover: (info: PickingInfoLike) => {
          const point = info.object
          onHoverArticle(point?.article_id ?? null)
          if (point && info.x != null && info.y != null) {
            setTooltip({ x: info.x, y: info.y, point })
          } else {
            setTooltip(null)
          }
        },
        onClick: (info: PickingInfoLike) => {
          const point = info.object
          onSelectArticle(point?.article_id ?? null)
        },
        updateTriggers: {
          getPosition: [viewMode],
          getRadius: [viewMode, selectedArticleId, hoveredArticleId, neighborKey],
          getFillColor: [viewMode, selectedArticleId, hoveredArticleId, neighborKey],
          getLineColor: [selectedArticleId],
        },
      }),
    ]
  }, [points, viewMode, selectedArticleId, hoveredArticleId, neighborIds, neighborKey, onHoverArticle, onSelectArticle])

  const resetView = () => {
    setViewState(buildInitialViewState(points))
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
          setViewState((current) => ({
            ...current,
            [viewMode === '3d' ? 'semantic-3d' : 'semantic-2d']: nextViewState as ViewStateMap[keyof ViewStateMap],
          }))
        }}
      >
        <div className="map-overlay map-overlay-stack">
          <div className="panel-header compact">
            <div>
              <strong>{viewMode === '3d' ? '3D semantic explorer' : '2D semantic explorer'}</strong>
              <p>
                {loading
                  ? 'Loading projection…'
                  : error
                    ? error
                    : `${points?.items.length ?? 0} visible points from ${points?.meta.projection_set ?? 'unknown set'}.`}
              </p>
            </div>
            <div className="segmented-control" role="tablist" aria-label="Explorer view mode">
              <button className={viewMode === '2d' ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onViewModeChange('2d')}>
                2D
              </button>
              <button className={viewMode === '3d' ? 'segmented-button active' : 'segmented-button'} type="button" onClick={() => onViewModeChange('3d')}>
                3D
              </button>
            </div>
          </div>
          <div className="hint-row">
            <span>{viewMode === '3d' ? 'Drag to orbit, scroll to zoom, right-drag to pan.' : 'Drag to pan, scroll to zoom, click for the inspector.'}</span>
            <button className="ghost-button" type="button" onClick={resetView}>
              Reset view
            </button>
          </div>
        </div>
        {!loading && !error && (points?.items.length ?? 0) === 0 ? (
          <div className="empty-state">No points match the current filters.</div>
        ) : null}
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
      <div className="muted point-coords">
        x {tooltip.point.x.toFixed(2)} · y {tooltip.point.y.toFixed(2)} · z {tooltip.point.z.toFixed(2)}
      </div>
    </div>
  )
}
