import { formatCount } from '../lib/format'
import type { StoryClusterListItem, StoryClusterListResponse } from '../lib/types'

type Props = {
  data: StoryClusterListResponse | null
  activeFilterCount: number
  selectedCluster: StoryClusterListItem | null
  selectedArticleId: number | null
  onResetFilters: () => void
}

export function ClusterStatusBar({
  data,
  activeFilterCount,
  selectedCluster,
  selectedArticleId,
  onResetFilters,
}: Props) {
  return (
    <div className="status-bar-content">
      <div>
        <strong>Story cluster browser</strong>
        <p className="muted">Browse the actual story groups first. The dot cloud can wait its turn.</p>
      </div>
      <div className="status-chip-row">
        <span className="status-chip">{data ? `${data.meta.offset + 1}-${data.meta.offset + data.items.length} / ${data.meta.total}` : 'Loading…'}</span>
        <span className="status-chip">{formatCount(selectedCluster?.article_count, 'articles')}</span>
        <span className="status-chip">{formatCount(selectedCluster?.source_count, 'sources')}</span>
        <span className="status-chip">{activeFilterCount} active filters</span>
        <span className="status-chip">{selectedArticleId ? `Article #${selectedArticleId}` : 'No article selected'}</span>
        <button className="ghost-button" type="button" onClick={onResetFilters}>
          Reset filters
        </button>
      </div>
    </div>
  )
}
