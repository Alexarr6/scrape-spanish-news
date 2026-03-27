from __future__ import annotations

from datetime import UTC, datetime

from src.analysis.shared.contracts import ArticleAnalysisRead
from src.analysis.clustering import ClusterPipeline
from src.analysis.shared.types import EnrichedArticle
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
    key_phrases: list[str] | None = None,
    source: str | None = None,
) -> EnrichedArticle:
    article = ArticleRead(
        id=article_id,
        source=source or ("elpais" if article_id % 2 else "elmundo"),
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
        key_phrases_json=str(
            key_phrases or ["presupuestos catalanes", "negociación con ERC"]
        ).replace("'", '"'),
        claims_json="[]",
        extraction_version="v1",
        content_hash="hash",
    )
    return EnrichedArticle(
        article=article,
        analysis=analysis,
        tag_codes=tags,
        entity_slugs=entities,
        key_phrases=key_phrases or ["presupuestos catalanes", "negociación con ERC"],
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
        key_phrases=["acuerdo presupuestos erc", "govern catalunya pacto", "cuentas catalanas"],
    )
    right = _enriched(
        article_id=2,
        title="El Govern sella con ERC las cuentas catalanas tras una larga negociación",
        summary="Resumen",
        article_type="news_report",
        tags=["politics_regional", "agreement_negotiation"],
        entities=["political_party-erc", "person-salvador-illa"],
        when=now,
        key_phrases=["acuerdo presupuestos erc", "cuentas catalanas", "pacto govern erc"],
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block is None
    assert reason.score >= 0.68
    assert reason.risky_bridge_pair is False


def test_story_pair_scoring_marks_entity_glue_bridge_as_risky():
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 18, tzinfo=UTC)
    left = _enriched(
        article_id=1,
        title="Illa firma el pacto con ERC",
        summary="Resumen",
        article_type="news_report",
        tags=["politics_regional", "agreement_negotiation"],
        entities=["political_party-erc", "person-salvador-illa"],
        when=now,
        key_phrases=["firma pacto", "presupuestos catalunya"],
    )
    right = _enriched(
        article_id=2,
        title="ERC mueve ficha tras el acuerdo",
        summary="Resumen",
        article_type="analysis",
        tags=["politics_regional", "statement_reaction"],
        entities=["political_party-erc", "person-salvador-illa"],
        when=now,
        key_phrases=["lectura politica", "reaccion interna"],
    )

    reason = pipeline.score_pair(left, right)

    assert reason.risky_bridge_pair is True
    assert "secondary_form_penalty" in reason.penalties
    assert "entity_glue_penalty" in reason.penalties


