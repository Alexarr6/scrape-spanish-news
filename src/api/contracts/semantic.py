from __future__ import annotations

from pydantic import BaseModel, Field


class ExplorerEditorialEvidence(BaseModel):
    type: str
    text: str
    note: str = ""


class ExplorerEditorialReviewFlags(BaseModel):
    missing_evidence: bool = False
    low_confidence: bool = False
    failed_analysis: bool = False
    unclear_bias: bool = False
    provider_missing: bool = False
    mapping_loss: bool = False
    out_of_domain: bool = False
    pending_analysis: bool = False
    needs_review: bool = False


class ExplorerEditorialDiagnosticsSummary(BaseModel):
    dimension_status: dict[str, str] = Field(default_factory=dict)


class ExplorerEditorialSummary(BaseModel):
    article_id: int
    analysis_status: str = "pending"
    editorial_applicability: str = "full"
    editorial_applicability_reason: str = "general_editorial_content"
    article_type: str = "unclear"
    article_type_confidence: float = 0.0
    bias_label: str = "unclear"
    bias_score: float = 0.0
    bias_confidence: float = 0.0
    tone_emotional: str = "unclear"
    tone_target: str = "unclear"
    opinionatedness: str = "unclear"
    sensationalism: str = "unclear"
    rhetorical_certainty: str = "unclear"
    framing_devices: list[str] = Field(default_factory=list)
    evidence_spans: list[ExplorerEditorialEvidence] = Field(default_factory=list)
    rationale: str = ""
    unclear_reasons: list[str] = Field(default_factory=list)
    review_flags: ExplorerEditorialReviewFlags = Field(default_factory=ExplorerEditorialReviewFlags)
    diagnostics_summary: ExplorerEditorialDiagnosticsSummary | None = None


class ExplorerSemanticSummary(BaseModel):
    cluster_id: int | None = None
    cluster_size: int | None = None
    is_outlier: bool = False
    local_density_distance: float | None = None
    source_neighbor_diversity: int | None = None
    nearby_sources: list[str] = Field(default_factory=list)
    neighbor_count: int = 0


class ExplorerPoint(BaseModel):
    article_id: int
    source: str
    title: str
    url: str
    published_at: str
    published_date: str = ""
    display_date: str = ""
    section: str = ""
    summary_snippet: str = ""
    x: float
    y: float
    z: float
    analysis: ExplorerSemanticSummary = Field(default_factory=ExplorerSemanticSummary)


class ExplorerProjectionBounds(BaseModel):
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float


class ExplorerClusterCentroid(BaseModel):
    x: float
    y: float
    z: float


class ExplorerClusterSummary(BaseModel):
    cluster_id: int
    size: int
    top_sources: dict[str, int] = Field(default_factory=dict)
    source_count: int = 0
    source_dominance: float = 0.0
    date_min: str = ""
    date_max: str = ""
    centroid: ExplorerClusterCentroid
    representative_article_ids: list[int] = Field(default_factory=list)


class ExplorerMeta(BaseModel):
    total: int
    returned: int
    limit: int
    projection_set: str
    bounds: ExplorerProjectionBounds | None = None
    available_sources: list[str] = Field(default_factory=list)
    available_sections: list[str] = Field(default_factory=list)
    available_clusters: list[int] = Field(default_factory=list)
    cluster_summaries: list[ExplorerClusterSummary] = Field(default_factory=list)


class ExplorerPointsResponse(BaseModel):
    items: list[ExplorerPoint]
    meta: ExplorerMeta


class ExplorerFiltersResponse(BaseModel):
    projection_set: str
    available_sources: list[str] = Field(default_factory=list)
    available_sections: list[str] = Field(default_factory=list)
    available_clusters: list[int] = Field(default_factory=list)
    cluster_summaries: list[ExplorerClusterSummary] = Field(default_factory=list)


class ExplorerNeighbor(BaseModel):
    article_id: int
    similarity: float
    source: str
    title: str
    url: str
    published_at: str
    published_date: str = ""
    display_date: str = ""
    section: str = ""
    summary_snippet: str = ""


class ExplorerArticleSummary(BaseModel):
    article_id: int
    source: str
    title: str
    url: str
    published_at: str
    published_date: str = ""
    display_date: str = ""
    section: str = ""
    summary: str = ""
    article_text_excerpt: str = ""


class ExplorerArticleDetail(BaseModel):
    article: ExplorerArticleSummary
    projection_set: str
    point: ExplorerPoint | None = None
    semantic_summary: ExplorerSemanticSummary = Field(default_factory=ExplorerSemanticSummary)
    editorial: ExplorerEditorialSummary | None = None
    neighbors: list[ExplorerNeighbor] = Field(default_factory=list)
