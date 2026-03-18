import { useState } from 'react'
import { ExplorerLayout } from '../components/ExplorerLayout'
import { FilterBar } from '../components/FilterBar'
import { InspectorPanel } from '../components/InspectorPanel'
import { MapPanel } from '../components/MapPanel'
import { StatusBar } from '../components/StatusBar'
import { useExplorerData } from '../hooks/useExplorerData'
import { useExplorerFilters } from '../hooks/useExplorerFilters'
import type { ExplorerColorMode, ExplorerViewMode } from '../lib/types'

export function ExplorerPage() {
  const [viewMode, setViewMode] = useState<ExplorerViewMode>('2d')
  const [colorMode, setColorMode] = useState<ExplorerColorMode>('neutral')
  const { query, activeFilterCount, updateQuery, resetQuery } = useExplorerFilters()
  const {
    pointsState,
    filtersState,
    detailState,
    selectedArticleId,
    selectedPoint,
    hoveredArticleId,
    neighborIds,
    setSelectedArticleId,
    clearSelectedArticle,
    setHoveredArticleId,
  } = useExplorerData(query)

  return (
    <ExplorerLayout
      status={
        <StatusBar
          meta={pointsState.data?.meta ?? null}
          activeFilterCount={activeFilterCount}
          selectedArticleId={selectedArticleId}
          viewMode={viewMode}
          colorMode={colorMode}
          onResetFilters={resetQuery}
        />
      }
      filters={
        <FilterBar
          filters={filtersState.data}
          query={query}
          onQueryChange={updateQuery}
          onReset={resetQuery}
          disabled={pointsState.loading && !pointsState.data}
        />
      }
      map={
        <MapPanel
          points={pointsState.data}
          loading={pointsState.loading}
          error={pointsState.error}
          selectedArticleId={selectedArticleId}
          hoveredArticleId={hoveredArticleId}
          neighborIds={neighborIds}
          viewMode={viewMode}
          colorMode={colorMode}
          onViewModeChange={setViewMode}
          onColorModeChange={setColorMode}
          onHoverArticle={setHoveredArticleId}
          onSelectArticle={setSelectedArticleId}
        />
      }
      inspector={
        <InspectorPanel
          selectedPoint={selectedPoint}
          detail={detailState.data}
          loading={detailState.loading}
          error={detailState.error}
          onClearSelection={clearSelectedArticle}
          onSelectArticle={setSelectedArticleId}
        />
      }
    />
  )
}
