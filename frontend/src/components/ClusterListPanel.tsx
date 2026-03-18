import { formatDate } from '../lib/format'
import type { StoryClusterListItem, StoryClusterListResponse } from '../lib/types'

type Props = {
  data: StoryClusterListResponse | null
  loading: boolean
  error: string | null
  selectedClusterId: number | null
  onSelectCluster: (clusterId: number) => void
  onNextPage: () => void
  onPreviousPage: () => void
}

export function ClusterListPanel({
  data,
  loading,
  error,
  selectedClusterId,
  onSelectCluster,
  onNextPage,
  onPreviousPage,
}: Props) {
  return (
    <div className="cluster-list-shell">
      <div className="cluster-list-header panel-header compact">
        <div>
          <h2>Story clusters</h2>
          <p className="muted">Pick a cluster, then compare the source members on the right.</p>
        </div>
        <div className="action-row">
          <button className="ghost-button" type="button" onClick={onPreviousPage} disabled={!data || data.meta.offset === 0}>
            Previous
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={onNextPage}
            disabled={!data || data.meta.offset + data.meta.limit >= data.meta.total}
          >
            Next
          </button>
        </div>
      </div>
      {loading && !data ? <div className="empty-state-inline">Loading clusters…</div> : null}
      {error ? <div className="empty-state-inline">{error}</div> : null}
      {!loading && !error && data?.items.length === 0 ? <div className="empty-state-inline">No clusters match the current filters.</div> : null}
      <div className="cluster-list">
        {(data?.items ?? []).map((cluster) => (
          <button
            key={cluster.id}
            type="button"
            className={selectedClusterId === cluster.id ? 'cluster-card active' : 'cluster-card'}
            onClick={() => onSelectCluster(cluster.id)}
          >
            <div className="panel-header compact">
              <span className="eyebrow">{cluster.cluster_type.replace(/_/g, ' ')}</span>
              <span className="status-chip">{cluster.article_count} articles · {cluster.source_count} sources</span>
            </div>
            <h3>{cluster.summary_headline}</h3>
            <p>{cluster.summary_text}</p>
            <div className="status-chip-row compact-row">
              {cluster.sources.map((source) => (
                <span key={source} className="status-chip">{source}</span>
              ))}
              {cluster.primary_tag ? <span className="status-chip">{cluster.primary_tag.display_name}</span> : null}
            </div>
            <div className="status-chip-row compact-row">
              {cluster.top_entities.slice(0, 3).map((entity) => (
                <span key={entity.slug} className="status-chip subtle">{entity.name}</span>
              ))}
            </div>
            <div className="muted small-row">
              {formatClusterWindow(cluster)}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function formatClusterWindow(cluster: StoryClusterListItem) {
  if (!cluster.first_article_published_at && !cluster.last_article_published_at) return 'No publication window'
  if (cluster.first_article_published_at === cluster.last_article_published_at) return formatDate(cluster.first_article_published_at ?? '')
  return `${formatDate(cluster.first_article_published_at ?? '')} → ${formatDate(cluster.last_article_published_at ?? '')}`
}
