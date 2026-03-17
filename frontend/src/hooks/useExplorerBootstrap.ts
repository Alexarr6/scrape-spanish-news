import { useEffect, useState } from 'react'
import { fetchExplorerFilters, fetchExplorerPoints } from '../lib/api'
import type { ExplorerFiltersResponse, ExplorerPointsResponse } from '../lib/types'

type BootstrapState = {
  points: ExplorerPointsResponse | null
  filters: ExplorerFiltersResponse | null
  loading: boolean
  error: string | null
}

export function useExplorerBootstrap(): BootstrapState {
  const [state, setState] = useState<BootstrapState>({
    points: null,
    filters: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [points, filters] = await Promise.all([
          fetchExplorerPoints(),
          fetchExplorerFilters(),
        ])
        if (!cancelled) {
          setState({ points, filters, loading: false, error: null })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            points: null,
            filters: null,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          })
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
