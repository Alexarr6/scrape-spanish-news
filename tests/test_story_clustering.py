from __future__ import annotations

from datetime import UTC, datetime

from src.analysis.contracts import ArticleAnalysisRead, StoryClusterMemberReason
from src.analysis.pipeline import ClusterPipeline, EnrichedArticle
from src.persistence.contracts import ArticleRead


def _enriched(
    article_id: int,
    source: str,
    title: str,
    article_type: str,
    when: datetime,
    tags: list[str],
    entities: list[str],
    key_phrases: list[str],
) -> EnrichedArticle:
    article = ArticleRead(
        id=article_id,
        source=source,
        title=title,
        url=f"https://example.com/{article_id}",
        published_at=when,
        scraped_at=when,
        section="politica",
        author="Reporter",
        summary=title,
        article_text=title,
        tags=",".join(tags),
    )
    analysis = ArticleAnalysisRead(
        article_id=article_id,
        article_type=article_type,
        article_type_confidence=0.9,
        is_event_coverage=article_type not in {"opinion", "editorial"},
        language="es",
        primary_topic_tag_id=None,
        key_phrases_json=str(key_phrases).replace("'", '"'),
        claims_json="[]",
        extraction_version="v1",
        content_hash="hash",
    )
    return EnrichedArticle(
        article=article,
        analysis=analysis,
        tag_codes=tags,
        entity_slugs=entities,
        key_phrases=key_phrases,
    )


def test_connected_components_keep_event_cluster_and_followup_separate():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    article_ids = [1, 2, 3]
    accepted_edges = [
        (
            1,
            2,
            StoryClusterMemberReason(
                score=0.82,
                semantic_similarity=0.8,
                title_similarity=0.7,
                shared_entity_score=1.0,
                tag_overlap_score=1.0,
                keyphrase_overlap_score=1.0,
                temporal_proximity_score=1.0,
            ),
        ),
    ]

    components = pipeline._connected_components(article_ids, accepted_edges)

    assert components == [[1, 2], [3]]


def test_score_pair_penalizes_followup_story():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    first = _enriched(
        1,
        "elpais",
        "Illa firma el acuerdo de presupuestos con ERC",
        "news_report",
        datetime(2026, 3, 18, tzinfo=UTC),
        ["politics_regional", "agreement_negotiation"],
        ["political_party-erc", "person-salvador-illa"],
        ["acuerdo presupuestos", "erc"],
    )
    followup = _enriched(
        2,
        "elmundo",
        "ERC exige nuevas condiciones a Illa dos días después del pacto",
        "news_report",
        datetime(2026, 3, 21, tzinfo=UTC),
        ["politics_regional", "statement_reaction"],
        ["political_party-erc", "person-salvador-illa"],
        ["nuevas condiciones", "erc"],
    )

    reason = pipeline.score_pair(first, followup)

    assert "followup_penalty" in reason.penalties
    assert reason.score < 0.68
