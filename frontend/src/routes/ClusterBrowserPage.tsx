import { ExplorerLayout } from '../components/ExplorerLayout'
import { ClusterFilterPanel } from '../components/ClusterFilterPanel'
import { ClusterInspectorPanel } from '../components/ClusterInspectorPanel'
import { ClusterListPanel } from '../components/ClusterListPanel'
import { ClusterStatusBar } from '../components/ClusterStatusBar'
import { useClusterBrowserData } from '../hooks/useClusterBrowserData'
import { useClusterFilters } from '../hooks/useClusterFilters'

export function ClusterBrowserPage() {
  const { query, activeFilterCount, updateQuery, resetQuery } = useClusterFilters()
  const {
    listState,
    filtersState,
    detailState,
    articleState,
    selectedCluster,
    selectedClusterId,
    selectedArticleId,
    setSelectedClusterId,
    setSelectedArticleId,
  } = useClusterBrowserData(query)

  return (
    <ExplorerLayout
      status={
        <ClusterStatusBar
          data={listState.data}
          activeFilterCount={activeFilterCount}
          selectedCluster={selectedCluster}
          selectedArticleId={selectedArticleId}
          onResetFilters={resetQuery}
        />
      }
      filters={
        <ClusterFilterPanel
          filters={filtersState.data}
          query={query}
          onQueryChange={updateQuery}
          onReset={resetQuery}
          disabled={listState.loading && !listState.data}
        />
      }
      map={
        <ClusterListPanel
          data={listState.data}
          loading={listState.loading}
          error={listState.error}
          selectedClusterId={selectedClusterId}
          onSelectCluster={(clusterId) => {
            setSelectedClusterId(clusterId)
            setSelectedArticleId(null)
          }}
          onNextPage={() => updateQuery({ offset: query.offset + query.limit })}
          onPreviousPage={() => updateQuery({ offset: Math.max(0, query.offset - query.limit) })}
        />
      }
      inspector={
        <ClusterInspectorPanel
          detail={detailState.data}
          article={articleState.data}
          loading={detailState.loading}
          articleLoading={articleState.loading}
          error={detailState.error}
          articleError={articleState.error}
          selectedArticleId={selectedArticleId}
          onSelectArticle={setSelectedArticleId}
        />
      }
    />
  )
}
