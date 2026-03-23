import type { ExplorerArticleDetail, StoryClusterDetail, StoryClusterListItem } from './types'

function cloneCurrentParams() {
  return new URLSearchParams(window.location.search)
}

export function isSemanticExplorerMode() {
  return new URLSearchParams(window.location.search).get('view') === 'semantic'
}

export function buildClusterBrowserHref(options?: { clusterId?: number | null }) {
  const params = cloneCurrentParams()
  params.delete('view')
  if (options?.clusterId != null) {
    params.set('cluster', String(options.clusterId))
  }
  const text = params.toString()
  return `${window.location.pathname}${text ? `?${text}` : ''}${window.location.hash}`
}

export function buildStoriesHref(clusterId: number | null): string | null {
  if (clusterId == null) return null
  return buildClusterBrowserHref({ clusterId })
}

export function buildSemanticExplorerHref(options: {
  cluster?: StoryClusterListItem | null
  detail?: StoryClusterDetail | null
  article?: ExplorerArticleDetail | null
  articleId?: number | null
}) {
  const params = cloneCurrentParams()
  params.set('view', 'semantic')

  const cluster = options.detail?.cluster ?? options.cluster ?? null
  const article = options.article?.article ?? null

  const seededStoryClusterId = cluster?.id ?? null
  const seededArticleId = options.articleId ?? article?.article_id ?? null

  params.delete('sem_search')
  params.delete('sem_source')
  params.delete('sem_from')
  params.delete('sem_to')
  params.delete('sem_cluster')
  params.delete('sem_section')
  params.delete('sem_outliers')

  if (seededStoryClusterId != null) params.set('sem_story_cluster', String(seededStoryClusterId))
  else params.delete('sem_story_cluster')

  if (seededArticleId != null) params.set('sem_article', String(seededArticleId))
  else params.delete('sem_article')

  const text = params.toString()
  return `${window.location.pathname}${text ? `?${text}` : ''}${window.location.hash}`
}
