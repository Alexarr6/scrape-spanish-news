from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.analysis.editorial.orm import ArticleEditorialAnalysisORM
from src.analysis.orm_models import (
    ArticleAnalysisORM,
    ArticleTagORM,
    ClusterEntityORM,
    ClusterMemberORM,
    EntityMentionORM,
    EntityORM,
    StoryClusterORM,
    TagORM,
)
from src.analysis.readside import ClusterListFilters, _matching_cluster_ids_stmt
from src.api.v1.articles import get_session
from src.api.v1.clusters import router
from src.persistence.orm_models import ArticleORM, Base


class TrackingSession(Session):
    closed_sessions: list[bool] = []

    def close(self) -> None:
        self.closed_sessions.append(True)
        super().close()


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=TrackingSession, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router)

    def override_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session

    with session_factory() as session:
        _seed_cluster_data(session)
        session.commit()

    return TestClient(app)


def _seed_cluster_data(session: Session) -> None:
    politics = TagORM(
        tag_code="politics_national",
        display_name="Politics / National",
        tag_group="politics",
        description="",
        sort_order=10,
    )
    climate = TagORM(
        tag_code="climate",
        display_name="Climate",
        tag_group="society",
        description="",
        sort_order=20,
    )
    session.add_all([politics, climate])
    session.flush()

    sanchez = EntityORM(
        entity_type="politician",
        canonical_name="Pedro Sánchez",
        normalized_name="pedro sanchez",
        slug="politician-pedro-sanchez",
        canonical_source="rule",
    )
    feijoo = EntityORM(
        entity_type="politician",
        canonical_name="Alberto Núñez Feijóo",
        normalized_name="alberto nunez feijoo",
        slug="politician-alberto-nunez-feijoo",
        canonical_source="rule",
    )
    aemet = EntityORM(
        entity_type="organization",
        canonical_name="AEMET",
        normalized_name="aemet",
        slug="organization-aemet",
        canonical_source="rule",
    )
    session.add_all([sanchez, feijoo, aemet])
    session.flush()

    article1 = ArticleORM(
        source="elpais",
        title="Sánchez defiende el acuerdo presupuestario",
        url="https://elpais.com/1",
        published_at=datetime(2026, 3, 18, 9, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 18, 9, 5, tzinfo=UTC),
        section="politica",
        summary="El Gobierno cierra apoyos clave.",
        article_text="Texto 1",
    )
    article2 = ArticleORM(
        source="elmundo",
        title="Feijóo carga contra el pacto del Gobierno",
        url="https://elmundo.es/2",
        published_at=datetime(2026, 3, 18, 10, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 18, 10, 5, tzinfo=UTC),
        section="politica",
        summary="La oposición critica el acuerdo.",
        article_text="Texto 2",
    )
    article3 = ArticleORM(
        source="eldiario",
        title="AEMET activa avisos por una nueva borrasca",
        url="https://eldiario.es/3",
        published_at=datetime(2026, 3, 17, 8, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 17, 8, 5, tzinfo=UTC),
        section="sociedad",
        summary="Avisos en varias comunidades.",
        article_text="Texto 3",
    )
    article4 = ArticleORM(
        source="abc",
        title="Última hora sobre la borrasca y nuevos avisos",
        url="https://abc.es/4",
        published_at=datetime(2026, 3, 18, 11, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 18, 11, 5, tzinfo=UTC),
        section="sociedad",
        summary="Nuevos avisos elevan la cobertura del temporal.",
        article_text="Texto 4",
    )
    article5 = ArticleORM(
        source="elpais",
        title="El Gobierno presume de estabilidad tras el acuerdo",
        url="https://elpais.com/5",
        published_at=datetime(2026, 3, 18, 9, 30, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 18, 9, 35, tzinfo=UTC),
        section="politica",
        summary="Nueva pieza sobre los apoyos parlamentarios.",
        article_text="Texto 5",
    )
    article6 = ArticleORM(
        source="elmundo",
        title="Nueva ofensiva contra el pacto del Ejecutivo",
        url="https://elmundo.es/6",
        published_at=datetime(2026, 3, 18, 10, 30, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 18, 10, 35, tzinfo=UTC),
        section="politica",
        summary="La crítica opositora endurece el tono.",
        article_text="Texto 6",
    )
    article7 = ArticleORM(
        source="elmundo",
        title="Un boletín de última hora añade poco contexto editorial",
        url="https://elmundo.es/7",
        published_at=datetime(2026, 3, 18, 10, 45, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 18, 10, 50, tzinfo=UTC),
        section="politica",
        summary="Pieza breve de seguimiento con señal limitada.",
        article_text="Texto 7",
    )
    session.add_all([article1, article2, article3, article4, article5, article6, article7])
    session.flush()

    session.add_all(
        [
            ArticleAnalysisORM(
                article_id=article1.id,
                article_type="news_report",
                article_type_confidence=0.9,
                is_event_coverage=True,
                language="es",
                extraction_version="v1",
                content_hash="a",
            ),
            ArticleAnalysisORM(
                article_id=article2.id,
                article_type="news_report",
                article_type_confidence=0.9,
                is_event_coverage=True,
                language="es",
                extraction_version="v1",
                content_hash="b",
            ),
            ArticleAnalysisORM(
                article_id=article3.id,
                article_type="news_report",
                article_type_confidence=0.9,
                is_event_coverage=True,
                language="es",
                extraction_version="v1",
                content_hash="c",
            ),
            ArticleAnalysisORM(
                article_id=article4.id,
                article_type="news_report",
                article_type_confidence=0.9,
                is_event_coverage=True,
                language="es",
                extraction_version="v1",
                content_hash="d",
            ),
            ArticleAnalysisORM(
                article_id=article5.id,
                article_type="news_report",
                article_type_confidence=0.9,
                is_event_coverage=True,
                language="es",
                extraction_version="v1",
                content_hash="e",
            ),
            ArticleAnalysisORM(
                article_id=article6.id,
                article_type="news_report",
                article_type_confidence=0.9,
                is_event_coverage=True,
                language="es",
                extraction_version="v1",
                content_hash="f",
            ),
            ArticleAnalysisORM(
                article_id=article7.id,
                article_type="news_report",
                article_type_confidence=0.9,
                is_event_coverage=True,
                language="es",
                extraction_version="v1",
                content_hash="g",
            ),
        ]
    )
    session.add_all(
        [
            ArticleTagORM(
                article_id=article1.id,
                tag_id=politics.id,
                assignment_source="test",
                confidence=0.9,
                is_primary=True,
            ),
            ArticleTagORM(
                article_id=article2.id,
                tag_id=politics.id,
                assignment_source="test",
                confidence=0.9,
                is_primary=True,
            ),
            ArticleTagORM(
                article_id=article3.id,
                tag_id=climate.id,
                assignment_source="test",
                confidence=0.9,
                is_primary=True,
            ),
            ArticleTagORM(
                article_id=article4.id,
                tag_id=climate.id,
                assignment_source="test",
                confidence=0.9,
                is_primary=True,
            ),
            ArticleTagORM(
                article_id=article5.id,
                tag_id=politics.id,
                assignment_source="test",
                confidence=0.9,
                is_primary=True,
            ),
            ArticleTagORM(
                article_id=article6.id,
                tag_id=politics.id,
                assignment_source="test",
                confidence=0.9,
                is_primary=True,
            ),
            ArticleTagORM(
                article_id=article7.id,
                tag_id=politics.id,
                assignment_source="test",
                confidence=0.9,
                is_primary=True,
            ),
        ]
    )
    session.add_all(
        [
            EntityMentionORM(
                article_id=article1.id,
                entity_id=sanchez.id,
                surface_form="Pedro Sánchez",
                mention_text_normalized="pedro sanchez",
                mention_count=3,
                title_hits=1,
                summary_hits=1,
                body_hits=1,
                relevance_score=0.95,
            ),
            EntityMentionORM(
                article_id=article2.id,
                entity_id=feijoo.id,
                surface_form="Alberto Núñez Feijóo",
                mention_text_normalized="alberto nunez feijoo",
                mention_count=2,
                title_hits=1,
                summary_hits=0,
                body_hits=1,
                relevance_score=0.91,
            ),
            EntityMentionORM(
                article_id=article3.id,
                entity_id=aemet.id,
                surface_form="AEMET",
                mention_text_normalized="aemet",
                mention_count=2,
                title_hits=1,
                summary_hits=1,
                body_hits=0,
                relevance_score=0.88,
            ),
            EntityMentionORM(
                article_id=article4.id,
                entity_id=aemet.id,
                surface_form="AEMET",
                mention_text_normalized="aemet",
                mention_count=1,
                title_hits=0,
                summary_hits=1,
                body_hits=0,
                relevance_score=0.72,
            ),
            EntityMentionORM(
                article_id=article5.id,
                entity_id=sanchez.id,
                surface_form="Pedro Sánchez",
                mention_text_normalized="pedro sanchez",
                mention_count=2,
                title_hits=1,
                summary_hits=1,
                body_hits=0,
                relevance_score=0.87,
            ),
            EntityMentionORM(
                article_id=article6.id,
                entity_id=feijoo.id,
                surface_form="Alberto Núñez Feijóo",
                mention_text_normalized="alberto nunez feijoo",
                mention_count=2,
                title_hits=1,
                summary_hits=1,
                body_hits=0,
                relevance_score=0.86,
            ),
            EntityMentionORM(
                article_id=article7.id,
                entity_id=feijoo.id,
                surface_form="Alberto Núñez Feijóo",
                mention_text_normalized="alberto nunez feijoo",
                mention_count=1,
                title_hits=0,
                summary_hits=1,
                body_hits=0,
                relevance_score=0.61,
            ),
        ]
    )

    cluster1 = StoryClusterORM(
        cluster_key="story-2026-03-18-budget",
        status="active",
        cluster_type="breaking_event",
        summary_headline="Gobierno y oposición chocan por el pacto presupuestario",
        summary_text="Cobertura cruzada sobre el acuerdo y la respuesta de la oposición.",
        primary_tag_id=politics.id,
        article_count=5,
        source_count=2,
        first_article_published_at=article1.published_at,
        last_article_published_at=article7.published_at,
        clustering_version="v1",
    )
    cluster2 = StoryClusterORM(
        cluster_key="story-2026-03-18-storm",
        status="active",
        cluster_type="breaking_event",
        summary_headline="Nueva borrasca con avisos de AEMET",
        summary_text="Seguimiento de la tormenta y sus avisos.",
        primary_tag_id=climate.id,
        article_count=1,
        source_count=1,
        first_article_published_at=article4.published_at,
        last_article_published_at=article4.published_at,
        clustering_version="v1",
    )
    session.add_all([cluster1, cluster2])
    session.flush()

    session.add_all(
        [
            ClusterMemberORM(
                cluster_id=cluster1.id,
                article_id=article1.id,
                membership_score=0.94,
                membership_reason_json="{}",
            ),
            ClusterMemberORM(
                cluster_id=cluster1.id,
                article_id=article2.id,
                membership_score=0.88,
                membership_reason_json="{}",
            ),
            ClusterMemberORM(
                cluster_id=cluster1.id,
                article_id=article5.id,
                membership_score=0.9,
                membership_reason_json="{}",
            ),
            ClusterMemberORM(
                cluster_id=cluster1.id,
                article_id=article6.id,
                membership_score=0.87,
                membership_reason_json="{}",
            ),
            ClusterMemberORM(
                cluster_id=cluster1.id,
                article_id=article7.id,
                membership_score=0.81,
                membership_reason_json="{}",
            ),
            ClusterMemberORM(
                cluster_id=cluster2.id,
                article_id=article4.id,
                membership_score=1.0,
                membership_reason_json="{}",
            ),
        ]
    )
    session.add_all(
        [
            ClusterEntityORM(
                cluster_id=cluster1.id,
                entity_id=sanchez.id,
                article_coverage_count=1,
                mention_count=3,
                aggregate_relevance_score=0.95,
            ),
            ClusterEntityORM(
                cluster_id=cluster1.id,
                entity_id=feijoo.id,
                article_coverage_count=1,
                mention_count=2,
                aggregate_relevance_score=0.91,
            ),
            ClusterEntityORM(
                cluster_id=cluster2.id,
                entity_id=aemet.id,
                article_coverage_count=1,
                mention_count=2,
                aggregate_relevance_score=0.88,
            ),
        ]
    )
    session.add_all(
        [
            ArticleEditorialAnalysisORM(
                article_id=article1.id,
                article_type="news",
                article_type_confidence=0.92,
                bias_label="center_left",
                bias_score=-0.22,
                bias_confidence=0.66,
                tone_emotional="measured",
                tone_target="government",
                opinionatedness="low",
                sensationalism="low",
                rhetorical_certainty="moderate",
                editorial_applicability="full",
                editorial_applicability_reason="general_editorial_content",
                unclear_reasons_json='["weak_signal"]',
                article_type_status="resolved",
                bias_status="resolved",
                tone_emotional_status="resolved",
                tone_target_status="resolved",
                opinionatedness_status="resolved",
                sensationalism_status="resolved",
                rhetorical_certainty_status="resolved",
                framing_status="resolved",
                framing_devices_json='["institutional_conflict","accountability_frame"]',
                evidence_spans_json='[{"type":"quote","text":"El Gobierno cierra apoyos clave.","note":"Lead framing"}]',
                diagnostics_json='{"dimension_status":{"bias":"resolved"}}',
                rationale="Cobertura principalmente informativa.",
                analysis_status="completed",
                failure_reason="",
                model_provider="openrouter",
                model_name="gpt-test",
                model_version="",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="ehash-1",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 18, 9, 10, tzinfo=UTC),
            ),
            ArticleEditorialAnalysisORM(
                article_id=article2.id,
                article_type="opinion",
                article_type_confidence=0.88,
                bias_label="center_right",
                bias_score=0.41,
                bias_confidence=0.39,
                tone_emotional="critical",
                tone_target="government",
                opinionatedness="high",
                sensationalism="moderate",
                rhetorical_certainty="high",
                editorial_applicability="limited",
                editorial_applicability_reason="limited_editorial_signal",
                unclear_reasons_json='["weak_signal"]',
                article_type_status="resolved",
                bias_status="resolved",
                tone_emotional_status="resolved",
                tone_target_status="resolved",
                opinionatedness_status="resolved",
                sensationalism_status="resolved",
                rhetorical_certainty_status="resolved",
                framing_status="resolved",
                framing_devices_json='["accountability_frame","conflict_frame"]',
                evidence_spans_json='[{"type":"quote","text":"La oposición critica el acuerdo.","note":"Summary framing"}]',
                diagnostics_json='{"dimension_status":{"bias":"weak_signal"}}',
                rationale="Texto con framing opositor y señal parcial.",
                analysis_status="completed",
                failure_reason="",
                model_provider="openrouter",
                model_name="gpt-test",
                model_version="",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="ehash-2",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 18, 10, 10, tzinfo=UTC),
            ),
            ArticleEditorialAnalysisORM(
                article_id=article4.id,
                article_type="news",
                article_type_confidence=0.77,
                bias_label="unclear",
                bias_score=0.0,
                bias_confidence=0.0,
                tone_emotional="unclear",
                tone_target="unclear",
                opinionatedness="unclear",
                sensationalism="unclear",
                rhetorical_certainty="unclear",
                editorial_applicability="out_of_domain",
                editorial_applicability_reason="weather_bulletin",
                unclear_reasons_json='["provider_missing"]',
                article_type_status="resolved",
                bias_status="out_of_domain",
                tone_emotional_status="out_of_domain",
                tone_target_status="out_of_domain",
                opinionatedness_status="out_of_domain",
                sensationalism_status="out_of_domain",
                rhetorical_certainty_status="out_of_domain",
                framing_status="out_of_domain",
                framing_devices_json="[]",
                evidence_spans_json="[]",
                diagnostics_json='{"dimension_status":{"bias":"out_of_domain"}}',
                rationale="Boletín meteorológico fuera de dominio editorial.",
                analysis_status="completed",
                failure_reason="",
                model_provider="openrouter",
                model_name="gpt-test",
                model_version="",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="ehash-4",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 18, 11, 10, tzinfo=UTC),
            ),
            ArticleEditorialAnalysisORM(
                article_id=article5.id,
                article_type="news",
                article_type_confidence=0.9,
                bias_label="center_left",
                bias_score=-0.31,
                bias_confidence=0.71,
                tone_emotional="measured",
                tone_target="government",
                opinionatedness="low",
                sensationalism="low",
                rhetorical_certainty="moderate",
                editorial_applicability="full",
                editorial_applicability_reason="general_editorial_content",
                unclear_reasons_json="[]",
                article_type_status="resolved",
                bias_status="resolved",
                tone_emotional_status="resolved",
                tone_target_status="resolved",
                opinionatedness_status="resolved",
                sensationalism_status="resolved",
                rhetorical_certainty_status="resolved",
                framing_status="resolved",
                framing_devices_json='["institutional_conflict"]',
                evidence_spans_json='[{"type":"quote","text":"Nueva pieza sobre los apoyos parlamentarios.","note":"Lead framing"}]',
                diagnostics_json='{"dimension_status":{"bias":"resolved"}}',
                rationale="Cobertura de seguimiento todavía informativa.",
                analysis_status="completed",
                failure_reason="",
                model_provider="openrouter",
                model_name="gpt-test",
                model_version="",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="ehash-5",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 18, 9, 40, tzinfo=UTC),
            ),
            ArticleEditorialAnalysisORM(
                article_id=article6.id,
                article_type="opinion",
                article_type_confidence=0.9,
                bias_label="right",
                bias_score=0.76,
                bias_confidence=0.69,
                tone_emotional="critical",
                tone_target="government",
                opinionatedness="high",
                sensationalism="moderate",
                rhetorical_certainty="high",
                editorial_applicability="full",
                editorial_applicability_reason="general_editorial_content",
                unclear_reasons_json="[]",
                article_type_status="resolved",
                bias_status="resolved",
                tone_emotional_status="resolved",
                tone_target_status="resolved",
                opinionatedness_status="resolved",
                sensationalism_status="resolved",
                rhetorical_certainty_status="resolved",
                framing_status="resolved",
                framing_devices_json='["conflict_frame","conflict_frame","accountability_frame"]',
                evidence_spans_json='[{"type":"quote","text":"La crítica opositora endurece el tono.","note":"Lead framing"}]',
                diagnostics_json='{"dimension_status":{"bias":"resolved"}}',
                rationale="Texto abiertamente adversarial contra el acuerdo.",
                analysis_status="completed",
                failure_reason="",
                model_provider="openrouter",
                model_name="gpt-test",
                model_version="",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="ehash-6",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 18, 10, 40, tzinfo=UTC),
            ),
            ArticleEditorialAnalysisORM(
                article_id=article7.id,
                article_type="news",
                article_type_confidence=0.68,
                bias_label="unclear",
                bias_score=0.0,
                bias_confidence=0.18,
                tone_emotional="unclear",
                tone_target="government",
                opinionatedness="unclear",
                sensationalism="unclear",
                rhetorical_certainty="unclear",
                editorial_applicability="limited",
                editorial_applicability_reason="limited_editorial_signal",
                unclear_reasons_json='["weak_signal"]',
                article_type_status="resolved",
                bias_status="weak_signal",
                tone_emotional_status="weak_signal",
                tone_target_status="resolved",
                opinionatedness_status="weak_signal",
                sensationalism_status="weak_signal",
                rhetorical_certainty_status="weak_signal",
                framing_status="weak_signal",
                framing_devices_json="[]",
                evidence_spans_json='[{"type":"quote","text":"Pieza breve de seguimiento con señal limitada.","note":"Thin support"}]',
                diagnostics_json='{"dimension_status":{"bias":"weak_signal"}}',
                rationale="Señal editorial demasiado tenue para resolver dimensiones centrales.",
                analysis_status="completed",
                failure_reason="",
                model_provider="openrouter",
                model_name="gpt-test",
                model_version="",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="ehash-7",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 18, 10, 55, tzinfo=UTC),
            ),
        ]
    )


