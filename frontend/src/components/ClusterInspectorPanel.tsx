import { clampText, formatDate, formatSimilarity } from '../lib/format'
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

export function ClusterInspectorPanel({
  detail,
  article,
  loading,
  articleLoading,
  error,
  articleError,
  selectedArticleId,
  onSelectArticle,
}: Props) {
  if (loading && !detail) {
    return <div className="panel-section"><h2>Cluster detail</h2><p>Loading cluster…</p></div>
  }

  if (error) {
    return <div className="panel-section"><h2>Cluster detail</h2><p>{error}</p></div>
  }

  if (!detail) {
    return <div className="panel-section"><h2>Cluster detail</h2><p>Select a story cluster to inspect its member articles.</p></div>
  }

  const groupedMembers = groupMembersBySource(detail.members)

  return (
    <div className="panel-section inspector-content">
      <div className="article-card">
        <div className="eyebrow">{detail.cluster.cluster_type.replace(/_/g, ' ')} · {detail.cluster.status}</div>
        <h2>{detail.cluster.summary_headline}</h2>
        <p>{detail.cluster.summary_text}</p>
        <div className="status-chip-row compact-row">
          <span className="status-chip">{detail.cluster.article_count} articles</span>
          <span className="status-chip">{detail.cluster.source_count} sources</span>
          {detail.cluster.primary_tag ? <span className="status-chip">{detail.cluster.primary_tag.display_name}</span> : null}
        </div>
        <div className="status-chip-row compact-row">
          {detail.cluster.top_entities.map((entity) => (
            <span key={entity.slug} className="status-chip subtle">{entity.name}</span>
          ))}
        </div>
      </div>

      <div className="panel-header compact">
        <h3>Coverage by source</h3>
        <span className="muted">Grouped so comparison doesn’t suck</span>
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
                <button
                  key={member.article_id}
                  type="button"
                  className={selectedArticleId === member.article_id ? 'member-card active' : 'member-card'}
                  onClick={() => onSelectArticle(member.article_id)}
                >
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
        <h3>Article inspection</h3>
        <span className="muted">Open a member to see more than a raw cluster card</span>
      </div>
      {articleLoading && !article ? <p>Loading article detail…</p> : null}
      {articleError ? <p>{articleError}</p> : null}
      {article ? (
        <div className="article-card">
          <div className="eyebrow">{article.article.source} · {article.article.section || 'no section'}</div>
          <h3>{article.article.title}</h3>
          <p className="muted">{formatDate(article.article.published_at)}</p>
          <p>{clampText(article.article.summary, article.article.article_text_excerpt || 'No article excerpt available.')}</p>
          <div className="action-row">
            <a className="ghost-button" href={article.article.url} target="_blank" rel="noreferrer">Open article</a>
          </div>
          <div className="status-chip-row compact-row">
            <span className="status-chip">Cluster {article.semantic_summary.cluster_id ?? '—'}</span>
            <span className="status-chip">{article.semantic_summary.neighbor_count} neighbors</span>
            <span className="status-chip">Outlier: {article.semantic_summary.is_outlier ? 'yes' : 'no'}</span>
          </div>
          {article.neighbors.length > 0 ? (
            <ul className="neighbor-list">
              {article.neighbors.slice(0, 5).map((neighbor) => (
                <li key={neighbor.article_id}>
                  <button className="neighbor-button" type="button" onClick={() => onSelectArticle(neighbor.article_id)}>
                    <span>
                      <strong>{neighbor.title}</strong>
                      <span className="muted">{neighbor.source} · {formatDate(neighbor.published_at)}</span>
                    </span>
                    <span className="status-chip">{formatSimilarity(neighbor.similarity)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <p className="muted">Select a member article to inspect it.</p>
      )}
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
