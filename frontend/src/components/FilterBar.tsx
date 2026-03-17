import type { ExplorerFiltersResponse } from '../lib/types'

type Props = {
  filters: ExplorerFiltersResponse | null
}

export function FilterBar({ filters }: Props) {
  return (
    <div>
      <h2>Foundation wiring</h2>
      <p>This phase only proves the API contract and UI structure.</p>
      <div className="stack">
        <div>
          <strong>Sources</strong>
          <ul>
            {(filters?.available_sources ?? []).map((source) => (
              <li key={source}>{source}</li>
            ))}
          </ul>
        </div>
        <div>
          <strong>Sections</strong>
          <ul>
            {(filters?.available_sections ?? []).map((section) => (
              <li key={section}>{section}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
