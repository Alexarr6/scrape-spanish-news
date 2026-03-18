import { useEffect, useMemo, useState } from 'react'
import {
  fetchExplorerArticleDetail,
  fetchStoryClusterDetail,
  fetchStoryClusterFilters,
  fetchStoryClusters,
} from '../lib/api'
import type {
  ExplorerArticleDetail,
  LoadState,
  StoryClusterDetail,
  StoryClusterFiltersResponse,
  StoryClusterListItem,
  StoryClusterListResponse,
  StoryClusterQuery,
} from '../lib/types'

export function useClusterBrowserData(query: StoryClusterQuery) {
  const [listState, setListState] = useState<LoadState<StoryClusterListResponse>>({
    data: null,
    loading: true,
    error: null,
  })
  const [filtersState, setFiltersState] = useState<LoadState<StoryClusterFiltersResponse>>({
    data: null,
    loading: true,
    error: null,
  })
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null)
  const [selectedArticleId, setSelectedArticleId] = useState<number | null>(null)
  const [detailState, setDetailState] = useState<LoadState<StoryClusterDetail>>({
    data: null,
    loading: false,
    error: null,
  })
  const [articleState, setArticleState] = useState<LoadState<ExplorerArticleDetail>>({
    data: null,
    loading: false,
    error: null,
  })

  useEffect(() => {
    let cancelled = false
    setFiltersState((current) => ({ ...current, loading: true, error: null }))
    fetchStoryClusterFilters(query)
      .then((data) => {
        if (!cancelled) setFiltersState({ data, loading: false, error: null })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setFiltersState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [query.source, query.dateFrom, query.dateTo, query.search])

  useEffect(() => {
    let cancelled = false
    setListState((current) => ({ ...current, loading: true, error: null }))
    fetchStoryClusters(query)
      .then((data) => {
        if (cancelled) return
        setListState({ data, loading: false, error: null })

        if (data.items.length === 0) {
          setSelectedClusterId(null)
          setSelectedArticleId(null)
          setDetailState({ data: null, loading: false, error: null })
          setArticleState({ data: null, loading: false, error: null })
          return
        }

        const hasSelection = selectedClusterId != null && data.items.some((item) => item.id === selectedClusterId)
        if (!hasSelection) {
          setSelectedClusterId(data.items[0].id)
          setSelectedArticleId(null)
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setListState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [query, selectedClusterId])

  useEffect(() => {
    if (selectedClusterId == null) {
      setDetailState({ data: null, loading: false, error: null })
      return
    }
    let cancelled = false
    setDetailState((current) => ({ data: current.data, loading: true, error: null }))
    fetchStoryClusterDetail(selectedClusterId)
      .then((data) => {
        if (cancelled) return
        setDetailState({ data, loading: false, error: null })
        if (selectedArticleId != null && !data.members.some((member) => member.article_id === selectedArticleId)) {
          setSelectedArticleId(data.members[0]?.article_id ?? null)
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDetailState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [selectedClusterId, selectedArticleId])

  useEffect(() => {
    if (selectedArticleId == null) {
      setArticleState({ data: null, loading: false, error: null })
      return
    }
    let cancelled = false
    setArticleState((current) => ({ data: current.data, loading: true, error: null }))
    fetchExplorerArticleDetail(selectedArticleId)
      .then((data) => {
        if (!cancelled) setArticleState({ data, loading: false, error: null })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setArticleState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [selectedArticleId])

  const selectedCluster = useMemo<StoryClusterListItem | null>(() => {
    if (selectedClusterId == null) return null
    return listState.data?.items.find((item) => item.id === selectedClusterId) ?? null
  }, [listState.data, selectedClusterId])

  return {
    listState,
    filtersState,
    detailState,
    articleState,
    selectedCluster,
    selectedClusterId,
    selectedArticleId,
    setSelectedClusterId,
    setSelectedArticleId,
    nextPage() {
      if (!listState.data) return null
      return { ...query, offset: query.offset + query.limit }
    },
    previousPage() {
      return { ...query, offset: Math.max(0, query.offset - query.limit) }
    },
  }
}
