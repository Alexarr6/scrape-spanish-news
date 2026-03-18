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
  const total = data?.meta.total ?? 0
  const start = total === 0 || !data ? 0 : data.meta.offset + 1
  const end = total === 0 || !data ? 0 : data.meta.offset + data.items.length

  return (
    <div className="cluster-list-shell">
      <div className="cluster-hero">
        <div>
          <div className="eyebrow">Story cluster browser</div>
          <h2>Track the shared story before you inspect the takes.</h2>
          <p className="muted">Cluster-first flow keeps the product honest: pick the story, compare the source coverage, then dive into individual articles.</p>
        </div>
        <div className="status-chip-row compact-row">
          <span className="status-chip">{start}-{end} shown</span>
          <span className="status-chip">{total} total clusters</span>
        </div>
      </div>

      <div className="cluster-list-header panel-header compact">
        <div>
          <h3>Story clusters</h3>
          <p className="muted">Pick a cluster, then compare the source members on the right.</p>
        </div>
        <div className="action-row">
          <button className="ghost-button" type="button" onClick={onPreviousPage} disabled={!data || data.meta.offset === 0}>
            Previous page
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={onNextPage}
            disabled={!data || data.meta.offset + data.meta.limit >= data.meta.total}
          >
            Next page
          </button>
        </div>
      </div>
      {loading && !data ? (
        <div className="empty-state-inline empty-state-card">
          <strong>Loading story clusters…</strong>
          <p className="muted">Pulling the latest grouped coverage from the API.</p>
        </div>
      ) : null}
      {error ? (
        <div className="empty-state-inline empty-state-card error-state">
          <strong>Cluster list failed to load</strong>
          <p>{error}</p>
        </div>
      ) : null}
      {!loading && !error && data?.items.length === 0 ? (
        <div className="empty-state-inline empty-state-card">
          <strong>No clusters match the current filters</strong>
          <p className="muted">Try clearing one of the filters or widening the date window.</p>
        </div>
      ) : null}
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
              {cluster.primary_tag ? <span className="status-chip subtle">{cluster.primary_tag.display_name}</span> : null}
            </div>
            <div className="status-chip-row compact-row">
              {cluster.top_entities.slice(0, 4).map((entity) => (
                <span key={entity.slug} className="status-chip subtle">{entity.name}</span>
              ))}
            </div>
            <div className="muted small-row">{formatClusterWindow(cluster)}</div>
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
