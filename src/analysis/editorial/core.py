from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EDITORIAL_ARTICLE_TYPES = (
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
)
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
EDITORIAL_APPLICABILITY_VALUES = ("full", "limited", "out_of_domain")
EDITORIAL_APPLICABILITY_REASONS = (
    "general_editorial_content",
    "procedural_hard_news",
    "accident_crime_bulletin",
    "sports_recap",
    "consumer_price_roundup",
    "weather_or_service_info",
    "insufficient_text",
)
EDITORIAL_DIMENSION_STATUS_VALUES = (
    "resolved",
    "weak_signal_abstain",
    "mapping_loss",
    "provider_missing",
    "out_of_domain",
    "conflicted_signal",
)



BoundedString40 = Annotated[str, Field(max_length=40)]
BoundedString80 = Annotated[str, Field(max_length=80)]
BoundedString120 = Annotated[str, Field(max_length=120)]
BoundedString240 = Annotated[str, Field(max_length=240)]
BoundedString500 = Annotated[str, Field(max_length=500)]
BoundedString1200 = Annotated[str, Field(max_length=1200)]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]
SignedBiasScore = Annotated[float, Field(ge=-1.0, le=1.0)]


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

    article_type: BoundedString120 | None = None
    article_type_confidence: Probability | BoundedString40 | dict[str, Any] | None = None
    bias_label: BoundedString80 | None = None
    ideological_bias_framing: BoundedString240 | dict[str, Any] | None = None
    bias_score: SignedBiasScore | BoundedString40 | None = None
    bias_confidence: Probability | BoundedString40 | dict[str, Any] | None = None
    confidence: Probability | BoundedString40 | dict[str, Any] | None = None
    tone_emotional: BoundedString80 | None = None
    tone_target: BoundedString80 | None = None
    opinionatedness: BoundedString80 | None = None
    sensationalism: BoundedString80 | None = None
    rhetorical_certainty: BoundedString80 | None = None
    tone_dimensions: dict[str, Any] | None = None
    framing_devices: list[Any] = Field(default_factory=list, max_length=20)
    evidence_spans: list[Any] = Field(default_factory=list, max_length=20)
    rationale: BoundedString1200 | dict[str, Any] | None = Field(default=None)
    notes: BoundedString500 | dict[str, Any] | None = Field(default=None)
    uncertainty_reason: BoundedString500 | dict[str, Any] | None = Field(default=None)


class EditorialDimensionDiagnostic(BaseModel):
    value: str
    status: Literal[
        "resolved",
        "weak_signal_abstain",
        "mapping_loss",
        "provider_missing",
        "out_of_domain",
        "conflicted_signal",
    ]
    reason: str
    notes: list[str] = Field(default_factory=list, max_length=8)
    raw_hints: list[str] = Field(default_factory=list, max_length=12)


class EditorialAnalysisDiagnostics(BaseModel):
    provider_path: str
    editorial_applicability: Literal["full", "limited", "out_of_domain"]
    editorial_applicability_reason: Literal[
        "general_editorial_content",
        "procedural_hard_news",
        "accident_crime_bulletin",
        "sports_recap",
        "consumer_price_roundup",
        "weather_or_service_info",
        "insufficient_text",
    ]
    dimension_status: dict[str, EditorialDimensionDiagnostic] = Field(default_factory=dict)
    repair_warnings: list[str] = Field(default_factory=list)
    normalization_warnings: list[str] = Field(default_factory=list)
    dropped_fields: list[str] = Field(default_factory=list)
    truncated_fields: list[str] = Field(default_factory=list)
    preserved_signals: dict[str, list[str]] = Field(default_factory=dict)
    provider_failures: list[str] = Field(default_factory=list)
    unclear_reasons: list[str] = Field(default_factory=list)


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
