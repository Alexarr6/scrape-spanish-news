import type { ExplorerColorMode, ExplorerViewMode } from '../../lib/types'

type Props = {
  viewMode: ExplorerViewMode
  colorMode: ExplorerColorMode
  pointCount: number
  activeFilterCount: number
  loading: boolean
  hasSelection: boolean
  onViewModeChange: (mode: ExplorerViewMode) => void
  onColorModeChange: (mode: ExplorerColorMode) => void
  onFitAll: () => void
  onFocusSelected: () => void
  onOpenFilters: () => void
}

export function ExplorerControlBar({
  viewMode,
  colorMode,
  pointCount,
  activeFilterCount,
  loading,
  hasSelection,
  onViewModeChange,
  onColorModeChange,
  onFitAll,
  onFocusSelected,
  onOpenFilters,
}: Props) {
  return (
    <div className="explorer-control-bar">
      <div className="explorer-controls-left">
        {/* View mode */}
        <div className="segmented-control" role="group" aria-label="View mode">
          <button
            type="button"
            className={`segmented-button${viewMode === '2d' ? ' active' : ''}`}
            onClick={() => onViewModeChange('2d')}
          >
            2D
          </button>
          <button
            type="button"
            className={`segmented-button${viewMode === '3d' ? ' active' : ''}`}
            onClick={() => onViewModeChange('3d')}
          >
            3D
          </button>
        </div>

        {/* Color mode */}
        <div className="segmented-control" role="group" aria-label="Color lens">
          {(['neutral', 'source', 'cluster'] as ExplorerColorMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`segmented-button${colorMode === mode ? ' active' : ''}`}
              onClick={() => onColorModeChange(mode)}
            >
              {mode}
            </button>
          ))}
        </div>

        {/* Camera controls */}
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
        <span className="explorer-point-count">
          {loading && pointCount === 0 ? 'Loading…' : `${pointCount} points`}
        </span>
        {activeFilterCount > 0 && (
          <span className="badge accent">{activeFilterCount} filters</span>
        )}
        <button className="btn-ghost" type="button" onClick={onOpenFilters}>
          Refine ↓
        </button>
      </div>
    </div>
  )
}
