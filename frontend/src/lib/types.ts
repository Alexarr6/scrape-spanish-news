export type ExplorerSemanticSummary = {
  cluster_id: number | null
  cluster_size: number | null
  is_outlier: boolean
  source_neighbor_diversity: number | null
  neighbor_count: number
}

export type ExplorerPoint = {
  article_id: number
  source: string
  title: string
  url: string
  published_at: string
  published_date: string
  display_date: string
  section: string
  summary_snippet: string
  x: number
  y: number
  analysis: ExplorerSemanticSummary
}

export type ExplorerMeta = {
  total: number
  returned: number
  limit: number
  projection_set: string
  bounds: { min_x: number; max_x: number; min_y: number; max_y: number } | null
  available_sources: string[]
  available_sections: string[]
  available_clusters: number[]
}

export type ExplorerPointsResponse = {
  items: ExplorerPoint[]
  meta: ExplorerMeta
}

export type ExplorerFiltersResponse = {
  projection_set: string
  available_sources: string[]
  available_sections: string[]
  available_clusters: number[]
}
