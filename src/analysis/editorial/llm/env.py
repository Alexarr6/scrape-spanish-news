from __future__ import annotations

import os


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