def test_cluster_list_detail_filters_and_404() -> None:
    TrackingSession.closed_sessions = []
    client = _build_client()

    listing = client.get("/api/v1/clusters")
    filtered = client.get("/api/v1/clusters", params={"tag_code": "climate"})
    detail = client.get("/api/v1/clusters/1")
    filters = client.get("/api/v1/clusters/filters")
    missing = client.get("/api/v1/clusters/999")

    assert listing.status_code == 200
    assert listing.json()["meta"] == {"total": 2, "limit": 20, "offset": 0}
    assert (
        listing.json()["items"][0]["summary_headline"]
        == "Gobierno y oposición chocan por el pacto presupuestario"
    )
    assert listing.json()["items"][0]["sources"] == ["elmundo", "elpais"]
    assert listing.json()["items"][0]["primary_tag"]["tag_code"] == "politics_national"
    assert listing.json()["items"][0]["top_entities"][0]["slug"] == "politician-pedro-sanchez"

    assert filtered.status_code == 200
    assert filtered.json()["meta"]["total"] == 1
    assert filtered.json()["items"][0]["cluster_key"] == "story-2026-03-18-storm"

    assert detail.status_code == 200
    assert detail.json()["cluster"]["id"] == 1
    assert len(detail.json()["members"]) == 5
    assert detail.json()["members"][0]["tags"][0]["tag_code"] == "politics_national"
    assert detail.json()["members"][0]["entities"]
    assert detail.json()["members"][0]["editorial_preview"]["analysis_status"] == "completed"
    assert (
        detail.json()["members"][0]["editorial_preview"]["review_flags"]["low_confidence"] is True
    )
    assert detail.json()["editorial_summary"]["analyzed_article_count"] == 5
    assert detail.json()["editorial_summary"]["applicability_breakdown"]["full"] == 3
    assert detail.json()["editorial_summary"]["applicability_breakdown"]["limited"] == 2
    assert detail.json()["editorial_summary"]["source_summaries"][0]["source"] == "elmundo"
    assert (
        detail.json()["editorial_summary"]["source_summaries"][0]["review_flag_counts"]["limited"]
        == 2
    )
    assert detail.json()["editorial_summary"]["cluster_signals"]
    comparative = detail.json()["editorial_summary"]["comparative_metrics"]
    assert comparative["eligible_source_count"] == 2
    assert comparative["divergence_signals"]
    assert {item["source"] for item in comparative["included_sources"]} == {"elpais", "elmundo"}

    assert filters.status_code == 200
    assert {item["value"] for item in filters.json()["sources"]} == {"elpais", "elmundo", "abc"}
    assert {item["value"] for item in filters.json()["tags"]} == {"politics_national", "climate"}
    assert {item["slug"] for item in filters.json()["entities"]} == {
        "politician-pedro-sanchez",
        "politician-alberto-nunez-feijoo",
        "organization-aemet",
    }

    assert missing.status_code == 404
    assert missing.json() == {"detail": "Story cluster not found"}
    assert len(TrackingSession.closed_sessions) >= 5


