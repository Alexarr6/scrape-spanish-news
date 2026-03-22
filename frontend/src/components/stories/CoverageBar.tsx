import type { StoryClusterMemberItem } from '../../lib/types'

type Props = {
  members: StoryClusterMemberItem[]
}

type CoverageEntry = {
  source: string
  count: number
  pct: number
}

function computeCoverage(members: StoryClusterMemberItem[]): CoverageEntry[] {
  const groups = new Map<string, number>()
  for (const m of members) {
    groups.set(m.source, (groups.get(m.source) ?? 0) + 1)
  }
  const total = members.length
  if (total === 0) return []
  return Array.from(groups.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([source, count]) => ({
      source,
      count,
      pct: Math.round((count / total) * 100),
    }))
}

export function CoverageBar({ members }: Props) {
  const coverage = computeCoverage(members)

  if (coverage.length === 0) {
    return <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>No coverage data</p>
  }

  return (
    <div className="coverage-bar">
      {coverage.map(({ source, count, pct }) => (
        <div key={source} className="coverage-bar-row">
          <span className="coverage-bar-label" title={source}>{source}</span>
          <div className="coverage-bar-track">
            <div
              className="coverage-bar-fill"
              style={{ width: `${pct}%` }}
              aria-label={`${pct}%`}
            />
          </div>
          <span className="coverage-bar-count">{count} · {pct}%</span>
        </div>
      ))}
    </div>
  )
}
