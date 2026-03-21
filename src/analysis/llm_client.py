from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from src.analysis.contracts import (
    ArticleEditorialAnalysisPayload,
    ArticleEnrichmentPayload,
    OpenRouterUsage,
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
EDITORIAL_ANALYSIS_SYSTEM_PROMPT = (
    """You are classifying a Spanish news article for editorial analysis.

Your task is to produce a conservative, evidence-backed JSON object that classifies:
- article type
- ideological bias framing
- tone dimensions
- framing devices
- rationale
- evidence spans

Rules:
1. Return strict JSON only.
2. Classify the article itself, not the outlet's reputation.
3. Be conservative. If evidence is weak or mixed, use `unclear` and lower confidence.
4. Do not infer ideology solely from topic. Use framing, wording, emphasis, and source treatment.
5. Distinguish between the article's own framing and quotations from sources.
6. Evidence spans must quote real text from the provided article content.
7. Keep rationale concise and specific."""
)
EDITORIAL_ANALYSIS_SCHEMA_VERSION = "editorial-analysis-v1"
EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION = "title_summary_body_v1"


@dataclass(frozen=True)
class OpenRouterSettings:
    api_key: str
    model: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: int = 60
    max_retries: int = 2
    prompt_version: str = "v1"

    @classmethod
    def from_env(cls) -> "OpenRouterSettings | None":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model = os.getenv("OPENROUTER_MODEL", "").strip()
        if not api_key or not model:
            return None
        return cls(
            api_key=api_key,
            model=model,
            base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
            timeout_seconds=int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "60")),
            max_retries=int(os.getenv("OPENROUTER_MAX_RETRIES", "2")),
            prompt_version=os.getenv("OPENROUTER_PROMPT_VERSION", "v1"),
        )


class OpenRouterClient:
    def __init__(self, settings: OpenRouterSettings) -> None:
        self.settings = settings
        self._client = OpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
            max_retries=settings.max_retries,
        )

    def enrich_article(
        self, *, article_prompt: str, schema: dict[str, Any]
    ) -> tuple[ArticleEnrichmentPayload, OpenRouterUsage]:
        response = self._client.chat.completions.create(
            model=self.settings.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON only. Use the provided taxonomy and stay conservative."
                    ),
                },
                {"role": "user", "content": article_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "article_enrichment",
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        content = response.choices[0].message.content or "{}"
        payload = ArticleEnrichmentPayload.model_validate(json.loads(content))
        usage = OpenRouterUsage.model_validate(getattr(response, "usage", {}) or {})
        return payload, usage

    def analyze_editorial(
        self, *, article_prompt: str, schema: dict[str, Any]
    ) -> tuple[ArticleEditorialAnalysisPayload, OpenRouterUsage]:
        response = self._client.chat.completions.create(
            model=self.settings.model,
            messages=[
                {"role": "system", "content": EDITORIAL_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": article_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "article_editorial_analysis",
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        content = response.choices[0].message.content or "{}"
        payload = ArticleEditorialAnalysisPayload.model_validate(json.loads(content))
        usage = OpenRouterUsage.model_validate(getattr(response, "usage", {}) or {})
        return payload, usage


def build_prompt(
    *,
    article_title: str,
    article_summary: str,
    article_text: str,
    candidate_entities: list[dict[str, Any]],
    allowed_tags: list[dict[str, str]],
) -> str:
    body = article_text[:4000]
    instructions = (
        "Analyze this Spanish news article. "
        "Choose article_type, up to 12 relevant entities, "
        "one primary tag and up to 3 secondary tags from the allowed list only, "
        "plus up to 5 key phrases and claims.\n\n"
    )
    return (
        instructions
        + f"TITLE: {article_title}\n"
        + f"SUMMARY: {article_summary}\n"
        + f"BODY: {body}\n\n"
        + f"CANDIDATE_ENTITIES: {json.dumps(candidate_entities, ensure_ascii=False)}\n"
        + f"ALLOWED_TAGS: {json.dumps(allowed_tags, ensure_ascii=False)}"
    )


def build_editorial_analysis_prompt(
    *,
    source: str,
    section: str,
    published_at: str,
    url: str,
    title: str,
    summary: str,
    body: str,
) -> str:
    article_body = body[:6000]
    return (
        "Analyze the following article and return strict JSON matching the required schema.\n\n"
        "ARTICLE_METADATA:\n"
        f"- source: {source}\n"
        f"- section: {section}\n"
        f"- published_at: {published_at}\n"
        f"- url: {url}\n\n"
        "ARTICLE_CONTENT:\n"
        f"TITLE: {title}\n"
        f"SUMMARY: {summary}\n"
        f"BODY: {article_body}"
    )


def enrichment_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "article_type": {"type": "string"},
            "article_type_confidence": {"type": "number"},
            "is_event_coverage": {"type": "boolean"},
            "language": {"type": "string"},
            "primary_tag_code": {"type": ["string", "null"]},
            "secondary_tag_codes": {"type": "array", "items": {"type": "string"}},
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "entity_type": {"type": "string"},
                        "canonical_name": {"type": "string"},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "relevance_score": {"type": "number"},
                        "role_hint": {"type": ["string", "null"]},
                    },
                    "required": [
                        "entity_type",
                        "canonical_name",
                        "aliases",
                        "relevance_score",
                        "role_hint",
                    ],
                },
            },
            "key_phrases": {"type": "array", "items": {"type": "string"}},
            "claims": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "article_type",
            "article_type_confidence",
            "is_event_coverage",
            "language",
            "primary_tag_code",
            "secondary_tag_codes",
            "entities",
            "key_phrases",
            "claims",
        ],
    }