def test_cluster_detail_preserves_out_of_domain_and_scope_notes() -> None:
    client = _build_client()
    detail = client.get("/api/v1/clusters/2")
    payload = detail.json()

    assert detail.status_code == 200
    assert payload["editorial_summary"]["analyzed_article_count"] == 1
    assert payload["editorial_summary"]["applicability_breakdown"]["out_of_domain"] == 1
    assert (
        payload["editorial_summary"]["source_summaries"][0]["review_flag_counts"]["out_of_domain"]
        == 1
    )
    assert payload["editorial_summary"]["comparative_metrics"]["eligible_source_count"] == 0
    assert payload["editorial_summary"]["comparative_metrics"]["divergence_signals"] == []
    assert (
        payload["editorial_summary"]["comparative_metrics"]["source_metrics"][0][
            "opinionatedness_index"
        ]
        is None
    )
    assert (
        payload["editorial_summary"]["comparative_metrics"]["source_metrics"][0][
            "bias_direction_index"
        ]
        is None
    )
    assert any(
        "hidden" in note.lower()
        for note in payload["editorial_summary"]["comparative_metrics"]["source_metrics"][0][
            "metric_notes"
        ]
    )
    assert (
        "fewer than two sources"
        in payload["editorial_summary"]["comparative_metrics"]["comparison_note"]
    )
    assert "story cluster only" in payload["editorial_summary"]["scope_note"]


