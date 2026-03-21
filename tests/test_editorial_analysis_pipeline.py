from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.analysis.orm_models import ArticleEditorialAnalysisORM
from src.analysis.pipeline import EditorialAnalysisPipeline
from src.persistence.orm_models import ArticleORM, Base


class _FakeLLM:
    settings = type("S", (), {"model": "openrouter/test-model", "prompt_version": "v1"})()

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def analyze_editorial(self, *, article_prompt: str, schema: dict[str, object]):
        from src.analysis.contracts import ArticleEditorialAnalysisPayload, OpenRouterUsage

        assert "ARTICLE_METADATA:" in article_prompt
        assert schema["properties"]["bias_label"]["enum"][-1] == "unclear"
        return (
            ArticleEditorialAnalysisPayload.model_validate(self.payload),
            OpenRouterUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )


VALID_PAYLOAD = {
    "article_type": "news_report",
    "article_type_confidence": 0.81,
    "bias_label": "center",
    "bias_score": 0.05,
    "bias_confidence": 0.42,
    "tone_emotional": "calm",
    "tone_target": "neutral",
    "opinionatedness": "straight_reporting",
    "sensationalism": "low",
    "rhetorical_certainty": "cautious",
    "framing_devices": ["institutional_stability"],
    "evidence_spans": [
        {
            "type": "headline",
            "text": "El Congreso aprueba el paquete fiscal",
            "note": "Descriptive institutional framing",
        }
    ],
    "rationale": (
        "The piece stays mostly descriptive, avoids ideological loading, and supports "
        "its framing with restrained institutional language."
    ),
}


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_editorial_pipeline_persists_completed_analysis_and_skips_unchanged() -> None:
    session = _make_session()
    article = ArticleORM(
        source="elpais",
        title="Título",
        url="https://elpais.com/a",
        published_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        section="politica",
        summary="Resumen",
        article_text="Cuerpo de prueba",
        tags="politica",
    )
    session.add(article)
    session.commit()

    pipeline = EditorialAnalysisPipeline(session)
    pipeline.llm = _FakeLLM(VALID_PAYLOAD)

    metrics = pipeline.analyze_articles(days_back=10, limit=10)
    stored = session.execute(select(ArticleEditorialAnalysisORM)).scalar_one()

    assert metrics.analyzed_count == 1
    assert metrics.failed_count == 0
    assert stored.article_id == article.id
    assert stored.analysis_status == "completed"
    assert stored.bias_label == "center"
    assert stored.model_name == "openrouter/test-model"
    assert "institutional_stability" in stored.framing_devices_json

    again = pipeline.analyze_articles(days_back=10, limit=10)
    assert again.skipped_count == 1


def test_editorial_pipeline_marks_failed_rows_when_validation_blows_up() -> None:
    session = _make_session()
    article = ArticleORM(
        source="abc",
        title="Título",
        url="https://abc.es/a",
        published_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        section="politica",
        summary="Resumen",
        article_text="Cuerpo de prueba",
        tags="politica",
    )
    session.add(article)
    session.commit()

    pipeline = EditorialAnalysisPipeline(session)

    class _BrokenLLM:
        settings = type("S", (), {"model": "broken-model", "prompt_version": "v1"})()

        def analyze_editorial(self, *, article_prompt: str, schema: dict[str, object]):
            raise ValueError("schema_validation_failed")

    pipeline.llm = _BrokenLLM()
    metrics = pipeline.analyze_articles(days_back=10, limit=10)
    stored = session.execute(select(ArticleEditorialAnalysisORM)).scalar_one()

    assert metrics.failed_count == 1
    assert stored.analysis_status == "failed"
    assert stored.failure_reason == "schema_validation_failed"
