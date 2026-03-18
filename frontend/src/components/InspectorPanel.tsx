import { clampText, formatDate, formatSimilarity } from '../lib/format'
import type { ExplorerArticleDetail, ExplorerPoint } from '../lib/types'

type Props = {
  selectedPoint: ExplorerPoint | null
  detail: ExplorerArticleDetail | null
  loading: boolean
  error: string | null
  onClearSelection: () => void
  onSelectArticle: (articleId: number) => void
}

export function InspectorPanel({
  selectedPoint,
  detail,
  loading,
  error,
  onClearSelection,
  onSelectArticle,
}: Props) {
  if (!selectedPoint) {
    return (
      <div className="panel-section">
        <h2>Inspector</h2>
        <p>Select a point to inspect the article, its semantic summary, and nearby neighbors.</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="panel-section">
        <h2>Inspector</h2>
        <p>Loading article detail…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="panel-section">
        <h2>Inspector</h2>
        <p>{error}</p>
      </div>
    )
  }

  if (!detail) return null

  const summary = detail.semantic_summary
  return (
    <div className="panel-section inspector-content">
      <div className="panel-header">
        <h2>Inspector</h2>
        <button className="ghost-button" type="button" onClick={onClearSelection}>
          Clear
        </button>
      </div>
      <div className="article-card">
        <div className="eyebrow">{detail.article.source} · {detail.article.section || 'no section'}</div>
        <h3>{detail.article.title}</h3>
        <p className="muted">{formatDate(detail.article.published_at)}</p>
        <p>{clampText(detail.article.summary, detail.article.article_text_excerpt || 'No summary available.')}</p>
        <div className="action-row">
          <a className="ghost-button" href={detail.article.url} target="_blank" rel="noreferrer">
            Open article
          </a>
        </div>
      </div>

      <div className="info-grid">
        <Info label="Cluster" value={summary.cluster_id == null ? 'Unclustered' : String(summary.cluster_id)} />
        <Info label="Cluster size" value={String(summary.cluster_size ?? 0)} />
        <Info label="Outlier" value={summary.is_outlier ? 'Yes' : 'No'} />
        <Info label="Neighbors" value={String(summary.neighbor_count)} />
        <Info label="Source diversity" value={String(summary.source_neighbor_diversity ?? 0)} />
        <Info label="Point" value={`${selectedPoint.x.toFixed(2)}, ${selectedPoint.y.toFixed(2)}, ${selectedPoint.z.toFixed(2)}`} />
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
                <button
                  className="neighbor-button"
                  type="button"
                  onClick={() => onSelectArticle(neighbor.article_id)}
                >
                  <span>
                    <strong>{neighbor.title}</strong>
                    <span className="muted">{neighbor.source} · {formatDate(neighbor.published_at)}</span>
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
