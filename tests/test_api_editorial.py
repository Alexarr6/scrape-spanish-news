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
from src.persistence.orm_models import ArticleORM, Base


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
        article = ArticleORM(
            source="eldiario",
            title="Una pieza",
            url="https://eldiario.es/a",
            published_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
            scraped_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
            section="politica",
            summary="Resumen",
            article_text="Cuerpo",
            tags="politica",
        )
        session.add(article)
        session.flush()
        session.add(
            ArticleEditorialAnalysisORM(
                article_id=article.id,
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
                framing_devices_json='["humanitarian"]',
                evidence_spans_json=(
                    '[{"type":"headline","text":"Texto","note":"Apoya el encuadre"}]'
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
        session.commit()

    return TestClient(app)


def test_editorial_api_returns_payload_and_404() -> None:
    client = _build_client()

    ok = client.get("/api/v1/editorial-analysis/1")
    missing = client.get("/api/v1/editorial-analysis/999")

    assert ok.status_code == 200
    assert ok.json()["article_id"] == 1
    assert ok.json()["framing_devices"] == ["humanitarian"]
    assert ok.json()["evidence_spans"][0]["type"] == "headline"
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Editorial analysis not found"}
