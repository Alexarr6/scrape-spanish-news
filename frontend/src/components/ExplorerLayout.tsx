import type { ReactNode } from 'react'

type Props = {
  status: ReactNode
  filters: ReactNode
  map: ReactNode
  inspector: ReactNode
}

export function ExplorerLayout({ status, filters, map, inspector }: Props) {
  return (
    <div className="app-shell">
      <header className="status-bar">{status}</header>
      <aside className="filter-panel">{filters}</aside>
      <main className="map-panel">{map}</main>
      <aside className="inspector-panel">{inspector}</aside>
    </div>
  )
}
