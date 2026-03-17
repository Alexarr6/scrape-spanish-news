import type { ExplorerMeta } from '../lib/types'

type Props = {
  meta: ExplorerMeta | null
}

export function StatusBar({ meta }: Props) {
  return (
    <div>
      <strong>Semantic Explorer</strong>
      <span className="status-chip">Phase 0 foundation</span>
      {meta ? (
        <span className="status-chip">
          {meta.returned}/{meta.total} articles · {meta.projection_set}
        </span>
      ) : null}
    </div>
  )
}
