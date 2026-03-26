import { useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_CLUSTER_QUERY } from '../lib/types'
import type { StoryClusterQuery } from '../lib/types'
import {
  deleteSearchParams,
  parseNonNegativeInt,
  parseOptionalPositiveInt,
  parseStrictPositiveInt,
  readSearchParams,
  replaceUrlSearchParams,
} from '../lib/urlState'

const CLUSTER_PARAM_KEYS = [
  'search',
  'source',
  'tag',
  'entity',
  'from',
  'to',
  'limit',
  'offset',
  'cluster',
  'article',
] as const

function readInitialState() {
  const params = readSearchParams()
  const query: StoryClusterQuery = {
    search: params.get('search') ?? DEFAULT_CLUSTER_QUERY.search,
    source: params.get('source') ?? DEFAULT_CLUSTER_QUERY.source,
    tagCode: params.get('tag') ?? DEFAULT_CLUSTER_QUERY.tagCode,
    entitySlug: params.get('entity') ?? DEFAULT_CLUSTER_QUERY.entitySlug,
    dateFrom: params.get('from') ?? DEFAULT_CLUSTER_QUERY.dateFrom,
    dateTo: params.get('to') ?? DEFAULT_CLUSTER_QUERY.dateTo,
    limit: parseStrictPositiveInt(params.get('limit'), DEFAULT_CLUSTER_QUERY.limit),
    offset: parseNonNegativeInt(params.get('offset'), DEFAULT_CLUSTER_QUERY.offset),
  }

  return {
    query,
    selectedClusterId: parseOptionalPositiveInt(params.get('cluster')),
    selectedArticleId: parseOptionalPositiveInt(params.get('article')),
  }
}

export function useClusterUrlState() {
  const [state, setState] = useState(readInitialState)

  useEffect(() => {
    const params = deleteSearchParams(readSearchParams(), CLUSTER_PARAM_KEYS)

    if (state.query.search.trim()) params.set('search', state.query.search.trim())
    if (state.query.source) params.set('source', state.query.source)
    if (state.query.tagCode) params.set('tag', state.query.tagCode)
    if (state.query.entitySlug) params.set('entity', state.query.entitySlug)
    if (state.query.dateFrom) params.set('from', state.query.dateFrom)
    if (state.query.dateTo) params.set('to', state.query.dateTo)
    if (state.query.limit !== DEFAULT_CLUSTER_QUERY.limit) params.set('limit', String(state.query.limit))
    if (state.query.offset !== DEFAULT_CLUSTER_QUERY.offset) params.set('offset', String(state.query.offset))
    if (state.selectedClusterId != null) params.set('cluster', String(state.selectedClusterId))
    if (state.selectedArticleId != null) params.set('article', String(state.selectedArticleId))

    replaceUrlSearchParams(params)
  }, [state])

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (state.query.search.trim()) count += 1
    if (state.query.source) count += 1
    if (state.query.tagCode) count += 1
    if (state.query.entitySlug) count += 1
    if (state.query.dateFrom) count += 1
    if (state.query.dateTo) count += 1
    if (state.query.limit !== DEFAULT_CLUSTER_QUERY.limit) count += 1
    return count
  }, [state.query])

  const updateQuery = useCallback((patch: Partial<StoryClusterQuery>) => {
    setState((current) => ({
      ...current,
      query: { ...current.query, ...patch },
    }))
  }, [])

  const resetQuery = useCallback(() => {
    setState({ query: { ...DEFAULT_CLUSTER_QUERY }, selectedClusterId: null, selectedArticleId: null })
  }, [])

  const setSelectedClusterId = useCallback((clusterId: number | null) => {
    setState((current) => ({ ...current, selectedClusterId: clusterId, selectedArticleId: null }))
  }, [])

  const setSelectedArticleId = useCallback((articleId: number | null) => {
    setState((current) => ({ ...current, selectedArticleId: articleId }))
  }, [])

  return {
    query: state.query,
    selectedClusterId: state.selectedClusterId,
    selectedArticleId: state.selectedArticleId,
    activeFilterCount,
    updateQuery,
    resetQuery,
    setSelectedClusterId,
    setSelectedArticleId,
  }
}
