from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.analysis.editorial.llm import EditorialAnalysisAttempt, EditorialAnalysisResult
from src.analysis.store.models import ArticleEditorialAnalysisORM
from src.analysis.editorial.selection import EditorialSelectionFilters
from src.analysis.editorial.service import EditorialAnalysisPipeline
from src.persistence.orm import ArticleORM, Base


class _Settings:
    model = "openrouter/test-model"
    prompt_version = "v1"
    provider_label = "openrouter"


class _CustomSettings:
    model = "custom/test-model"
    prompt_version = "v1"
    provider_label = "custom"


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


class _FakeLLM:
    def __init__(self, result: EditorialAnalysisResult, *, settings=None) -> None:
        self.result = result
        self.settings = settings or _Settings()

    def analyze_editorial(self, *, article_prompt: str, schema: dict[str, object]):
        assert "ARTICLE_METADATA:" in article_prompt
        assert "bias_label" in schema["properties"]
        assert "ideological_bias_framing" not in schema["properties"]
        return self.result


def _attempt(
    *,
    mode: str = "strict_json_schema",
    request_accepted: bool = True,
    payload=None,
    failure_class=None,
    failure_message="",
    raw_content=None,
    parsed_json=None,
    normalization_warnings=(),
    repair_warnings=(),
    dropped_fields=(),
    truncated_fields=(),
    unclear_reasons=(),
    diagnostics=None,
):
    from src.analysis.shared.contracts import (
        ArticleEditorialAnalysisPayload,
        EditorialAnalysisDiagnostics,
        OpenRouterUsage,
    )

    return EditorialAnalysisAttempt(
        mode=mode,
        request_accepted=request_accepted,
        payload=None
        if payload is None
        else ArticleEditorialAnalysisPayload.model_validate(payload),
        usage=OpenRouterUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        failure_class=failure_class,
        failure_message=failure_message,
        raw_message={"content": raw_content},
        raw_content=raw_content,
        parsed_json=parsed_json,
        normalization_warnings=tuple(normalization_warnings),
        repair_warnings=tuple(repair_warnings),
        dropped_fields=tuple(dropped_fields),
        truncated_fields=tuple(truncated_fields),
        unclear_reasons=tuple(unclear_reasons),
        diagnostics=None
        if diagnostics is None
        else EditorialAnalysisDiagnostics.model_validate(diagnostics),
        raw_response={"id": "resp_test"},
    )


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _make_article(session: Session, *, source: str = "elpais", title: str = "Título") -> ArticleORM:
    article = ArticleORM(
        source=source,
        title=title,
        url=f"https://{source}.com/{title.lower().replace(' ', '-')}",
        published_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        section="politica",
        summary="Resumen",
        article_text="Cuerpo de prueba",
        tags="politica",
    )
    session.add(article)
    session.commit()
    return article


def test_editorial_pipeline_persists_completed_analysis_and_skips_unchanged() -> None:
    session = _make_session()
    article = _make_article(session)
    pipeline = EditorialAnalysisPipeline(session)
    pipeline.llm = _FakeLLM(EditorialAnalysisResult(attempts=(_attempt(payload=VALID_PAYLOAD),)))

    metrics = pipeline.analyze_articles(days_back=10, limit=10)
    stored = session.execute(select(ArticleEditorialAnalysisORM)).scalar_one()

    assert metrics.analyzed_count == 1
    assert metrics.failed_count == 0
    assert metrics.request_count == 1
    assert stored.article_id == article.id
    assert stored.analysis_status == "completed"
    assert stored.bias_label == "center"
    assert stored.model_provider == "openrouter"
    assert stored.model_name == "openrouter/test-model"
    assert stored.bias_status == "resolved"
    assert json.loads(stored.unclear_reasons_json) == ["limited_applicability"]
    assert "institutional_stability" in stored.framing_devices_json
    assert metrics.strict_success_count == 1

    again = pipeline.analyze_articles(days_back=10, limit=10, status="any")
    assert again.skipped_count == 1