def test_cluster_comparative_metrics_expose_meaningful_divergence_and_suppress_weak_dimensions() -> (
    None
):
    client = _build_client()
    payload = client.get("/api/v1/clusters/1").json()["editorial_summary"]["comparative_metrics"]

    source_metrics = {item["source"]: item for item in payload["source_metrics"]}
    included_sources = {item["source"]: item for item in payload["included_sources"]}
    divergence_by_dimension = {item["dimension"]: item for item in payload["divergence_signals"]}

    assert included_sources["elpais"]["comparison_eligibility"] == "eligible"
    assert included_sources["elmundo"]["comparison_eligibility"] == "limited"
    assert included_sources["elmundo"]["limited_applicability_count"] == 2
    assert source_metrics["elpais"]["opinionatedness_index"] == 0.0
    assert source_metrics["elpais"]["emotional_tone_index"] == 0.0
    assert source_metrics["elpais"]["bias_direction_index"] == -0.5
    assert source_metrics["elmundo"]["opinionatedness_index"] == 1.0
    assert source_metrics["elmundo"]["emotional_tone_index"] == 1.0
    assert source_metrics["elmundo"]["bias_direction_index"] == 0.75
    assert source_metrics["elmundo"]["confidence_band"] == "low"
    assert any(
        "limited-applicability" in note.lower()
        for note in source_metrics["elmundo"]["metric_notes"]
    )
    assert divergence_by_dimension["bias"]["leading_source"] == "elmundo"
    assert divergence_by_dimension["bias"]["trailing_source"] == "elpais"
    assert divergence_by_dimension["bias"]["support"]["leading_usable_articles"] == 2
    assert divergence_by_dimension["bias"]["support"]["trailing_usable_articles"] == 2
    assert divergence_by_dimension["opinionatedness"]["leading_source"] == "elmundo"
    assert divergence_by_dimension["tone"]["leading_source"] == "elmundo"


