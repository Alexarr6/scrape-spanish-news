import { OrthographicView } from '@deck.gl/core'
import DeckGL from '@deck.gl/react'
import type { ExplorerPointsResponse } from '../lib/types'

type Props = {
  points: ExplorerPointsResponse | null
}

function buildInitialViewState(points: ExplorerPointsResponse | null) {
  const bounds = points?.meta.bounds
  if (!bounds) {
    return {
      'semantic-2d': { target: [0, 0, 0] as [number, number, number], zoom: 0 },
    }
  }
  return {
    'semantic-2d': {
      target: [
        (bounds.min_x + bounds.max_x) / 2,
        (bounds.min_y + bounds.max_y) / 2,
        0,
      ] as [number, number, number],
      zoom: 0,
    },
  }
}

export function MapPanel({ points }: Props) {
  return (
    <div className="map-canvas">
      <DeckGL
        views={[new OrthographicView({ id: 'semantic-2d' })]}
        controller
        layers={[]}
        initialViewState={buildInitialViewState(points)}
      >
        <div className="map-overlay">
          <strong>deck.gl wired</strong>
          <p>{points?.items.length ?? 0} points available for the next phase.</p>
        </div>
      </DeckGL>
    </div>
  )
}
