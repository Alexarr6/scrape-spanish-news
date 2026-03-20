import type { ReactNode } from 'react'
import { TopBar } from './TopBar'

export type NavItem = {
  key: string
  label: string
  href: string
  active?: boolean
}

type Props = {
  navItems: NavItem[]
  children: ReactNode
}

export function Shell({ navItems, children }: Props) {
  return (
    <div className="app-shell">
      <TopBar navItems={navItems} />
      <main className="app-main">{children}</main>
    </div>
  )
}
