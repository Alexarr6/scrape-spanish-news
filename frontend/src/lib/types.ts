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

export type ExplorerEditorialEvidence = {
  type: string
  text: string
  note: string
}

export type ExplorerEditorialReviewFlags = {
  missing_evidence: boolean
  low_confidence: boolean
  failed_analysis: boolean
  unclear_bias: boolean
  provider_missing: boolean
  mapping_loss: boolean
  out_of_domain: boolean
  pending_analysis: boolean
  needs_review: boolean
}

export type ExplorerEditorialSummary = {
  article_id: number
  analysis_status: string
  editorial_applicability: 'full' | 'limited' | 'out_of_domain'
  editorial_applicability_reason: string
  article_type: string
  article_type_confidence: number
  bias_label: string
  bias_score: number
  bias_confidence: number
  tone_emotional: string
  tone_target: string
  opinionatedness: string
  sensationalism: string
  rhetorical_certainty: string
  framing_devices: string[]
  evidence_spans: ExplorerEditorialEvidence[]
  rationale: string
  unclear_reasons: string[]
  review_flags: ExplorerEditorialReviewFlags
  diagnostics_summary: { dimension_status: Record<string, string> } | null
}

export type ExplorerArticleDetail = {
  article: ExplorerArticleSummary
  projection_set: string
  point: ExplorerPoint | null
  semantic_summary: ExplorerSemanticSummary
  editorial: ExplorerEditorialSummary | null
  neighbors: ExplorerNeighbor[]
}

export type ExplorerQuery = {
  search: string
  source: string
  section: string
  clusterId: string
  storyClusterId: string
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
  storyClusterId: '',
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

export type StoryClusterMemberEditorialPreview = {
  analysis_status: string
  article_type: string
  bias_label: string
  bias_confidence: number
  editorial_applicability: 'full' | 'limited' | 'out_of_domain'
  review_flags: {
    low_confidence: boolean
    needs_review: boolean
  }
}

export type StoryClusterEditorialSourceSummary = {
  source: string
  article_count: number
  analyzed_article_count: number
  applicability_breakdown: Record<string, number>
  article_type_breakdown: Record<string, number>
  bias_label_breakdown: Record<string, number>
  opinionatedness_breakdown: Record<string, number>
  tone_emotional_breakdown: Record<string, number>
  top_framing_devices: Array<{
    framing_device: string
    count: number
    example_article_ids: number[]
  }>
  review_flag_counts: {
    low_confidence: number
    needs_review: number
    out_of_domain: number
    limited: number
  }
}

export type StoryClusterEditorialSignal = {
  label: string
  strength: 'strong' | 'moderate' | 'weak'
  supporting_sources: string[]
  example_article_ids: number[]
  note: string
}

export type StoryClusterEditorialComparativeSource = {
  source: string
  usable_article_count: number
  full_applicability_count: number
  limited_applicability_count: number
  low_confidence_count: number
  comparison_eligibility: 'eligible' | 'limited' | 'insufficient_sample'
  comparison_note: string
}

export type StoryClusterEditorialComparativeSourceMetric = {
  source: string
  usable_article_count: number
  opinionatedness_index: number | null
  emotional_tone_index: number | null
  bias_direction_index: number | null
  framing_concentration_index: number | null
  confidence_band: 'high' | 'moderate' | 'low' | 'insufficient'
  metric_notes: string[]
}

export type StoryClusterEditorialComparativeSignal = {
  dimension: 'bias' | 'opinionatedness' | 'tone' | 'framing'
  label: string
  leading_source: string
  trailing_source: string
  delta: number
  strength: 'strong' | 'moderate' | 'weak'
  support: {
    leading_usable_articles: number
    trailing_usable_articles: number
    compared_sources: string[]
  }
  note: string
  example_article_ids: number[]
}

export type StoryClusterEditorialComparativeMetrics = {
  eligible_source_count: number
  minimum_articles_per_source: number
  included_sources: StoryClusterEditorialComparativeSource[]
  source_metrics: StoryClusterEditorialComparativeSourceMetric[]
  divergence_signals: StoryClusterEditorialComparativeSignal[]
  comparison_note: string
}

export type StoryClusterEditorialSummary = {
  analyzed_article_count: number
  pending_article_count: number
  failed_article_count: number
  applicability_breakdown: Record<string, number>
  article_type_breakdown: Record<string, number>
  source_summaries: StoryClusterEditorialSourceSummary[]
  cluster_signals: StoryClusterEditorialSignal[]
  comparative_metrics: StoryClusterEditorialComparativeMetrics | null
  confidence_note: string
  scope_note: string
}

export type StoryClusterMemberDiagnostics = {
  support_edge_count: number
  best_support_score: number
  mean_support_score: number
  supporting_article_ids: number[]
  accepted_via_guarded_merge: boolean
  risky_bridge_support: boolean
  penalties: string[]
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
  membership_diagnostics: StoryClusterMemberDiagnostics | null
  tags: ClusterTagSummary[]
  entities: ClusterEntitySummary[]
  editorial_preview: StoryClusterMemberEditorialPreview | null
}

export type StoryClusterDetail = {
  cluster: StoryClusterListItem
  members: StoryClusterMemberItem[]
  editorial_summary: StoryClusterEditorialSummary | null
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
