from __future__ import annotations

import json
from typing import Any

from src.analysis.editorial.llm.types import (
    EDITORIAL_ANALYSIS_SYSTEM_PROMPT,
    FailureClass,
    SchemaMode,
)


def editorial_system_prompt(mode: SchemaMode) -> str:
    if mode == "strict_json_schema":
        return EDITORIAL_ANALYSIS_SYSTEM_PROMPT
    return (
        EDITORIAL_ANALYSIS_SYSTEM_PROMPT
        + "\n8. Do not use markdown fences or commentary. Return only one JSON object."
    )


def extract_message_content(message: Any) -> tuple[str | None, FailureClass | None]:
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
            if item.get("type") in {"text", "output_text"} and isinstance(item.get("text"), str):
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


def extract_json_block(content: str) -> str | None:
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
