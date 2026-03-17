import type { ExplorerPointsResponse } from '../lib/types'

type Props = {
  points: ExplorerPointsResponse | null
  error: string | null
  loading: boolean
}

export function InspectorPanel({ points, error, loading }: Props) {
  if (loading) {
    return <p>Loading explorer foundation…</p>
  }
  if (error) {
    return <p>{error}</p>
  }
  return (
    <div>
      <h2>Inspector placeholder</h2>
      <p>Phase 1 will turn this into the real article inspector.</p>
      <p>Current dataset payload: {points?.items.length ?? 0} points loaded.</p>
    </div>
  )
}
