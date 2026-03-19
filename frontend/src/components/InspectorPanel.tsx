import { useEffect, useMemo, useState } from 'react'
import { clampText, formatDate, formatSimilarity } from '../lib/format'
import { buildClusterBrowserHref } from '../lib/navigation'
import type { ExplorerArticleDetail, ExplorerClusterSummary, ExplorerColorMode, ExplorerPoint, ExplorerViewMode } from '../lib/types'

type InspectorTab = 'guide' | 'article' | 'cluster' | 'legend'

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

export function InspectorPanel({
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
  const [activeTab, setActiveTab] = useState<InspectorTab>('guide')

  useEffect(() => {
    setActiveTab(selectedPoint ? 'article' : 'guide')
  }, [selectedPoint?.article_id])

  const selectedCluster = useMemo(() => {
    const clusterId = detail?.semantic_summary.cluster_id ?? selectedPoint?.analysis.cluster_id ?? null
    if (clusterId == null) return null
    return clusterSummaries.find((cluster) => cluster.cluster_id === clusterId) ?? null
  }, [clusterSummaries, detail?.semantic_summary.cluster_id, selectedPoint?.analysis.cluster_id])

  if (!selectedPoint) {
    return (
      <div className="selection-stack explorer-context-panel">
        <TabBar activeTab={activeTab} onChange={setActiveTab} tabs={[{ key: 'guide', label: 'Guide' }, { key: 'legend', label: 'Legend' }]} />
        {activeTab === 'legend' ? <LegendTab viewMode={viewMode} colorMode={colorMode} /> : <GuideTab viewMode={viewMode} />}
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
    <div className="panel-section inspector-content selection-stack explorer-context-panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Context panel</div>
          <h2>Selection</h2>
          <p className="muted">Switch between article evidence, cluster context, and a persistent legend.</p>
        </div>
        <button className="ghost-button" type="button" onClick={onClearSelection}>Clear</button>
      </div>

      <TabBar
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[
          { key: 'article', label: 'Article' },
          { key: 'cluster', label: 'Cluster' },
          { key: 'legend', label: 'Legend' },
        ]}
      />

      {activeTab === 'cluster' ? (
        <ClusterTab summary={summary} selectedCluster={selectedCluster} />
      ) : activeTab === 'legend' ? (
        <LegendTab viewMode={viewMode} colorMode={colorMode} />
      ) : (
        <ArticleTab detail={detail} selectedPoint={selectedPoint} onSelectArticle={onSelectArticle} />
      )}
    </div>
  )
}

function TabBar({
  activeTab,
  onChange,
  tabs,
}: {
  activeTab: InspectorTab
  onChange: (tab: InspectorTab) => void
  tabs: Array<{ key: InspectorTab; label: string }>
}) {
  return (
    <div className="segmented-control context-tab-bar" role="tablist" aria-label="Explorer context tabs">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          className={activeTab === tab.key ? 'segmented-button active' : 'segmented-button'}
          type="button"
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}

function GuideTab({ viewMode }: { viewMode: ExplorerViewMode }) {
  return (
    <>
      <div className="legend-card">
        <div className="eyebrow">Guide</div>
        <h3>How to read this workspace</h3>
        <p>Explorer is for semantic shape, not coverage comparison. Start in Neutral, scan the layout, then click into the article neighborhoods that actually look interesting.</p>
      </div>
      <div className="helper-card">
        <strong>Current best use of {viewMode.toUpperCase()}</strong>
        <p>{viewMode === '3d' ? 'Use 3D to inspect whether clusters are actually separated or just look separate in a flat view.' : 'Use 2D to scan quickly, compare cluster spread, and decide what deserves a closer look.'}</p>
      </div>
      <div className="empty-state-card">
        <h2>No point selected</h2>
        <p className="muted">Click a point to inspect the article, its cluster status, and nearest semantic neighbors. If what you need is story comparison, jump back to Stories.</p>
      </div>
    </>
  )
}

function LegendTab({ viewMode, colorMode }: { viewMode: ExplorerViewMode; colorMode: ExplorerColorMode }) {
  return (
    <>
      <div className="legend-card">
        <div className="eyebrow">Legend</div>
        <h3>Point emphasis</h3>
        <ul className="legend-list">
          <li><span><span className="legend-dot" style={{ background: '#4f46e5' }} />Neutral is the sober baseline for reading shape and density.</span></li>
          <li><span><span className="legend-dot" style={{ background: '#0ea5e9' }} />Selected points are the active article under inspection.</span></li>
          <li><span><span className="legend-dot" style={{ background: '#22c55e' }} />Neighbors show the local semantic neighborhood.</span></li>
          <li><span><span className="legend-dot" style={{ background: '#ef4444' }} />Outliers are semantically oddballs worth sanity-checking.</span></li>
        </ul>
      </div>
      <div className="helper-card">
        <strong>Current mode</strong>
        <p><strong>{viewMode.toUpperCase()}</strong> is active. {viewMode === '3d' ? 'This is the better mode for overlap, thickness, and fringe inspection.' : 'This is the faster mode for an overall layout scan.'}</p>
        <p><strong>Color lens:</strong> {colorMode === 'source' ? 'source, for outlet grouping.' : colorMode === 'cluster' ? 'cluster, for grouping coherence.' : 'neutral, for structure-first reading.'}</p>
      </div>
      <div className="helper-card">
        <strong>Camera controls</strong>
        <p><strong>Fit all</strong> resets the visible subset. <strong>Focus selected</strong> tightens around the selected article plus its nearby semantic neighborhood.</p>
      </div>
    </>
  )
}

function ClusterTab({ summary, selectedCluster }: { summary: ExplorerArticleDetail['semantic_summary']; selectedCluster: ExplorerClusterSummary | null }) {
  const topSources = selectedCluster ? Object.entries(selectedCluster.top_sources).sort((a, b) => b[1] - a[1]).slice(0, 3) : []
  return (
    <>
      <div className="selection-card">
        <div className="eyebrow">Cluster context</div>
        <h3>{summary.cluster_id == null ? 'Unclustered or outlier article' : `Cluster ${summary.cluster_id}`}</h3>
        <p className="muted">
          {summary.cluster_id == null
            ? summary.is_outlier
              ? 'This article sits outside the main grouped structure.'
              : 'This article is currently outside a stable cluster grouping.'
            : `This article sits inside a cluster with ${summary.cluster_size ?? 0} articles.`}
        </p>
      </div>

      <div className="metric-grid">
        <Info label="Cluster size" value={String(summary.cluster_size ?? 0)} />
        <Info label="Outlier" value={summary.is_outlier ? 'Yes' : 'No'} />
        <Info label="Neighbor count" value={String(summary.neighbor_count)} />
        <Info label="Source diversity" value={String(summary.source_neighbor_diversity ?? 0)} />
      </div>

      <div className="helper-card">
        <div className="panel-header compact">
          <h3>Interpretation</h3>
          <span className="muted">Analytical read</span>
        </div>
        <p className="muted">{summary.is_outlier ? 'Treat this as fringe coverage or a semantically unusual angle. In 3D, check whether it floats well outside the main cloud or merely sits on the cluster edge.' : 'Use local density and neighbors together: a tighter neighborhood usually means the article belongs to a more coherent semantic pocket.'}</p>
      </div>

      <div className="helper-card">
        <div className="panel-header compact">
          <h3>Cluster composition</h3>
          <span className="muted">Derived from current dataset</span>
        </div>
        <p className="muted">Top nearby sources: {summary.nearby_sources.join(', ') || '—'}</p>
        {topSources.length > 0 ? (
          <div className="status-chip-row compact-row">
            {topSources.map(([source, count]) => (
              <span key={source} className="status-chip subtle">{source} · {count}</span>
            ))}
          </div>
        ) : (
          <p className="muted">No cluster-level source breakdown available for this selection.</p>
        )}
      </div>
    </>
  )
}

function ArticleTab({
  detail,
  selectedPoint,
  onSelectArticle,
}: {
  detail: ExplorerArticleDetail
  selectedPoint: ExplorerPoint
  onSelectArticle: (articleId: number) => void
}) {
  const summary = detail.semantic_summary
  return (
    <>
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
          <h3>Reading the selection</h3>
          <span className="muted">Quick interpretation</span>
        </div>
        <p className="muted">Use neighbors to judge whether this article sits inside a coherent pocket or near a semantic edge. Higher density usually means it belongs to a tighter local theme.</p>
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
    </>
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
