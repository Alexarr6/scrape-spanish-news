import type { ExplorerQuery, StoryClusterQuery } from './types'

function buildQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value == null) continue
    if (typeof value === 'string' && !value.trim()) continue
    if (typeof value === 'boolean') {
      if (value) searchParams.set(key, 'true')
      continue
    }
    searchParams.set(key, String(value))
  }
  const text = searchParams.toString()
  return text ? `?${text}` : ''
}

export function buildExplorerPointsQuery(
  query: ExplorerQuery,
  visualMode?: 'highlight' | 'filter',
): string {
  return buildQuery({
    search: query.search.trim(),
    source: query.source,
    section: query.section,
    cluster_id: query.clusterId,
    sem_story_cluster: query.storyClusterId,
    sem_mode: visualMode,
    date_from: query.dateFrom,
    date_to: query.dateTo,
    outlier_only: query.outlierOnly,
    limit: query.limit,
  })
}

export function buildStoryClusterQuery(query: StoryClusterQuery): string {
  return buildQuery({
    search: query.search.trim(),
    source: query.source,
    tag_code: query.tagCode,
    entity_slug: query.entitySlug,
    date_from: query.dateFrom,
    date_to: query.dateTo,
    limit: query.limit,
    offset: query.offset,
  })
}

export function buildStoryClusterFiltersQuery(query: StoryClusterQuery): string {
  return buildQuery({
    search: query.search.trim(),
    source: query.source,
    date_from: query.dateFrom,
    date_to: query.dateTo,
  })
}
