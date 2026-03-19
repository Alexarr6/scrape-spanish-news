import { AppShell } from './components/AppShell'
import { buildClusterBrowserHref, buildSemanticExplorerHref, isSemanticExplorerMode } from './lib/navigation'
import { ClusterBrowserPage } from './routes/ClusterBrowserPage'
import { ExplorerPage } from './routes/ExplorerPage'

const navItems = [
  {
    key: 'stories',
    label: 'Stories',
    description: 'Cluster-first workspace for coverage comparison.',
    href: buildClusterBrowserHref(),
    active: !isSemanticExplorerMode(),
  },
  {
    key: 'explorer',
    label: 'Explorer',
    description: 'Semantic map for spatial and cluster analysis.',
    href: buildSemanticExplorerHref({}),
    active: isSemanticExplorerMode(),
  },
]

export default function App() {
  return isSemanticExplorerMode() ? <ExplorerPage navItems={navItems} shell={AppShell} /> : <ClusterBrowserPage navItems={navItems} shell={AppShell} />
}