def test_editorial_pipeline_counts_request_and_writes_artifact_on_parse_failure(
    tmp_path: Path,
) -> None:
    session = _make_session()
    article = _make_article(session, source="abc")
    pipeline = EditorialAnalysisPipeline(session)
    pipeline.llm = _FakeLLM(
        EditorialAnalysisResult(
            attempts=(
                _attempt(
                    failure_class="json_parse_failed",
                    failure_message="Expecting value: line 1 column 1 (char 0)",
                    raw_content="",
                ),
            )
        )
    )

    from src.analysis.editorial import service as editorial_service_module

    original = editorial_service_module.editorial_debug_artifact_dir
    editorial_service_module.editorial_debug_artifact_dir = lambda: tmp_path
    try:
        metrics = pipeline.analyze_articles(days_back=10, limit=10)
    finally:
        editorial_service_module.editorial_debug_artifact_dir = original

    stored = session.execute(select(ArticleEditorialAnalysisORM)).scalar_one()
    artifacts = list(tmp_path.glob("*.json"))

    assert metrics.request_count == 1
    assert metrics.failed_count == 1
    assert metrics.parse_failed_count == 1
    assert stored.analysis_status == "failed"
    assert stored.provider_failure_class == "json_parse_failed"
    assert stored.failure_reason.startswith("json_parse_failed:")
    assert "artifact=" in stored.failure_reason
    assert len(artifacts) == 1
    artifact_payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert artifact_payload["article_id"] == article.id
    assert artifact_payload["attempts"][0]["failure_class"] == "json_parse_failed"
    assert artifact_payload["attempts"][0]["repair_warnings"] == []
    assert artifact_payload["attempts"][0]["final_unclear_reasons"] == []


def test_editorial_pipeline_marks_failed_rows_for_incompatible_provider() -> None:
    session = _make_session()
    _make_article(session, source="eldiario")
    pipeline = EditorialAnalysisPipeline(session)
    pipeline.llm = _FakeLLM(
        EditorialAnalysisResult(
            attempts=(
                _attempt(
                    request_accepted=False,
                    failure_class="provider_incompatible_schema",
                    failure_message=(
                        "provider 'custom' does not support editorial strict schema"
                    ),
                ),
            )
        ),
        settings=_CustomSettings(),
    )

    metrics = pipeline.analyze_articles(days_back=10, limit=10)
    stored = session.execute(select(ArticleEditorialAnalysisORM)).scalar_one()

    assert metrics.request_count == 0
    assert metrics.provider_rejected_count == 0
    assert metrics.analyzed_count == 0
    assert metrics.fallback_success_count == 0
    assert metrics.fallback_after_strict_reject_count == 0
    assert stored.analysis_status == "failed"
    assert stored.provider_failure_class == "provider_incompatible_schema"
    assert stored.failure_reason.startswith("provider_incompatible_schema:")


def test_editorial_pipeline_default_diagnostics_treat_unclear_as_abstention() -> None:
    session = _make_session()
    _make_article(session, source="elpais")
    payload = dict(VALID_PAYLOAD)
    payload.update(
        {
            "bias_label": "unclear",
            "bias_score": 0.0,
            "bias_confidence": 0.3,
            "tone_target": "unclear",
            "rhetorical_certainty": "unclear",
            "framing_devices": [],
            "rationale": "Agenda cultural descriptiva con tono neutro y señal editorial débil.",
        }
    )
    pipeline = EditorialAnalysisPipeline(session)
    pipeline.llm = _FakeLLM(EditorialAnalysisResult(attempts=(_attempt(payload=payload),)))

    metrics = pipeline.analyze_articles(days_back=10, limit=10)
    stored = session.execute(select(ArticleEditorialAnalysisORM)).scalar_one()

    assert metrics.analyzed_count == 1
    assert metrics.fallback_success_count == 0
    assert metrics.bias_mapping_loss_count == 0
    assert metrics.rows_with_unmapped_signals_count == 0
    assert json.loads(stored.unclear_reasons_json) == [
        "limited_applicability",
        "weak_signal_abstain",
    ]
    assert stored.bias_status == "weak_signal_abstain"
    assert stored.tone_target_status == "weak_signal_abstain"
    assert stored.rhetorical_certainty_status == "weak_signal_abstain"
    assert stored.framing_status == "weak_signal_abstain"


