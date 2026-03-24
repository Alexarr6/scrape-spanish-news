import {
  buildExplorerPointsQuery,
  buildStoryClusterFiltersQuery,
  buildStoryClusterQuery,
} from './query'
import type {
  ExplorerArticleDetail,
  ExplorerFiltersResponse,
  ExplorerPointsResponse,
  ExplorerQuery,
  StoryClusterDetail,
  StoryClusterFiltersResponse,
  StoryClusterListResponse,
  StoryClusterQuery,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export function fetchExplorerPoints(
  query: ExplorerQuery,
  visualMode?: 'highlight' | 'filter',
): Promise<ExplorerPointsResponse> {
  return requestJson(`/api/v1/semantic/explorer/points${buildExplorerPointsQuery(query, visualMode)}`)
}

export function fetchExplorerFilters(): Promise<ExplorerFiltersResponse> {
  return requestJson('/api/v1/semantic/explorer/filters')
}

export function fetchExplorerArticleDetail(articleId: number): Promise<ExplorerArticleDetail> {
  return requestJson(`/api/v1/semantic/explorer/articles/${articleId}`)
}

export function fetchStoryClusters(query: StoryClusterQuery): Promise<StoryClusterListResponse> {
  return requestJson(`/api/v1/clusters${buildStoryClusterQuery(query)}`)
}

export function fetchStoryClusterFilters(query: StoryClusterQuery): Promise<StoryClusterFiltersResponse> {
  return requestJson(`/api/v1/clusters/filters${buildStoryClusterFiltersQuery(query)}`)
}

export function fetchStoryClusterDetail(clusterId: number): Promise<StoryClusterDetail> {
  return requestJson(`/api/v1/clusters/${clusterId}`)
}
