from __future__ import annotations

from pydantic import BaseModel, Field


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


class StoryClusterDetail(BaseModel):
    cluster: StoryClusterListItem
    members: list[StoryClusterMemberItem] = Field(default_factory=list)


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
