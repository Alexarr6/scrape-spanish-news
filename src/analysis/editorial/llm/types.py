from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.analysis.editorial.llm.env import (
    _first_env,
    _parse_int_env,
    _resolve_api_key,
    _resolve_base_url,
)
from src.analysis.shared.contracts import (
    EditorialAnalysisDiagnostics,
    OpenRouterUsage,
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
    def final_attempt(self) -> EditorialAnalysisAttempt:
        return self.attempts[-1]

    @property
    def successful_attempt(self) -> EditorialAnalysisAttempt | None:
        return next((attempt for attempt in self.attempts if attempt.payload is not None), None)


OpenRouterSettings = LLMSettings
