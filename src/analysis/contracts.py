from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
EDITORIAL_ARTICLE_TYPES = ARTICLE_TYPES + ("unclear",)
BIAS_LABELS = (
    "far_left",
    "left",
    "center_left",
    "center",
    "center_right",
    "right",
    "far_right",
    "unclear",
)
TONE_EMOTIONAL_VALUES = ("calm", "loaded", "inflammatory", "unclear")
TONE_TARGET_VALUES = ("supportive", "neutral", "critical", "hostile", "mixed", "unclear")
OPINIONATEDNESS_VALUES = (
    "straight_reporting",
    "interpretive",
    "opinionated",
    "activist",
    "unclear",
)
SENSATIONALISM_VALUES = ("low", "medium", "high", "unclear")
RHETORICAL_CERTAINTY_VALUES = ("cautious", "assertive", "absolute", "unclear")
FRAMING_DEVICE_VALUES = (
    "conflict",
    "economic_consequence",
    "moral_judgment",
    "public_order_security",
    "identity_culture",
    "governance_competence",
    "corruption_scandal",
    "humanitarian",
    "victimization",
    "progress_modernization",
    "institutional_stability",
    "strategic_geopolitics",
)
EVIDENCE_SPAN_TYPES = ("headline", "summary", "body")
EDITORIAL_ANALYSIS_STATUSES = ("pending", "completed", "failed", "skipped")


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


class ArticleEditorialEvidenceSpan(BaseModel):
    type: Literal["headline", "summary", "body"]
    text: str = Field(min_length=3, max_length=400)
    note: str = Field(min_length=3, max_length=240)

    @field_validator("text", "note")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class ArticleEditorialAnalysisRawPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    article_type: str | None = None
    article_type_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    bias_label: str | None = None
    ideological_bias_framing: str | dict[str, Any] | None = None
    bias_score: float | None = None
    bias_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tone_emotional: str | None = None
    tone_target: str | None = None
    opinionatedness: str | None = None
    sensationalism: str | None = None
    rhetorical_certainty: str | None = None
    tone_dimensions: dict[str, Any] | None = None
    framing_devices: list[Any] = Field(default_factory=list, max_length=8)
    evidence_spans: list[Any] = Field(default_factory=list, max_length=6)
    rationale: str | dict[str, Any] | None = Field(default=None)
    notes: str | None = Field(default=None, max_length=500)
    uncertainty_reason: str | None = Field(default=None, max_length=500)


class ArticleEditorialAnalysisPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
        "unclear",
    ]
    article_type_confidence: float = Field(ge=0.0, le=1.0)
    bias_label: Literal[
        "far_left",
        "left",
        "center_left",
        "center",
        "center_right",
        "right",
        "far_right",
        "unclear",
    ]
    bias_score: float = Field(ge=-1.0, le=1.0)
    bias_confidence: float = Field(ge=0.0, le=1.0)
    tone_emotional: Literal["calm", "loaded", "inflammatory", "unclear"]
    tone_target: Literal["supportive", "neutral", "critical", "hostile", "mixed", "unclear"]
    opinionatedness: Literal[
        "straight_reporting",
        "interpretive",
        "opinionated",
        "activist",
        "unclear",
    ]
    sensationalism: Literal["low", "medium", "high", "unclear"]
    rhetorical_certainty: Literal["cautious", "assertive", "absolute", "unclear"]
    framing_devices: list[
        Literal[
            "conflict",
            "economic_consequence",
            "moral_judgment",
            "public_order_security",
            "identity_culture",
            "governance_competence",
            "corruption_scandal",
            "humanitarian",
            "victimization",
            "progress_modernization",
            "institutional_stability",
            "strategic_geopolitics",
        ]
    ] = Field(default_factory=list, max_length=5)
    evidence_spans: list[ArticleEditorialEvidenceSpan] = Field(default_factory=list, max_length=3)
    rationale: str = Field(min_length=12, max_length=1200)

    @field_validator("framing_devices")
    @classmethod
    def _ensure_unique_framing_devices(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("framing_devices must not contain duplicates")
        return value

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 12:
            raise ValueError("rationale is too short")
        return cleaned

    @field_validator("evidence_spans")
    @classmethod
    def _validate_evidence_spans(
        cls, value: list[ArticleEditorialEvidenceSpan]
    ) -> list[ArticleEditorialEvidenceSpan]:
        if not value:
            raise ValueError("at least one evidence span is required")
        return value

    @model_validator(mode="after")
    def _validate_bias_semantics(self) -> "ArticleEditorialAnalysisPayload":
        label_direction = {
            "far_left": -0.9,
            "left": -0.65,
            "center_left": -0.35,
            "center": 0.0,
            "center_right": 0.35,
            "right": 0.65,
            "far_right": 0.9,
            "unclear": 0.0,
        }
        target = label_direction[self.bias_label]
        if self.bias_label == "unclear":
            if abs(self.bias_score) > 0.2:
                raise ValueError("bias_score must stay near neutral when bias_label is unclear")
            if self.bias_confidence > 0.6:
                raise ValueError(
                    "bias_confidence must stay low/moderate when bias_label is unclear"
                )
        elif self.bias_label == "center":
            if abs(self.bias_score) > 0.3:
                raise ValueError("center bias_label requires a near-neutral bias_score")
        else:
            if target < 0 and self.bias_score > -0.1:
                raise ValueError("left-leaning labels require a meaningfully negative bias_score")
            if target > 0 and self.bias_score < 0.1:
                raise ValueError("right-leaning labels require a meaningfully positive bias_score")
            if abs(self.bias_score - target) > 0.55:
                raise ValueError("bias_score is inconsistent with bias_label")

        if self.article_type == "unclear" and self.article_type_confidence > 0.6:
            raise ValueError(
                "article_type_confidence must stay low/moderate when article_type is unclear"
            )
        if self.tone_emotional == "inflammatory" and self.sensationalism == "low":
            raise ValueError("inflammatory tone cannot pair with low sensationalism")
        if self.tone_target == "hostile" and self.opinionatedness == "straight_reporting":
            raise ValueError("hostile tone is inconsistent with straight_reporting")
        if self.rhetorical_certainty == "absolute" and self.bias_confidence < 0.2:
            raise ValueError(
                "absolute rhetorical certainty with near-zero bias_confidence is inconsistent"
            )
        return self


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


class ArticleEditorialAnalysisRead(BaseModel):
    article_id: int
    article_type: str
    article_type_confidence: float
    bias_label: str
    bias_score: float
    bias_confidence: float
    tone_emotional: str
    tone_target: str
    opinionatedness: str
    sensationalism: str
    rhetorical_certainty: str
    framing_devices_json: str = "[]"
    evidence_spans_json: str = "[]"
    rationale: str
    analysis_status: str
    failure_reason: str = ""
    model_provider: str
    model_name: str
    model_version: str = ""
    prompt_version: str
    schema_version: str
    content_hash: str
    source_text_version: str = "title_summary_body_v1"
    analyzed_at: datetime | None = None
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


class EditorialAnalysisRunMetrics(BaseModel):
    article_count: int = 0
    analyzed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    request_count: int = 0
    provider_rejected_count: int = 0
    parse_failed_count: int = 0
    validation_failed_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class StoryClusterQuery(BaseModel):
    days_back: int | None = Field(default=None, ge=1)
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=100, ge=1, le=1000)
