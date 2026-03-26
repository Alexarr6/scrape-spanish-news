import { Shell } from './components/layout/Shell'
import type { NavItem } from './components/layout/Shell'
import { buildExplorerSurfaceHref, buildStoriesSurfaceHref } from './lib/navigation'
import { getAppModeFromSearch } from './lib/urlState'
import { ClusterBrowserPage } from './routes/ClusterBrowserPage'
import { ExplorerPage } from './routes/ExplorerPage'

export default function App() {
  const appMode = getAppModeFromSearch()

  const navItems: NavItem[] = [
    {
      key: 'stories',
      label: 'Stories',
      href: buildStoriesSurfaceHref(),
      active: appMode === 'stories',
    },
    {
      key: 'explorer',
      label: 'Explorer',
      href: buildExplorerSurfaceHref({}),
      active: appMode === 'explorer',
    },
  ]

  return (
    <Shell navItems={navItems}>
      {appMode === 'explorer' ? <ExplorerPage /> : <ClusterBrowserPage />}
    </Shell>
  )
}
