import type { ExplorerFiltersResponse, ExplorerPointsResponse } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export function fetchExplorerPoints(): Promise<ExplorerPointsResponse> {
  return requestJson('/api/v1/semantic/explorer/points')
}

export function fetchExplorerFilters(): Promise<ExplorerFiltersResponse> {
  return requestJson('/api/v1/semantic/explorer/filters')
}
