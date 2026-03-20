import type { StoryClusterListItem } from '../../lib/types'

type Props = {
  cluster: StoryClusterListItem
  selected: boolean
  onClick: () => void
}

export function StoryCard({ cluster, selected, onClick }: Props) {
  return (
    <button
      type="button"
      className={`story-card${selected ? ' selected' : ''}`}
      onClick={onClick}
      aria-pressed={selected}
    >
      <div className="story-card-meta">
        <span className="text-eyebrow">{cluster.cluster_type.replace(/_/g, ' ')}</span>
        <span className="story-card-counts">
          {cluster.article_count} articles · {cluster.source_count} sources
        </span>
      </div>

      <h2 className="story-card-headline">{cluster.summary_headline}</h2>

      <p className="story-card-summary">{cluster.summary_text}</p>

      <div className="story-card-footer">
        <div className="story-card-sources">
          {cluster.sources.slice(0, 3).map((source) => (
            <span key={source} className="badge">{source}</span>
          ))}
          {cluster.sources.length > 3 && (
            <span className="badge muted">+{cluster.sources.length - 3}</span>
          )}
        </div>
        <span className="story-card-date">{formatClusterWindow(cluster)}</span>
      </div>
    </button>
  )
}

function formatClusterWindow(cluster: StoryClusterListItem): string {
  const { first_article_published_at: first, last_article_published_at: last } = cluster
  if (!first && !last) return ''
  if (!first || !last || first === last) return formatShortDate(first ?? last ?? '')
  return `${formatShortDate(first)} – ${formatShortDate(last)}`
}

function formatShortDate(value: string): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' }).format(d)
}
