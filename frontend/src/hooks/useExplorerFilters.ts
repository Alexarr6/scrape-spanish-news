import { useMemo, useState } from 'react'
import { DEFAULT_QUERY } from '../lib/types'
import type { ExplorerQuery } from '../lib/types'

export function useExplorerFilters() {
  const [query, setQuery] = useState<ExplorerQuery>(DEFAULT_QUERY)

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (query.search.trim()) count += 1
    if (query.source) count += 1
    if (query.section) count += 1
    if (query.dateFrom) count += 1
    if (query.dateTo) count += 1
    if (query.limit !== DEFAULT_QUERY.limit) count += 1
    return count
  }, [query])

  return {
    query,
    activeFilterCount,
    updateQuery(patch: Partial<ExplorerQuery>) {
      setQuery((current) => ({ ...current, ...patch }))
    },
    resetQuery() {
      setQuery(DEFAULT_QUERY)
    },
  }
}
