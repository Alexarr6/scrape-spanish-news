import type { ChangeEvent } from 'react'
import type { ExplorerFiltersResponse, ExplorerQuery } from '../lib/types'

type Props = {
  filters: ExplorerFiltersResponse | null
  query: ExplorerQuery
  onQueryChange: (patch: Partial<ExplorerQuery>) => void
  onReset: () => void
  disabled?: boolean
}

export function FilterBar({ filters, query, onQueryChange, onReset, disabled = false }: Props) {
  const onTextChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target
    onQueryChange({ [name]: value })
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
        <span>Search title/summary</span>
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
            <option key={source} value={source}>
              {source}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Section</span>
        <select name="section" value={query.section} onChange={onTextChange} disabled={disabled}>
          <option value="">All sections</option>
          {(filters?.available_sections ?? []).map((section) => (
            <option key={section} value={section}>
              {section}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Semantic cluster</span>
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
        <span>Point limit</span>
        <select
          name="limit"
          value={String(query.limit)}
          onChange={(event) => onQueryChange({ limit: Number(event.target.value) })}
          disabled={disabled}
        >
          {[100, 250, 500].map((limit) => (
            <option key={limit} value={limit}>
              {limit}
            </option>
          ))}
        </select>
      </label>
      <div className="note-card">
        <strong>Cluster controls are real now</strong>
        <p>
          Cluster and outlier filters now come from persisted semantic analysis on embeddings, not from hand-wavy UI fiction.
        </p>
      </div>
    </div>
  )
}
