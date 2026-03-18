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

  return (
    <div className="panel-section">
      <div className="panel-header">
        <h2>Filters</h2>
        <button className="ghost-button" type="button" onClick={onReset}>
          Clear all
        </button>
      </div>
      <label className="field">
        <span>Search headline/summary</span>
        <input
          name="search"
          value={query.search}
          onChange={onTextChange}
          placeholder="housing, Gaza, budgets…"
          disabled={disabled}
        />
      </label>
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
      <label className="field">
        <span>Clusters per page</span>
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
      <div className="note-card">
        <strong>Practical filters, no cosplay</strong>
        <p>These options come from the cluster read API, so the browse flow stays grounded in what the backend actually knows.</p>
      </div>
    </div>
  )
}
