import type { ChangeEvent } from 'react'
import type { StoryClusterFiltersResponse, StoryClusterQuery } from '../lib/types'

type Props = {
  filters: StoryClusterFiltersResponse | null
  query: StoryClusterQuery
  onQueryChange: (patch: Partial<StoryClusterQuery>) => void
  onReset: () => void
  disabled?: boolean
}

export function ClusterFilterPanel({ filters, query, onQueryChange, onReset, disabled = false }: Props) {
  const onTextChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target
    onQueryChange({ [name]: value, offset: 0 })
  }

  const activeTokens = [query.search, query.source, query.tagCode, query.entitySlug, query.dateFrom, query.dateTo].filter(Boolean)

  return (
    <div className="panel-section filter-stack">
      <div className="panel-header">
        <div>
          <h2>Clusters</h2>
          <p className="panel-help">Filter the story set first. The right-hand detail becomes useful only after this is clean.</p>
        </div>
        <button className="ghost-button" type="button" onClick={onReset}>
          Clear all
        </button>
      </div>

      <div className="filter-group">
        <div className="filter-group-header">
          <h3>Active scope</h3>
          <span className="muted">{activeTokens.length} applied</span>
        </div>
        <div className="status-chip-row compact-row">
          {activeTokens.length > 0 ? activeTokens.map((token) => <span key={token} className="status-chip subtle">{token}</span>) : <span className="status-chip">No filters yet</span>}
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-group-header">
          <h3>Find a story</h3>
          <span className="muted">Search + entity cues</span>
        </div>
        <label className="field">
          <span>Search headline or summary</span>
          <input name="search" value={query.search} onChange={onTextChange} placeholder="housing, Gaza, budgets…" disabled={disabled} />
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
        <div className="filter-group-header">
          <h3>Coverage scope</h3>
          <span className="muted">Source, topic, time</span>
        </div>
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
            <input type="date" name="dateFrom" value={query.dateFrom} onChange={onTextChange} disabled={disabled} />
          </label>
          <label className="field">
            <span>To</span>
            <input type="date" name="dateTo" value={query.dateTo} onChange={onTextChange} disabled={disabled} />
          </label>
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-group-header">
          <h3>Result volume</h3>
          <span className="muted">Keep the browsing pace sane</span>
        </div>
        <label className="field">
          <span>Clusters per page</span>
          <select name="limit" value={String(query.limit)} onChange={(event) => onQueryChange({ limit: Number(event.target.value), offset: 0 })} disabled={disabled}>
            {[10, 20, 40].map((limit) => (
              <option key={limit} value={limit}>
                {limit}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="helper-card">
        <strong>How to use this workspace</strong>
        <p>Pick the story cluster first, compare source membership second, and only then open article-level detail or jump into the explorer.</p>
      </div>
    </div>
  )
}
