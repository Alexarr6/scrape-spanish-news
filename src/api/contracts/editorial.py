from __future__ import annotations

from pydantic import BaseModel, Field


class EditorialEvidenceSpan(BaseModel):
    type: str
    text: str
    note: str


class ArticleEditorialAnalysisResponse(BaseModel):
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
    framing_devices: list[str] = Field(default_factory=list)
    evidence_spans: list[EditorialEvidenceSpan] = Field(default_factory=list)
    rationale: str
    analysis_status: str
    failure_reason: str = ""
    model_provider: str
    model_name: str
    model_version: str = ""
    prompt_version: str
    schema_version: str
    content_hash: str
    source_text_version: str
    analyzed_at: str | None = None
    updated_at: str | None = None
