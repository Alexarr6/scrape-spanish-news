import { ExplorerLayout } from '../components/ExplorerLayout'
import { FilterBar } from '../components/FilterBar'
import { InspectorPanel } from '../components/InspectorPanel'
import { MapPanel } from '../components/MapPanel'
import { StatusBar } from '../components/StatusBar'
import { useExplorerBootstrap } from '../hooks/useExplorerBootstrap'

export function ExplorerPage() {
  const { points, filters, loading, error } = useExplorerBootstrap()

  return (
    <ExplorerLayout
      status={<StatusBar meta={points?.meta ?? null} />}
      filters={<FilterBar filters={filters} />}
      map={<MapPanel points={points} />}
      inspector={<InspectorPanel points={points} error={error} loading={loading} />}
    />
  )
}
