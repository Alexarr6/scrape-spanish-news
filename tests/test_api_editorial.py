from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.analysis.orm_models import ArticleEditorialAnalysisORM
from src.api.v1.articles import get_session
from src.api.v1.editorial import router
from src.persistence.orm import ArticleORM, Base


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
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
        article1 = ArticleORM(
            source="eldiario",
            title="Una pieza",
            url="https://eldiario.es/a",
            published_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
            scraped_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
            section="politica",
            summary="Resumen",
            article_text="Cuerpo con bastante texto para preview",
            tags="politica",
        )
        article2 = ArticleORM(
            source="abc",
            title="Otra pieza",
            url="https://abc.es/b",
            published_at=datetime(2026, 3, 19, 9, 0, tzinfo=UTC),
            scraped_at=datetime(2026, 3, 19, 9, 5, tzinfo=UTC),
            section="espana",
            summary="Otro resumen",
            article_text="Otro cuerpo",
            tags="espana",
        )
        article3 = ArticleORM(
            source="elpais",
            title="Pendiente sin fila editorial",
            url="https://elpais.com/c",
            published_at=datetime(2026, 3, 18, 8, 0, tzinfo=UTC),
            scraped_at=datetime(2026, 3, 18, 8, 5, tzinfo=UTC),
            section="opinion",
            summary="Pendiente",
            article_text="Sin análisis todavía",
            tags="opinion",
        )
        session.add_all([article1, article2, article3])
        session.flush()
        session.add(
            ArticleEditorialAnalysisORM(
                article_id=article1.id,
                article_type="analysis",
                article_type_confidence=0.8,
                bias_label="center_left",
                bias_score=-0.25,
                bias_confidence=0.61,
                tone_emotional="loaded",
                tone_target="critical",
                opinionatedness="interpretive",
                sensationalism="medium",
                rhetorical_certainty="assertive",
                editorial_applicability="full",
                editorial_applicability_reason="general_editorial_content",
                analysis_path="strict",
                framing_devices_json='["humanitarian"]',
                evidence_spans_json=(
                    '[{"type":"headline","text":"Texto","note":"Apoya el encuadre"}]'
                ),
                diagnostics_json=(
                    '{"provider_path":"strict_success","editorial_applicability":"full",'
                    '"editorial_applicability_reason":"general_editorial_content",'
                    '"dimension_status":{"bias":{"value":"center_left","status":"resolved",'
                    '"reason":"canonical_value_resolved","notes":[],"raw_hints":[]}},'
                    '"repair_warnings":[],"normalization_warnings":[],"dropped_fields":[],'
                    '"truncated_fields":[],"preserved_signals":{},"provider_failures":[],'
                    '"unclear_reasons":[]}'
                ),
                rationale="The article foregrounds social harm and uses clear evaluative framing.",
                analysis_status="completed",
                model_provider="openrouter",
                model_name="model-x",
                model_version="model-x",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="abc",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 20, 12, 6, tzinfo=UTC),
            )
        )
        session.add(
            ArticleEditorialAnalysisORM(
                article_id=article2.id,
                article_type="unclear",
                article_type_confidence=0.2,
                bias_label="unclear",
                bias_score=0.0,
                bias_confidence=0.2,
                tone_emotional="unclear",
                tone_target="unclear",
                opinionatedness="unclear",
                sensationalism="unclear",
                rhetorical_certainty="unclear",
                editorial_applicability="out_of_domain",
                editorial_applicability_reason="sports_recap",
                analysis_path="strict_json_schema:payload_validation_failed",
                framing_devices_json="[]",
                evidence_spans_json="[]",
                diagnostics_json="{}",
                rationale="Failed attempt placeholder rationale.",
                analysis_status="failed",
                failure_reason="schema exploded",
                model_provider="openrouter",
                model_name="model-x",
                model_version="model-x",
                prompt_version="v1",
                schema_version="editorial-analysis-v1",
                content_hash="def",
                source_text_version="title_summary_body_v1",
                analyzed_at=datetime(2026, 3, 19, 9, 6, tzinfo=UTC),
            )
        )
        session.commit()

    return TestClient(app)


def test_editorial_api_returns_payload_and_404() -> None:
    client = _build_client()

    ok = client.get("/api/v1/editorial-analysis/1")
    missing = client.get("/api/v1/editorial-analysis/999")

    assert ok.status_code == 200
    assert ok.json()["article_id"] == 1
    assert ok.json()["source"] == "eldiario"
    assert ok.json()["framing_devices"] == ["humanitarian"]
    assert ok.json()["editorial_applicability"] == "full"
    assert ok.json()["diagnostics"]["dimension_status"]["bias"]["status"] == "resolved"
    assert ok.json()["evidence_spans"][0]["type"] == "headline"
    assert ok.json()["review_flags"]["needs_review"] is False
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Editorial analysis not found"}


def test_editorial_list_api_filters_and_treats_missing_rows_as_pending() -> None:
    client = _build_client()

    pending = client.get("/api/v1/editorial-analysis", params={"status": "pending"})
    failed = client.get("/api/v1/editorial-analysis", params={"status": "failed"})
    filtered = client.get(
        "/api/v1/editorial-analysis",
        params={"source": "eldiario", "min_bias_confidence": 0.5, "limit": 1, "offset": 0},
    )

    assert pending.status_code == 200
    assert pending.json()["total"] == 1
    assert pending.json()["items"][0]["title"] == "Pendiente sin fila editorial"
    assert pending.json()["items"][0]["analysis_status"] == "pending"
    assert pending.json()["items"][0]["review_flags"]["pending_analysis"] is True

    assert failed.status_code == 200
    assert failed.json()["total"] == 1
    assert failed.json()["items"][0]["editorial_applicability"] == "out_of_domain"
    assert failed.json()["items"][0]["failure_reason"] == "schema exploded"
    assert failed.json()["items"][0]["review_flags"]["failed_analysis"] is True
    assert failed.json()["items"][0]["review_flags"]["needs_review"] is True

    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["limit"] == 1
    assert filtered.json()["items"][0]["source"] == "eldiario"
    assert filtered.json()["items"][0]["evidence_count"] == 1
