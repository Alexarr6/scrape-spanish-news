export function humanizeValue(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  return value.replace(/_/g, ' ')
}

export function formatConfidence(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return 'Unscored'
  const label = value >= 0.75 ? 'High' : value >= 0.55 ? 'Moderate' : value > 0 ? 'Low' : 'Unscored'
  return `${label} · ${value.toFixed(2)}`
}

export function formatBreakdownSummary(
  breakdown: Record<string, number>,
  maxItems = 2,
  fallback = 'No strong signal',
): string {
  const items = Object.entries(breakdown)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, maxItems)

  if (items.length === 0) return fallback

  return items
    .map(([label, count]) => `${humanizeValue(label)} ${count}`)
    .join(' · ')
}
