from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from src.analysis.shared.contracts import ArticleAnalysisRead
from src.analysis.clustering import ClusterPipeline
from src.analysis.shared.types import EnrichedArticle
from src.analysis.ops.story_eval import build_pair_artifacts, evaluate_candidate_recall
from src.persistence.core import ArticleRead


def _enriched(
    *,
    article_id: int,
    title: str,
    summary: str,
    tags: list[str],
    entities: list[str],
    key_phrases: list[str],
    when: datetime,
    article_type: str = "news_report",
) -> EnrichedArticle:
    article = ArticleRead(
        id=article_id,
        source=f"source-{article_id}",
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
        key_phrases_json=str(key_phrases).replace("'", '"'),
        claims_json="[]",
        extraction_version="v1",
        content_hash=f"hash-{article_id}",
    )
    return EnrichedArticle(
        article=article,
        analysis=analysis,
        tag_codes=tags,
        entity_slugs=entities,
        key_phrases=key_phrases,
    )


def test_candidate_generation_emits_auditable_origins_for_followup_pair() -> None:
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    articles = [
        _enriched(
            article_id=1,
            title="Illa anuncia un acuerdo con ERC sobre presupuestos",
            summary="Pacto presupuestario con ERC.",
            tags=["politics_regional", "agreement_negotiation"],
            entities=["political_party-erc", "person-salvador-illa"],
            key_phrases=["acuerdo presupuestos erc", "cuentas catalanas"],
            when=datetime(2026, 3, 18, 10, tzinfo=UTC),
        ),
        _enriched(
            article_id=2,
            title="ERC exige nuevas condiciones a Illa dos días después del pacto",
            summary="Las conversaciones siguen abiertas.",
            tags=["politics_regional", "statement_reaction"],
            entities=["political_party-erc", "person-salvador-illa"],
            key_phrases=["nuevas condiciones erc", "pacto presupuestario"],
            when=datetime(2026, 3, 20, 9, tzinfo=UTC),
        ),
        _enriched(
            article_id=3,
            title="La Aemet activa avisos por lluvia en Galicia",
            summary="Tema distinto.",
            tags=["weather_alert"],
            entities=["organization-aemet", "region_city-galicia"],
            key_phrases=["avisos lluvia galicia"],
            when=datetime(2026, 3, 18, 8, tzinfo=UTC),
        ),
    ]

    pairs, summaries = pipeline._generate_candidate_pairs(  # noqa: SLF001
        articles,
        per_seed_limit=5,
        per_origin_limit=5,
    )

    pair = next(pair for pair in pairs if {pair.left_article_id, pair.right_article_id} == {1, 2})
    assert {"temporal_window", "shared_tag", "shared_entity"} <= pair.origins
    assert pair.rank == 1

    seed_one = next(summary for summary in summaries if summary.seed_article_id == 1)
    assert seed_one.origin_counts["shared_entity"] >= 1
    assert seed_one.origin_counts["shared_tag"] >= 1
    assert seed_one.candidate_count >= 1


def test_candidate_generation_adds_semantic_neighbor_origin_when_available(monkeypatch) -> None:
    from src.semantic import dbstore

    pipeline = ClusterPipeline(session=object())  # type: ignore[arg-type]
    now = datetime(2026, 3, 18, tzinfo=UTC)
    articles = [
        _enriched(
            article_id=1,
            title="Acuerdo presupuestario en Catalunya",
            summary="Resumen A",
            tags=["politics_regional"],
            entities=["person-salvador-illa"],
            key_phrases=["alpha"],
            when=now,
        ),
        _enriched(
            article_id=2,
            title="Las cuentas catalanas siguen abiertas",
            summary="Resumen B",
            tags=["economy"],
            entities=["organization-govern"],
            key_phrases=["beta"],
            when=now,
        ),
    ]

    def _fake_neighbors(_session, *, article_id: int, limit: int):
        assert limit >= 5
        if article_id == 1:
            return [SimpleNamespace(article_id=2, similarity=0.93)]
        return []

    monkeypatch.setattr(dbstore, "nearest_neighbors", _fake_neighbors)

    pairs, summaries = pipeline._generate_candidate_pairs(  # noqa: SLF001
        articles,
        per_seed_limit=5,
        per_origin_limit=5,
    )

    pair = next(pair for pair in pairs if {pair.left_article_id, pair.right_article_id} == {1, 2})
    assert "semantic_neighbor" in pair.origins
    seed_one = next(summary for summary in summaries if summary.seed_article_id == 1)
    assert seed_one.origin_counts["semantic_neighbor"] == 1


