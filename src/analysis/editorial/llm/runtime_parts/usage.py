from __future__ import annotations

from typing import Any

from src.analysis.shared.contracts import OpenRouterUsage


def normalize_usage(usage: Any) -> OpenRouterUsage:
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


def safe_dump_model(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def openrouter_provider_preferences(model: str) -> dict[str, Any]:
    preferences: dict[str, Any] = {
        "require_parameters": True,
        "allow_fallbacks": False,
    }
    if model.startswith("openai/"):
        preferences["only"] = ["openai"]
    return preferences
