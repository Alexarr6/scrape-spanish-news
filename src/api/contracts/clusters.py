from __future__ import annotations

from pydantic import BaseModel, Field


class StoryClusterMemberEditorialPreviewReviewFlags(BaseModel):
    low_confidence: bool = False
    needs_review: bool = False


class StoryClusterMemberEditorialPreview(BaseModel):
    analysis_status: str = "pending"
    article_type: str = "unclear"
    bias_label: str = "unclear"
    bias_confidence: float = 0.0
    editorial_applicability: str = "full"
    review_flags: StoryClusterMemberEditorialPreviewReviewFlags = Field(
        default_factory=StoryClusterMemberEditorialPreviewReviewFlags
    )


class StoryClusterEditorialFramingSummary(BaseModel):
    framing_device: str
    count: int
    example_article_ids: list[int] = Field(default_factory=list)


class StoryClusterEditorialReviewFlagCounts(BaseModel):
    low_confidence: int = 0
    needs_review: int = 0
    out_of_domain: int = 0
    limited: int = 0


class StoryClusterEditorialSourceSummary(BaseModel):
    source: str
    article_count: int
    analyzed_article_count: int
    applicability_breakdown: dict[str, int] = Field(default_factory=dict)
    article_type_breakdown: dict[str, int] = Field(default_factory=dict)
    bias_label_breakdown: dict[str, int] = Field(default_factory=dict)
    opinionatedness_breakdown: dict[str, int] = Field(default_factory=dict)
    tone_emotional_breakdown: dict[str, int] = Field(default_factory=dict)
    top_framing_devices: list[StoryClusterEditorialFramingSummary] = Field(default_factory=list)
    review_flag_counts: StoryClusterEditorialReviewFlagCounts = Field(
        default_factory=StoryClusterEditorialReviewFlagCounts
    )


class StoryClusterEditorialSignal(BaseModel):
    label: str
    strength: str
    supporting_sources: list[str] = Field(default_factory=list)
    example_article_ids: list[int] = Field(default_factory=list)
    note: str = ""


class StoryClusterEditorialComparativeSource(BaseModel):
    source: str
    usable_article_count: int = 0
    full_applicability_count: int = 0
    limited_applicability_count: int = 0
    low_confidence_count: int = 0
    comparison_eligibility: str = "insufficient_sample"
    comparison_note: str = ""


class StoryClusterEditorialComparativeSourceMetric(BaseModel):
    source: str
    usable_article_count: int = 0
    opinionatedness_index: float | None = None
    emotional_tone_index: float | None = None
    bias_direction_index: float | None = None
    framing_concentration_index: float | None = None
    confidence_band: str = "insufficient"
    metric_notes: list[str] = Field(default_factory=list)


class StoryClusterEditorialComparativeSignalSupport(BaseModel):
    leading_usable_articles: int = 0
    trailing_usable_articles: int = 0
    compared_sources: list[str] = Field(default_factory=list)


class StoryClusterEditorialComparativeSignal(BaseModel):
    dimension: str
    label: str
    leading_source: str
    trailing_source: str
    delta: float = 0.0
    strength: str
    support: StoryClusterEditorialComparativeSignalSupport = Field(
        default_factory=StoryClusterEditorialComparativeSignalSupport
    )
    note: str = ""
    example_article_ids: list[int] = Field(default_factory=list)


class StoryClusterEditorialComparativeMetrics(BaseModel):
    eligible_source_count: int = 0
    minimum_articles_per_source: int = 2
    included_sources: list[StoryClusterEditorialComparativeSource] = Field(default_factory=list)
    source_metrics: list[StoryClusterEditorialComparativeSourceMetric] = Field(default_factory=list)
    divergence_signals: list[StoryClusterEditorialComparativeSignal] = Field(default_factory=list)
    comparison_note: str = ""


class StoryClusterEditorialSummary(BaseModel):
    analyzed_article_count: int = 0
    pending_article_count: int = 0
    failed_article_count: int = 0
    applicability_breakdown: dict[str, int] = Field(default_factory=dict)
    article_type_breakdown: dict[str, int] = Field(default_factory=dict)
    source_summaries: list[StoryClusterEditorialSourceSummary] = Field(default_factory=list)
    cluster_signals: list[StoryClusterEditorialSignal] = Field(default_factory=list)
    comparative_metrics: StoryClusterEditorialComparativeMetrics | None = None
    confidence_note: str = ""
    scope_note: str = ""


class ClusterFilterOption(BaseModel):
    value: str
    label: str
    count: int = 0


class ClusterEntityOption(BaseModel):
    slug: str
    name: str
    entity_type: str
    count: int = 0


class ClusterTagSummary(BaseModel):
    tag_code: str
    display_name: str
    tag_group: str


class ClusterEntitySummary(BaseModel):
    entity_id: int
    slug: str
    name: str
    entity_type: str
    article_coverage_count: int = 0
    mention_count: int = 0


class StoryClusterListItem(BaseModel):
    id: int
    cluster_key: str
    status: str
    cluster_type: str
    summary_headline: str
    summary_text: str
    article_count: int
    source_count: int
    first_article_published_at: str | None = None
    last_article_published_at: str | None = None
    sources: list[str] = Field(default_factory=list)
    primary_tag: ClusterTagSummary | None = None
    top_entities: list[ClusterEntitySummary] = Field(default_factory=list)


class StoryClusterMemberItem(BaseModel):
    article_id: int
    source: str
    title: str
    url: str
    published_at: str | None = None
    section: str = ""
    summary: str = ""
    membership_score: float
    tags: list[ClusterTagSummary] = Field(default_factory=list)
    entities: list[ClusterEntitySummary] = Field(default_factory=list)
    editorial_preview: StoryClusterMemberEditorialPreview | None = None


class StoryClusterDetail(BaseModel):
    cluster: StoryClusterListItem
    members: list[StoryClusterMemberItem] = Field(default_factory=list)
    editorial_summary: StoryClusterEditorialSummary | None = None


class StoryClusterListMeta(BaseModel):
    total: int
    limit: int
    offset: int


class StoryClusterListResponse(BaseModel):
    items: list[StoryClusterListItem]
    meta: StoryClusterListMeta


class StoryClusterFiltersResponse(BaseModel):
    sources: list[ClusterFilterOption] = Field(default_factory=list)
    tags: list[ClusterFilterOption] = Field(default_factory=list)
    entities: list[ClusterEntityOption] = Field(default_factory=list)
