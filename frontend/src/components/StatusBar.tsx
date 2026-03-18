import { buildClusterBrowserHref } from '../lib/navigation'
import type { ExplorerColorMode, ExplorerMeta, ExplorerViewMode } from '../lib/types'

type Props = {
  meta: ExplorerMeta | null
  activeFilterCount: number
  selectedArticleId: number | null
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  onResetFilters: () => void
}

export function StatusBar({
  meta,
  activeFilterCount,
  selectedArticleId,
  viewMode,
  colorMode,
  onResetFilters,
}: Props) {
  const clusterCount = meta?.available_clusters.length ?? 0
  return (
    <div className="status-bar-content">
      <div>
        <strong>Semantic Explorer</strong>
        <p className="muted">Dual-view deck.gl explorer with persisted semantic clustering. Finally less bluff, more signal.</p>
      </div>
      <div className="status-chip-row">
        <span className="status-chip">{meta ? `${meta.returned}/${meta.total} points` : 'Loading…'}</span>
        {meta ? <span className="status-chip">{meta.projection_set}</span> : null}
        <span className="status-chip">Mode: {viewMode.toUpperCase()}</span>
        <span className="status-chip">Color: {colorMode}</span>
        <span className="status-chip">Clusters: {clusterCount}</span>
        <span className="status-chip">{activeFilterCount} active filters</span>
        <span className="status-chip">{selectedArticleId ? `Selected #${selectedArticleId}` : 'No selection'}</span>
        <a className="ghost-button" href={buildClusterBrowserHref()}>
          Back to cluster browser
        </a>
        <button className="ghost-button" type="button" onClick={onResetFilters}>
          Reset filters
        </button>
      </div>
    </div>
  )
}
