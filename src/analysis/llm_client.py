from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from openai import BadRequestError, OpenAI
from pydantic import ValidationError

from src.analysis.contracts import (
    ArticleEditorialAnalysisPayload,
    ArticleEnrichmentPayload,
    EditorialAnalysisDiagnostics,
    OpenRouterUsage,
)
from src.analysis.editorial_normalization import (
    EditorialNormalizationError,
    build_editorial_diagnostics_from_payload,
    normalize_editorial_payload,
)
from src.analysis.schemas import (
    editorial_analysis_json_schema as build_editorial_analysis_json_schema,
)
from src.analysis.schemas import (
    editorial_analysis_raw_json_schema as build_editorial_analysis_raw_json_schema,
)
from src.analysis.schemas import (
    enrichment_json_schema as build_enrichment_json_schema,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EDITORIAL_ANALYSIS_SYSTEM_PROMPT = """You are classifying a Spanish news article.
Perform editorial analysis conservatively.

Your task is to produce one conservative, evidence-backed canonical JSON object using exactly
the schema provided by the API response_format.

Rules:
1. Return strict JSON only.
2. Use only the canonical field names and canonical taxonomy values from the schema.
3. Classify the article itself, not the outlet's reputation.
4. Be conservative. If evidence is weak or mixed, use `unclear` and lower confidence.
5. Do not infer ideology solely from topic. Use framing, wording, emphasis, and source treatment.
6. Distinguish between the article's own framing and quotations from sources.
7. Evidence spans must quote real text from the provided article content.
8. Do not invent helper keys, alternate taxonomies, nested diagnostic objects, or free-form hints.
9. `framing_devices` must be an array of canonical string codes.
10. Keep rationale concise and specific."""
EDITORIAL_ANALYSIS_SCHEMA_VERSION = "editorial-analysis-v1-normalized"
EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION = "title_summary_body_v1"

FailureClass = Literal[
    "provider_incompatible_schema",
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
EditorialAPIMode = Literal[
    "chat_completions_parse",
    "chat_completions_json_schema",
    "unsupported",
]


@dataclass(frozen=True)
class LLMProviderProfile:
    provider_id: Literal["openai", "openrouter", "custom"]
    supports_editorial_strict_schema: bool
    editorial_api_mode: EditorialAPIMode


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    model: str
    base_url: str | None = None
    timeout_seconds: int = 60
    max_retries: int = 2
    prompt_version: str = "v1"

    @classmethod
    def from_env(cls) -> "LLMSettings | None":
        model = _first_env("LLM_MODEL", "OPENAI_MODEL", "OPENROUTER_MODEL")
        base_url = _resolve_base_url()
        api_key = _resolve_api_key(base_url=base_url)
        if not api_key or not model:
            return None
        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=_parse_int_env(
                "60",
                "LLM_TIMEOUT_SECONDS",
                "OPENAI_TIMEOUT_SECONDS",
                "OPENROUTER_TIMEOUT_SECONDS",
            ),
            max_retries=_parse_int_env(
                "2",
                "LLM_MAX_RETRIES",
                "OPENAI_MAX_RETRIES",
                "OPENROUTER_MAX_RETRIES",
            ),
            prompt_version=(
                _first_env(
                    "LLM_PROMPT_VERSION",
                    "OPENAI_PROMPT_VERSION",
                    "OPENROUTER_PROMPT_VERSION",
                )
                or "v1"
            ),
        )

    @property
    def provider_label(self) -> str:
        return self.provider_profile.provider_id

    @property
    def provider_profile(self) -> LLMProviderProfile:
        if not self.base_url:
            return LLMProviderProfile(
                provider_id="openai",
                supports_editorial_strict_schema=True,
                editorial_api_mode="chat_completions_parse",
            )
        if "openrouter.ai" in self.base_url.lower():
            return LLMProviderProfile(
                provider_id="openrouter",
                supports_editorial_strict_schema=True,
                editorial_api_mode="chat_completions_json_schema",
            )
        return LLMProviderProfile(
            provider_id="custom",
            supports_editorial_strict_schema=False,
            editorial_api_mode="unsupported",
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
    diagnostics: EditorialAnalysisDiagnostics | None = None


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


class LLMClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings
        client_kwargs: dict[str, Any] = {
            "api_key": settings.api_key,
            "timeout": settings.timeout_seconds,
            "max_retries": settings.max_retries,
        }
        if settings.base_url:
            client_kwargs["base_url"] = settings.base_url
        self._client = OpenAI(**client_kwargs)

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
        profile = self.settings.provider_profile
        if not profile.supports_editorial_strict_schema:
            return EditorialAnalysisResult(
                attempts=(
                    EditorialAnalysisAttempt(
                        mode="strict_json_schema",
                        request_accepted=False,
                        failure_class="provider_incompatible_schema",
                        failure_message=(
                            f"provider {profile.provider_id!r} does not support "
                            "editorial strict schema"
                        ),
                    ),
                )
            )
        if profile.editorial_api_mode == "chat_completions_parse":
            return EditorialAnalysisResult(
                attempts=(self._run_editorial_strict_attempt(article_prompt=article_prompt),)
            )
        if profile.editorial_api_mode == "chat_completions_json_schema":
            return EditorialAnalysisResult(
                attempts=(
                    self._run_editorial_openrouter_attempt(
                        article_prompt=article_prompt,
                        schema=schema,
                    ),
                )
            )
        return EditorialAnalysisResult(
            attempts=(
                EditorialAnalysisAttempt(
                    mode="strict_json_schema",
                    request_accepted=False,
                    failure_class="provider_incompatible_schema",
                    failure_message=(
                        f"provider {profile.provider_id!r} does not support "
                        "editorial strict schema"
                    ),
                ),
            )
        )

    def _run_editorial_strict_attempt(self, *, article_prompt: str) -> EditorialAnalysisAttempt:
        messages = [
            {"role": "system", "content": self._editorial_system_prompt("strict_json_schema")},
            {"role": "user", "content": article_prompt},
        ]
        try:
            response = self._client.chat.completions.parse(
                model=self.settings.model,
                messages=messages,
                response_format=ArticleEditorialAnalysisPayload,
            )
        except BadRequestError as exc:
            failure_class = (
                "provider_schema_rejected"
                if "schema" in str(exc).lower() or "response_format" in str(exc).lower()
                else "provider_request_failed"
            )
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
                request_accepted=False,
                failure_class=failure_class,
                failure_message=str(exc),
            )
        except Exception as exc:
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
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
                mode="strict_json_schema",
                request_accepted=True,
                usage=usage,
                failure_class="refusal_or_blocked",
                failure_message=str(refusal),
                raw_response=raw_response,
                raw_message=raw_message,
            )

        parsed = getattr(message, "parsed", None) if message is not None else None
        if parsed is None:
            extracted_content, content_error = self._extract_message_content(message)
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
                request_accepted=True,
                usage=usage,
                failure_class=content_error or "unknown_response_shape",
                failure_message="assistant parsed payload missing",
                raw_response=raw_response,
                raw_message=raw_message,
                raw_content=extracted_content,
            )

        try:
            payload = ArticleEditorialAnalysisPayload.model_validate(
                parsed.model_dump(mode="json") if hasattr(parsed, "model_dump") else parsed
            )
        except ValidationError as exc:
            extracted_content, _ = self._extract_message_content(message)
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
                request_accepted=True,
                usage=usage,
                failure_class="payload_validation_failed",
                failure_message=str(exc),
                raw_response=raw_response,
                raw_message=raw_message,
                raw_content=extracted_content,
            )

        parsed_json = payload.model_dump(mode="json")
        diagnostics = build_editorial_diagnostics_from_payload(
            payload,
            provider_path="strict_success",
        )
        return EditorialAnalysisAttempt(
            mode="strict_json_schema",
            request_accepted=True,
            payload=payload,
            usage=usage,
            raw_response=raw_response,
            raw_message=raw_message,
            raw_content=json.dumps(parsed_json, ensure_ascii=False),
            parsed_json=parsed_json,
            diagnostics=diagnostics,
        )

    def _run_editorial_openrouter_attempt(
        self,
        *,
        article_prompt: str,
        schema: dict[str, Any],
    ) -> EditorialAnalysisAttempt:
        messages = [
            {"role": "system", "content": self._editorial_system_prompt("strict_json_schema")},
            {"role": "user", "content": article_prompt},
        ]
        request_kwargs: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "article_editorial_analysis",
                    "strict": True,
                    "schema": schema,
                },
            },
            "extra_body": {"provider": self._openrouter_provider_preferences()},
        }
        try:
            response = self._client.chat.completions.create(**request_kwargs)
        except BadRequestError as exc:
            failure_class = (
                "provider_schema_rejected"
                if "schema" in str(exc).lower() or "response_format" in str(exc).lower()
                else "provider_request_failed"
            )
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
                request_accepted=False,
                failure_class=failure_class,
                failure_message=str(exc),
            )
        except Exception as exc:
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
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
                mode="strict_json_schema",
                request_accepted=True,
                usage=usage,
                failure_class="refusal_or_blocked",
                failure_message=str(refusal),
                raw_response=raw_response,
                raw_message=raw_message,
            )

        extracted_content, content_error = self._extract_message_content(message)
        if content_error is not None or extracted_content is None:
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
                request_accepted=True,
                usage=usage,
                failure_class=content_error or "unknown_response_shape",
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
                    mode="strict_json_schema",
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
                    mode="strict_json_schema",
                    request_accepted=True,
                    usage=usage,
                    failure_class="json_parse_failed",
                    failure_message=str(retry_exc),
                    raw_response=raw_response,
                    raw_message=raw_message,
                    raw_content=extracted_content,
                )
        try:
            payload = ArticleEditorialAnalysisPayload.model_validate(parsed_json)
        except ValidationError as exc:
            return EditorialAnalysisAttempt(
                mode="strict_json_schema",
                request_accepted=True,
                usage=usage,
                failure_class="payload_validation_failed",
                failure_message=str(exc),
                raw_response=raw_response,
                raw_message=raw_message,
                raw_content=extracted_content,
                parsed_json=parsed_json,
            )

        diagnostics = build_editorial_diagnostics_from_payload(
            payload,
            provider_path="strict_success",
        )
        return EditorialAnalysisAttempt(
            mode="strict_json_schema",
            request_accepted=True,
            payload=payload,
            usage=usage,
            raw_response=raw_response,
            raw_message=raw_message,
            raw_content=extracted_content,
            parsed_json=parsed_json,
            diagnostics=diagnostics,
        )

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

        diagnostics = normalization.diagnostics.model_copy(
            update={
                "provider_path": "strict_success"
                if mode == "strict_json_schema"
                else "fallback_success"
            }
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
            diagnostics=diagnostics,
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

    def _openrouter_provider_preferences(self) -> dict[str, Any]:
        preferences: dict[str, Any] = {
            "require_parameters": True,
            "allow_fallbacks": False,
        }
        if self.settings.model.startswith("openai/"):
            preferences["only"] = ["openai"]
        return preferences


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
        "Analyze the following article and return one canonical JSON object "
        "for editorial analysis.\n"
        "Use only the canonical schema fields. Do not return helper fields such as "
        "`ideological_bias_framing`, `tone_dimensions`, `notes`, or `uncertainty_reason`.\n\n"
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
    return build_enrichment_json_schema()


def editorial_analysis_json_schema() -> dict[str, Any]:
    return build_editorial_analysis_json_schema()


def editorial_analysis_raw_json_schema() -> dict[str, Any]:
    return build_editorial_analysis_raw_json_schema()


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _normalized_base_url(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned or cleaned.lower() in {"none", "null", "default", "openai"}:
        return None
    return cleaned


def _resolve_base_url() -> str | None:
    for name in ("LLM_BASE_URL", "OPENAI_BASE_URL", "OPENROUTER_BASE_URL"):
        if name in os.environ:
            return _normalized_base_url(os.environ.get(name, ""))
    return None


def _parse_int_env(default: str, *names: str) -> int:
    raw = _first_env(*names)
    if not raw:
        return int(default)
    try:
        return int(raw)
    except ValueError:
        return int(default)


def _resolve_api_key(*, base_url: str | None) -> str:
    generic_key = _first_env("LLM_API_KEY")
    if generic_key:
        return generic_key
    if base_url and "openrouter.ai" in base_url.lower():
        return _first_env("OPENROUTER_API_KEY", "OPENAI_API_KEY")
    return _first_env("OPENAI_API_KEY", "OPENROUTER_API_KEY")


OpenRouterSettings = LLMSettings
OpenRouterClient = LLMClient