def test_cluster_list_supports_source_entity_and_search_filters() -> None:
    client = _build_client()

    by_source = client.get("/api/v1/clusters", params={"source": "elpais"})
    by_entity = client.get("/api/v1/clusters", params={"entity_slug": "organization-aemet"})
    by_search = client.get("/api/v1/clusters", params={"search": "oposición"})

    assert by_source.status_code == 200
    assert by_source.json()["meta"]["total"] == 1
    assert by_source.json()["items"][0]["id"] == 1

    assert by_entity.status_code == 200
    assert by_entity.json()["meta"]["total"] == 1
    assert by_entity.json()["items"][0]["id"] == 2

    assert by_search.status_code == 200
    assert by_search.json()["meta"]["total"] == 1
    assert by_search.json()["items"][0]["id"] == 1


def test_cluster_id_query_is_postgres_safe_and_keeps_stable_ordering() -> None:
    stmt = _matching_cluster_ids_stmt(ClusterListFilters()).order_by(
        StoryClusterORM.article_count.desc(),
        StoryClusterORM.source_count.desc(),
        StoryClusterORM.last_article_published_at.desc().nullslast(),
        StoryClusterORM.id.desc(),
    )
    compiled = str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )

    assert "SELECT DISTINCT" not in compiled
    assert (
        "GROUP BY story_clusters.id, story_clusters.article_count, story_clusters.source_count, story_clusters.last_article_published_at"
        in compiled
    )
    assert (
        "ORDER BY story_clusters.article_count DESC, story_clusters.source_count DESC, story_clusters.last_article_published_at DESC NULLS LAST, story_clusters.id DESC"
        in compiled
    )

    client = _build_client()
    response = client.get("/api/v1/clusters", params={"limit": 20, "offset": 0})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [1, 2]
    assert (
        response.json()["items"][0]["article_count"] > response.json()["items"][1]["article_count"]
    )
    assert (
        response.json()["items"][0]["last_article_published_at"]
        < response.json()["items"][1]["last_article_published_at"]
    )
