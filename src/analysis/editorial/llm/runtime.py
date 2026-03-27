from __future__ import annotations

import json
from typing import Any

from openai import BadRequestError, OpenAI
from pydantic import ValidationError

from src.analysis.editorial.llm.runtime_parts.parsing import (
    editorial_system_prompt,
    extract_json_block,
    extract_message_content,
)
from src.analysis.editorial.llm.runtime_parts.usage import (
    normalize_usage,
    openrouter_provider_preferences,
    safe_dump_model,
)
from src.analysis.editorial.llm.types import (
    EditorialAnalysisAttempt,
    EditorialAnalysisResult,
    LLMSettings,
)
from src.analysis.editorial.normalization import build_editorial_diagnostics_from_payload
from src.analysis.shared.contracts import (
    ArticleEditorialAnalysisPayload,
    ArticleEnrichmentPayload,
    OpenRouterUsage,
)


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
        usage = normalize_usage(getattr(response, "usage", None))
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
            {"role": "system", "content": editorial_system_prompt("strict_json_schema")},
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

        usage = normalize_usage(getattr(response, "usage", None))
        raw_response = safe_dump_model(response)
        choice = response.choices[0] if getattr(response, "choices", None) else None
        message = getattr(choice, "message", None)
        raw_message = safe_dump_model(message)
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
            extracted_content, content_error = extract_message_content(message)
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
            extracted_content, _ = extract_message_content(message)
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

    def _normalize_usage(self, usage: Any):
        return normalize_usage(usage)

    def _run_editorial_openrouter_attempt(
        self,
        *,
        article_prompt: str,
        schema: dict[str, Any],
    ) -> EditorialAnalysisAttempt:
        messages = [
            {"role": "system", "content": editorial_system_prompt("strict_json_schema")},
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
            "extra_body": {"provider": openrouter_provider_preferences(self.settings.model)},
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

        usage = normalize_usage(getattr(response, "usage", None))
        raw_response = safe_dump_model(response)
        choice = response.choices[0] if getattr(response, "choices", None) else None
        message = getattr(choice, "message", None)
        raw_message = safe_dump_model(message)
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

        extracted_content, content_error = extract_message_content(message)
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
            cleaned = extract_json_block(extracted_content)
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
