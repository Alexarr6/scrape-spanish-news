import { useMemo, useRef, useState, type ChangeEvent } from 'react'
import { ExplorerControlBar } from '../components/explorer/ExplorerControlBar'
import { ExplorerContextRail, type ActiveMatchTarget, type SeedContext } from '../components/explorer/ExplorerContextRail'
import { MapPanel, type MapPanelHandle } from '../components/explorer/MapPanel'
import { FilterDrawer } from '../components/layout/FilterDrawer'
import { useExplorerData } from '../hooks/useExplorerData'
import { useExplorerUrlState } from '../hooks/useExplorerUrlState'
import type {
  ExplorerFiltersResponse,
  ExplorerPoint,
  ExplorerQuery,
  ExplorerViewMode,
} from '../lib/types'

function hasStoryClusterMetadata(points: ExplorerPoint[]) {
  return points.some((point) => Array.isArray(point.analysis.story_cluster_ids))
}

export function ExplorerPage() {
  const [viewMode, setViewMode] = useState<ExplorerViewMode>('2d')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const mapRef = useRef<MapPanelHandle>(null)

  const {
    query,
    selectedArticleId,
    visualMode,
    colorMode,
    activeFilterCount,
    updateQuery,
    resetQuery,
    setSelectedArticleId,
    setVisualMode,
    setColorMode,
  } = useExplorerUrlState()

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

  const seedContext = useMemo<SeedContext>(() => {
    if (query.storyClusterId) return { type: 'story-cluster', clusterId: Number(query.storyClusterId) }
    if (query.clusterId) return { type: 'cluster', clusterId: Number(query.clusterId) }
    if (query.search.trim()) return { type: 'search', query: query.search.trim() }
    return null
  }, [query.storyClusterId, query.clusterId, query.search])

  const activeMatchTarget = useMemo<ActiveMatchTarget>(() => {
    const points = pointsState.data?.items ?? []
    if (query.storyClusterId) {
      return {
        type: 'story-cluster',
        id: Number(query.storyClusterId),
        available: hasStoryClusterMetadata(points),
      }
    }
    if (query.clusterId) return { type: 'semantic-cluster', id: Number(query.clusterId) }
    if (query.search.trim()) return { type: 'search', query: query.search.trim() }
    if (query.source) return { type: 'source', source: query.source }
    return null
  }, [pointsState.data?.items, query.storyClusterId, query.clusterId, query.search, query.source])

  return (
    <div className="explorer-layout">
      <ExplorerControlBar
        viewMode={viewMode}
        visualMode={visualMode}
        colorMode={colorMode}
        pointCount={pointsState.data?.meta.returned ?? 0}
        activeFilterCount={activeFilterCount}
        loading={pointsState.loading}
        hasSelection={selectedArticleId !== null}
        onViewModeChange={setViewMode}
        onVisualModeChange={setVisualMode}
        onColorModeChange={setColorMode}
        onFitAll={() => mapRef.current?.fitAll()}
        onFocusSelected={() => mapRef.current?.focusSelected()}
        onOpenFilters={() => setFiltersOpen(true)}
      />

      <div className="explorer-workspace">
        <div className="explorer-canvas-area">
          <MapPanel
            ref={mapRef}
            points={pointsState.data}
            loading={pointsState.loading}
            error={pointsState.error}
            selectedArticleId={selectedArticleId}
            hoveredArticleId={hoveredArticleId}
            neighborIds={neighborIds}
            viewMode={viewMode}
            visualMode={visualMode}
            colorMode={colorMode}
            activeMatchTarget={activeMatchTarget}
            onHoverArticle={setHoveredArticleId}
            onSelectArticle={setSelectedArticleId}
          />
        </div>

        <ExplorerContextRail
          selectedPoint={selectedPoint}
          detail={detailState.data}
          loading={detailState.loading}
          error={detailState.error}
          clusterSummaries={pointsState.data?.meta.cluster_summaries ?? filtersState.data?.cluster_summaries ?? []}
          viewMode={viewMode}
          visualMode={visualMode}
          colorMode={colorMode}
          activeMatchTarget={activeMatchTarget}
          onClearSelection={clearSelectedArticle}
          onSelectArticle={setSelectedArticleId}
          seedContext={seedContext}
          onClearSeed={resetQuery}
        />
      </div>

      <FilterDrawer
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        title="Refine Explorer"
        activeCount={activeFilterCount}
        onReset={resetQuery}
      >
        <ExplorerFilterFields
          filters={filtersState.data}
          query={query}
          onQueryChange={updateQuery}
          disabled={pointsState.loading && !pointsState.data}
        />
      </FilterDrawer>
    </div>
  )
}

function ExplorerFilterFields({
  filters,
  query,
  onQueryChange,
  disabled,
}: {
  filters: ExplorerFiltersResponse | null
  query: ExplorerQuery
  onQueryChange: (patch: Partial<ExplorerQuery>) => void
  disabled?: boolean
}) {
  const onTextChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target
    onQueryChange({ [name]: value })
  }

  return (
    <>
      <div className="filter-group">
        <div className="filter-group-label">Subset</div>
        <label className="field">
          <span>Search title or summary</span>
          <input
            name="search"
            value={query.search}
            onChange={onTextChange}
            placeholder="energy, election, housing…"
            disabled={disabled}
          />
        </label>
        <label className="field">
          <span>Source</span>
          <select name="source" value={query.source} onChange={onTextChange} disabled={disabled}>
            <option value="">All sources</option>
            {(filters?.available_sources ?? []).map((source) => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Section</span>
          <select name="section" value={query.section} onChange={onTextChange} disabled={disabled}>
            <option value="">All sections</option>
            {(filters?.available_sections ?? []).map((section) => (
              <option key={section} value={section}>{section}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="filter-group">
        <div className="filter-group-label">Semantic structure</div>
        <label className="field">
          <span>Cluster</span>
          <select name="clusterId" value={query.clusterId} onChange={onTextChange} disabled={disabled}>
            <option value="">All clusters</option>
            {(filters?.cluster_summaries ?? []).map((cluster) => (
              <option key={cluster.cluster_id} value={String(cluster.cluster_id)}>
                Cluster {cluster.cluster_id} · {cluster.size} articles
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={query.outlierOnly}
            onChange={(event) => onQueryChange({ outlierOnly: event.target.checked })}
            disabled={disabled}
          />
          <span>Show only outliers</span>
        </label>
      </div>

      <div className="filter-group">
        <div className="filter-group-label">Date window</div>
        <div className="field-row">
          <label className="field">
            <span>From</span>
            <input type="date" name="dateFrom" value={query.dateFrom} onChange={onTextChange} disabled={disabled} />
          </label>
          <label className="field">
            <span>To</span>
            <input type="date" name="dateTo" value={query.dateTo} onChange={onTextChange} disabled={disabled} />
          </label>
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-group-label">Point volume</div>
        <label className="field">
          <span>Point limit</span>
          <select
            name="limit"
            value={String(query.limit)}
            onChange={(event) => onQueryChange({ limit: Number(event.target.value) })}
            disabled={disabled}
          >
            {[100, 250, 500].map((limit) => (
              <option key={limit} value={limit}>{limit}</option>
            ))}
          </select>
        </label>
      </div>
    </>
  )
}
