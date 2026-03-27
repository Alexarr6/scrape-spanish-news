from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.analysis.shared.contracts import StoryClusterMemberReason
from src.analysis.shared.normalization import slugify
from src.analysis.shared.types import EnrichedArticle
from src.analysis.store.models import (
    ClusterEntityORM,
    ClusterMemberORM,
    EntityMentionORM,
    StoryClusterORM,
    TagORM,
)


def persist_clusters(
    session: Session,
    *,
    articles: list[EnrichedArticle],
    components: list[list[int]],
    accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    member_closure_meta: dict[int, dict[str, object]],
) -> None:
    edge_map = {
        (min(left, right), max(left, right)): reason for left, right, reason in accepted_edges
    }
    article_by_id = {item.article.id: item for item in articles}
    session.execute(delete(ClusterEntityORM))
    session.execute(delete(ClusterMemberORM))
    session.execute(delete(StoryClusterORM))
    session.flush()
    for index, members in enumerate(components, start=1):
        member_articles = [article_by_id[article_id] for article_id in members]
        ordered = sorted(
            member_articles,
            key=lambda item: item.article.published_at or datetime.now(UTC),
        )
        primary_tags = [tag for item in member_articles for tag in item.tag_codes]
        tag_code = Counter(primary_tags).most_common(1)[0][0] if primary_tags else None
        primary_tag_row = (
            session.execute(select(TagORM).where(TagORM.tag_code == tag_code)).scalar_one_or_none()
            if tag_code
            else None
        )
        representative = ordered[0]
        cluster = StoryClusterORM(
            cluster_key=(
                f"story-{representative.article.published_at.date().isoformat()}-"
                f"{slugify(representative.article.title)[:48]}-{index}"
            ),
            status="active",
            event_date_start=(
                ordered[0].article.published_at.date()
                if ordered[0].article.published_at
                else None
            ),
            event_date_end=(
                ordered[-1].article.published_at.date()
                if ordered[-1].article.published_at
                else None
            ),
            first_article_published_at=ordered[0].article.published_at,
            last_article_published_at=ordered[-1].article.published_at,
            cluster_type="breaking_event",
            summary_headline=representative.article.title,
            summary_text=" | ".join(
                dict.fromkeys(
                    item.article.summary.strip() for item in ordered if item.article.summary.strip()
                )
            )[:1000],
            primary_tag_id=primary_tag_row.id if primary_tag_row else None,
            article_count=len(members),
            source_count=len({item.article.source for item in member_articles}),
            clustering_version="v1",
        )
        session.add(cluster)
        session.flush()
        entity_counts: dict[int, tuple[int, int, float]] = defaultdict(lambda: (0, 0, 0.0))
        for article_id in members:
            supporting_edges = [
                (left_id, right_id, reason)
                for (left_id, right_id), reason in edge_map.items()
                if article_id in {left_id, right_id} and left_id in members and right_id in members
            ]
            pair_scores = [reason.score for _, _, reason in supporting_edges]
            membership_score = sum(pair_scores) / len(pair_scores) if pair_scores else 1.0
            supporting_article_ids = sorted(
                {
                    right_id if left_id == article_id else left_id
                    for left_id, right_id, _ in supporting_edges
                }
            )
            reason_payload = {
                "support_edge_count": len(pair_scores),
                "best_support_score": round(max(pair_scores), 4) if pair_scores else 1.0,
                "mean_support_score": round(membership_score, 4),
                "supporting_article_ids": supporting_article_ids,
                "accepted_via_guarded_merge": len(members) > 1,
                "risky_bridge_support": any(
                    reason.risky_bridge_pair for _, _, reason in supporting_edges
                ),
                "penalties": sorted(
                    {penalty for _, _, reason in supporting_edges for penalty in reason.penalties}
                ),
                "edge_scores": pair_scores,
                "closure": member_closure_meta.get(
                    article_id,
                    {
                        "closure_stage": "singleton",
                        "closure_decision": "no_support",
                        "closure_support_count": 0,
                    },
                ),
            }
            session.add(
                ClusterMemberORM(
                    cluster_id=cluster.id,
                    article_id=article_id,
                    membership_score=membership_score,
                    membership_reason_json=json.dumps(reason_payload),
                )
            )
            mentions = (
                session.execute(
                    select(EntityMentionORM).where(EntityMentionORM.article_id == article_id)
                )
                .scalars()
                .all()
            )
            seen_entities: set[int] = set()
            for mention in mentions:
                coverage, mention_count, relevance = entity_counts[mention.entity_id]
                entity_counts[mention.entity_id] = (
                    coverage + (0 if mention.entity_id in seen_entities else 1),
                    mention_count + mention.mention_count,
                    relevance + mention.relevance_score,
                )
                seen_entities.add(mention.entity_id)
        for entity_id, (coverage, mention_count, relevance) in entity_counts.items():
            session.add(
                ClusterEntityORM(
                    cluster_id=cluster.id,
                    entity_id=entity_id,
                    article_coverage_count=coverage,
                    mention_count=mention_count,
                    aggregate_relevance_score=round(relevance, 4),
                )
            )
