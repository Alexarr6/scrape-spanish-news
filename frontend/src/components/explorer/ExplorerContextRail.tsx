import { useMemo } from 'react'
import { clampText, formatDate, formatSimilarity } from '../../lib/format'
import { buildStoriesHref } from '../../lib/navigation'
import type {
  ExplorerArticleDetail,
  ExplorerClusterSummary,
  ExplorerColorMode,
  ExplorerPoint,
  ExplorerViewMode,
} from '../../lib/types'
import { SectionDivider } from '../layout/SectionDivider'
import { LoadingState } from '../system/LoadingState'

type Props = {
  selectedPoint: ExplorerPoint | null
  detail: ExplorerArticleDetail | null
  loading: boolean
  error: string | null
  clusterSummaries: ExplorerClusterSummary[]
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  onClearSelection: () => void
  onSelectArticle: (articleId: number) => void
}

export function ExplorerContextRail({
  selectedPoint,
  detail,
  loading,
  error,
  clusterSummaries,
  viewMode,
  colorMode,
  onClearSelection,
  onSelectArticle,
}: Props) {
  const selectedCluster = useMemo(() => {
    const clusterId =
      detail?.semantic_summary.cluster_id ?? selectedPoint?.analysis.cluster_id ?? null
    if (clusterId == null) return null
    return clusterSummaries.find((c) => c.cluster_id === clusterId) ?? null
  }, [clusterSummaries, detail?.semantic_summary.cluster_id, selectedPoint?.analysis.cluster_id])

  // No selection state
  if (!selectedPoint) {
    return (
      <div className="context-rail">
        <p className="context-guide-text">
          Click any point to inspect an article and its semantic neighborhood.
        </p>

        <SectionDivider label="Legend" />
        <ColorLegend colorMode={colorMode} />

        <SectionDivider label="Dataset" />
        <DatasetSummary clusterSummaries={clusterSummaries} viewMode={viewMode} />
      </div>
    )
  }

  const storiesHref = buildStoriesHref(
    detail?.semantic_summary.cluster_id ?? selectedPoint.analysis.cluster_id ?? null,
  )

  return (
    <div className="context-rail">
      {/* Header with clear button */}
      <div className="context-rail-header">
        <button className="btn-text" type="button" onClick={onClearSelection}>
          ← Clear
        </button>
      </div>

      {/* Article section */}
      {loading && !detail ? (
        <LoadingState label="Loading article…" hint="Fetching detail and neighbors." centered={false} />
      ) : error ? (
        <div>
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-danger)' }}>
            Failed to load article detail
          </span>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
            {error}
          </p>
        </div>
      ) : detail ? (
        <div className="context-article">
          <span className="context-article-eyebrow">
            {detail.article.source}
            {detail.article.section ? ` · ${detail.article.section}` : ''}
          </span>
          <h3 className="context-article-title">{detail.article.title}</h3>
          <span className="context-article-date">{formatDate(detail.article.published_at)}</span>
          <p className="context-article-summary">
            {clampText(detail.article.summary, detail.article.article_text_excerpt || 'No summary available.')}
          </p>
          <div className="context-article-actions">
            <a
              href={detail.article.url}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost"
            >
              Open article ↗
            </a>
            {storiesHref && (
              <a href={storiesHref} className="btn-ghost">
                Open in Stories →
              </a>
            )}
          </div>
        </div>
      ) : (
        // Point selected but detail not loaded yet — show title from point data
        <div className="context-article">
          <span className="context-article-eyebrow">
            {selectedPoint.source}
            {selectedPoint.section ? ` · ${selectedPoint.section}` : ''}
          </span>
          <h3 className="context-article-title">{selectedPoint.title}</h3>
          <span className="context-article-date">{formatDate(selectedPoint.published_at)}</span>
          {selectedPoint.summary_snippet && (
            <p className="context-article-summary">{selectedPoint.summary_snippet}</p>
          )}
        </div>
      )}

      {/* Cluster context section */}
      {detail && (
        <>
          <SectionDivider label="Cluster context" />
          <ClusterContextSection
            summary={detail.semantic_summary}
            selectedCluster={selectedCluster}
          />
        </>
      )}

      {/* Semantic neighborhood section */}
      {detail && detail.neighbors.length > 0 && (
        <>
          <SectionDivider label="Semantic neighborhood" />
          <div className="context-neighborhood">
            <ul className="neighbor-list">
              {detail.neighbors.slice(0, 5).map((neighbor) => (
                <li key={neighbor.article_id}>
                  <button
                    className="neighbor-button"
                    type="button"
                    onClick={() => onSelectArticle(neighbor.article_id)}
                  >
                    <div>
                      <div className="neighbor-title">{neighbor.title}</div>
                      <div className="neighbor-meta">
                        {neighbor.source} · {formatDate(neighbor.published_at)}
                      </div>
                    </div>
                    <span className="badge muted">{formatSimilarity(neighbor.similarity)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

/* ─── Color legend ──────────────────────────────────────────────────────── */
function ColorLegend({ colorMode }: { colorMode: ExplorerColorMode }) {
  return (
    <ul className="legend-list">
      <li className="legend-item">
        <span className="legend-dot" style={{ background: '#0ea5e9' }} />
        <span>Selected article</span>
      </li>
      <li className="legend-item">
        <span className="legend-dot" style={{ background: '#22c55e' }} />
        <span>Semantic neighbors</span>
      </li>
      <li className="legend-item">
        <span className="legend-dot" style={{ background: '#ef4444' }} />
        <span>Outliers</span>
      </li>
      <li className="legend-item">
        <span className="legend-dot" style={{ background: '#4338ca' }} />
        <span>
          {colorMode === 'source'
            ? 'Color by source outlet'
            : colorMode === 'cluster'
              ? 'Color by cluster assignment'
              : 'Neutral (structural baseline)'}
        </span>
      </li>
    </ul>
  )
}

/* ─── Dataset summary ───────────────────────────────────────────────────── */
function DatasetSummary({
  clusterSummaries,
  viewMode,
}: {
  clusterSummaries: ExplorerClusterSummary[]
  viewMode: ExplorerViewMode
}) {
  const totalArticles = clusterSummaries.reduce((sum, c) => sum + c.size, 0)
  const allSources = new Set(clusterSummaries.flatMap((c) => Object.keys(c.top_sources)))

  return (
    <div className="context-dataset">
      <div className="context-dataset-row">
        <strong>{clusterSummaries.length}</strong> clusters · <strong>{allSources.size}</strong> sources
      </div>
      {totalArticles > 0 && (
        <div className="context-dataset-row">
          <strong>{totalArticles}</strong> clustered articles
        </div>
      )}
      <div className="context-dataset-row" style={{ color: 'var(--color-text-muted)' }}>
        {viewMode === '3d'
          ? '3D: better for overlap and cluster depth inspection.'
          : '2D: faster for layout scanning and broad comparison.'}
      </div>
    </div>
  )
}

/* ─── Cluster context ───────────────────────────────────────────────────── */
function ClusterContextSection({
  summary,
  selectedCluster,
}: {
  summary: ExplorerArticleDetail['semantic_summary']
  selectedCluster: ExplorerClusterSummary | null
}) {
  const topSources = selectedCluster
    ? Object.entries(selectedCluster.top_sources)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4)
    : []

  return (
    <div className="context-cluster">
      <div className="context-cluster-headline">
        {summary.cluster_id == null ? 'Unclustered / outlier' : `Cluster ${summary.cluster_id}`}
      </div>
      <p className="context-cluster-meta">
        {summary.cluster_id == null
          ? summary.is_outlier
            ? 'This article sits outside the main grouped structure.'
            : 'This article is currently outside a stable cluster grouping.'
          : `${summary.cluster_size ?? 0} articles in this cluster.`}
      </p>
      <div className="context-metrics">
        <MetricItem label="Outlier" value={summary.is_outlier ? 'Yes' : 'No'} />
        <MetricItem label="Neighbors" value={String(summary.neighbor_count)} />
        <MetricItem label="Src diversity" value={String(summary.source_neighbor_diversity ?? 0)} />
        {summary.local_density_distance != null && (
          <MetricItem label="Density dist." value={summary.local_density_distance.toFixed(3)} />
        )}
      </div>
      {topSources.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
          {topSources.map(([source, count]) => (
            <span key={source} className="badge muted">
              {source} · {count}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-item">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  )
}
