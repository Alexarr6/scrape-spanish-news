import { buildArticleTypeOptions } from '../../lib/explorerEditorial'
import type {
  ExplorerColorMode,
  ExplorerEditorialMetadata,
  ExplorerEditorialTarget,
  ExplorerViewMode,
  ExplorerVisualMode,
} from '../../lib/types'

type Props = {
  viewMode: ExplorerViewMode
  visualMode: ExplorerVisualMode
  colorMode: ExplorerColorMode
  pointCount: number
  activeFilterCount: number
  loading: boolean
  hasSelection: boolean
  editorialTarget: ExplorerEditorialTarget
  editorialOptions: ExplorerEditorialMetadata | null
  onViewModeChange: (mode: ExplorerViewMode) => void
  onVisualModeChange: (mode: ExplorerVisualMode) => void
  onColorModeChange: (mode: ExplorerColorMode) => void
  onEditorialTargetChange: (target: ExplorerEditorialTarget) => void
  onFitAll: () => void
  onFocusSelected: () => void
  onOpenFilters: () => void
}

const COLOR_MODE_LABELS: Record<ExplorerColorMode, string> = {
  neutral: 'Neutral',
  source: 'By source',
  cluster: 'By cluster',
  'active-match': 'Active match',
  'article-type': 'Article type',
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
  editorialTarget,
  editorialOptions,
  onViewModeChange,
  onVisualModeChange,
  onColorModeChange,
  onEditorialTargetChange,
  onFitAll,
  onFocusSelected,
  onOpenFilters,
}: Props) {
  const pointCountLabel = loading
    ? pointCount === 0
      ? 'Loading…'
      : `${pointCount} points (updating)`
    : `${pointCount} points`

  const articleTypeOptions = buildArticleTypeOptions(editorialOptions)

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
          {(['neutral', 'source', 'cluster', 'active-match', 'article-type'] as ExplorerColorMode[]).map((mode) => (
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

        <label className="explorer-inline-field explorer-editorial-field">
          <span>Editorial lens</span>
          <div className="explorer-inline-field-row">
            <select
              aria-label="Article type editorial lens"
              value={editorialTarget?.value ?? ''}
              onChange={(event) => {
                const value = event.target.value
                onEditorialTargetChange(value ? { dimension: 'article_type', value } : null)
              }}
            >
              <option value="">Article type…</option>
              {articleTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label} · {option.count}
                </option>
              ))}
            </select>
            {editorialTarget && (
              <button className="btn-ghost" type="button" onClick={() => onEditorialTargetChange(null)}>
                Clear lens
              </button>
            )}
          </div>
        </label>

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
        {editorialTarget && <span className="badge accent">Article type lens</span>}
        {activeFilterCount > 0 && <span className="badge accent">{activeFilterCount} filters</span>}
        <button className="btn-ghost" type="button" onClick={onOpenFilters}>
          Refine ↓
        </button>
      </div>
    </div>
  )
}
