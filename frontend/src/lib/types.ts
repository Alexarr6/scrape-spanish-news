export type ExplorerSemanticSummary = {
  cluster_id: number | null
  cluster_size: number | null
  is_outlier: boolean
  local_density_distance: number | null
  source_neighbor_diversity: number | null
  nearby_sources: string[]
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
  z: number
  analysis: ExplorerSemanticSummary
}

export type ExplorerProjectionBounds = {
  min_x: number
  max_x: number
  min_y: number
  max_y: number
  min_z: number
  max_z: number
}

export type ExplorerClusterSummary = {
  cluster_id: number
  size: number
  top_sources: Record<string, number>
  source_count: number
  source_dominance: number
  date_min: string
  date_max: string
  centroid: { x: number; y: number; z: number }
  representative_article_ids: number[]
}

export type ExplorerMeta = {
  total: number
  returned: number
  limit: number
  projection_set: string
  bounds: ExplorerProjectionBounds | null
  available_sources: string[]
  available_sections: string[]
  available_clusters: number[]
  cluster_summaries: ExplorerClusterSummary[]
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
  cluster_summaries: ExplorerClusterSummary[]
}

export type ExplorerNeighbor = {
  article_id: number
  similarity: number
  source: string
  title: string
  url: string
  published_at: string
  published_date: string
  display_date: string
  section: string
  summary_snippet: string
}

export type ExplorerArticleSummary = {
  article_id: number
  source: string
  title: string
  url: string
  published_at: string
  published_date: string
  display_date: string
  section: string
  summary: string
  article_text_excerpt: string
}

export type ExplorerArticleDetail = {
  article: ExplorerArticleSummary
  projection_set: string
  point: ExplorerPoint | null
  semantic_summary: ExplorerSemanticSummary
  neighbors: ExplorerNeighbor[]
}

export type ExplorerQuery = {
  search: string
  source: string
  section: string
  clusterId: string
  dateFrom: string
  dateTo: string
  outlierOnly: boolean
  limit: number
}

export type ExplorerViewMode = '2d' | '3d'
export type ExplorerColorMode = 'neutral' | 'source' | 'cluster'

export const DEFAULT_QUERY: ExplorerQuery = {
  search: '',
  source: '',
  section: '',
  clusterId: '',
  dateFrom: '',
  dateTo: '',
  outlierOnly: false,
  limit: 250,
}

export type LoadState<T> = {
  data: T | null
  loading: boolean
  error: string | null
}
