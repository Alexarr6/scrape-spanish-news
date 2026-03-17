import type { ExplorerQuery } from './types'

export function buildExplorerPointsQuery(query: ExplorerQuery): string {
  const params = new URLSearchParams()
  if (query.search.trim()) params.set('search', query.search.trim())
  if (query.source) params.set('source', query.source)
  if (query.section) params.set('section', query.section)
  if (query.dateFrom) params.set('date_from', query.dateFrom)
  if (query.dateTo) params.set('date_to', query.dateTo)
  params.set('limit', String(query.limit))
  const text = params.toString()
  return text ? `?${text}` : ''
}
