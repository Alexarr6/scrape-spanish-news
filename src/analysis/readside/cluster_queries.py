from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from src.analysis.readside.common import (
    iso_datetime,
    load_article_entities,
    load_article_tags,
    load_editorial_rows_for_articles,
)
from src.analysis.readside.editorial_summary import (
    build_cluster_editorial_summary,
    parse_json_object,
    shape_member_editorial_preview,
)
from src.analysis.readside.filters import ClusterListFilters
from src.analysis.store.models import (
    ArticleTagORM,
    ClusterEntityORM,
    ClusterMemberORM,
    EntityMentionORM,
    EntityORM,
    StoryClusterORM,
    TagORM,
)
from src.persistence.orm import ArticleORM


def load_story_clusters(session: Session, filters: ClusterListFilters) -> tuple[list[dict], int]:
    cluster_ids = _matching_cluster_ids_stmt(filters)
    total = session.execute(select(func.count()).select_from(cluster_ids.subquery())).scalar_one()
    ids = (
        session.execute(
            cluster_ids.order_by(
                StoryClusterORM.article_count.desc(),
                StoryClusterORM.source_count.desc(),
                StoryClusterORM.last_article_published_at.desc().nullslast(),
                StoryClusterORM.id.desc(),
            )
            .offset(filters.offset)
            .limit(filters.limit)
        )
        .scalars()
        .all()
    )
    if not ids:
        return [], total
    payload, _ = load_story_clusters_for_ids(session, ids)
    return payload, total


def load_story_cluster_detail(session: Session, cluster_id: int) -> dict | None:
    cluster = session.execute(
        select(StoryClusterORM).where(StoryClusterORM.id == cluster_id)
    ).scalar_one_or_none()
    if cluster is None:
        return None
    cluster_payload, _ = load_story_clusters_for_ids(session, [cluster_id])
    members = session.execute(
        select(
            ClusterMemberORM.article_id,
            ClusterMemberORM.membership_score,
            ClusterMemberORM.membership_reason_json,
            ArticleORM.source,
            ArticleORM.title,
            ArticleORM.url,
            ArticleORM.published_at,
            ArticleORM.section,
            ArticleORM.summary,
        )
        .join(ArticleORM, ArticleORM.id == ClusterMemberORM.article_id)
        .where(ClusterMemberORM.cluster_id == cluster_id)
        .order_by(
            ArticleORM.published_at.desc().nullslast(), ClusterMemberORM.membership_score.desc()
        )
    ).all()
    article_ids = [row.article_id for row in members]
    tags_by_article = load_article_tags(session, article_ids)
    entities_by_article = load_article_entities(session, article_ids)
    editorial_rows = load_editorial_rows_for_articles(session, article_ids)
    return {
        "cluster": cluster_payload[0],
        "members": [
            {
                "article_id": row.article_id,
                "source": row.source,
                "title": row.title,
                "url": row.url,
                "published_at": iso_datetime(row.published_at),
                "section": row.section or "",
                "summary": row.summary or "",
                "membership_score": round(float(row.membership_score), 4),
                "membership_diagnostics": parse_json_object(row.membership_reason_json),
                "tags": tags_by_article.get(row.article_id, []),
                "entities": entities_by_article.get(row.article_id, []),
                "editorial_preview": shape_member_editorial_preview(
                    editorial_rows.get(row.article_id)
                ),
            }
            for row in members
        ],
        "editorial_summary": build_cluster_editorial_summary(members, editorial_rows),
    }


def load_story_clusters_for_ids(session: Session, ids: list[int]) -> tuple[list[dict], int]:
    if not ids:
        return [], 0
    clusters = {
        row.id: row
        for row in session.execute(
            select(StoryClusterORM).where(StoryClusterORM.id.in_(ids))
        ).scalars()
    }
    primary_tags = {row.id: row for row in session.execute(select(TagORM)).scalars()}
    source_rows = session.execute(
        select(ClusterMemberORM.cluster_id, ArticleORM.source)
        .join(ArticleORM, ArticleORM.id == ClusterMemberORM.article_id)
        .where(ClusterMemberORM.cluster_id.in_(ids))
    ).all()
    sources_by_cluster: dict[int, list[str]] = {cluster_id: [] for cluster_id in ids}
    for cluster_id, source in source_rows:
        bucket = sources_by_cluster.setdefault(cluster_id, [])
        if source not in bucket:
            bucket.append(source)
    entity_rows = session.execute(
        select(
            ClusterEntityORM.cluster_id,
            EntityORM.id,
            EntityORM.slug,
            EntityORM.canonical_name,
            EntityORM.entity_type,
            ClusterEntityORM.article_coverage_count,
            ClusterEntityORM.mention_count,
            ClusterEntityORM.aggregate_relevance_score,
        )
        .join(EntityORM, EntityORM.id == ClusterEntityORM.entity_id)
        .where(ClusterEntityORM.cluster_id.in_(ids))
        .order_by(
            ClusterEntityORM.cluster_id,
            ClusterEntityORM.article_coverage_count.desc(),
            ClusterEntityORM.aggregate_relevance_score.desc(),
            ClusterEntityORM.mention_count.desc(),
        )
    ).all()
    entities_by_cluster: dict[int, list[dict]] = {cluster_id: [] for cluster_id in ids}
    for row in entity_rows:
        items = entities_by_cluster.setdefault(row.cluster_id, [])
        if len(items) >= 5:
            continue
        items.append(
            {
                "entity_id": row.id,
                "slug": row.slug,
                "name": row.canonical_name,
                "entity_type": row.entity_type,
                "article_coverage_count": row.article_coverage_count,
                "mention_count": row.mention_count,
            }
        )
    payload = []
    for cluster_id in ids:
        cluster = clusters.get(cluster_id)
        if cluster is None:
            continue
        primary_tag = primary_tags.get(cluster.primary_tag_id) if cluster.primary_tag_id else None
        payload.append(
            {
                "id": cluster.id,
                "cluster_key": cluster.cluster_key,
                "status": cluster.status,
                "cluster_type": cluster.cluster_type,
                "summary_headline": cluster.summary_headline,
                "summary_text": cluster.summary_text,
                "article_count": cluster.article_count,
                "source_count": cluster.source_count,
                "first_article_published_at": iso_datetime(cluster.first_article_published_at),
                "last_article_published_at": iso_datetime(cluster.last_article_published_at),
                "sources": sorted(sources_by_cluster.get(cluster_id, [])),
                "primary_tag": (
                    {
                        "tag_code": primary_tag.tag_code,
                        "display_name": primary_tag.display_name,
                        "tag_group": primary_tag.tag_group,
                    }
                    if primary_tag
                    else None
                ),
                "top_entities": entities_by_cluster.get(cluster_id, []),
            }
        )
    return payload, len(payload)


