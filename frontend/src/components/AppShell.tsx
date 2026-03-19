import type { ReactNode } from 'react'

type NavItem = {
  key: string
  label: string
  description: string
  href: string
  active?: boolean
}

type Props = {
  section: string
  title: string
  description: string
  summary?: ReactNode
  actions?: ReactNode
  navItems: NavItem[]
  status?: ReactNode
  filters?: ReactNode
  filtersTitle?: string
  main: ReactNode
  detail?: ReactNode
  detailTitle?: string
  mainClassName?: string
  contentClassName?: string
}

export function AppShell({
  section,
  title,
  description,
  summary,
  actions,
  navItems,
  status,
  filters,
  filtersTitle = 'Refine',
  main,
  detail,
  detailTitle = 'Context',
  mainClassName,
  contentClassName,
}: Props) {
  return (
    <div className="product-shell">
      <aside className="app-sidebar">
        <div className="brand-block">
          <div className="brand-kicker">Spain media analysis</div>
          <h1>Signal over noise</h1>
          <p>Serious story clustering and semantic exploration without the demo-scene nonsense.</p>
        </div>

        <nav className="primary-nav" aria-label="Primary">
          {navItems.map((item) => (
            <a
              key={item.key}
              className={item.active ? 'nav-item active' : 'nav-item'}
              href={item.href}
              aria-current={item.active ? 'page' : undefined}
            >
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </a>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="eyebrow">Workspace</span>
          <strong>{section}</strong>
          <p>Keep clusters as the default read of reality. Use the explorer when you need semantic shape, not before.</p>
        </div>
      </aside>

      <div className="app-main-shell">
        <header className="page-header">
          <div className="page-header-main">
            <div className="eyebrow">{section}</div>
            <h2>{title}</h2>
            <p className="page-description">{description}</p>
            {summary ? <div className="page-summary">{summary}</div> : null}
          </div>
          {actions ? <div className="page-actions">{actions}</div> : null}
        </header>

        {status ? <section className="status-strip">{status}</section> : null}

        <div className={contentClassName ?? 'workspace-grid'}>
          {filters ? (
            <aside className="workspace-panel workspace-panel-filters">
              <div className="workspace-panel-header">
                <span className="eyebrow">Refine</span>
                <h3>{filtersTitle}</h3>
              </div>
              {filters}
            </aside>
          ) : null}

          <main className={mainClassName ?? 'workspace-panel workspace-panel-main'}>{main}</main>

          {detail ? (
            <aside className="workspace-panel workspace-panel-detail">
              <div className="workspace-panel-header">
                <span className="eyebrow">Context</span>
                <h3>{detailTitle}</h3>
              </div>
              {detail}
            </aside>
          ) : null}
        </div>
      </div>
    </div>
  )
}
