import { useEffect, useMemo, useState } from 'react'
import {
  fetchExplorerArticleDetail,
  fetchExplorerFilters,
  fetchExplorerPoints,
} from '../lib/api'
import type {
  ExplorerArticleDetail,
  ExplorerFiltersResponse,
  ExplorerPoint,
  ExplorerPointsResponse,
  ExplorerQuery,
  ExplorerVisualMode,
  LoadState,
} from '../lib/types'

export function useExplorerData(
  query: ExplorerQuery,
  visualMode: ExplorerVisualMode,
  selectedArticleId: number | null,
  setSelectedArticleId: (articleId: number | null) => void,
) {
  const [pointsState, setPointsState] = useState<LoadState<ExplorerPointsResponse>>({
    data: null,
    loading: true,
    error: null,
  })
  const [filtersState, setFiltersState] = useState<LoadState<ExplorerFiltersResponse>>({
    data: null,
    loading: true,
    error: null,
  })
  const [hoveredArticleId, setHoveredArticleId] = useState<number | null>(null)
  const [detailState, setDetailState] = useState<LoadState<ExplorerArticleDetail>>({
    data: null,
    loading: false,
    error: null,
  })

  useEffect(() => {
    let cancelled = false
    setFiltersState((current) => ({ ...current, loading: true, error: null }))
    fetchExplorerFilters()
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
  }, [])

  useEffect(() => {
    let cancelled = false
    setPointsState((current) => ({ ...current, loading: true, error: null }))
    fetchExplorerPoints(query, visualMode)
      .then((data) => {
        if (cancelled) return
        setPointsState({ data, loading: false, error: null })
        if (
          selectedArticleId != null &&
          !data.items.some((item) => item.article_id === selectedArticleId)
        ) {
          setSelectedArticleId(null)
          setDetailState({ data: null, loading: false, error: null })
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setPointsState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [query, visualMode, selectedArticleId, setSelectedArticleId])

  useEffect(() => {
    if (selectedArticleId == null) {
      setDetailState({ data: null, loading: false, error: null })
      return
    }
    let cancelled = false
    setDetailState({ data: null, loading: true, error: null })
    fetchExplorerArticleDetail(selectedArticleId)
      .then((data) => {
        if (!cancelled) setDetailState({ data, loading: false, error: null })
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
  }, [selectedArticleId])

  const selectedPoint = useMemo<ExplorerPoint | null>(() => {
    if (selectedArticleId == null) return null
    return pointsState.data?.items.find((item) => item.article_id === selectedArticleId) ?? null
  }, [pointsState.data, selectedArticleId])

  const neighborIds = useMemo(() => {
    return new Set(detailState.data?.neighbors.map((neighbor) => neighbor.article_id) ?? [])
  }, [detailState.data])

  return {
    pointsState,
    filtersState,
    detailState,
    selectedPoint,
    hoveredArticleId,
    neighborIds,
    setSelectedArticleId,
    clearSelectedArticle() {
      setSelectedArticleId(null)
      setDetailState({ data: null, loading: false, error: null })
    },
    setHoveredArticleId,
  }
}
