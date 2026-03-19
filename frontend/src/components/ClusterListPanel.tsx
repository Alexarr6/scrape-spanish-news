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

export function ClusterListPanel({ data, loading, error, selectedClusterId, onSelectCluster, onNextPage, onPreviousPage }: Props) {
  const total = data?.meta.total ?? 0
  const start = total === 0 || !data ? 0 : data.meta.offset + 1
  const end = total === 0 || !data ? 0 : data.meta.offset + data.items.length

  return (
    <div className="cluster-list-shell">
      <div className="story-hero">
        <div className="panel-header compact">
          <div>
            <div className="eyebrow">Stories / Clusters</div>
            <h2>Track the event before you argue about the framing.</h2>
            <p className="muted">A proper story workspace: filters on the left, ranked cluster stream in the middle, inspection on the right.</p>
          </div>
          <div className="story-stats">
            <span className="summary-pill emphasis">{start}-{end} shown</span>
            <span className="summary-pill">{total} total clusters</span>
          </div>
        </div>
      </div>

      <div className="cluster-results-header">
        <div className="panel-header compact">
          <div>
            <h3>Cluster results</h3>
            <p className="muted">Select a story cluster to inspect member coverage and article detail.</p>
          </div>
          <div className="action-row">
            <button className="ghost-button" type="button" onClick={onPreviousPage} disabled={!data || data.meta.offset === 0}>
              Previous page
            </button>
            <button className="ghost-button" type="button" onClick={onNextPage} disabled={!data || data.meta.offset + data.meta.limit >= data.meta.total}>
              Next page
            </button>
          </div>
        </div>
      </div>

      {loading && !data ? (
        <div className="loading-card">
          <strong>Loading story clusters…</strong>
          <p className="muted">Pulling grouped coverage and story summaries from the API.</p>
        </div>
      ) : null}
      {error ? (
        <div className="state-card error-state">
          <strong>Cluster list failed to load</strong>
          <p>{error}</p>
          <p className="muted">Try again or widen the current filters if the dataset window is too narrow.</p>
        </div>
      ) : null}
      {!loading && !error && data?.items.length === 0 ? (
        <div className="empty-state-card">
          <strong>No story clusters match the current filters</strong>
          <p className="muted">Clear one of the filters or widen the date window. Right now you’ve filtered reality into a void.</p>
        </div>
      ) : null}

      <div className="cluster-list">
        {(data?.items ?? []).map((cluster) => (
          <button key={cluster.id} type="button" className={selectedClusterId === cluster.id ? 'cluster-card active' : 'cluster-card'} onClick={() => onSelectCluster(cluster.id)}>
            <div className="result-meta">
              <span className="eyebrow">{cluster.cluster_type.replace(/_/g, ' ')}</span>
              <div className="status-chip-row compact-row">
                <span className="status-chip emphasis">{cluster.article_count} articles</span>
                <span className="status-chip">{cluster.source_count} sources</span>
              </div>
            </div>
            <div className="cluster-card-title">{cluster.summary_headline}</div>
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
            <div className="small-row muted">{formatClusterWindow(cluster)}</div>
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
