from __future__ import annotations

from src.analysis.llm_client import LLMClient, LLMSettings


class _UsageWithModelDump:
    def __init__(self, *, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def model_dump(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class _CompletionUsageLike:
    def __init__(self, *, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


def _client() -> LLMClient:
    return LLMClient(LLMSettings(api_key="test", model="openrouter/test-model"))


def test_normalize_usage_accepts_dict_model_dump_object_attr_object_and_none() -> None:
    client = _client()

    from_dict = client._normalize_usage(
        {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}
    )
    from_model_dump = client._normalize_usage(
        _UsageWithModelDump(prompt_tokens=4, completion_tokens=5, total_tokens=9)
    )
    from_attrs = client._normalize_usage(
        _CompletionUsageLike(prompt_tokens=6, completion_tokens=7, total_tokens=13)
    )
    from_none = client._normalize_usage(None)

    assert (from_dict.prompt_tokens, from_dict.completion_tokens, from_dict.total_tokens) == (
        1,
        2,
        3,
    )
    assert (
        from_model_dump.prompt_tokens,
        from_model_dump.completion_tokens,
        from_model_dump.total_tokens,
    ) == (4, 5, 9)
    assert (from_attrs.prompt_tokens, from_attrs.completion_tokens, from_attrs.total_tokens) == (
        6,
        7,
        13,
    )
    assert (from_none.prompt_tokens, from_none.completion_tokens, from_none.total_tokens) == (
        0,
        0,
        0,
    )


def test_llm_settings_prefers_generic_env_and_defaults_to_openai_when_no_base_url(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "generic-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-5-mini")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)

    settings = LLMSettings.from_env()

    assert settings is not None
    assert settings.api_key == "generic-key"
    assert settings.model == "gpt-5-mini"
    assert settings.base_url is None
    assert settings.provider_label == "openai"
    assert settings.provider_profile.supports_editorial_strict_schema is True
    assert settings.provider_profile.editorial_api_mode == "chat_completions_parse"


def test_llm_settings_accepts_custom_base_url_and_openrouter_fallback(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-key")
    monkeypatch.setenv("LLM_MODEL", "minimax/minimax-m2.7")
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")

    settings = LLMSettings.from_env()

    assert settings is not None
    assert settings.api_key == "router-key"
    assert settings.model == "minimax/minimax-m2.7"
    assert settings.base_url == "https://openrouter.ai/api/v1"
    assert settings.provider_label == "openrouter"
    assert settings.provider_profile.supports_editorial_strict_schema is True
    assert settings.provider_profile.editorial_api_mode == "chat_completions_json_schema"


def test_empty_generic_base_url_overrides_legacy_openrouter_base_url(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("LLM_MODEL", "gpt-5-mini")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    settings = LLMSettings.from_env()

    assert settings is not None
    assert settings.api_key == "openai-key"
    assert settings.base_url is None
    assert settings.provider_label == "openai"


def test_custom_base_url_is_not_editorial_strict_capable(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "generic-key")
    monkeypatch.setenv("LLM_MODEL", "custom/model")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")

    settings = LLMSettings.from_env()

    assert settings is not None
    assert settings.provider_label == "custom"
    assert settings.provider_profile.supports_editorial_strict_schema is False
