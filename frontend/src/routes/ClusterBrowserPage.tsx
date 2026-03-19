import type { ComponentType, ReactNode } from 'react'
import { ClusterFilterPanel } from '../components/ClusterFilterPanel'
import { ClusterInspectorPanel } from '../components/ClusterInspectorPanel'
import { ClusterListPanel } from '../components/ClusterListPanel'
import { ClusterStatusBar } from '../components/ClusterStatusBar'
import { useClusterBrowserData } from '../hooks/useClusterBrowserData'
import { useClusterUrlState } from '../hooks/useClusterUrlState'

type ShellProps = {
  section: string
  title: string
  description: string
  summary?: ReactNode
  actions?: ReactNode
  navItems: Array<{ key: string; label: string; description: string; href: string; active?: boolean }>
  status?: ReactNode
  filters?: ReactNode
  filtersTitle?: string
  main: ReactNode
  detail?: ReactNode
  detailTitle?: string
  contentClassName?: string
  mainClassName?: string
}

type Props = {
  navItems: ShellProps['navItems']
  shell: ComponentType<ShellProps>
}

export function ClusterBrowserPage({ navItems, shell: Shell }: Props) {
  const {
    query,
    activeFilterCount,
    updateQuery,
    resetQuery,
    selectedClusterId,
    selectedArticleId,
    setSelectedClusterId,
    setSelectedArticleId,
  } = useClusterUrlState()

  const { listState, filtersState, detailState, articleState, selectedCluster } = useClusterBrowserData(
    query,
    selectedClusterId,
    selectedArticleId,
    setSelectedClusterId,
    setSelectedArticleId,
  )

  return (
    <Shell
      section="Stories"
      title="Cluster browser"
      description="Start with the shared story, not with a random article. Compare coverage, source mix, and the cluster context before diving into individual pieces."
      summary={
        <>
          <span className="summary-pill emphasis">Default workspace</span>
          <span className="summary-pill">{listState.data?.meta.total ?? 0} clusters in scope</span>
          <span className="summary-pill">{activeFilterCount} active filters</span>
          <span className="summary-pill subtle">{selectedCluster ? `${selectedCluster.source_count} sources in selected story` : 'Select a story to inspect coverage'}</span>
        </>
      }
      navItems={navItems}
      status={
        <ClusterStatusBar
          data={listState.data}
          activeFilterCount={activeFilterCount}
          selectedCluster={selectedCluster}
          selectedArticleId={selectedArticleId}
          onResetFilters={resetQuery}
        />
      }
      filtersTitle="Story filters"
      filters={
        <ClusterFilterPanel
          filters={filtersState.data}
          query={query}
          onQueryChange={updateQuery}
          onReset={resetQuery}
          disabled={listState.loading && !listState.data}
        />
      }
      mainClassName="workspace-panel workspace-panel-main"
      main={
        <ClusterListPanel
          data={listState.data}
          loading={listState.loading}
          error={listState.error}
          selectedClusterId={selectedClusterId}
          onSelectCluster={setSelectedClusterId}
          onNextPage={() => updateQuery({ offset: query.offset + query.limit })}
          onPreviousPage={() => updateQuery({ offset: Math.max(0, query.offset - query.limit) })}
        />
      }
      detailTitle="Story detail"
      detail={
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
