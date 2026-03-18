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

export type ClusterFilterOption = {
  value: string
  label: string
  count: number
}

export type ClusterEntityOption = {
  slug: string
  name: string
  entity_type: string
  count: number
}

export type ClusterTagSummary = {
  tag_code: string
  display_name: string
  tag_group: string
}

export type ClusterEntitySummary = {
  entity_id: number
  slug: string
  name: string
  entity_type: string
  article_coverage_count: number
  mention_count: number
}

export type StoryClusterListItem = {
  id: number
  cluster_key: string
  status: string
  cluster_type: string
  summary_headline: string
  summary_text: string
  article_count: number
  source_count: number
  first_article_published_at: string | null
  last_article_published_at: string | null
  sources: string[]
  primary_tag: ClusterTagSummary | null
  top_entities: ClusterEntitySummary[]
}

export type StoryClusterMemberItem = {
  article_id: number
  source: string
  title: string
  url: string
  published_at: string | null
  section: string
  summary: string
  membership_score: number
  tags: ClusterTagSummary[]
  entities: ClusterEntitySummary[]
}

export type StoryClusterDetail = {
  cluster: StoryClusterListItem
  members: StoryClusterMemberItem[]
}

export type StoryClusterListResponse = {
  items: StoryClusterListItem[]
  meta: {
    total: number
    limit: number
    offset: number
  }
}

export type StoryClusterFiltersResponse = {
  sources: ClusterFilterOption[]
  tags: ClusterFilterOption[]
  entities: ClusterEntityOption[]
}

export type StoryClusterQuery = {
  search: string
  source: string
  tagCode: string
  entitySlug: string
  dateFrom: string
  dateTo: string
  limit: number
  offset: number
}

export const DEFAULT_CLUSTER_QUERY: StoryClusterQuery = {
  search: '',
  source: '',
  tagCode: '',
  entitySlug: '',
  dateFrom: '',
  dateTo: '',
  limit: 20,
  offset: 0,
}

export type LoadState<T> = {
  data: T | null
  loading: boolean
  error: string | null
}
