import { useEffect, type ReactNode } from 'react'

type Props = {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  activeCount?: number
  onReset?: () => void
}

export function FilterDrawer({ open, onClose, title, children, activeCount, onReset }: Props) {
  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  return (
    <>
      {open && (
        <div
          className="filter-drawer-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <div
        className={`filter-drawer${open ? ' open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="filter-drawer-header">
          <span className="filter-drawer-title">{title}</span>
          <div className="filter-drawer-header-actions">
            {onReset && (
              <button className="btn-text" type="button" onClick={onReset}>
                Clear all
              </button>
            )}
            {activeCount != null && activeCount > 0 && (
              <span className="badge accent">{activeCount} active</span>
            )}
            <button className="btn-ghost" type="button" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
        <div className="filter-drawer-body">{children}</div>
      </div>
    </>
  )
}
