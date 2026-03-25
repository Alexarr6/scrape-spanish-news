import type { ExplorerEditorialEvidence } from '../../lib/types'

export function EditorialEvidenceList({
  evidence,
  compact = false,
}: {
  evidence: ExplorerEditorialEvidence[]
  compact?: boolean
}) {
  return (
    <ul className={`editorial-evidence-list${compact ? ' compact' : ''}`}>
      {evidence.map((item, index) => (
        <li key={`${item.type}-${index}`} className="editorial-evidence-item">
          <div className="editorial-evidence-head">
            <span className="badge muted">{item.type}</span>
          </div>
          <p className="editorial-evidence-text">“{item.text}”</p>
          {item.note && <p className="editorial-evidence-note">{item.note}</p>}
        </li>
      ))}
    </ul>
  )
}
