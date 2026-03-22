from __future__ import annotations

from src.analysis.llm_client import OpenRouterClient, OpenRouterSettings


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


def _client() -> OpenRouterClient:
    return OpenRouterClient(OpenRouterSettings(api_key="test", model="openrouter/test-model"))


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
