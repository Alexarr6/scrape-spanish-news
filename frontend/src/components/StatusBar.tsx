import type { ExplorerMeta, ExplorerViewMode } from '../lib/types'

type Props = {
  meta: ExplorerMeta | null
  activeFilterCount: number
  selectedArticleId: number | null
  viewMode: ExplorerViewMode
  onResetFilters: () => void
}

export function StatusBar({
  meta,
  activeFilterCount,
  selectedArticleId,
  viewMode,
  onResetFilters,
}: Props) {
  return (
    <div className="status-bar-content">
      <div>
        <strong>Semantic Explorer</strong>
        <p className="muted">Dual-view deck.gl explorer: quick read in 2D, real depth in 3D, no circus.</p>
      </div>
      <div className="status-chip-row">
        <span className="status-chip">{meta ? `${meta.returned}/${meta.total} points` : 'Loading…'}</span>
        {meta ? <span className="status-chip">{meta.projection_set}</span> : null}
        <span className="status-chip">Mode: {viewMode.toUpperCase()}</span>
        <span className="status-chip">{activeFilterCount} active filters</span>
        <span className="status-chip">{selectedArticleId ? `Selected #${selectedArticleId}` : 'No selection'}</span>
        <button className="ghost-button" type="button" onClick={onResetFilters}>
          Reset filters
        </button>
      </div>
    </div>
  )
}
