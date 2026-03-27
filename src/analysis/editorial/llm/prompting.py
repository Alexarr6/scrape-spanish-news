from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.analysis.shared.schemas import (
    editorial_analysis_json_schema as build_editorial_analysis_json_schema,
)
from src.analysis.shared.schemas import (
    editorial_analysis_raw_json_schema as build_editorial_analysis_raw_json_schema,
)
from src.analysis.shared.schemas import enrichment_json_schema as build_enrichment_json_schema


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
    root = Path(__file__).resolve().parents[4]
    return root / "var" / "analysis" / "editorial"


def enrichment_json_schema() -> dict[str, Any]:
    return build_enrichment_json_schema()


def editorial_analysis_json_schema() -> dict[str, Any]:
    return build_editorial_analysis_json_schema()


def editorial_analysis_raw_json_schema() -> dict[str, Any]:
    return build_editorial_analysis_raw_json_schema()
