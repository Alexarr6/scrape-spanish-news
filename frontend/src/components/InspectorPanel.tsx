import { clampText, formatDate, formatSimilarity } from '../lib/format'
import { buildClusterBrowserHref } from '../lib/navigation'
import type { ExplorerArticleDetail, ExplorerPoint } from '../lib/types'

type Props = {
  selectedPoint: ExplorerPoint | null
  detail: ExplorerArticleDetail | null
  loading: boolean
  error: string | null
  onClearSelection: () => void
  onSelectArticle: (articleId: number) => void
}

export function InspectorPanel({ selectedPoint, detail, loading, error, onClearSelection, onSelectArticle }: Props) {
  if (!selectedPoint) {
    return (
      <div className="selection-stack">
        <div className="empty-state-card">
          <h2>No point selected</h2>
          <p className="muted">Click a point to inspect the article, cluster metadata, and nearest semantic neighbors.</p>
        </div>
        <div className="legend-card">
          <div className="eyebrow">Legend</div>
          <h3>What the map is telling you</h3>
          <ul className="legend-list">
            <li><span><span className="legend-dot" style={{ background: '#4f46e5' }} />Neutral color mode uses one sober baseline.</span></li>
            <li><span><span className="legend-dot" style={{ background: '#0ea5e9' }} />Selected points get stronger emphasis.</span></li>
            <li><span><span className="legend-dot" style={{ background: '#22c55e' }} />Neighbors show local semantic context.</span></li>
          </ul>
        </div>
      </div>
    )
  }

  if (loading) {
    return <div className="loading-card"><h2>Selection</h2><p className="muted">Loading article detail…</p></div>
  }

  if (error) {
    return <div className="state-card error-state"><h2>Selection failed</h2><p>{error}</p></div>
  }

  if (!detail) return null

  const summary = detail.semantic_summary
  return (
    <div className="panel-section inspector-content selection-stack">
      <div className="panel-header">
        <div>
          <h2>Selected article</h2>
          <p className="muted">Article evidence, cluster status, and local semantic context.</p>
        </div>
        <button className="ghost-button" type="button" onClick={onClearSelection}>Clear</button>
      </div>

      <div className="selection-card">
        <div className="eyebrow">{detail.article.source} · {detail.article.section || 'no section'}</div>
        <h3>{detail.article.title}</h3>
        <p className="muted">{formatDate(detail.article.published_at)}</p>
        <p>{clampText(detail.article.summary, detail.article.article_text_excerpt || 'No summary available.')}</p>
        <div className="action-row">
          <a className="ghost-button" href={detail.article.url} target="_blank" rel="noreferrer">Open article</a>
          <a className="ghost-button" href={buildClusterBrowserHref()}>Back to Stories</a>
        </div>
      </div>

      <div className="metric-grid">
        <Info label="Cluster" value={summary.cluster_id == null ? 'Unclustered' : String(summary.cluster_id)} />
        <Info label="Cluster size" value={String(summary.cluster_size ?? 0)} />
        <Info label="Outlier" value={summary.is_outlier ? 'Yes' : 'No'} />
        <Info label="Neighbors" value={String(summary.neighbor_count)} />
        <Info label="Source diversity" value={String(summary.source_neighbor_diversity ?? 0)} />
        <Info label="Local density" value={summary.local_density_distance?.toFixed(3) ?? '0.000'} />
      </div>

      <div className="helper-card">
        <div className="panel-header compact">
          <h3>Spatial coordinates</h3>
          <span className="muted">Projection context</span>
        </div>
        <p className="muted">Point {selectedPoint.x.toFixed(2)}, {selectedPoint.y.toFixed(2)}, {selectedPoint.z.toFixed(2)}</p>
        <p className="muted">Nearby sources: {summary.nearby_sources.join(', ') || '—'}</p>
      </div>

      <div>
        <div className="panel-header compact">
          <h3>Nearest neighbors</h3>
          <span className="muted">{detail.neighbors.length} linked articles</span>
        </div>
        {detail.neighbors.length === 0 ? (
          <p className="muted">No semantic neighbors returned for this article.</p>
        ) : (
          <ul className="neighbor-list">
            {detail.neighbors.map((neighbor) => (
              <li key={neighbor.article_id}>
                <button className="neighbor-button" type="button" onClick={() => onSelectArticle(neighbor.article_id)}>
                  <span>
                    <strong>{neighbor.title}</strong>
                    <span className="muted block-row">{neighbor.source} · {formatDate(neighbor.published_at)}</span>
                  </span>
                  <span className="status-chip">{formatSimilarity(neighbor.similarity)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-card">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
