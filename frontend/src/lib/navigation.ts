import type { ExplorerArticleDetail, StoryClusterDetail, StoryClusterListItem } from './types'
import { buildHrefFromSearchParams, deleteSearchParams, readSearchParams } from './urlState'

const EXPLORER_HANDOFF_CLEAR_KEYS = [
  'sem_search',
  'sem_source',
  'sem_from',
  'sem_to',
  'sem_cluster',
  'sem_section',
  'sem_outliers',
  'sem_editorial_dim',
  'sem_editorial_value',
] as const

export function buildStoriesSurfaceHref(options?: { clusterId?: number | null }) {
  const params = readSearchParams()
  params.delete('view')

  if (options?.clusterId != null) params.set('cluster', String(options.clusterId))

  return buildHrefFromSearchParams(params)
}

export function buildStoriesHref(clusterId: number | null): string | null {
  if (clusterId == null) return null
  return buildStoriesSurfaceHref({ clusterId })
}

export function buildExplorerSurfaceHref(options: {
  cluster?: StoryClusterListItem | null
  detail?: StoryClusterDetail | null
  article?: ExplorerArticleDetail | null
  articleId?: number | null
}) {
  const params = deleteSearchParams(readSearchParams(), EXPLORER_HANDOFF_CLEAR_KEYS)
  const cluster = options.detail?.cluster ?? options.cluster ?? null
  const article = options.article?.article ?? null

  const seededStoryClusterId = cluster?.id ?? null
  const seededArticleId = options.articleId ?? article?.article_id ?? null

  params.set('view', 'semantic')
  params.set('sem_mode', 'highlight')
  params.set('sem_color', 'active-match')

  if (seededStoryClusterId != null) params.set('sem_story_cluster', String(seededStoryClusterId))
  else params.delete('sem_story_cluster')

  if (seededArticleId != null) params.set('sem_article', String(seededArticleId))
  else params.delete('sem_article')

  return buildHrefFromSearchParams(params)
}
