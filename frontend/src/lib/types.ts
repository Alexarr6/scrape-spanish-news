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
  dateFrom: string
  dateTo: string
  limit: number
}

export const DEFAULT_QUERY: ExplorerQuery = {
  search: '',
  source: '',
  section: '',
  dateFrom: '',
  dateTo: '',
  limit: 250,
}

export type LoadState<T> = {
  data: T | null
  loading: boolean
  error: string | null
}
