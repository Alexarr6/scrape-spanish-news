import { useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_QUERY } from '../lib/types'
import type { ExplorerQuery } from '../lib/types'

const EXPLORER_PARAM_KEYS = [
  'view',
  'sem_search',
  'sem_source',
  'sem_section',
  'sem_cluster',
  'sem_story_cluster',
  'sem_from',
  'sem_to',
  'sem_outliers',
  'sem_limit',
  'sem_article',
] as const

function parseStrictPositiveInteger(value: string | null, fallback: number): number {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

function parseOptionalInteger(value: string | null): number | null {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

function readInitialState() {
  const params = new URLSearchParams(window.location.search)
  const query: ExplorerQuery = {
    search: params.get('sem_search') ?? DEFAULT_QUERY.search,
    source: params.get('sem_source') ?? DEFAULT_QUERY.source,
    section: params.get('sem_section') ?? DEFAULT_QUERY.section,
    clusterId: params.get('sem_cluster') ?? DEFAULT_QUERY.clusterId,
    storyClusterId: params.get('sem_story_cluster') ?? DEFAULT_QUERY.storyClusterId,
    dateFrom: params.get('sem_from') ?? DEFAULT_QUERY.dateFrom,
    dateTo: params.get('sem_to') ?? DEFAULT_QUERY.dateTo,
    outlierOnly: params.get('sem_outliers') === 'true',
    limit: parseStrictPositiveInteger(params.get('sem_limit'), DEFAULT_QUERY.limit),
  }

  return {
    query,
    selectedArticleId: parseOptionalInteger(params.get('sem_article')),
  }
}

export function useExplorerUrlState() {
  const [state, setState] = useState(readInitialState)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    for (const key of EXPLORER_PARAM_KEYS) params.delete(key)

    params.set('view', 'semantic')
    if (state.query.search.trim()) params.set('sem_search', state.query.search.trim())
    if (state.query.source) params.set('sem_source', state.query.source)
    if (state.query.section) params.set('sem_section', state.query.section)
    if (state.query.clusterId) params.set('sem_cluster', state.query.clusterId)
    if (state.query.storyClusterId) params.set('sem_story_cluster', state.query.storyClusterId)
    if (state.query.dateFrom) params.set('sem_from', state.query.dateFrom)
    if (state.query.dateTo) params.set('sem_to', state.query.dateTo)
    if (state.query.outlierOnly) params.set('sem_outliers', 'true')
    if (state.query.limit !== DEFAULT_QUERY.limit) params.set('sem_limit', String(state.query.limit))
    if (state.selectedArticleId != null) params.set('sem_article', String(state.selectedArticleId))

    const nextUrl = `${window.location.pathname}?${params.toString()}${window.location.hash}`
    window.history.replaceState(null, '', nextUrl)
  }, [state])

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (state.query.search.trim()) count += 1
    if (state.query.source) count += 1
    if (state.query.section) count += 1
    if (state.query.clusterId) count += 1
    if (state.query.storyClusterId) count += 1
    if (state.query.dateFrom) count += 1
    if (state.query.dateTo) count += 1
    if (state.query.outlierOnly) count += 1
    if (state.query.limit !== DEFAULT_QUERY.limit) count += 1
    return count
  }, [state.query])

  const updateQuery = useCallback((patch: Partial<ExplorerQuery>) => {
    setState((current) => ({ ...current, query: { ...current.query, ...patch } }))
  }, [])

  const resetQuery = useCallback(() => {
    setState({ query: { ...DEFAULT_QUERY }, selectedArticleId: null })
  }, [])

  const setSelectedArticleId = useCallback((articleId: number | null) => {
    setState((current) => ({ ...current, selectedArticleId: articleId }))
  }, [])

  return {
    query: state.query,
    selectedArticleId: state.selectedArticleId,
    activeFilterCount,
    updateQuery,
    resetQuery,
    setSelectedArticleId,
  }
}
