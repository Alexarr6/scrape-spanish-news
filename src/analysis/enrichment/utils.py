from __future__ import annotations

import hashlib

from src.persistence.core import ArticleRead
from src.persistence.orm import ArticleORM


def content_hash(article: ArticleRead) -> str:
    raw = "\n".join(
        [article.title, article.summary, article.article_text, article.section, article.tags]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def select_source_balanced_enrichment_rows(
    rows: list[ArticleORM],
    *,
    limit: int,
) -> list[ArticleORM]:
    """Round-robin recent enrichment work across sources after recency filtering."""

    if limit <= 0 or not rows:
        return []
    buckets: dict[str, list[ArticleORM]] = {}
    source_order: list[str] = []
    for row in rows:
        source = row.source or ""
        bucket = buckets.setdefault(source, [])
        if not bucket:
            source_order.append(source)
        bucket.append(row)

    selected: list[ArticleORM] = []
    indices: dict[str, int] = {source: 0 for source in source_order}
    while len(selected) < limit and source_order:
        next_round: list[str] = []
        for source in source_order:
            bucket = buckets[source]
            index = indices[source]
            if index < len(bucket):
                selected.append(bucket[index])
                indices[source] = index + 1
                if len(selected) >= limit:
                    break
            if indices[source] < len(bucket):
                next_round.append(source)
        source_order = next_round
    return selected
