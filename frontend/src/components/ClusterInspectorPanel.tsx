import { clampText, formatDate, formatSimilarity } from '../lib/format'
import { buildSemanticExplorerHref } from '../lib/navigation'
import type { ExplorerArticleDetail, StoryClusterDetail, StoryClusterMemberItem } from '../lib/types'

type Props = {
  detail: StoryClusterDetail | null
  article: ExplorerArticleDetail | null
  loading: boolean
  articleLoading: boolean
  error: string | null
  articleError: string | null
  selectedArticleId: number | null
  onSelectArticle: (articleId: number) => void
}

export function ClusterInspectorPanel({ detail, article, loading, articleLoading, error, articleError, selectedArticleId, onSelectArticle }: Props) {
  if (loading && !detail) {
    return <div className="loading-card"><h2>Story detail</h2><p className="muted">Loading story coverage and member articles…</p></div>
  }

  if (error) {
    return <div className="state-card error-state"><h2>Story detail unavailable</h2><p>{error}</p></div>
  }

  if (!detail) {
    return <div className="empty-state-card"><h2>Story detail</h2><p className="muted">Select a cluster to inspect the source mix, browse its member articles, and compare coverage properly.</p></div>
  }

  const groupedMembers = groupMembersBySource(detail.members)

  return (
    <div className="panel-section inspector-content">
      <div className="selected-story-banner">
        <div className="eyebrow">{detail.cluster.cluster_type.replace(/_/g, ' ')} · {detail.cluster.status}</div>
        <h2>{detail.cluster.summary_headline}</h2>
        <p>{detail.cluster.summary_text}</p>
        <div className="status-chip-row compact-row">
          <span className="status-chip emphasis">{detail.cluster.article_count} articles</span>
          <span className="status-chip">{detail.cluster.source_count} sources</span>
          {detail.cluster.primary_tag ? <span className="status-chip subtle">{detail.cluster.primary_tag.display_name}</span> : null}
        </div>
        <div className="inline-actions">
          <a className="ghost-button" href={buildSemanticExplorerHref({ detail, articleId: selectedArticleId })}>Open story in Explorer</a>
        </div>
        {detail.cluster.top_entities.length > 0 ? (
          <div className="status-chip-row compact-row">
            {detail.cluster.top_entities.map((entity) => (
              <span key={entity.slug} className="status-chip subtle">{entity.name}</span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="panel-header compact">
        <div>
          <h3>Coverage by source</h3>
          <p className="muted">Grouped by outlet so the comparison is actually legible.</p>
        </div>
      </div>
      <div className="source-groups">
        {groupedMembers.map(([source, members]) => (
          <section key={source} className="source-group">
            <div className="panel-header compact">
              <h3>{source}</h3>
              <span className="status-chip">{members.length} article{members.length === 1 ? '' : 's'}</span>
            </div>
            <div className="member-list">
              {members.map((member) => (
                <button key={member.article_id} type="button" className={selectedArticleId === member.article_id ? 'member-card active' : 'member-card'} onClick={() => onSelectArticle(member.article_id)}>
                  <div className="panel-header compact">
                    <strong>{member.title}</strong>
                    <span className="status-chip">{formatSimilarity(member.membership_score)}</span>
                  </div>
                  <div className="muted small-row">{formatDate(member.published_at ?? '')} · {member.section || 'no section'}</div>
                  <p>{clampText(member.summary, 'No summary available.')}</p>
                  <div className="status-chip-row compact-row">
                    {member.tags.slice(0, 2).map((tag) => <span key={tag.tag_code} className="status-chip subtle">{tag.display_name}</span>)}
                    {member.entities.slice(0, 3).map((entity) => <span key={entity.slug} className="status-chip subtle">{entity.name}</span>)}
                  </div>
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>

      <div className="panel-header compact">
        <div>
          <h3>Selected article</h3>
          <p className="muted">Inspect one member article and its nearby semantic context.</p>
        </div>
      </div>
      {articleLoading && !article ? <div className="loading-card"><strong>Loading article detail…</strong></div> : null}
      {articleError ? <div className="state-card error-state"><strong>Article detail failed</strong><p>{articleError}</p></div> : null}
      {article ? (
        <div className="article-card detail-article-card">
          <div className="eyebrow">{article.article.source} · {article.article.section || 'no section'}</div>
          <h3>{article.article.title}</h3>
          <p className="muted">{formatDate(article.article.published_at)}</p>
          <p>{clampText(article.article.summary, article.article.article_text_excerpt || 'No article excerpt available.')}</p>
          <div className="action-row">
            <a className="ghost-button" href={article.article.url} target="_blank" rel="noreferrer">Open article</a>
            <a className="ghost-button" href={buildSemanticExplorerHref({ detail, article, articleId: article.article.article_id })}>Open article in Explorer</a>
          </div>
          <div className="metric-grid">
            <Info label="Cluster" value={article.semantic_summary.cluster_id == null ? '—' : String(article.semantic_summary.cluster_id)} />
            <Info label="Neighbors" value={String(article.semantic_summary.neighbor_count)} />
            <Info label="Outlier" value={article.semantic_summary.is_outlier ? 'Yes' : 'No'} />
            <Info label="Nearby sources" value={String(article.semantic_summary.source_neighbor_diversity ?? 0)} />
          </div>
          {article.neighbors.length > 0 ? (
            <ul className="neighbor-list">
              {article.neighbors.slice(0, 5).map((neighbor) => (
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
          ) : (
            <p className="muted">No semantic neighbors returned for this article yet.</p>
          )}
        </div>
      ) : (
        <div className="empty-state-card">
          <strong>No article selected</strong>
          <p className="muted">Pick a member article to inspect the piece itself and the nearby semantic context.</p>
        </div>
      )}
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function groupMembersBySource(members: StoryClusterMemberItem[]) {
  const grouped = new Map<string, StoryClusterMemberItem[]>()
  for (const member of members) {
    const current = grouped.get(member.source) ?? []
    current.push(member)
    grouped.set(member.source, current)
  }
  return Array.from(grouped.entries()).sort((a, b) => a[0].localeCompare(b[0]))
}
