import { useEffect, useMemo, useRef, useState } from 'react'
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
  const [articleTypeMenuOpen, setArticleTypeMenuOpen] = useState(false)
  const articleTypeMenuRef = useRef<HTMLDivElement | null>(null)

  const activeArticleTypeLabel = useMemo(
    () => articleTypeOptions.find((option) => option.value === editorialTarget?.value)?.label ?? editorialTarget?.value ?? null,
    [articleTypeOptions, editorialTarget],
  )

  useEffect(() => {
    if (!articleTypeMenuOpen) return

    const handlePointerDown = (event: MouseEvent) => {
      if (!articleTypeMenuRef.current?.contains(event.target as Node)) {
        setArticleTypeMenuOpen(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setArticleTypeMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [articleTypeMenuOpen])

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

        <div className="explorer-toolbar-menu" ref={articleTypeMenuRef}>
          <button
            type="button"
            className={`explorer-toolbar-trigger${editorialTarget ? ' active' : ''}`}
            aria-haspopup="menu"
            aria-expanded={articleTypeMenuOpen}
            aria-label={editorialTarget ? `Article type lens: ${activeArticleTypeLabel}` : 'Article type lens'}
            onClick={() => setArticleTypeMenuOpen((open) => !open)}
          >
            <span>{editorialTarget ? `Type: ${activeArticleTypeLabel}` : 'Article type'}</span>
            <span className="explorer-toolbar-trigger-chevron" aria-hidden="true">▾</span>
          </button>

          {articleTypeMenuOpen && (
            <div className="explorer-toolbar-popover" role="menu" aria-label="Article type lens options">
              <button
                type="button"
                role="menuitemradio"
                aria-checked={editorialTarget === null}
                className={`explorer-toolbar-option${editorialTarget === null ? ' selected' : ''}`}
                onClick={() => {
                  onEditorialTargetChange(null)
                  setArticleTypeMenuOpen(false)
                }}
              >
                <span className="explorer-toolbar-option-label">Clear lens</span>
                <span className="explorer-toolbar-option-meta">All article types</span>
              </button>

              <div className="explorer-toolbar-popover-divider" />

              {articleTypeOptions.map((option) => {
                const selected = editorialTarget?.value === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    role="menuitemradio"
                    aria-checked={selected}
                    className={`explorer-toolbar-option${selected ? ' selected' : ''}`}
                    onClick={() => {
                      onEditorialTargetChange({ dimension: 'article_type', value: option.value })
                      setArticleTypeMenuOpen(false)
                    }}
                  >
                    <span className="explorer-toolbar-option-label">{option.label}</span>
                    <span className="explorer-toolbar-option-meta">
                      {option.count}
                      <span className="explorer-toolbar-option-check" aria-hidden="true">{selected ? '✓' : ''}</span>
                    </span>
                  </button>
                )
              })}
            </div>
          )}
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
