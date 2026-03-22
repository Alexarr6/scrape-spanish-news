from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from openai import BadRequestError, OpenAI

from src.analysis.contracts import ArticleEnrichmentPayload, OpenRouterUsage
from src.analysis.editorial_normalization import (
    EditorialNormalizationError,
    normalize_editorial_payload,
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
EDITORIAL_ANALYSIS_SYSTEM_PROMPT = """You are classifying a Spanish news article.
Perform editorial analysis conservatively.

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
EDITORIAL_ANALYSIS_SCHEMA_VERSION = "editorial-analysis-v1-normalized"
EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION = "title_summary_body_v1"

FailureClass = Literal[
    "provider_schema_rejected",
    "provider_request_failed",
    "empty_content",
    "non_json_content",
    "json_parse_failed",
    "payload_validation_failed",
    "refusal_or_blocked",
    "unknown_response_shape",
]
SchemaMode = Literal["strict_json_schema", "fallback_json_text"]


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


@dataclass(frozen=True)
class EditorialAnalysisAttempt:
    mode: SchemaMode
    request_accepted: bool
    payload: Any | None = None
    usage: OpenRouterUsage | None = None
    failure_class: FailureClass | None = None
    failure_message: str = ""
    raw_response: Any = None
    raw_message: Any = None
    raw_content: str | None = None
    parsed_json: dict[str, Any] | list[Any] | None = None
    normalization_warnings: tuple[str, ...] = ()
    repair_warnings: tuple[str, ...] = ()
    dropped_fields: tuple[str, ...] = ()
    truncated_fields: tuple[str, ...] = ()
    unclear_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class EditorialAnalysisResult:
    attempts: tuple[EditorialAnalysisAttempt, ...]

    @property
    def success(self) -> bool:
        return any(attempt.payload is not None for attempt in self.attempts)

    @property
    def final_attempt(self) -> EditorialAnalysisAttempt:
        return self.attempts[-1]

    @property
    def successful_attempt(self) -> EditorialAnalysisAttempt | None:
        return next((attempt for attempt in self.attempts if attempt.payload is not None), None)


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
        usage = self._normalize_usage(getattr(response, "usage", None))
        return payload, usage

    def analyze_editorial(
        self, *, article_prompt: str, schema: dict[str, Any]
    ) -> EditorialAnalysisResult:
        strict_attempt = self._run_editorial_attempt(
            article_prompt=article_prompt,
            schema=schema,
            mode="strict_json_schema",
        )
        attempts = [strict_attempt]
        if strict_attempt.payload is not None:
            return EditorialAnalysisResult(attempts=tuple(attempts))
        if self._should_retry_with_fallback(strict_attempt):
            attempts.append(
                self._run_editorial_attempt(
                    article_prompt=article_prompt,
                    schema=schema,
                    mode="fallback_json_text",
                )
            )
        return EditorialAnalysisResult(attempts=tuple(attempts))

    def _run_editorial_attempt(
        self,
        *,
        article_prompt: str,
        schema: dict[str, Any],
        mode: SchemaMode,
    ) -> EditorialAnalysisAttempt:
        messages = [
            {"role": "system", "content": self._editorial_system_prompt(mode)},
            {"role": "user", "content": article_prompt},
        ]
        request_kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
        }
        if mode == "strict_json_schema":
            request_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "article_editorial_analysis",
                    "strict": True,
                    "schema": schema,
                },
            }
        try:
            response = self._client.chat.completions.create(**request_kwargs)
        except BadRequestError as exc:
            failure_class = (
                "provider_schema_rejected"
                if "invalid schema" in str(exc).lower() and "response_format" in str(exc).lower()
                else "provider_request_failed"
            )
            return EditorialAnalysisAttempt(
                mode=mode,
                request_accepted=False,
                failure_class=failure_class,
                failure_message=str(exc),
            )
        except Exception as exc:
            return EditorialAnalysisAttempt(
                mode=mode,
                request_accepted=False,
                failure_class="provider_request_failed",
                failure_message=str(exc),
            )

        usage = self._normalize_usage(getattr(response, "usage", None))
        raw_response = self._safe_dump_model(response)
        choice = response.choices[0] if getattr(response, "choices", None) else None
        message = getattr(choice, "message", None)
        raw_message = self._safe_dump_model(message)
        refusal = getattr(message, "refusal", None) if message is not None else None
        if refusal:
            return EditorialAnalysisAttempt(
                mode=mode,
                request_accepted=True,
                usage=usage,
                failure_class="refusal_or_blocked",
                failure_message=str(refusal),
                raw_response=raw_response,
                raw_message=raw_message,
            )

        extracted_content, content_error = self._extract_message_content(message)
        if content_error is not None:
            return EditorialAnalysisAttempt(
                mode=mode,
                request_accepted=True,
                usage=usage,
                failure_class=content_error,
                failure_message="assistant content missing or unusable",
                raw_response=raw_response,
                raw_message=raw_message,
            )

        try:
            parsed_json = json.loads(extracted_content)
        except json.JSONDecodeError as exc:
            cleaned = self._extract_json_block(extracted_content)
            if cleaned is None:
                return EditorialAnalysisAttempt(
                    mode=mode,
                    request_accepted=True,
                    usage=usage,
                    failure_class="non_json_content",
                    failure_message=str(exc),
                    raw_response=raw_response,
                    raw_message=raw_message,
                    raw_content=extracted_content,
                )
            try:
                parsed_json = json.loads(cleaned)
                extracted_content = cleaned
            except json.JSONDecodeError as retry_exc:
                return EditorialAnalysisAttempt(
                    mode=mode,
                    request_accepted=True,
                    usage=usage,
                    failure_class="json_parse_failed",
                    failure_message=str(retry_exc),
                    raw_response=raw_response,
                    raw_message=raw_message,
                    raw_content=extracted_content,
                )

        try:
            normalization = normalize_editorial_payload(parsed_json)
        except EditorialNormalizationError as exc:
            return EditorialAnalysisAttempt(
                mode=mode,
                request_accepted=True,
                usage=usage,
                failure_class="payload_validation_failed",
                failure_message=str(exc),
                raw_response=raw_response,
                raw_message=raw_message,
                raw_content=extracted_content,
                parsed_json=parsed_json,
                normalization_warnings=exc.normalization_warnings or exc.warnings,
                repair_warnings=exc.repair_warnings,
                dropped_fields=exc.dropped_fields,
                truncated_fields=exc.truncated_fields,
                unclear_reasons=exc.unclear_reasons,
            )

        return EditorialAnalysisAttempt(
            mode=mode,
            request_accepted=True,
            payload=normalization.final_payload,
            usage=usage,
            raw_response=raw_response,
            raw_message=raw_message,
            raw_content=extracted_content,
            parsed_json=parsed_json,
            normalization_warnings=normalization.normalization_warnings,
            repair_warnings=normalization.repair_warnings,
            dropped_fields=normalization.dropped_fields,
            truncated_fields=normalization.truncated_fields,
            unclear_reasons=normalization.unclear_reasons,
        )

    def _should_retry_with_fallback(self, attempt: EditorialAnalysisAttempt) -> bool:
        return attempt.mode == "strict_json_schema" and attempt.failure_class in {
            "provider_schema_rejected",
            "empty_content",
            "non_json_content",
            "json_parse_failed",
            "unknown_response_shape",
        }

    def _editorial_system_prompt(self, mode: SchemaMode) -> str:
        if mode == "strict_json_schema":
            return EDITORIAL_ANALYSIS_SYSTEM_PROMPT
        return (
            EDITORIAL_ANALYSIS_SYSTEM_PROMPT
            + "\n8. Do not use markdown fences or commentary. Return only one JSON object."
        )

    def _extract_message_content(self, message: Any) -> tuple[str | None, FailureClass | None]:
        if message is None:
            return None, "unknown_response_shape"
        content = getattr(message, "content", None)
        if isinstance(content, str):
            cleaned = content.strip()
            return (cleaned, None) if cleaned else (None, "empty_content")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    if item.strip():
                        parts.append(item.strip())
                    continue
                if not isinstance(item, dict):
                    continue
                if item.get("type") in {"text", "output_text"} and isinstance(
                    item.get("text"), str
                ):
                    if item["text"].strip():
                        parts.append(item["text"].strip())
                    continue
                if item.get("type") == "json" and isinstance(item.get("json"), (dict, list)):
                    return json.dumps(item["json"], ensure_ascii=False), None
                if isinstance(item.get("content"), str) and item["content"].strip():
                    parts.append(item["content"].strip())
            joined = "\n".join(part for part in parts if part).strip()
            return (joined, None) if joined else (None, "empty_content")
        if isinstance(content, dict):
            if isinstance(content.get("text"), str) and content["text"].strip():
                return content["text"].strip(), None
            if isinstance(content.get("json"), (dict, list)):
                return json.dumps(content["json"], ensure_ascii=False), None
        return None, "unknown_response_shape"

    def _extract_json_block(self, content: str) -> str | None:
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                inner = "\n".join(lines[1:-1]).strip()
                if inner.lower().startswith("json\n"):
                    inner = inner[5:].strip()
                return inner or None
        start_positions = [idx for idx in (stripped.find("{"), stripped.find("[")) if idx >= 0]
        if not start_positions:
            return None
        start = min(start_positions)
        for end_char in ("}", "]"):
            end = stripped.rfind(end_char)
            if end > start:
                candidate = stripped[start : end + 1].strip()
                if candidate:
                    return candidate
        return None

    def _normalize_usage(self, usage: Any) -> OpenRouterUsage:
        if usage is None:
            return OpenRouterUsage()
        if isinstance(usage, dict):
            return OpenRouterUsage.model_validate(usage)
        if hasattr(usage, "model_dump"):
            return OpenRouterUsage.model_validate(usage.model_dump())
        return OpenRouterUsage.model_validate(
            {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        )

    def _safe_dump_model(self, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value


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
        "Analyze the following article and return one portable raw JSON object "
        "for editorial analysis.\n"
        "Use the preferred keys when possible, but if the article is straightforward "
        "or the exact taxonomy feels forced, stay conservative and still return "
        "valid JSON.\n\n"
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


def editorial_debug_artifact_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / ".artifacts" / "editorial-analysis"


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
    def bounded_string(max_length: int = 1200) -> dict[str, Any]:
        return {"type": "string", "maxLength": max_length}

    return {
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "article_type": bounded_string(120),
            "article_type_confidence": {
                "anyOf": [
                    {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    bounded_string(40),
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
            "bias_label": bounded_string(80),
            "ideological_bias_framing": {
                "anyOf": [
                    bounded_string(240),
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
            "bias_score": {
                "anyOf": [{"type": "number", "minimum": -1.0, "maximum": 1.0}, bounded_string(40)]
            },
            "bias_confidence": {
                "anyOf": [
                    {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    bounded_string(40),
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
            "confidence": {
                "anyOf": [
                    {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    bounded_string(40),
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
            "tone_emotional": bounded_string(80),
            "tone_target": bounded_string(80),
            "opinionatedness": bounded_string(80),
            "sensationalism": bounded_string(80),
            "rhetorical_certainty": bounded_string(80),
            "tone_dimensions": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "emotionality": bounded_string(80),
                    "target": bounded_string(80),
                    "polarity": bounded_string(80),
                    "opinionatedness": bounded_string(80),
                    "style": bounded_string(80),
                    "sensationalism": bounded_string(80),
                    "rhetorical_certainty": bounded_string(80),
                    "certainty": bounded_string(80),
                },
            },
            "framing_devices": {
                "type": "array",
                "maxItems": 20,
                "items": {
                    "anyOf": [
                        {"type": "string", "maxLength": 240},
                        {"type": "object", "additionalProperties": True},
                    ]
                },
            },
            "evidence_spans": {
                "type": "array",
                "maxItems": 20,
                "items": {
                    "anyOf": [
                        bounded_string(400),
                        {
                            "type": "object",
                            "additionalProperties": True,
                            "properties": {
                                "type": bounded_string(40),
                                "location": bounded_string(40),
                                "text": bounded_string(400),
                                "note": bounded_string(240),
                                "explanation": bounded_string(240),
                            },
                        },
                    ]
                },
            },
            "rationale": {
                "anyOf": [
                    bounded_string(1200),
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
            "notes": {
                "anyOf": [
                    bounded_string(500),
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
            "uncertainty_reason": {
                "anyOf": [
                    bounded_string(500),
                    {"type": "object", "additionalProperties": True},
                    {"type": "null"},
                ]
            },
        },
        "required": ["article_type", "framing_devices", "evidence_spans", "rationale"],
    }
