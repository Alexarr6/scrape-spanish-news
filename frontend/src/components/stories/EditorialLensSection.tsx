import type {
  StoryClusterEditorialComparativeSignal,
  StoryClusterEditorialComparativeSource,
  StoryClusterEditorialComparativeSourceMetric,
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
  const metricBySource = new Map((comparative?.source_metrics ?? []).map((item) => [item.source, item]))
  const includedBySource = new Map((comparative?.included_sources ?? []).map((item) => [item.source, item]))

  return (
    <section className="editorial-lens-section">
      <div className="editorial-lens-header">
        <div>
          <span className="section-divider-label">Editorial lens</span>
          <h3 className="editorial-lens-title">How sources are framing this cluster</h3>
        </div>
        <div className="editorial-badge-row editorial-badge-row-wrap">
          <span className="badge muted">{editorialSummary.analyzed_article_count} analyzed</span>
          {editorialSummary.pending_article_count > 0 && <EditorialStatusBadge kind="pending" compact>{editorialSummary.pending_article_count} pending</EditorialStatusBadge>}
          {editorialSummary.failed_article_count > 0 && <EditorialStatusBadge kind="failed" compact>{editorialSummary.failed_article_count} failed</EditorialStatusBadge>}
        </div>
      </div>

      <div className="editorial-lens-coverage">
        <div className="metric-item">
          <span className="metric-label">Applicability</span>
          <span className="metric-value">{formatBreakdownSummary(editorialSummary.applicability_breakdown, 3)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Article types</span>
          <span className="metric-value">{formatBreakdownSummary(editorialSummary.article_type_breakdown, 3)}</span>
        </div>
      </div>

      <div className="editorial-section-block">
        <span className="editorial-section-label">Comparative signals</span>
        {comparative ? (
          <>
            <div className="editorial-callout">{comparative.comparison_note}</div>
            <div className="editorial-compare-source-list">
              {editorialSummary.source_summaries.map((sourceSummary) => (
                <EditorialSourceComparisonRow
                  key={sourceSummary.source}
                  sourceSummary={sourceSummary}
                  comparativeSource={includedBySource.get(sourceSummary.source) ?? null}
                  sourceMetric={metricBySource.get(sourceSummary.source) ?? null}
                  onSelectArticle={onSelectArticle}
                />
              ))}
            </div>
            <div className="editorial-section-block">
              <span className="editorial-section-label">Divergence callouts</span>
              {comparative.divergence_signals.length > 0 ? (
                <div className="editorial-signal-list">
                  {comparative.divergence_signals.map((signal) => (
                    <ComparativeSignalCard key={`${signal.dimension}-${signal.leading_source}-${signal.trailing_source}`} signal={signal} onSelectArticle={onSelectArticle} />
                  ))}
                </div>
              ) : (
                <p className="editorial-empty-copy">No dimension cleared the support threshold for a cleaner divergence claim.</p>
              )}
            </div>
          </>
        ) : (
          <p className="editorial-empty-copy">Comparative metrics are not available for this cluster.</p>
        )}
      </div>

      <div className="editorial-section-block">
        <span className="editorial-section-label">Cluster signals</span>
        {editorialSummary.cluster_signals.length > 0 ? (
          <div className="editorial-signal-list">
            {editorialSummary.cluster_signals.map((signal) => (
              <div key={`${signal.label}-${signal.note}`} className="editorial-signal-card">
                <div className="editorial-signal-header">
                  <span className="badge">{humanizeValue(signal.strength)}</span>
                  <strong>{signal.label}</strong>
                </div>
                <p className="editorial-signal-note">{signal.note}</p>
                <div className="editorial-badge-row editorial-badge-row-wrap">
                  {signal.supporting_sources.map((source) => <span key={source} className="badge muted">{source}</span>)}
                  {signal.example_article_ids.slice(0, 2).map((articleId) => (
                    <button key={articleId} type="button" className="btn-text" onClick={() => onSelectArticle(articleId)}>
                      Article {articleId}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="editorial-empty-copy">Signal is mixed or too thin to support a stronger cluster-level read.</p>
        )}
      </div>

      <div className="editorial-callout">{editorialSummary.confidence_note}</div>
      <p className="editorial-scope-note">{editorialSummary.scope_note}</p>
    </section>
  )
}

function EditorialSourceComparisonRow({
  sourceSummary,
  comparativeSource,
  sourceMetric,
  onSelectArticle,
}: {
  sourceSummary: StoryClusterEditorialSourceSummary
  comparativeSource: StoryClusterEditorialComparativeSource | null
  sourceMetric: StoryClusterEditorialComparativeSourceMetric | null
  onSelectArticle: (articleId: number) => void
}) {
  return (
    <article className="editorial-source-row">
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
          {sourceMetric && <span className="badge muted">{humanizeValue(sourceMetric.confidence_band)} confidence</span>}
          {sourceSummary.review_flag_counts.low_confidence > 0 && <EditorialStatusBadge kind="low_confidence" compact>{sourceSummary.review_flag_counts.low_confidence}</EditorialStatusBadge>}
          {sourceSummary.review_flag_counts.needs_review > 0 && <EditorialStatusBadge kind="needs_review" compact>{sourceSummary.review_flag_counts.needs_review}</EditorialStatusBadge>}
          {sourceSummary.review_flag_counts.limited > 0 && <EditorialStatusBadge kind="limited" compact>{sourceSummary.review_flag_counts.limited}</EditorialStatusBadge>}
        </div>
      </div>

      {comparativeSource && (
        <div className="editorial-source-note">{comparativeSource.comparison_note}</div>
      )}

      <div className="editorial-source-grid">
        <div className="metric-item"><span className="metric-label">Type mix</span><span className="metric-value">{formatBreakdownSummary(sourceSummary.article_type_breakdown)}</span></div>
        <div className="metric-item"><span className="metric-label">Bias labels</span><span className="metric-value">{formatBreakdownSummary(sourceSummary.bias_label_breakdown)}</span></div>
        <div className="metric-item"><span className="metric-label">Opinionatedness</span><span className="metric-value">{formatBreakdownSummary(sourceSummary.opinionatedness_breakdown)}</span></div>
        <div className="metric-item"><span className="metric-label">Tone</span><span className="metric-value">{formatBreakdownSummary(sourceSummary.tone_emotional_breakdown)}</span></div>
      </div>

      {sourceMetric && (
        <div className="editorial-comparative-metric-grid">
          <ComparativeMetric label="Opinionatedness" value={sourceMetric.opinionatedness_index} />
          <ComparativeMetric label="Emotional tone" value={sourceMetric.emotional_tone_index} />
          <ComparativeMetric label="Bias direction" value={sourceMetric.bias_direction_index} />
          <ComparativeMetric label="Framing concentration" value={sourceMetric.framing_concentration_index} />
        </div>
      )}

      {sourceMetric?.metric_notes?.length ? (
        <ul className="editorial-note-list">
          {sourceMetric.metric_notes.slice(0, 3).map((note) => <li key={note}>{note}</li>)}
        </ul>
      ) : null}

      {sourceSummary.top_framing_devices.length > 0 && (
        <div className="editorial-section-block">
          <span className="editorial-section-label">Framing highlights</span>
          <div className="editorial-chip-row">
            {sourceSummary.top_framing_devices.slice(0, 2).map((item) => (
              <button key={item.framing_device} type="button" className="editorial-framing-chip" onClick={() => item.example_article_ids[0] && onSelectArticle(item.example_article_ids[0])}>
                {humanizeValue(item.framing_device)} · {item.count}
              </button>
            ))}
          </div>
        </div>
      )}
    </article>
  )
}

function ComparativeMetric({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="editorial-dimension-item">
      <span className="editorial-dimension-label">{label}</span>
      <span className="editorial-dimension-value">{value == null ? 'Hidden' : value.toFixed(2)}</span>
    </div>
  )
}

function ComparativeSignalCard({
  signal,
  onSelectArticle,
}: {
  signal: StoryClusterEditorialComparativeSignal
  onSelectArticle: (articleId: number) => void
}) {
  return (
    <div className="editorial-signal-card editorial-comparative-signal-card">
      <div className="editorial-signal-header">
        <div>
          <div className="editorial-badge-row editorial-badge-row-wrap">
            <span className="badge">{humanizeValue(signal.strength)}</span>
            <span className="badge muted">{humanizeValue(signal.dimension)}</span>
          </div>
          <strong>{signal.label}</strong>
        </div>
        <div className="editorial-compare-delta">Δ {signal.delta.toFixed(2)}</div>
      </div>
      <p className="editorial-signal-note">
        <strong>{signal.leading_source}</strong> vs <strong>{signal.trailing_source}</strong> · {signal.note}
      </p>
      <div className="editorial-badge-row editorial-badge-row-wrap">
        {signal.support.compared_sources.map((source) => <span key={source} className="badge muted">{source}</span>)}
        <span className="badge muted">{signal.support.leading_usable_articles} vs {signal.support.trailing_usable_articles} usable</span>
        {signal.example_article_ids.slice(0, 2).map((articleId) => (
          <button key={articleId} type="button" className="btn-text" onClick={() => onSelectArticle(articleId)}>
            Article {articleId}
          </button>
        ))}
      </div>
    </div>
  )
}
