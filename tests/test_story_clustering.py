from __future__ import annotations

from datetime import UTC, datetime

from src.analysis.contracts import ArticleAnalysisRead, StoryClusterMemberReason
from src.analysis.pipeline import ClusterPipeline, EnrichedArticle
from src.persistence.core import ArticleRead


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


def test_score_pair_keeps_legitimate_followup_out_of_default_penalty_bucket():
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

    assert "followup_penalty" not in reason.penalties
    assert reason.risky_bridge_pair is False
    assert reason.score >= 0.55


def test_closure_v2_attaches_followup_via_strong_pivot():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    accepted_edges = [
        (
            1,
            2,
            StoryClusterMemberReason(
                score=0.84,
                semantic_similarity=0.8,
                title_similarity=0.72,
                shared_entity_score=1.0,
                tag_overlap_score=1.0,
                keyphrase_overlap_score=0.8,
                temporal_proximity_score=1.0,
                days_delta=0,
                shared_entity_count=2,
                shared_tag_count=2,
                shared_keyphrase_count=2,
            ),
        ),
        (
            2,
            3,
            StoryClusterMemberReason(
                score=0.75,
                semantic_similarity=0.67,
                title_similarity=0.58,
                shared_entity_score=0.8,
                tag_overlap_score=0.5,
                keyphrase_overlap_score=0.42,
                temporal_proximity_score=0.86,
                days_delta=2,
                shared_entity_count=2,
                shared_tag_count=1,
                shared_keyphrase_count=1,
            ),
        ),
    ]

    components = pipeline._connected_components([1, 2, 3], accepted_edges)

    assert components == [[1, 2, 3]]



def test_guarded_components_prevent_bridge_article_false_merge():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    accepted_edges = [
        (
            1,
            2,
            StoryClusterMemberReason(
                score=0.83,
                semantic_similarity=0.8,
                title_similarity=0.72,
                shared_entity_score=1.0,
                tag_overlap_score=1.0,
                keyphrase_overlap_score=0.7,
                temporal_proximity_score=1.0,
            ),
        ),
        (
            2,
            3,
            StoryClusterMemberReason(
                score=0.71,
                semantic_similarity=0.69,
                title_similarity=0.48,
                shared_entity_score=0.66,
                tag_overlap_score=0.5,
                keyphrase_overlap_score=0.2,
                temporal_proximity_score=0.95,
                risky_bridge_pair=True,
                penalties=["entity_glue_penalty"],
            ),
        ),
    ]

    components = pipeline._connected_components([1, 2, 3], accepted_edges)

    assert components == [[1, 2], [3]]


def test_closure_v2_does_not_attach_single_bridge_without_pivot_compatibility():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    accepted_edges = [
        (
            1,
            2,
            StoryClusterMemberReason(
                score=0.84,
                semantic_similarity=0.82,
                title_similarity=0.71,
                shared_entity_score=0.8,
                tag_overlap_score=1.0,
                keyphrase_overlap_score=0.75,
                temporal_proximity_score=1.0,
                days_delta=0,
                shared_entity_count=2,
                shared_tag_count=2,
                shared_keyphrase_count=2,
            ),
        ),
        (
            2,
            3,
            StoryClusterMemberReason(
                score=0.76,
                semantic_similarity=0.7,
                title_similarity=0.55,
                shared_entity_score=0.8,
                tag_overlap_score=0.0,
                keyphrase_overlap_score=0.2,
                temporal_proximity_score=0.9,
                days_delta=2,
                shared_entity_count=2,
                shared_tag_count=0,
                shared_keyphrase_count=0,
                penalties=["entity_glue_penalty"],
            ),
        ),
    ]

    components = pipeline._connected_components([1, 2, 3], accepted_edges)

    assert components == [[1, 2], [3]]



def test_guarded_components_keep_analysis_bridge_from_fusing_clusters():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    accepted_edges = [
        (
            1,
            2,
            StoryClusterMemberReason(
                score=0.84,
                semantic_similarity=0.82,
                title_similarity=0.71,
                shared_entity_score=0.8,
                tag_overlap_score=1.0,
                keyphrase_overlap_score=0.75,
                temporal_proximity_score=1.0,
            ),
        ),
        (
            2,
            3,
            StoryClusterMemberReason(
                score=0.74,
                semantic_similarity=0.71,
                title_similarity=0.5,
                shared_entity_score=0.66,
                tag_overlap_score=0.5,
                keyphrase_overlap_score=0.25,
                temporal_proximity_score=1.0,
                article_type_pair_class="secondary_form_pair",
                risky_bridge_pair=True,
                penalties=["secondary_form_penalty", "entity_glue_penalty"],
            ),
        ),
    ]

    components = pipeline._connected_components([1, 2, 3], accepted_edges)

    assert components == [[1, 2], [3]]


def test_raw_connected_components_can_merge_more_than_guarded_closure():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    accepted_edges = [
        (
            1,
            2,
            StoryClusterMemberReason(
                score=0.85,
                semantic_similarity=0.82,
                title_similarity=0.74,
                shared_entity_score=0.8,
                tag_overlap_score=1.0,
                keyphrase_overlap_score=0.78,
                temporal_proximity_score=1.0,
                days_delta=0,
                shared_entity_count=2,
                shared_tag_count=2,
                shared_keyphrase_count=2,
            ),
        ),
        (
            3,
            4,
            StoryClusterMemberReason(
                score=0.83,
                semantic_similarity=0.8,
                title_similarity=0.72,
                shared_entity_score=0.8,
                tag_overlap_score=1.0,
                keyphrase_overlap_score=0.76,
                temporal_proximity_score=1.0,
                days_delta=0,
                shared_entity_count=2,
                shared_tag_count=2,
                shared_keyphrase_count=2,
            ),
        ),
        (
            2,
            3,
            StoryClusterMemberReason(
                score=0.74,
                semantic_similarity=0.7,
                title_similarity=0.6,
                shared_entity_score=0.8,
                tag_overlap_score=0.5,
                keyphrase_overlap_score=0.35,
                temporal_proximity_score=0.9,
                days_delta=2,
                shared_entity_count=2,
                shared_tag_count=1,
                shared_keyphrase_count=0,
            ),
        ),
    ]

    raw_components = pipeline._raw_connected_components([1, 2, 3, 4], accepted_edges)
    guarded_components = pipeline._connected_components([1, 2, 3, 4], accepted_edges)

    assert raw_components == [[1, 2, 3, 4]]
    assert guarded_components == [[1, 2], [3, 4]]


def test_build_clusters_rolls_back_failed_rebuild() -> None:
    class RecordingSession:
        def __init__(self) -> None:
            self.commit_calls = 0
            self.rollback_calls = 0

        def commit(self) -> None:
            self.commit_calls += 1

        def rollback(self) -> None:
            self.rollback_calls += 1

    session = RecordingSession()
    pipeline = ClusterPipeline(session=session)  # type: ignore[arg-type]
    pipeline._load_enriched_articles = lambda **_: []  # type: ignore[method-assign]
    pipeline._build_guarded_components = lambda article_ids, accepted_edges: ([[]], {})  # type: ignore[method-assign]

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    pipeline._persist_clusters = _boom  # type: ignore[method-assign]

    try:
        pipeline.build_clusters()
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("expected rebuild failure to be re-raised")

    assert session.rollback_calls == 1
    assert session.commit_calls == 0