def test_story_pair_scoring_blocks_recurring_daily_results_series() -> None:
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    left = _enriched(
        article_id=1,
        title="Comprobar Bonoloto: resultados de hoy, lunes 23 de marzo de 2026",
        summary="Resultados del sorteo de hoy.",
        article_type="news_report",
        tags=["other"],
        entities=[],
        when=datetime(2026, 3, 23, tzinfo=UTC),
        key_phrases=["bonoloto resultados"],
        source="20minutos",
    )
    right = _enriched(
        article_id=2,
        title="Comprobar Bonoloto: resultados de hoy, martes 24 de marzo de 2026",
        summary="Resultados del sorteo de hoy.",
        article_type="news_report",
        tags=["other"],
        entities=[],
        when=datetime(2026, 3, 24, tzinfo=UTC),
        key_phrases=["bonoloto resultados"],
        source="20minutos",
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block == "recurring_results_series_excluded"


def test_story_pair_scoring_blocks_distinct_same_day_results_games() -> None:
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    when = datetime(2026, 3, 24, tzinfo=UTC)
    left = _enriched(
        article_id=1,
        title="Comprobar Bonoloto: resultados de hoy, martes 24 de marzo de 2026",
        summary="Resultados del sorteo de hoy.",
        article_type="news_report",
        tags=["other"],
        entities=[],
        when=when,
        key_phrases=["bonoloto resultados"],
        source="20minutos",
    )
    right = _enriched(
        article_id=2,
        title="Comprobar ONCE: resultados de hoy, martes 24 de marzo de 2026",
        summary="Resultados del sorteo de hoy.",
        article_type="news_report",
        tags=["other"],
        entities=[],
        when=when,
        key_phrases=["once resultados"],
        source="20minutos",
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block == "recurring_results_series_excluded"


def test_story_pair_scoring_blocks_same_source_question_utility_series() -> None:
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 24, tzinfo=UTC)
    left = _enriched(
        article_id=1,
        title=(
            "¿Tengo derecho a quedarme siete años en un piso de alquiler "
            "si el casero es una sociedad limitada?"
        ),
        summary="Consulta sobre alquiler, vivienda y casero.",
        article_type="explainer",
        tags=["housing"],
        entities=["organization-legalitas", "region_city-madrid"],
        when=now,
        key_phrases=["alquiler vivienda casero"],
        source="elpais",
    )
    right = _enriched(
        article_id=2,
        title="¿Qué necesito para cambiar el uso de un local a vivienda?",
        summary="Consulta sobre local, vivienda y trámites.",
        article_type="explainer",
        tags=["housing"],
        entities=["organization-legalitas", "region_city-madrid"],
        when=now,
        key_phrases=["local vivienda tramites"],
        source="elpais",
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block == "question_utility_series_excluded"


def test_story_pair_scoring_blocks_same_source_schedule_series() -> None:
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 24, tzinfo=UTC)
    left = _enriched(
        article_id=1,
        title="Itinerarios y horarios del Martes Santo de la Semana Santa de Córdoba 2026",
        summary="Horarios e itinerarios de las cofradías del Martes Santo en Córdoba.",
        article_type="news_report",
        tags=["local"],
        entities=["region_city-cordoba"],
        when=now,
        key_phrases=["semana santa cordoba itinerarios"],
        source="abc",
    )
    right = _enriched(
        article_id=2,
        title="Itinerarios y horarios del Viernes Santo de la Semana Santa de Córdoba 2026",
        summary="Horarios e itinerarios de las cofradías del Viernes Santo en Córdoba.",
        article_type="news_report",
        tags=["local"],
        entities=["region_city-cordoba"],
        when=now,
        key_phrases=["semana santa cordoba itinerarios"],
        source="abc",
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block == "schedule_series_excluded"


def test_story_pair_scoring_blocks_same_source_live_blog_vs_standard_piece() -> None:
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 25, tzinfo=UTC)
    left = _enriched(
        article_id=1,
        title=(
            "Última hora de la comparecencia de Sánchez en el Congreso "
            "sobre la guerra, en directo"
        ),
        summary="Sigue en directo la comparecencia de Sánchez en el Congreso.",
        article_type="news_report",
        tags=["politics"],
        entities=["person-pedro-sanchez", "institution-congreso"],
        when=now,
        key_phrases=["comparecencia congreso guerra"],
        source="eldiario",
    )
    right = _enriched(
        article_id=2,
        title="Sánchez alerta de que los efectos de Irán serán mucho peores que los de Irak",
        summary="Resumen de la comparecencia de Sánchez en el Congreso.",
        article_type="news_report",
        tags=["politics"],
        entities=["person-pedro-sanchez", "institution-congreso"],
        when=now,
        key_phrases=["comparecencia congreso guerra"],
        source="eldiario",
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block == "live_blog_series_excluded"


def test_story_pair_scoring_rewards_clean_rewrite_with_sparse_entity_support() -> None:
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    now = datetime(2026, 3, 23, tzinfo=UTC)
    left = _enriched(
        article_id=1,
        title="Estrasburgo rechaza revisar las prisiones del procés y vuelve a avalar al Supremo",
        summary="El tribunal europeo rechaza revisar el caso de Junqueras, Turull y Sànchez.",
        article_type="news_report",
        tags=["justice"],
        entities=["institution-tribunal-supremo"],
        when=now,
        key_phrases=["estrasburgo proceso supremo"],
        source="abc",
    )
    right = _enriched(
        article_id=2,
        title=(
            "Estrasburgo avala el rechazo a revisar el caso de prisión preventiva "
            "a Junqueras, Turull y Sànchez"
        ),
        summary="La corte europea respalda al Supremo en el caso del procés.",
        article_type="news_report",
        tags=["justice"],
        entities=["institution-tribunal-supremo"],
        when=now,
        key_phrases=["estrasburgo proceso supremo"],
        source="lavanguardia",
    )

    reason = pipeline.score_pair(left, right)

    assert reason.hard_block is None
    assert reason.risky_bridge_pair is False
    assert reason.score >= 0.6
