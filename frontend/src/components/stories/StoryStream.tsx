import { EmptyState } from '../system/EmptyState'
import { ErrorState } from '../system/ErrorState'
import { StoryCard } from './StoryCard'
import type { StoryClusterListResponse } from '../../lib/types'

type Props = {
  data: StoryClusterListResponse | null
  loading: boolean
  error: string | null
  selectedClusterId: number | null
  onSelectCluster: (clusterId: number) => void
  onNextPage: () => void
  onPreviousPage: () => void
}

export function StoryStream({
  data,
  loading,
  error,
  selectedClusterId,
  onSelectCluster,
  onNextPage,
  onPreviousPage,
}: Props) {
  const total = data?.meta.total ?? 0
  const start = data && total > 0 ? data.meta.offset + 1 : 0
  const end = data ? data.meta.offset + data.items.length : 0
  const hasPrev = data != null && data.meta.offset > 0
  const hasNext = data != null && data.meta.offset + data.meta.limit < data.meta.total

  return (
    <div className="story-stream">
      {/* Loading skeleton */}
      {loading && !data && (
        <div className="story-stream-loading" aria-label="Loading story clusters">
          {[1, 2, 3].map((i) => (
            <div key={i} className="story-card-skeleton" />
          ))}
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <ErrorState
          message="Failed to load stories"
          hint={error}
        />
      )}

      {/* Empty state */}
      {!loading && !error && data?.items.length === 0 && (
        <EmptyState
          title="No stories match the current filters"
          hint="Clear a filter or widen the date window."
        />
      )}

      {/* Story cards */}
      {(data?.items ?? []).map((cluster) => (
        <StoryCard
          key={cluster.id}
          cluster={cluster}
          selected={selectedClusterId === cluster.id}
          onClick={() => onSelectCluster(cluster.id)}
        />
      ))}

      {/* Pagination */}
      {data && total > 0 && (
        <div className="story-pagination">
          <button
            className="btn-ghost"
            type="button"
            onClick={onPreviousPage}
            disabled={!hasPrev}
          >
            ← Previous
          </button>
          <span className="story-pagination-info">
            {start}–{end} of {total}
          </span>
          <button
            className="btn-ghost"
            type="button"
            onClick={onNextPage}
            disabled={!hasNext}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
