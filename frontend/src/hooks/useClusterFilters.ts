import { useMemo, useState } from 'react'
import { DEFAULT_CLUSTER_QUERY } from '../lib/types'
import type { StoryClusterQuery } from '../lib/types'

export function useClusterFilters() {
  const [query, setQuery] = useState<StoryClusterQuery>(DEFAULT_CLUSTER_QUERY)

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (query.search.trim()) count += 1
    if (query.source) count += 1
    if (query.tagCode) count += 1
    if (query.entitySlug) count += 1
    if (query.dateFrom) count += 1
    if (query.dateTo) count += 1
    if (query.limit !== DEFAULT_CLUSTER_QUERY.limit) count += 1
    return count
  }, [query])

  return {
    query,
    activeFilterCount,
    updateQuery(patch: Partial<StoryClusterQuery>) {
      setQuery((current) => ({ ...current, ...patch }))
    },
    resetQuery() {
      setQuery(DEFAULT_CLUSTER_QUERY)
    },
  }
}
