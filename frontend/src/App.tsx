import { Shell } from './components/layout/Shell'
import type { NavItem } from './components/layout/Shell'
import { buildClusterBrowserHref, buildSemanticExplorerHref, isSemanticExplorerMode } from './lib/navigation'
import { ClusterBrowserPage } from './routes/ClusterBrowserPage'
import { ExplorerPage } from './routes/ExplorerPage'

const navItems: NavItem[] = [
  {
    key: 'stories',
    label: 'Stories',
    href: buildClusterBrowserHref(),
    active: !isSemanticExplorerMode(),
  },
  {
    key: 'explorer',
    label: 'Explorer',
    href: buildSemanticExplorerHref({}),
    active: isSemanticExplorerMode(),
  },
]

export default function App() {
  return (
    <Shell navItems={navItems}>
      {isSemanticExplorerMode() ? <ExplorerPage /> : <ClusterBrowserPage />}
    </Shell>
  )
}
