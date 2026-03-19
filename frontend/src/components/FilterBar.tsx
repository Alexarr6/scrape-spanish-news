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

  const activeTokens = [query.search, query.source, query.section, query.clusterId, query.dateFrom, query.dateTo, query.outlierOnly ? 'outliers only' : ''].filter(Boolean)

  return (
    <div className="panel-section filter-stack">
      <div className="panel-header">
        <div>
          <h2>Explorer scope</h2>
          <p className="panel-help">This workspace is for spatial questions. Keep the subset intentional or the map turns into soup.</p>
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
          {activeTokens.length > 0 ? activeTokens.map((token) => <span key={token} className="status-chip subtle">{token}</span>) : <span className="status-chip">Entire semantic set</span>}
        </div>
      </div>

      <div className="filter-group">
        <div className="filter-group-header">
          <h3>Subset</h3>
          <span className="muted">Search, source, section</span>
        </div>
        <label className="field">
          <span>Search title or summary</span>
          <input name="search" value={query.search} onChange={onTextChange} placeholder="energy, election, housing…" disabled={disabled} />
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
      </div>

      <div className="filter-group">
        <div className="filter-group-header">
          <h3>Semantic structure</h3>
          <span className="muted">Cluster and anomaly controls</span>
        </div>
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
          <input type="checkbox" checked={query.outlierOnly} onChange={(event) => onQueryChange({ outlierOnly: event.target.checked })} disabled={disabled} />
          <span>Show only outliers</span>
        </label>
      </div>

      <div className="filter-group">
        <div className="filter-group-header">
          <h3>Window + density</h3>
          <span className="muted">Control point volume</span>
        </div>
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
          <select name="limit" value={String(query.limit)} onChange={(event) => onQueryChange({ limit: Number(event.target.value) })} disabled={disabled}>
            {[100, 250, 500].map((limit) => (
              <option key={limit} value={limit}>
                {limit}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="helper-card">
        <strong>Why this workspace exists</strong>
        <p>Use Explorer to spot semantic neighborhoods, isolate strange articles, and inspect cluster geometry. If you just need coverage comparison, Stories is the better home.</p>
      </div>
    </div>
  )
}