def test_candidate_generation_skips_semantic_neighbors_when_embeddings_missing(monkeypatch) -> None:
    from src.semantic import dbstore

    pipeline = ClusterPipeline(session=object())  # type: ignore[arg-type]
    now = datetime(2026, 3, 18, tzinfo=UTC)
    articles = [
        _enriched(
            article_id=1,
            title="Acuerdo presupuestario en Catalunya",
            summary="Resumen A",
            tags=["politics_regional"],
            entities=["person-salvador-illa"],
            key_phrases=["alpha"],
            when=now,
        ),
        _enriched(
            article_id=2,
            title="Las cuentas catalanas siguen abiertas",
            summary="Resumen B",
            tags=["economy"],
            entities=["organization-govern"],
            key_phrases=["beta"],
            when=now,
        ),
    ]

    def _missing_neighbors(_session, *, article_id: int, limit: int):
        raise RuntimeError("article_embeddings table is missing; run semantic-db-init first")

    monkeypatch.setattr(dbstore, "nearest_neighbors", _missing_neighbors)

    pairs, summaries = pipeline._generate_candidate_pairs(  # noqa: SLF001
        articles,
        per_seed_limit=5,
        per_origin_limit=5,
    )

    pair = next(pair for pair in pairs if {pair.left_article_id, pair.right_article_id} == {1, 2})
    assert "semantic_neighbor" not in pair.origins
    assert all("semantic_neighbor" not in summary.origin_counts for summary in summaries)


def test_candidate_generation_high_recall_prioritizes_semantic_neighbors(monkeypatch) -> None:
    from src.semantic import dbstore

    pipeline = ClusterPipeline(session=object())  # type: ignore[arg-type]
    now = datetime(2026, 3, 18, tzinfo=UTC)
    articles = [
        _enriched(
            article_id=1,
            title="Acuerdo presupuestario en Catalunya",
            summary="Resumen A",
            tags=["politics_regional"],
            entities=["person-salvador-illa"],
            key_phrases=["alpha"],
            when=now,
        ),
        _enriched(
            article_id=2,
            title="Las cuentas catalanas siguen abiertas",
            summary="Resumen B",
            tags=["economy"],
            entities=["organization-govern"],
            key_phrases=["beta"],
            when=now,
        ),
        _enriched(
            article_id=3,
            title="Temporal en Galicia deja lluvias intensas",
            summary="Resumen C",
            tags=["politics_regional"],
            entities=["person-salvador-illa"],
            key_phrases=["gamma"],
            when=now,
        ),
    ]

    def _fake_neighbors(_session, *, article_id: int, limit: int):
        assert limit >= 5
        if article_id == 1:
            return [SimpleNamespace(article_id=2, similarity=0.94)]
        return []

    monkeypatch.setattr(dbstore, "nearest_neighbors", _fake_neighbors)

    pairs, summaries = pipeline._generate_candidate_pairs(  # noqa: SLF001
        articles,
        per_seed_limit=1,
        per_origin_limit=1,
        recall_mode="high_recall",
        semantic_backfill_limit=1,
    )

    pair = next(pair for pair in pairs if {pair.left_article_id, pair.right_article_id} == {1, 2})
    seed_one = next(summary for summary in summaries if summary.seed_article_id == 1)

    assert "semantic_neighbor" in pair.origins
    assert pair.rank == 1
    assert seed_one.origin_counts["semantic_neighbor"] == 1


def test_candidate_generation_recall_summary_counts_positive_pairs_covered_by_rank() -> None:
    from src.analysis.ops.story_eval import PairLabel

    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 18, tzinfo=UTC)
    articles = [
        _enriched(
            article_id=1,
            title="A",
            summary="A",
            tags=["politics_regional"],
            entities=["person-salvador-illa"],
            key_phrases=["alpha"],
            when=now,
        ),
        _enriched(
            article_id=2,
            title="B",
            summary="B",
            tags=["politics_regional"],
            entities=["person-salvador-illa"],
            key_phrases=["beta"],
            when=now,
        ),
        _enriched(
            article_id=3,
            title="C",
            summary="C",
            tags=["weather_alert"],
            entities=["organization-aemet"],
            key_phrases=["gamma"],
            when=now,
        ),
    ]

    artifacts, _, _ = build_pair_artifacts(pipeline, articles)
    summary = evaluate_candidate_recall(
        artifacts,
        [
            PairLabel(left_article_id=1, right_article_id=2, label="same_event"),
            PairLabel(left_article_id=1, right_article_id=3, label="same_event"),
        ],
        ks=(1, 5),
    )

    assert summary is not None
    assert summary.positive_pair_count == 2
    assert summary.covered_pair_count_by_k == {"1": 2, "5": 2}
    assert summary.recall_at_k == {"1": 1.0, "5": 1.0}
