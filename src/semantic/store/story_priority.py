from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.semantic.contracts import EmbeddingArtifact, PointArtifact, SemanticArticle

T = TypeVar("T")


@dataclass(frozen=True)
class StoryClusterPriorityGroup:
    cluster_id: int
    article_count: int
    article_ids: list[int]


def select_source_balanced_article_ids(
    records: Sequence[SemanticArticle | EmbeddingArtifact | PointArtifact], *, limit: int
) -> list[int]:
    if limit <= 0:
        return []
    buckets: dict[str, list[int]] = defaultdict(list)
    source_order: list[str] = []
    for record in records:
        source = getattr(record, "source", "") or ""
        article_id = int(getattr(record, "article_id"))
        if source not in buckets:
            source_order.append(source)
        buckets[source].append(article_id)

    selected: list[int] = []
    while len(selected) < limit and source_order:
        next_round: list[str] = []
        for source in source_order:
            bucket = buckets[source]
            if bucket:
                selected.append(bucket.pop(0))
                if len(selected) >= limit:
                    break
            if bucket:
                next_round.append(source)
        source_order = next_round
    return selected


def select_cluster_aware_article_ids(
    records: Sequence[SemanticArticle | EmbeddingArtifact | PointArtifact],
    *,
    limit: int,
    priority_groups: Sequence[StoryClusterPriorityGroup] | None = None,
) -> list[int]:
    if limit <= 0:
        return []
    record_ids = [int(getattr(record, "article_id")) for record in records]
    record_id_set = set(record_ids)

    selected: list[int] = []
    selected_set: set[int] = set()

    for group in priority_groups or []:
        cluster_ids = [
            article_id for article_id in group.article_ids if article_id in record_id_set
        ]
        if len(cluster_ids) != group.article_count:
            continue
        if len(selected) + len(cluster_ids) > limit:
            continue
        for article_id in cluster_ids:
            if article_id not in selected_set:
                selected.append(article_id)
                selected_set.add(article_id)

    remainder_records = [
        record for record in records if int(getattr(record, "article_id")) not in selected_set
    ]
    selected.extend(
        select_source_balanced_article_ids(remainder_records, limit=max(0, limit - len(selected)))
    )
    return selected[:limit]


def load_story_cluster_priority_groups(
    session: Session, *, article_ids: list[int], min_article_count: int = 2
) -> list[StoryClusterPriorityGroup]:
    if not article_ids:
        return []
    placeholders = ", ".join(f":article_id_{index}" for index in range(len(article_ids)))
    params = {f"article_id_{index}": article_id for index, article_id in enumerate(article_ids)}
    params["min_article_count"] = min_article_count
    rows = (
        session.execute(
            text(
                f"""
                SELECT sc.id AS cluster_id,
                       sc.article_count AS article_count,
                       cm.article_id AS article_id
                FROM story_clusters sc
                JOIN cluster_members cm ON cm.cluster_id = sc.id
                WHERE sc.article_count >= :min_article_count
                  AND cm.article_id IN ({placeholders})
                ORDER BY sc.last_article_published_at DESC NULLS LAST,
                         sc.id ASC,
                         cm.article_id ASC
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    grouped: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for row in rows:
        cluster_id = int(row["cluster_id"])
        if cluster_id not in grouped:
            grouped[cluster_id] = {
                "article_count": int(row["article_count"]),
                "article_ids": [],
            }
            order.append(cluster_id)
        grouped[cluster_id]["article_ids"].append(int(row["article_id"]))
    return [
        StoryClusterPriorityGroup(
            cluster_id=cluster_id,
            article_count=grouped[cluster_id]["article_count"],
            article_ids=grouped[cluster_id]["article_ids"],
        )
        for cluster_id in order
    ]


def source_balance_candidates(candidates: list[T]) -> list[T]:
    if not candidates:
        return []
    article_ids = select_source_balanced_article_ids(
        [getattr(candidate, "article") for candidate in candidates], limit=len(candidates)
    )
    by_article_id = {getattr(candidate.article, "article_id"): candidate for candidate in candidates}
    return [by_article_id[article_id] for article_id in article_ids if article_id in by_article_id]