def editorial_analysis_json_schema() -> dict[str, Any]:
    def controlled_string(values: list[str]) -> dict[str, Any]:
        return {"type": "string", "enum": list(values)}

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "article_type": controlled_string(
                [
                    "news_report",
                    "analysis",
                    "opinion",
                    "editorial",
                    "interview",
                    "feature",
                    "explainer",
                    "live_blog",
                    "other",
                    "unclear",
                ]
            ),
            "article_type_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "bias_label": controlled_string(
                [
                    "far_left",
                    "left",
                    "center_left",
                    "center",
                    "center_right",
                    "right",
                    "far_right",
                    "unclear",
                ]
            ),
            "bias_score": {"type": "number", "minimum": -1.0, "maximum": 1.0},
            "bias_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "tone_emotional": controlled_string(["calm", "loaded", "inflammatory", "unclear"]),
            "tone_target": controlled_string(
                ["supportive", "neutral", "critical", "hostile", "mixed", "unclear"]
            ),
            "opinionatedness": controlled_string(
                ["straight_reporting", "interpretive", "opinionated", "activist", "unclear"]
            ),
            "sensationalism": controlled_string(["low", "medium", "high", "unclear"]),
            "rhetorical_certainty": controlled_string(
                ["cautious", "assertive", "absolute", "unclear"]
            ),
            "framing_devices": {
                "type": "array",
                "maxItems": 5,
                "items": controlled_string(
                    [
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
                ),
                "uniqueItems": True,
            },
            "evidence_spans": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": controlled_string(["headline", "summary", "body"]),
                        "text": {"type": "string", "minLength": 3, "maxLength": 400},
                        "note": {"type": "string", "minLength": 3, "maxLength": 240},
                    },
                    "required": ["type", "text", "note"],
                },
            },
            "rationale": {"type": "string", "minLength": 12, "maxLength": 1200},
        },
        "required": [
            "article_type",
            "article_type_confidence",
            "bias_label",
            "bias_score",
            "bias_confidence",
            "tone_emotional",
            "tone_target",
            "opinionatedness",
            "sensationalism",
            "rhetorical_certainty",
            "framing_devices",
            "evidence_spans",
            "rationale",
        ],
    }
