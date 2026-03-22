import { clampText, formatDate, formatSimilarity } from '../../lib/format'
import { buildSemanticExplorerHref } from '../../lib/navigation'
import type { ExplorerArticleDetail, StoryClusterDetail, StoryClusterMemberItem } from '../../lib/types'
import { SectionDivider } from '../layout/SectionDivider'
import { ErrorState } from '../system/ErrorState'
import { LoadingState } from '../system/LoadingState'
import { CoverageBar } from './CoverageBar'

type Props = {
  detail: StoryClusterDetail | null
  article: ExplorerArticleDetail | null
  loading: boolean
  articleLoading: boolean
  error: string | null
  articleError: string | null
  selectedArticleId: number | null
  onSelectArticle: (articleId: number | null) => void
}

export function StoryFocusPanel({
  detail,
  article,
  loading,
  articleLoading,
  error,
  articleError,
  selectedArticleId,
  onSelectArticle,
}: Props) {
  // Loading first load
  if (loading && !detail) {
    return (
      <div className="story-focus-panel">
        <LoadingState label="Loading story…" hint="Fetching coverage and member articles." />
      </div>
    )
  }

  // Error
  if (error) {
    return (
      <div className="story-focus-panel">
        <ErrorState
          message="Failed to load story detail"
          hint={error}
        />
      </div>
    )
  }

  // Empty (no selection)
  if (!detail) {
    return (
      <div className="story-focus-panel">
        <div className="story-focus-empty">
          <span className="story-focus-empty-title">Select a story</span>
          <p className="story-focus-empty-desc">
            Pick any cluster from the stream to inspect its source coverage and article detail.
          </p>
          <a href="?view=semantic" className="btn-ghost">
            Open Explorer →
          </a>
        </div>
      </div>
    )
  }

  const explorerHref = buildSemanticExplorerHref({ detail, articleId: selectedArticleId })

  return (
    <div className="story-focus-panel">
      {/* Section 1: Story brief */}
      <section className="focus-brief">
        <div className="focus-brief-type">
          <span className="text-eyebrow">
            {detail.cluster.cluster_type.replace(/_/g, ' ')} · {detail.cluster.status}
          </span>
        </div>
        <h2>{detail.cluster.summary_headline}</h2>
        <p className="focus-brief-summary">{detail.cluster.summary_text}</p>
        <div className="focus-brief-meta">
          {detail.cluster.article_count} articles · {detail.cluster.source_count} sources
          {detail.cluster.first_article_published_at && (
            <> · {formatDate(detail.cluster.first_article_published_at)}</>
          )}
        </div>
        <div style={{ marginTop: 'var(--space-1)' }}>
          <a href={explorerHref} className="btn-ghost">
            Open in Explorer →
          </a>
        </div>
      </section>

      <SectionDivider label="Coverage" />

      {/* Section 2: Coverage bar */}
      <section className="focus-section">
        <CoverageBar members={detail.members} />
      </section>

      <SectionDivider label="Articles by source" />

      {/* Section 3 or 4: Article list or article detail */}
      <section className="focus-section">
        {selectedArticleId && (article || articleLoading || articleError) ? (
          <ArticleDetailSection
            article={article}
            loading={articleLoading}
            error={articleError}
            detail={detail}
            onBack={() => onSelectArticle(null)}
          />
        ) : (
          <SourceGroupList
            members={detail.members}
            selectedArticleId={selectedArticleId}
            onSelectArticle={onSelectArticle}
          />
        )}
      </section>
    </div>
  )
}

