import { useState, type ComponentType, type ReactNode } from 'react'
import { FilterBar } from '../components/FilterBar'
import { InspectorPanel } from '../components/InspectorPanel'
import { MapPanel } from '../components/MapPanel'
import { StatusBar } from '../components/StatusBar'
import { useExplorerData } from '../hooks/useExplorerData'
import { useExplorerUrlState } from '../hooks/useExplorerUrlState'
import type { ExplorerColorMode, ExplorerViewMode } from '../lib/types'

type ShellProps = {
  section: string
  title: string
  description: string
  summary?: ReactNode
  actions?: ReactNode
  navItems: Array<{ key: string; label: string; description: string; href: string; active?: boolean }>
  status?: ReactNode
  filters?: ReactNode
  filtersTitle?: string
  main: ReactNode
  detail?: ReactNode
  detailTitle?: string
  contentClassName?: string
  mainClassName?: string
}

type Props = {
  navItems: ShellProps['navItems']
  shell: ComponentType<ShellProps>
}

export function ExplorerPage({ navItems, shell: Shell }: Props) {
  const [viewMode, setViewMode] = useState<ExplorerViewMode>('2d')
  const [colorMode, setColorMode] = useState<ExplorerColorMode>('neutral')
  const { query, selectedArticleId, activeFilterCount, updateQuery, resetQuery, setSelectedArticleId } = useExplorerUrlState()
  const {
    pointsState,
    filtersState,
    detailState,
    selectedPoint,
    hoveredArticleId,
    neighborIds,
    clearSelectedArticle,
    setHoveredArticleId,
  } = useExplorerData(query, selectedArticleId, setSelectedArticleId)

  return (
    <Shell
      section="Explorer"
      title="Semantic workspace"
      description="Use this when you need semantic shape: isolate outliers, inspect cluster topology, and trace how close different outlets sit in embedding space."
      summary={
        <>
          <span className="summary-pill emphasis">{viewMode.toUpperCase()} view</span>
          <span className="summary-pill">{colorMode} encoding</span>
          <span className="summary-pill">{pointsState.data?.meta.returned ?? 0} visible points</span>
          <span className="summary-pill subtle">{activeFilterCount} active filters</span>
        </>
      }
      navItems={navItems}
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
      filtersTitle="Explorer filters"
      filters={
        <FilterBar
          filters={filtersState.data}
          query={query}
          onQueryChange={updateQuery}
          onReset={resetQuery}
          disabled={pointsState.loading && !pointsState.data}
        />
      }
      contentClassName="workspace-grid explorer-grid"
      mainClassName="workspace-panel workspace-panel-main explorer-main"
      main={
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
      detailTitle="Selection"
      detail={
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
