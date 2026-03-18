from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.analysis.taxonomy import validate_tag_codes

ARTICLE_TYPES = (
    "news_report",
    "live_blog",
    "analysis",
    "opinion",
    "editorial",
    "interview",
    "feature",
    "explainer",
    "other",
)
ENTITY_TYPES = (
    "politician",
    "political_party",
    "person",
    "organization",
    "institution",
    "country",
    "region_city",
    "company",
    "event",
)


class ArticleAnalysisExtractedEntity(BaseModel):
    entity_type: Literal[
        "politician",
        "political_party",
        "person",
        "organization",
        "institution",
        "country",
        "region_city",
        "company",
        "event",
    ]
    canonical_name: str = Field(min_length=2, max_length=200)
    aliases: list[str] = Field(default_factory=list, max_length=5)
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    role_hint: str | None = Field(default=None, max_length=80)


class ArticleEnrichmentPayload(BaseModel):
    article_type: Literal[
        "news_report",
        "live_blog",
        "analysis",
        "opinion",
        "editorial",
        "interview",
        "feature",
        "explainer",
        "other",
    ]
    article_type_confidence: float = Field(ge=0.0, le=1.0)
    is_event_coverage: bool = True
    language: str = Field(default="es", min_length=2, max_length=10)
    primary_tag_code: str | None = None
    secondary_tag_codes: list[str] = Field(default_factory=list, max_length=3)
    entities: list[ArticleAnalysisExtractedEntity] = Field(default_factory=list, max_length=12)
    key_phrases: list[str] = Field(default_factory=list, max_length=5)
    claims: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("primary_tag_code")
    @classmethod
    def _validate_primary(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_tag_codes([value])[0]

    @field_validator("secondary_tag_codes")
    @classmethod
    def _validate_secondary(cls, value: list[str]) -> list[str]:
        return validate_tag_codes(value)


class OpenRouterUsage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ArticleAnalysisRead(BaseModel):
    article_id: int
    article_type: str
    article_type_confidence: float
    is_event_coverage: bool
    language: str
    primary_topic_tag_id: int | None = None
    key_phrases_json: str = "[]"
    claims_json: str = "[]"
    extraction_version: str
    content_hash: str
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EntityRead(BaseModel):
    id: int
    entity_type: str
    canonical_name: str
    normalized_name: str
    slug: str
    canonical_source: str

    model_config = ConfigDict(from_attributes=True)


class EntityMentionRead(BaseModel):
    id: int
    article_id: int
    entity_id: int
    surface_form: str
    mention_text_normalized: str
    mention_count: int
    title_hits: int
    summary_hits: int
    body_hits: int
    relevance_score: float
    role_hint: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TagRead(BaseModel):
    id: int
    tag_code: str
    display_name: str
    tag_group: str
    description: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class StoryClusterRead(BaseModel):
    id: int
    cluster_key: str
    status: str
    cluster_type: str
    summary_headline: str
    summary_text: str
    article_count: int
    source_count: int
    clustering_version: str

    model_config = ConfigDict(from_attributes=True)


class StoryClusterMemberReason(BaseModel):
    score: float
    semantic_similarity: float
    title_similarity: float
    shared_entity_score: float
    tag_overlap_score: float
    keyphrase_overlap_score: float
    temporal_proximity_score: float
    hard_block: str | None = None
    penalties: list[str] = Field(default_factory=list)


class PairScoreArtifact(BaseModel):
    left_article_id: int
    right_article_id: int
    accepted: bool
    reason: StoryClusterMemberReason


class ClusterRebuildMetrics(BaseModel):
    article_count: int = 0
    candidate_pair_count: int = 0
    accepted_pair_count: int = 0
    rejected_pair_count: int = 0
    cluster_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class EnrichmentRunMetrics(BaseModel):
    article_count: int = 0
    enriched_count: int = 0
    skipped_count: int = 0
    request_count: int = 0
    invalid_schema_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class StoryClusterQuery(BaseModel):
    days_back: int | None = Field(default=None, ge=1)
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=100, ge=1, le=1000)
