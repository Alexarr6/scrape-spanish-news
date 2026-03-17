import { OrthographicView } from '@deck.gl/core'
import { ScatterplotLayer } from '@deck.gl/layers'
import DeckGL from '@deck.gl/react'
import { useMemo, useState } from 'react'
import { formatDate } from '../lib/format'
import type { ExplorerPoint, ExplorerPointsResponse } from '../lib/types'

type Props = {
  points: ExplorerPointsResponse | null
  loading: boolean
  error: string | null
  selectedArticleId: number | null
  hoveredArticleId: number | null
  neighborIds: Set<number>
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

function buildInitialViewState(points: ExplorerPointsResponse | null) {
  const bounds = points?.meta.bounds
  if (!bounds) {
    return { 'semantic-2d': { target: [0, 0, 0] as [number, number, number], zoom: 0 } }
  }
  const spanX = Math.max(Math.abs(bounds.max_x - bounds.min_x), 1)
  const spanY = Math.max(Math.abs(bounds.max_y - bounds.min_y), 1)
  const dominantSpan = Math.max(spanX, spanY)
  return {
    'semantic-2d': {
      target: [(bounds.min_x + bounds.max_x) / 2, (bounds.min_y + bounds.max_y) / 2, 0] as [number, number, number],
      zoom: Math.max(-2, Math.min(4, Math.log2(2 / dominantSpan))),
    },
  }
}

export function MapPanel({
  points,
  loading,
  error,
  selectedArticleId,
  hoveredArticleId,
  neighborIds,
  onHoverArticle,
  onSelectArticle,
}: Props) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)
  const neighborKey = Array.from(neighborIds).sort((a, b) => a - b).join(',')

  const layers = useMemo(() => {
    const items = points?.items ?? []
    return [
      new ScatterplotLayer<ExplorerPoint>({
        id: 'semantic-points',
        data: items,
        pickable: true,
        filled: true,
        stroked: true,
        radiusUnits: 'pixels',
        getPosition: (point: ExplorerPoint) => [point.x, point.y],
        getRadius: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return 11
          if (neighborIds.has(point.article_id)) return 8
          if (point.article_id === hoveredArticleId) return 7
          return 5
        },
        getLineWidth: (point: ExplorerPoint) => (point.article_id === selectedArticleId ? 3 : 1),
        getFillColor: (point: ExplorerPoint) => {
          if (point.article_id === selectedArticleId) return [250, 204, 21, 255]
          if (neighborIds.has(point.article_id)) return [34, 197, 94, 220]
          if (point.article_id === hoveredArticleId) return [96, 165, 250, 235]
          return [59, 130, 246, 190]
        },
        getLineColor: (point: ExplorerPoint) =>
          point.article_id === selectedArticleId ? [255, 255, 255, 255] : [15, 23, 42, 120],
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
          getRadius: [selectedArticleId, hoveredArticleId, neighborKey],
          getFillColor: [selectedArticleId, hoveredArticleId, neighborKey],
          getLineColor: [selectedArticleId],
        },
      }),
    ]
  }, [points, selectedArticleId, hoveredArticleId, neighborIds, neighborKey, onHoverArticle, onSelectArticle])

  return (
    <div className="map-canvas">
      <DeckGL
        views={[new OrthographicView({ id: 'semantic-2d' })]}
        controller={{ dragRotate: false, doubleClickZoom: true, touchRotate: false }}
        layers={layers}
        initialViewState={buildInitialViewState(points) as never}
      >
        <div className="map-overlay">
          <strong>2D semantic map</strong>
          <p>
            {loading
              ? 'Loading points…'
              : error
                ? error
                : `${points?.items.length ?? 0} visible points. Hover for context, click for the inspector.`}
          </p>
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
    </div>
  )
}
