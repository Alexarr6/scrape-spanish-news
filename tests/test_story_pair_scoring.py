from __future__ import annotations

from datetime import UTC, datetime

from src.analysis.contracts import ArticleAnalysisRead
from src.analysis.pipeline import ClusterPipeline, EnrichedArticle
from src.persistence.core import ArticleRead


def _enriched(
    *,
    article_id: int,
    title: str,
    summary: str,
    article_type: str,
    tags: list[str],
    entities: list[str],
    when: datetime,
) -> EnrichedArticle:
    article = ArticleRead(
        id=article_id,
        source="elpais" if article_id % 2 else "elmundo",
        title=title,
        url=f"https://example.com/{article_id}",
        published_at=when,
        scraped_at=when,
        section="politica",
        author="Reporter",
        summary=summary,
        article_text=summary,
        tags=",".join(tags),
    )
    analysis = ArticleAnalysisRead(
        article_id=article_id,
        article_type=article_type,
        article_type_confidence=0.9,
        is_event_coverage=article_type not in {"opinion", "editorial"},
        language="es",
        primary_topic_tag_id=None,
        key_phrases_json='["presupuestos catalanes", "negociación con ERC"]',
        claims_json="[]",
        extraction_version="v1",
        content_hash="hash",
    )
    return EnrichedArticle(
        article=article,
        analysis=analysis,
        tag_codes=tags,
        entity_slugs=entities,
        key_phrases=["presupuestos catalanes", "negociación con ERC"],
    )


def test_story_pair_scoring_blocks_opinion_vs_news():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 18, tzinfo=UTC)
    report = _enriched(
        article_id=1,
        title="Illa negocia los presupuestos con ERC",
        summary="Resumen",
        article_type="news_report",
        tags=["politics_regional"],
        entities=["political_party-erc", "person-salvador-illa"],
        when=now,
    )
    opinion = _enriched(
        article_id=2,
        title="Opinión: los pactos de Illa con ERC",
        summary="Resumen",
        article_type="opinion",
        tags=["politics_regional"],
        entities=["political_party-erc", "person-salvador-illa"],
        when=now,
    )

    reason = pipeline.score_pair(report, opinion)

    assert reason.hard_block == "opinion_editorial_excluded_from_primary_clusters"


def test_story_pair_scoring_rewards_same_event_signals():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 18, tzinfo=UTC)
    left = _enriched(
        article_id=1,
        title="Illa anuncia un acuerdo con ERC sobre presupuestos",
        summary="Resumen",
        article_type="news_report",
        tags=["politics_regional", "agreement_negotiation"],
        entities=["political_party-erc", "person-salvador-illa"],
        when=now,
    )
    right = _enriched(
        article_id=2,
        title="ERC y el Govern cierran el pacto de presupuestos en Catalunya",
        summary="Resumen",
        article_type="news_report",
        tags=["politics_regional", "agreement_negotiation"],
        entities=["political_party-erc", "person-salvador-illa"],
        when=now,
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block is None
    assert reason.score >= 0.68
