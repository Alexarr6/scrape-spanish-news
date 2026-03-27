from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from src.analysis.editorial.llm import EditorialAnalysisResult
from src.analysis.editorial.orm import ArticleEditorialAnalysisORM
from src.persistence.core import ArticleRead


def analysis_path_for_result(result: EditorialAnalysisResult) -> str:
    parts = []
    for attempt in result.attempts:
        if attempt.payload is not None:
            parts.append("strict" if attempt.mode == "strict_json_schema" else "fallback")
        elif attempt.failure_class:
            parts.append(f"{attempt.mode}:{attempt.failure_class}")
        else:
            parts.append(attempt.mode)
    return " -> ".join(parts)


def write_failure_artifact(
    *,
    article: ArticleRead,
    analysis: ArticleEditorialAnalysisORM,
    prompt: str,
    result: EditorialAnalysisResult,
    artifact_dir_factory: Callable[[], Path],
) -> str:
    artifact_dir = artifact_dir_factory()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = artifact_dir / f"{timestamp}-article-{article.id}.json"
    artifact = {
        "article_id": article.id,
        "model_provider": analysis.model_provider,
        "model_name": analysis.model_name,
        "prompt_version": analysis.prompt_version,
        "schema_version": analysis.schema_version,
        "source_text_version": analysis.source_text_version,
        "attempts": [
            {
                "mode": attempt.mode,
                "request_accepted": attempt.request_accepted,
                "failure_class": attempt.failure_class,
                "failure_message": attempt.failure_message,
                "usage": None if attempt.usage is None else attempt.usage.model_dump(mode="json"),
                "raw_message": attempt.raw_message,
                "raw_content": attempt.raw_content,
                "parsed_json": attempt.parsed_json,
                "repair_warnings": list(attempt.repair_warnings),
                "normalization_warnings": list(attempt.normalization_warnings),
                "dropped_fields": list(attempt.dropped_fields),
                "truncated_fields": list(attempt.truncated_fields),
                "final_unclear_reasons": list(attempt.unclear_reasons),
                "diagnostics": None
                if attempt.diagnostics is None
                else attempt.diagnostics.model_dump(mode="json"),
                "fallback_success": attempt.mode == "fallback_json_text"
                and attempt.payload is not None,
                "raw_response": attempt.raw_response,
            }
            for attempt in result.attempts
        ],
        "prompt_excerpt": prompt[:1200],
        "article_metadata": {
            "source": article.source,
            "section": article.section,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "url": str(article.url),
            "title": article.title,
        },
    }
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(artifact_path)
