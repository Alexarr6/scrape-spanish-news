import { isSemanticExplorerMode } from './lib/navigation'
import { ClusterBrowserPage } from './routes/ClusterBrowserPage'
import { ExplorerPage } from './routes/ExplorerPage'

export default function App() {
  return isSemanticExplorerMode() ? <ExplorerPage /> : <ClusterBrowserPage />
}
