import type { ExplorerColorMode, ExplorerViewMode, ExplorerVisualMode } from '../../lib/types'

type Props = {
  viewMode: ExplorerViewMode
  visualMode: ExplorerVisualMode
  colorMode: ExplorerColorMode
  pointCount: number
  activeFilterCount: number
  loading: boolean
  hasSelection: boolean
  onViewModeChange: (mode: ExplorerViewMode) => void
  onVisualModeChange: (mode: ExplorerVisualMode) => void
  onColorModeChange: (mode: ExplorerColorMode) => void
  onFitAll: () => void
  onFocusSelected: () => void
  onOpenFilters: () => void
}

const COLOR_MODE_LABELS: Record<ExplorerColorMode, string> = {
  neutral: 'Neutral',
  source: 'By source',
  cluster: 'By cluster',
  'active-match': 'Active match',
}

const VISUAL_MODE_LABELS: Record<ExplorerVisualMode, string> = {
  highlight: 'Highlight',
  filter: 'Filter',
}

export function ExplorerControlBar({
  viewMode,
  visualMode,
  colorMode,
  pointCount,
  activeFilterCount,
  loading,
  hasSelection,
  onViewModeChange,
  onVisualModeChange,
  onColorModeChange,
  onFitAll,
  onFocusSelected,
  onOpenFilters,
}: Props) {
  const pointCountLabel = loading
    ? pointCount === 0
      ? 'Loading…'
      : `${pointCount} points (updating)`
    : `${pointCount} points`

  return (
    <div className="explorer-control-bar">
      <div className="explorer-controls-left">
        <div className="segmented-control" role="group" aria-label="View mode">
          <button
            type="button"
            className={`segmented-button${viewMode === '2d' ? ' active' : ''}`}
            title="2D: flat layout for broad comparison"
            onClick={() => onViewModeChange('2d')}
          >
            2D
          </button>
          <button
            type="button"
            className={`segmented-button${viewMode === '3d' ? ' active' : ''}`}
            title="3D: depth view for cluster overlap inspection"
            onClick={() => onViewModeChange('3d')}
          >
            3D
          </button>
        </div>

        <div className="segmented-control" role="group" aria-label="Visual mode">
          {(['highlight', 'filter'] as ExplorerVisualMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`segmented-button${visualMode === mode ? ' active' : ''}`}
              onClick={() => onVisualModeChange(mode)}
            >
              {VISUAL_MODE_LABELS[mode]}
            </button>
          ))}
        </div>

        <div className="segmented-control" role="group" aria-label="Color mode">
          {(['neutral', 'source', 'cluster', 'active-match'] as ExplorerColorMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`segmented-button${colorMode === mode ? ' active' : ''}`}
              onClick={() => onColorModeChange(mode)}
            >
              {COLOR_MODE_LABELS[mode]}
            </button>
          ))}
        </div>

        <button className="btn-ghost" type="button" onClick={onFitAll}>
          Fit all
        </button>
        {hasSelection && (
          <button className="btn-ghost" type="button" onClick={onFocusSelected}>
            Focus selected
          </button>
        )}
      </div>

      <div className="explorer-controls-right">
        <span className="explorer-point-count">{pointCountLabel}</span>
        {activeFilterCount > 0 && <span className="badge accent">{activeFilterCount} filters</span>}
        <button className="btn-ghost" type="button" onClick={onOpenFilters}>
          Refine ↓
        </button>
      </div>
    </div>
  )
}
