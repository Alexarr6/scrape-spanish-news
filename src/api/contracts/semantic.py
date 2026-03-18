from __future__ import annotations

from pydantic import BaseModel, Field


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
    neighbors: list[ExplorerNeighbor] = Field(default_factory=list)
