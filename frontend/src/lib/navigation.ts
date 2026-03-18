import type { ExplorerArticleDetail, StoryClusterDetail, StoryClusterListItem } from './types'

function cloneCurrentParams() {
  return new URLSearchParams(window.location.search)
}

export function isSemanticExplorerMode() {
  return new URLSearchParams(window.location.search).get('view') === 'semantic'
}

export function buildClusterBrowserHref() {
  const params = cloneCurrentParams()
  params.delete('view')
  const text = params.toString()
  return `${window.location.pathname}${text ? `?${text}` : ''}${window.location.hash}`
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

  const seededSearch = article?.title?.trim() || cluster?.summary_headline?.trim() || ''
  const seededSource = article?.source?.trim() || ''
  const seededFrom = cluster?.first_article_published_at?.slice(0, 10) || ''
  const seededTo = cluster?.last_article_published_at?.slice(0, 10) || ''
  const seededArticleId = options.articleId ?? article?.article_id ?? null

  if (seededSearch) params.set('sem_search', seededSearch)
  else params.delete('sem_search')

  if (seededSource) params.set('sem_source', seededSource)
  else params.delete('sem_source')

  if (seededFrom) params.set('sem_from', seededFrom)
  else params.delete('sem_from')

  if (seededTo) params.set('sem_to', seededTo)
  else params.delete('sem_to')

  params.delete('sem_cluster')
  params.delete('sem_section')
  params.delete('sem_outliers')

  if (seededArticleId != null) params.set('sem_article', String(seededArticleId))
  else params.delete('sem_article')

  const text = params.toString()
  return `${window.location.pathname}${text ? `?${text}` : ''}${window.location.hash}`
}
