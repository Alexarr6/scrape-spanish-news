import type { ExplorerMeta } from '../lib/types'

type Props = {
  meta: ExplorerMeta | null
  activeFilterCount: number
  selectedArticleId: number | null
  onResetFilters: () => void
}

export function StatusBar({
  meta,
  activeFilterCount,
  selectedArticleId,
  onResetFilters,
}: Props) {
  return (
    <div className="status-bar-content">
      <div>
        <strong>Semantic Explorer</strong>
        <p className="muted">A proper 2D deck.gl shell, not a placeholder with delusions.</p>
      </div>
      <div className="status-chip-row">
        <span className="status-chip">{meta ? `${meta.returned}/${meta.total} points` : 'Loading…'}</span>
        {meta ? <span className="status-chip">{meta.projection_set}</span> : null}
        <span className="status-chip">{activeFilterCount} active filters</span>
        <span className="status-chip">{selectedArticleId ? `Selected #${selectedArticleId}` : 'No selection'}</span>
        <button className="ghost-button" type="button" onClick={onResetFilters}>
          Reset filters
        </button>
      </div>
    </div>
  )
}
