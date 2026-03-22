import type { NavItem } from './Shell'

type Props = {
  navItems: NavItem[]
  scopeLabel?: string
}

export function TopBar({ navItems, scopeLabel }: Props) {
  return (
    <header className="topbar">
      <span className="topbar-wordmark">Signal</span>
      <nav className="topbar-nav" aria-label="Primary navigation">
        {navItems.map((item) => (
          <a
            key={item.key}
            href={item.href}
            className={item.active ? 'topbar-nav-item active' : 'topbar-nav-item'}
            aria-current={item.active ? 'page' : undefined}
          >
            {item.label}
          </a>
        ))}
      </nav>
      {scopeLabel && (
        <span className="badge muted topbar-scope">{scopeLabel}</span>
      )}
    </header>
  )
}
