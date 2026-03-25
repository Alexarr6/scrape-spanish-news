import { useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_QUERY } from '../lib/types'
import type {
  ExplorerColorMode,
  ExplorerEditorialDimension,
  ExplorerEditorialTarget,
  ExplorerQuery,
  ExplorerVisualMode,
} from '../lib/types'

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
  'sem_mode',
  'sem_color',
  'sem_editorial_dim',
  'sem_editorial_value',
] as const

function parseStrictPositiveInteger(value: string | null, fallback: number): number {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

function parseOptionalInteger(value: string | null): number | null {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

function parseVisualMode(value: string | null): ExplorerVisualMode {
  return value === 'filter' ? 'filter' : 'highlight'
}

function parseColorMode(value: string | null): ExplorerColorMode {
  return value === 'source' || value === 'cluster' || value === 'active-match' || value === 'article-type' || value === 'bias'
    ? value
    : 'neutral'
}

function parseEditorialDimension(value: string | null): ExplorerEditorialDimension | '' {
  return value === 'article_type' || value === 'bias_label' ? value : ''
}

function readInitialState() {
  const params = new URLSearchParams(window.location.search)
  const editorialDimension = parseEditorialDimension(params.get('sem_editorial_dim'))
  const editorialValue = editorialDimension ? params.get('sem_editorial_value') ?? DEFAULT_QUERY.editorialValue : ''

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
    editorialDimension,
    editorialValue,
  }

  return {
    query,
    selectedArticleId: parseOptionalInteger(params.get('sem_article')),
    visualMode: parseVisualMode(params.get('sem_mode')),
    colorMode: parseColorMode(params.get('sem_color')),
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
    if (state.visualMode !== 'highlight') params.set('sem_mode', state.visualMode)
    if (state.colorMode !== 'neutral') params.set('sem_color', state.colorMode)
    if (state.query.editorialDimension && state.query.editorialValue) {
      params.set('sem_editorial_dim', state.query.editorialDimension)
      params.set('sem_editorial_value', state.query.editorialValue)
    }

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
    if (state.query.editorialDimension && state.query.editorialValue) count += 1
    return count
  }, [state.query])

  const updateQuery = useCallback((patch: Partial<ExplorerQuery>) => {
    setState((current) => ({ ...current, query: { ...current.query, ...patch } }))
  }, [])

  const resetQuery = useCallback(() => {
    setState((current) => ({ ...current, query: { ...DEFAULT_QUERY }, selectedArticleId: null }))
  }, [])

  const setSelectedArticleId = useCallback((articleId: number | null) => {
    setState((current) => ({ ...current, selectedArticleId: articleId }))
  }, [])

  const setVisualMode = useCallback((visualMode: ExplorerVisualMode) => {
    setState((current) => ({ ...current, visualMode }))
  }, [])

  const setColorMode = useCallback((colorMode: ExplorerColorMode) => {
    setState((current) => ({ ...current, colorMode }))
  }, [])

  const setEditorialTarget = useCallback((target: ExplorerEditorialTarget) => {
    setState((current) => ({
      ...current,
      query: {
        ...current.query,
        editorialDimension: target?.dimension ?? '',
        editorialValue: target?.value ?? '',
      },
    }))
  }, [])

  return {
    query: state.query,
    selectedArticleId: state.selectedArticleId,
    visualMode: state.visualMode,
    colorMode: state.colorMode,
    activeFilterCount,
    updateQuery,
    resetQuery,
    setSelectedArticleId,
    setVisualMode,
    setColorMode,
    setEditorialTarget,
    editorialTarget: state.query.editorialDimension && state.query.editorialValue
      ? { dimension: state.query.editorialDimension, value: state.query.editorialValue }
      : null,
  }
}