def test_editorial_pipeline_marks_failed_rows_when_validation_blows_up() -> None:
    session = _make_session()
    _make_article(session, source="larazon")
    invalid_payload = dict(VALID_PAYLOAD)
    invalid_payload["evidence_spans"] = []
    pipeline = EditorialAnalysisPipeline(session)
    pipeline.llm = _FakeLLM(
        EditorialAnalysisResult(
            attempts=(
                _attempt(
                    failure_class="payload_validation_failed",
                    failure_message="at least one evidence span is required",
                    raw_content=json.dumps(invalid_payload),
                    parsed_json=invalid_payload,
                ),
            )
        )
    )

    metrics = pipeline.analyze_articles(days_back=10, limit=10)
    stored = session.execute(select(ArticleEditorialAnalysisORM)).scalar_one()

    assert metrics.failed_count == 1
    assert metrics.validation_failed_count == 1
    assert stored.analysis_status == "failed"
    assert stored.failure_reason.startswith("payload_validation_failed:")


def test_editorial_pipeline_supports_pending_failed_targeting_and_dry_run() -> None:
    session = _make_session()
    fresh = ArticleORM(
        source="eldiario",
        title="Fresh",
        url="https://eldiario.es/fresh",
        published_at=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        section="politica",
        summary="Resumen",
        article_text="Texto",
        tags="politica",
    )
    failed_article = ArticleORM(
        source="abc",
        title="Failed",
        url="https://abc.es/failed",
        published_at=datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 19, 12, 5, tzinfo=UTC),
        section="politica",
        summary="Resumen",
        article_text="Texto",
        tags="politica",
    )
    done = ArticleORM(
        source="elpais",
        title="Done",
        url="https://elpais.com/done",
        published_at=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 18, 12, 5, tzinfo=UTC),
        section="politica",
        summary="Resumen",
        article_text="Texto",
        tags="politica",
    )
    session.add_all([fresh, failed_article, done])
    session.flush()
    session.add(
        ArticleEditorialAnalysisORM(
            article_id=failed_article.id,
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
            framing_devices_json="[]",
            evidence_spans_json="[]",
            rationale="Earlier broken run placeholder.",
            analysis_status="failed",
            failure_reason="boom",
            model_provider="openrouter",
            model_name="model",
            model_version="model",
            prompt_version="v1",
            schema_version="editorial-analysis-v1",
            content_hash="x",
            source_text_version="title_summary_body_v1",
        )
    )
    session.add(
        ArticleEditorialAnalysisORM(
            article_id=done.id,
            article_type="news_report",
            article_type_confidence=0.8,
            bias_label="center",
            bias_score=0.0,
            bias_confidence=0.7,
            tone_emotional="calm",
            tone_target="neutral",
            opinionatedness="straight_reporting",
            sensationalism="low",
            rhetorical_certainty="cautious",
            framing_devices_json="[]",
            evidence_spans_json='[{"type":"headline","text":"Done","note":"Done"}]',
            rationale="Already complete editorial read.",
            analysis_status="completed",
            failure_reason="",
            model_provider="openrouter",
            model_name="model",
            model_version="model",
            prompt_version="v1",
            schema_version="editorial-analysis-v1",
            content_hash="y",
            source_text_version="title_summary_body_v1",
        )
    )
    session.commit()

    pipeline = EditorialAnalysisPipeline(session)
    pending_rows = pipeline._select_candidate_articles(
        EditorialSelectionFilters(days_back=10, limit=10, status="pending")
    )
    failed_rows = pipeline._select_candidate_articles(
        EditorialSelectionFilters(days_back=10, limit=10, status="failed")
    )

    assert [row.id for row in pending_rows] == [fresh.id]
    assert [row.id for row in failed_rows] == [failed_article.id]
    assert pipeline.effective_status(status="pending", reprocess=True, article_ids=None) == "any"
    assert pipeline.selection_status_counts(days_back=10, limit=10)["completed"] == 1

    dry_run = pipeline.analyze_articles(
        days_back=10,
        limit=10,
        status="pending",
        article_ids=[fresh.id, failed_article.id],
        published_from=date(2026, 3, 19),
        published_to=date(2026, 3, 20),
        dry_run=True,
    )
    assert dry_run.article_count == 2
    assert dry_run.analyzed_count == 0
    assert (
        session.execute(select(func.count()).select_from(ArticleEditorialAnalysisORM)).scalar_one()
        == 2
    )
