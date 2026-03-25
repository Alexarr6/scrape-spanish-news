import type { ReactNode } from 'react'

type EditorialStatusKind =
  | 'completed'
  | 'pending'
  | 'failed'
  | 'limited'
  | 'out_of_domain'
  | 'low_confidence'
  | 'needs_review'
  | 'missing_evidence'

const STATUS_COPY: Record<EditorialStatusKind, { label: string; tone: string }> = {
  completed: { label: 'Resolved', tone: 'neutral' },
  pending: { label: 'Pending', tone: 'muted' },
  failed: { label: 'Analysis failed', tone: 'danger' },
  limited: { label: 'Limited', tone: 'warning' },
  out_of_domain: { label: 'Out of domain', tone: 'muted' },
  low_confidence: { label: 'Low confidence', tone: 'warning' },
  needs_review: { label: 'Needs review', tone: 'danger' },
  missing_evidence: { label: 'Evidence missing', tone: 'warning' },
}

export function EditorialStatusBadge({
  kind,
  compact = false,
  children,
}: {
  kind: EditorialStatusKind
  compact?: boolean
  children?: ReactNode
}) {
  const config = STATUS_COPY[kind]
  return (
    <span className={`editorial-status-badge editorial-status-${config.tone}${compact ? ' compact' : ''}`}>
      {children ?? config.label}
    </span>
  )
}
