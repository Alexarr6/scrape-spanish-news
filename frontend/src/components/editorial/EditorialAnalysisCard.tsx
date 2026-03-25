import type { ExplorerEditorialSummary } from '../../lib/types'
import { EditorialDimensionGrid } from './EditorialDimensionGrid'
import { EditorialEvidenceList } from './EditorialEvidenceList'
import { formatConfidence, humanizeValue } from './editorialFormat'
import { EditorialStatusBadge } from './EditorialStatusBadge'

export function EditorialAnalysisCard({
  editorial,
  variant,
  clusterId,
  storiesHref,
}: {
  editorial: ExplorerEditorialSummary | null
  variant: 'full' | 'compact'
  clusterId?: number | null
  storiesHref?: string | null
}) {
  if (!editorial) {
    return (
      <section className={`editorial-card ${variant}`}>
        <div className="editorial-card-header">
          <div>
            <div className="section-divider-label">Editorial read</div>
            <p className="editorial-empty-copy">Editorial analysis is not available for this article yet.</p>
          </div>
        </div>
      </section>
    )
  }

  const limitationBadges = [
    editorial.editorial_applicability === 'limited' ? 'limited' : null,
    editorial.editorial_applicability === 'out_of_domain' ? 'out_of_domain' : null,
    editorial.review_flags.low_confidence ? 'low_confidence' : null,
    editorial.review_flags.needs_review ? 'needs_review' : null,
    editorial.review_flags.missing_evidence ? 'missing_evidence' : null,
  ].filter(Boolean) as Array<'limited' | 'out_of_domain' | 'low_confidence' | 'needs_review' | 'missing_evidence'>

  return (
    <section className={`editorial-card ${variant}`}>
      <div className="editorial-card-header">
        <div>
          <div className="section-divider-label">Editorial read</div>
          <h4 className="editorial-card-title">Evidence-backed editorial interpretation</h4>
        </div>
        <div className="editorial-badge-row">
          <EditorialStatusBadge kind={editorial.analysis_status === 'completed' ? 'completed' : editorial.analysis_status === 'pending' ? 'pending' : 'failed'} />
          <EditorialStatusBadge kind={editorial.editorial_applicability === 'full' ? 'completed' : editorial.editorial_applicability}>
            {humanizeValue(editorial.editorial_applicability)}
          </EditorialStatusBadge>
        </div>
      </div>

      <EditorialDimensionGrid {...editorial} compact={variant === 'compact'} />

      {editorial.framing_devices.length > 0 && (
        <div className="editorial-section-block">
          <span className="editorial-section-label">Framing devices</span>
          <div className="editorial-chip-row">
            {editorial.framing_devices.slice(0, 3).map((device) => (
              <span key={device} className="badge">{humanizeValue(device)}</span>
            ))}
          </div>
        </div>
      )}

      {editorial.evidence_spans.length > 0 ? (
        <div className="editorial-section-block">
          <span className="editorial-section-label">Evidence</span>
          <EditorialEvidenceList evidence={editorial.evidence_spans.slice(0, variant === 'compact' ? 2 : 3)} compact={variant === 'compact'} />
        </div>
      ) : editorial.analysis_status === 'completed' ? (
        <div className="editorial-callout warning">Completed analysis, but no supporting evidence spans were returned.</div>
      ) : null}

      {editorial.rationale && variant === 'full' && (
        <div className="editorial-section-block">
          <span className="editorial-section-label">Rationale</span>
          <p className="editorial-rationale">{editorial.rationale}</p>
        </div>
      )}

      <div className="editorial-section-block">
        <span className="editorial-section-label">Limits and review state</span>
        <div className="editorial-badge-row editorial-badge-row-wrap">
          {limitationBadges.length > 0 ? limitationBadges.map((kind) => <EditorialStatusBadge key={kind} kind={kind} compact />) : <span className="badge muted">No material review flags</span>}
        </div>
        <p className="editorial-limits-copy">
          {editorial.editorial_applicability_reason || editorial.unclear_reasons[0] || `Bias confidence ${formatConfidence(editorial.bias_confidence)}`}
        </p>
      </div>

      {(storiesHref || clusterId) && variant === 'compact' && (
        <div className="editorial-card-actions">
          {storiesHref && <a href={storiesHref} className="btn-ghost">Open story comparison →</a>}
          {!storiesHref && clusterId != null && <span className="badge muted">Cluster #{clusterId}</span>}
        </div>
      )}
    </section>
  )
}