/* ─── Source group list ────────────────────────────────────────────────── */
function SourceGroupList({
  members,
  selectedArticleId,
  onSelectArticle,
}: {
  members: StoryClusterMemberItem[]
  selectedArticleId: number | null
  onSelectArticle: (id: number | null) => void
}) {
  const grouped = groupMembersBySource(members)

  return (
    <div className="source-groups">
      {grouped.map(([source, items]) => (
        <section key={source} className="source-group">
          <div className="source-group-header">
            <span className="source-group-name">{source}</span>
            <span className="badge muted">{items.length}</span>
          </div>
          <div className="member-list">
            {items.map((member) => (
              <button
                key={member.article_id}
                type="button"
                className={`member-card${selectedArticleId === member.article_id ? ' selected' : ''}`}
                onClick={() => onSelectArticle(member.article_id)}
              >
                <div className="member-card-title">{member.title}</div>
                <div className="member-card-meta">
                  <span className="member-card-date">
                    {formatDate(member.published_at ?? '')} · {member.section || 'no section'}
                  </span>
                  <span className="member-card-score">{formatSimilarity(member.membership_score)}</span>
                </div>
                {member.summary && (
                  <p className="member-card-summary">
                    {clampText(member.summary, '')}
                  </p>
                )}
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

/* ─── Article detail section ───────────────────────────────────────────── */
function ArticleDetailSection({
  article,
  loading,
  error,
  detail,
  onBack,
}: {
  article: ExplorerArticleDetail | null
  loading: boolean
  error: string | null
  detail: StoryClusterDetail
  onBack: () => void
}) {
  return (
    <div className="article-detail">
      <div className="article-detail-back">
        <button className="btn-text" type="button" onClick={onBack}>
          ← Back to articles
        </button>
      </div>

      {loading && !article && (
        <LoadingState label="Loading article…" centered={false} />
      )}

      {error && (
        <ErrorState message="Failed to load article detail" hint={error} centered={false} />
      )}

      {article && (
        <>
          <div>
            <span className="context-article-eyebrow">
              {article.article.source}
              {article.article.section ? ` · ${article.article.section}` : ''}
            </span>
          </div>
          <h3>{article.article.title}</h3>
          <span className="article-detail-date">{formatDate(article.article.published_at)}</span>
          <p className="article-detail-summary">
            {clampText(article.article.summary, article.article.article_text_excerpt || 'No summary available.')}
          </p>

          <div className="article-detail-actions">
            <a
              href={article.article.url}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost"
            >
              Open article ↗
            </a>
            <a
              href={buildSemanticExplorerHref({ detail, article, articleId: article.article.article_id })}
              className="btn-ghost"
            >
              Open in Explorer →
            </a>
          </div>

          <div style={{ marginTop: 'var(--space-2)' }}>
            <div className="section-divider-label">Semantic context</div>
            <div className="article-detail-metrics">
              <MetricItem label="Cluster" value={article.semantic_summary.cluster_id == null ? '—' : `#${article.semantic_summary.cluster_id}`} />
              <MetricItem label="Outlier" value={article.semantic_summary.is_outlier ? 'Yes' : 'No'} />
              <MetricItem label="Neighbors" value={String(article.semantic_summary.neighbor_count)} />
              <MetricItem label="Src diversity" value={String(article.semantic_summary.source_neighbor_diversity ?? 0)} />
            </div>
          </div>

          {article.neighbors.length > 0 && (
            <div>
              <div className="section-divider-label">Nearby articles</div>
              <ul className="neighbor-list">
                {article.neighbors.slice(0, 4).map((neighbor) => (
                  <li key={neighbor.article_id}>
                    <div className="neighbor-button">
                      <div>
                        <div className="neighbor-title">{neighbor.title}</div>
                        <div className="neighbor-meta">
                          {neighbor.source} · {formatDate(neighbor.published_at)}
                        </div>
                      </div>
                      <span className="badge muted">{formatSimilarity(neighbor.similarity)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
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

function groupMembersBySource(members: StoryClusterMemberItem[]): [string, StoryClusterMemberItem[]][] {
  const grouped = new Map<string, StoryClusterMemberItem[]>()
  for (const member of members) {
    const current = grouped.get(member.source) ?? []
    current.push(member)
    grouped.set(member.source, current)
  }
  return Array.from(grouped.entries()).sort((a, b) => b[1].length - a[1].length)
}
