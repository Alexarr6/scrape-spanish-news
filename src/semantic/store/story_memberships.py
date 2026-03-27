from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def load_story_cluster_memberships(
    session: Session, *, article_ids: list[int]
) -> dict[int, list[int]]:
    if not article_ids:
        return {}
    placeholders = ", ".join(f":article_id_{index}" for index in range(len(article_ids)))
    params = {f"article_id_{index}": article_id for index, article_id in enumerate(article_ids)}
    rows = (
        session.execute(
            text(
                f"""
                SELECT article_id, cluster_id
                FROM cluster_members
                WHERE article_id IN ({placeholders})
                ORDER BY article_id ASC, cluster_id ASC
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    memberships: dict[int, list[int]] = {int(article_id): [] for article_id in article_ids}
    for row in rows:
        memberships.setdefault(int(row["article_id"]), []).append(int(row["cluster_id"]))
    return memberships