def load_story_cluster_filters(session: Session, filters: ClusterListFilters) -> dict:
    cluster_ids = session.execute(_matching_cluster_ids_stmt(filters)).scalars().all()
    if not cluster_ids:
        return {"sources": [], "tags": [], "entities": []}
    sources = session.execute(
        select(ArticleORM.source, func.count(func.distinct(ClusterMemberORM.cluster_id)))
        .join(ClusterMemberORM, ClusterMemberORM.article_id == ArticleORM.id)
        .where(ClusterMemberORM.cluster_id.in_(cluster_ids))
        .group_by(ArticleORM.source)
        .order_by(func.count(func.distinct(ClusterMemberORM.cluster_id)).desc(), ArticleORM.source)
    ).all()
    tags = session.execute(
        select(
            TagORM.tag_code,
            TagORM.display_name,
            func.count(func.distinct(ClusterMemberORM.cluster_id)),
        )
        .join(ArticleTagORM, ArticleTagORM.tag_id == TagORM.id)
        .join(ClusterMemberORM, ClusterMemberORM.article_id == ArticleTagORM.article_id)
        .where(ClusterMemberORM.cluster_id.in_(cluster_ids))
        .group_by(TagORM.tag_code, TagORM.display_name)
        .order_by(func.count(func.distinct(ClusterMemberORM.cluster_id)).desc(), TagORM.tag_code)
    ).all()
    entities = session.execute(
        select(
            EntityORM.slug,
            EntityORM.canonical_name,
            EntityORM.entity_type,
            func.count(func.distinct(ClusterEntityORM.cluster_id)),
        )
        .join(ClusterEntityORM, ClusterEntityORM.entity_id == EntityORM.id)
        .where(ClusterEntityORM.cluster_id.in_(cluster_ids))
        .group_by(EntityORM.slug, EntityORM.canonical_name, EntityORM.entity_type)
        .order_by(
            func.count(func.distinct(ClusterEntityORM.cluster_id)).desc(), EntityORM.canonical_name
        )
        .limit(50)
    ).all()
    return {
        "sources": [
            {"value": source, "label": source, "count": count} for source, count in sources
        ],
        "tags": [
            {"value": tag_code, "label": display_name, "count": count}
            for tag_code, display_name, count in tags
        ],
        "entities": [
            {
                "slug": slug,
                "name": name,
                "entity_type": entity_type,
                "count": count,
            }
            for slug, name, entity_type, count in entities
        ],
    }


def _matching_cluster_ids_stmt(filters: ClusterListFilters) -> Select:
    stmt = (
        select(StoryClusterORM.id)
        .join(ClusterMemberORM, ClusterMemberORM.cluster_id == StoryClusterORM.id)
        .join(ArticleORM, ArticleORM.id == ClusterMemberORM.article_id)
        .group_by(
            StoryClusterORM.id,
            StoryClusterORM.article_count,
            StoryClusterORM.source_count,
            StoryClusterORM.last_article_published_at,
        )
    )
    if filters.source:
        stmt = stmt.where(ArticleORM.source == filters.source)
    if filters.tag_code:
        stmt = stmt.join(ArticleTagORM, ArticleTagORM.article_id == ArticleORM.id).join(
            TagORM, TagORM.id == ArticleTagORM.tag_id
        )
        stmt = stmt.where(TagORM.tag_code == filters.tag_code)
    if filters.entity_slug:
        stmt = stmt.join(EntityMentionORM, EntityMentionORM.article_id == ArticleORM.id).join(
            EntityORM, EntityORM.id == EntityMentionORM.entity_id
        )
        stmt = stmt.where(EntityORM.slug == filters.entity_slug)
    if filters.date_from:
        stmt = stmt.where(StoryClusterORM.last_article_published_at >= filters.date_from)
    if filters.date_to:
        stmt = stmt.where(
            StoryClusterORM.first_article_published_at
            < datetime.combine(filters.date_to, datetime.max.time())
        )
    if filters.search:
        term = f"%{filters.search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(StoryClusterORM.summary_headline).like(term),
                func.lower(StoryClusterORM.summary_text).like(term),
                func.lower(ArticleORM.title).like(term),
            )
        )
    return stmt
