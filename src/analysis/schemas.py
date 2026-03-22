from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from src.analysis.contracts import ArticleEnrichmentPayload
from src.analysis.editorial.core import ArticleEditorialAnalysisRawPayload

_PROVIDER_NOISE_KEYS = {"default", "title", "examples"}


def enrichment_json_schema() -> dict[str, Any]:
    schema = _provider_schema(ArticleEnrichmentPayload)
    schema.setdefault("additionalProperties", False)
    schema["required"] = list(ArticleEnrichmentPayload.model_fields)
    return schema


def editorial_analysis_json_schema() -> dict[str, Any]:
    schema = _provider_schema(ArticleEditorialAnalysisRawPayload)
    schema["required"] = ["article_type", "framing_devices", "evidence_spans", "rationale"]
    return schema


def _provider_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    return _strip_provider_noise(deepcopy(schema))


def _strip_provider_noise(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_provider_noise(item)
            for key, item in value.items()
            if key not in _PROVIDER_NOISE_KEYS
        }
    if isinstance(value, list):
        return [_strip_provider_noise(item) for item in value]
    return value
