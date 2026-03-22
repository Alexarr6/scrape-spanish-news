import { useState, type ChangeEvent } from 'react'
import { FilterDrawer } from '../components/layout/FilterDrawer'
import { StoryFocusPanel } from '../components/stories/StoryFocusPanel'
import { StoryStream } from '../components/stories/StoryStream'
import { useClusterBrowserData } from '../hooks/useClusterBrowserData'
import { useClusterUrlState } from '../hooks/useClusterUrlState'
import type { StoryClusterFiltersResponse, StoryClusterQuery } from '../lib/types'

export function ClusterBrowserPage() {
  const [filtersOpen, setFiltersOpen] = useState(false)

  const {
    query,
    activeFilterCount,
    updateQuery,
    resetQuery,
    selectedClusterId,
    selectedArticleId,
    setSelectedClusterId,
    setSelectedArticleId,
  } = useClusterUrlState()

  const { listState, filtersState, detailState, articleState } = useClusterBrowserData(
    query,
    selectedClusterId,
    selectedArticleId,
    setSelectedClusterId,
    setSelectedArticleId,
  )

  const total = listState.data?.meta.total ?? 0

  return (
    <div className="stories-layout">
      {/* Stories header */}
      <header className="stories-header">
        <div>
          <h1 className="stories-title">Stories</h1>
          <p className="stories-scope">
            {total > 0 ? `${total} stories in scope` : listState.loading ? 'Loading…' : 'No stories'}
          </p>
        </div>
        <div className="stories-header-actions">
          {activeFilterCount > 0 && (
            <span className="badge accent">{activeFilterCount} filters</span>
          )}
          <button
            className="btn-ghost"
            type="button"
            onClick={() => setFiltersOpen(true)}
          >
            Refine ↓
          </button>
        </div>
      </header>

      {/* Main workspace */}
      <div className="stories-workspace">
        <StoryStream
          data={listState.data}
          loading={listState.loading}
          error={listState.error}
          selectedClusterId={selectedClusterId}
          onSelectCluster={setSelectedClusterId}
          onNextPage={() => updateQuery({ offset: query.offset + query.limit })}
          onPreviousPage={() => updateQuery({ offset: Math.max(0, query.offset - query.limit) })}
        />

        <StoryFocusPanel
          detail={detailState.data}
          article={articleState.data}
          loading={detailState.loading}
          articleLoading={articleState.loading}
          error={detailState.error}
          articleError={articleState.error}
          selectedArticleId={selectedArticleId}
          onSelectArticle={setSelectedArticleId}
        />
      </div>

      {/* Filter drawer */}
      <FilterDrawer
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        title="Refine Stories"
        activeCount={activeFilterCount}
        onReset={resetQuery}
      >
        <StoriesFilterFields
          filters={filtersState.data}
          query={query}
          onQueryChange={updateQuery}
          disabled={listState.loading && !listState.data}
        />
      </FilterDrawer>
    </div>
  )
}

/* ─── Filter fields ─────────────────────────────────────────────────────── */
function StoriesFilterFields({
  filters,
  query,
  onQueryChange,
  disabled,
}: {
  filters: StoryClusterFiltersResponse | null
  query: StoryClusterQuery
  onQueryChange: (patch: Partial<StoryClusterQuery>) => void
  disabled?: boolean
}) {
  const onTextChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target
    onQueryChange({ [name]: value, offset: 0 })
  }

  return (
    <>
      <div className="filter-group">
        <div className="filter-group-label">Find a story</div>
        <label className="field">
          <span>Search headline or summary</span>
          <input
            name="search"
            value={query.search}
            onChange={onTextChange}
            placeholder="housing, Gaza, budgets…"
            disabled={disabled}
          />
        </label>
        <label className="field">
          <span>Entity</span>
          <select name="entitySlug" value={query.entitySlug} onChange={onTextChange} disabled={disabled}>
            <option value="">All entities</option>
            {(filters?.entities ?? []).map((entity) => (
              <option key={entity.slug} value={entity.slug}>
                {entity.name} · {entity.entity_type} ({entity.count})
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="filter-group">
        <div className="filter-group-label">Coverage scope</div>
        <label className="field">
          <span>Source</span>
          <select name="source" value={query.source} onChange={onTextChange} disabled={disabled}>
            <option value="">All sources</option>
            {(filters?.sources ?? []).map((source) => (
              <option key={source.value} value={source.value}>
                {source.label} ({source.count})
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Primary tag</span>
          <select name="tagCode" value={query.tagCode} onChange={onTextChange} disabled={disabled}>
            <option value="">All tags</option>
            {(filters?.tags ?? []).map((tag) => (
              <option key={tag.value} value={tag.value}>
                {tag.label} ({tag.count})
              </option>
            ))}
          </select>
        </label>
        <div className="field-row">
          <label className="field">
            <span>From</span>
            <input
              type="date"
              name="dateFrom"
              value={query.dateFrom}
              onChange={onTextChange}
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>To</span>
            <input
              type="date"
              name="dateTo"
              value={query.dateTo}
              onChange={onTextChange}
              disabled={disabled}
            />
          </label>
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-group-label">Result volume</div>
        <label className="field">
          <span>Stories per page</span>
          <select
            name="limit"
            value={String(query.limit)}
            onChange={(event) => onQueryChange({ limit: Number(event.target.value), offset: 0 })}
            disabled={disabled}
          >
            {[10, 20, 40].map((limit) => (
              <option key={limit} value={limit}>
                {limit}
              </option>
            ))}
          </select>
        </label>
      </div>
    </>
  )
}
