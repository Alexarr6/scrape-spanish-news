export function formatDate(value: string): string {
  if (!value) return 'Unknown date'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
  }).format(date)
}

export function formatSimilarity(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return `${Math.round(value * 100)}%`
}

export function formatCount(value: number | null | undefined, noun: string): string {
  if (value == null) return `0 ${noun}`
  return `${value} ${noun}`
}

export function clampText(value: string, fallback: string): string {
  const trimmed = value.trim()
  return trimmed || fallback
}
