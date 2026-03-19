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

export function StatusBar({ meta, activeFilterCount, selectedArticleId, viewMode, colorMode, onResetFilters }: Props) {
  const clusterCount = meta?.available_clusters.length ?? 0
  return (
    <div className="status-bar-content">
      <div>
        <strong>Explorer workspace</strong>
        <p className="muted">Spatial analysis mode: inspect neighborhoods, outliers, and cluster topology without pretending the map is the whole product.</p>
      </div>
      <div className="status-chip-row">
        <span className="status-chip emphasis">{meta ? `${meta.returned}/${meta.total} points` : 'Loading…'}</span>
        {meta ? <span className="status-chip">{meta.projection_set}</span> : null}
        <span className="status-chip">View {viewMode.toUpperCase()}</span>
        <span className="status-chip">Color {colorMode}</span>
        <span className="status-chip">{clusterCount} clusters</span>
        <span className="status-chip">{activeFilterCount} active filters</span>
        <span className="status-chip subtle">{selectedArticleId ? `Selected #${selectedArticleId}` : 'No selection'}</span>
        <a className="ghost-button" href={buildClusterBrowserHref()}>
          Back to Stories
        </a>
        <button className="ghost-button" type="button" onClick={onResetFilters}>
          Reset filters
        </button>
      </div>
    </div>
  )
}
