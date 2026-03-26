import type {
  StoryClusterEditorialComparativeSource,
  StoryClusterEditorialSourceSummary,
  StoryClusterEditorialSummary,
} from '../../lib/types'
import { formatBreakdownSummary, humanizeValue } from '../editorial/editorialFormat'
import { EditorialStatusBadge } from '../editorial/EditorialStatusBadge'

export function EditorialLensSection({
  editorialSummary,
  onSelectArticle,
}: {
  editorialSummary: StoryClusterEditorialSummary | null
  onSelectArticle: (articleId: number) => void
}) {
  if (!editorialSummary) {
    return <div className="editorial-lens-empty">Editorial comparison is not yet available for this story.</div>
  }

  const comparative = editorialSummary.comparative_metrics
  const includedBySource = new Map((comparative?.included_sources ?? []).map((item) => [item.source, item]))
  const hasThinSignal = !comparative || editorialSummary.cluster_signals.length === 0

  return (
    <section className="editorial-lens-section">
      <div className="editorial-lens-header">
        <div>
          <h3 className="editorial-lens-title">How sources are framing this cluster</h3>
          <p className="editorial-empty-copy editorial-lens-intro">
            Compact source-by-source summaries of the clearest editorial signal in this story.
          </p>
        </div>
        <div className="editorial-badge-row editorial-badge-row-wrap">
          <span className="badge muted">{editorialSummary.analyzed_article_count} analyzed</span>
          {editorialSummary.pending_article_count > 0 && <EditorialStatusBadge kind="pending" compact>{editorialSummary.pending_article_count} pending</EditorialStatusBadge>}
          {editorialSummary.failed_article_count > 0 && <EditorialStatusBadge kind="failed" compact>{editorialSummary.failed_article_count} failed</EditorialStatusBadge>}
        </div>
      </div>

      {hasThinSignal && (
        <p className="editorial-lens-muted-note">
          Comparative signal is limited; source summaries are the clearest read right now.
        </p>
      )}

      <div className="editorial-compare-source-list">
        {editorialSummary.source_summaries.map((sourceSummary) => (
          <EditorialSourceComparisonRow
            key={sourceSummary.source}
            sourceSummary={sourceSummary}
            comparativeSource={includedBySource.get(sourceSummary.source) ?? null}
            onSelectArticle={onSelectArticle}
          />
        ))}
      </div>
    </section>
  )
}

function EditorialSourceComparisonRow({
  sourceSummary,
  comparativeSource,
  onSelectArticle,
}: {
  sourceSummary: StoryClusterEditorialSourceSummary
  comparativeSource: StoryClusterEditorialComparativeSource | null
  onSelectArticle: (articleId: number) => void
}) {
  const toneSummary = formatBreakdownSummary(sourceSummary.tone_emotional_breakdown)
  const biasSummary = formatBreakdownSummary(sourceSummary.bias_label_breakdown)
  const secondarySummary = biasSummary === 'No signal yet' ? toneSummary : biasSummary

  return (
    <article className="editorial-source-row compact">
      <div className="editorial-source-row-head">
        <div>
          <strong>{sourceSummary.source}</strong>
          <div className="editorial-source-meta">
            {sourceSummary.analyzed_article_count} / {sourceSummary.article_count} analyzed
            {comparativeSource ? ` · ${comparativeSource.usable_article_count} usable` : ''}
          </div>
        </div>
        <div className="editorial-badge-row editorial-badge-row-wrap">
          {comparativeSource && <span className="badge muted">{humanizeValue(comparativeSource.comparison_eligibility)}</span>}
          {sourceSummary.review_flag_counts.low_confidence > 0 && <EditorialStatusBadge kind="low_confidence" compact>{sourceSummary.review_flag_counts.low_confidence}</EditorialStatusBadge>}
          {sourceSummary.review_flag_counts.needs_review > 0 && <EditorialStatusBadge kind="needs_review" compact>{sourceSummary.review_flag_counts.needs_review}</EditorialStatusBadge>}
          {sourceSummary.review_flag_counts.limited > 0 && <EditorialStatusBadge kind="limited" compact>{sourceSummary.review_flag_counts.limited}</EditorialStatusBadge>}
        </div>
      </div>

      {comparativeSource?.comparison_note && (
        <div className="editorial-source-note">{comparativeSource.comparison_note}</div>
      )}

      <div className="editorial-source-grid compact">
        <div className="editorial-dimension-item"><span className="editorial-dimension-label">Type mix</span><span className="editorial-dimension-value">{formatBreakdownSummary(sourceSummary.article_type_breakdown)}</span></div>
        <div className="editorial-dimension-item"><span className="editorial-dimension-label">Editorial mix</span><span className="editorial-dimension-value">{secondarySummary}</span></div>
      </div>

      {sourceSummary.top_framing_devices.length > 0 && (
        <div className="editorial-chip-row">
          {sourceSummary.top_framing_devices.slice(0, 2).map((item) => (
            <button key={item.framing_device} type="button" className="editorial-framing-chip" onClick={() => item.example_article_ids[0] && onSelectArticle(item.example_article_ids[0])}>
              {humanizeValue(item.framing_device)} · {item.count}
            </button>
          ))}
        </div>
      )}
    </article>
  )
}
