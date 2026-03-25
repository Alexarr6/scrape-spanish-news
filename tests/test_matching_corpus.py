from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.analysis.matching_corpus import MatchingCorpusPipeline
from src.analysis.orm_models import ArticleAnalysisORM, ArticleMatchingSelectionORM
from src.analysis.pipeline import AnalysisPipeline
from src.persistence.orm import ArticleORM, Base


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _article(
    session: Session,
    *,
    source: str,
    title: str,
    section: str,
    url: str,
    summary: str = "Resumen político",
    article_text: str = "Texto largo " * 120,
    published_at: datetime | None = None,
) -> ArticleORM:
    row = ArticleORM(
        source=source,
        title=title,
        url=url,
        published_at=published_at or datetime(2026, 3, 22, 12, 0, tzinfo=UTC),
        scraped_at=datetime(2026, 3, 22, 12, 5, tzinfo=UTC),
        section=section,
        summary=summary,
        article_text=article_text,
        tags=section,
    )
    session.add(row)
    session.commit()
    return row


def test_matching_corpus_excludes_opinion_and_soft_content_but_keeps_hard_news() -> None:
    session = _make_session()
    selected = _article(
        session,
        source="elpais",
        title="El Gobierno aprueba el decreto energético en el Congreso",
        section="España",
        url="https://elpais.com/espana/2026-03-22/decreto-energetico.html",
    )
    _article(
        session,
        source="elpais",
        title="Brújula sentimental del fin de semana",
        section="Opinión",
        url="https://elpais.com/opinion/2026-03-22/columna.html",
    )
    _article(
        session,
        source="abc",
        title="Juanma Moreno felicita al club por ganar la Copa",
        section="espana",
        url="https://www.abc.es/espana/andalucia/jaen/futbol-sala.html",
    )

    metrics = MatchingCorpusPipeline(session).build(days_back=30, daily_cap=10)

    rows = {
        row.article_id: row
        for row in session.execute(select(ArticleMatchingSelectionORM)).scalars().all()
    }

    assert metrics.article_count == 3
    assert rows[selected.id].eligible is True
    assert rows[selected.id].selection_rank == 1
    assert rows[selected.id].bucket in {"politics", "economy"}
    assert rows[selected.id].eligibility_reason == "eligible_hard_news"
    excluded_reasons = {
        row.eligibility_reason
        for article_id, row in rows.items()
        if article_id != selected.id
    }
    assert (
        "excluded_article_type" in excluded_reasons
        or "excluded_source_policy" in excluded_reasons
    )


def test_matching_corpus_uses_local_madrid_day_for_selection() -> None:
    session = _make_session()
    article = _article(
        session,
        source="elmundo",
        title="El Congreso debate la nueva ley de vivienda",
        section="Espana",
        url="https://www.elmundo.es/espana/2026/03/23/ley-vivienda.html",
        published_at=datetime(2026, 3, 22, 23, 3, 33, tzinfo=UTC),
    )

    MatchingCorpusPipeline(session).build(days_back=30, daily_cap=10)

    stored = session.execute(
        select(ArticleMatchingSelectionORM).where(
            ArticleMatchingSelectionORM.article_id == article.id
        )
    ).scalar_one()
    assert str(stored.local_published_date) == "2026-03-23"


def test_analysis_pipeline_defaults_to_matching_corpus_selection() -> None:
    session = _make_session()
    selected = _article(
        session,
        source="elpais",
        title="Sánchez anuncia un pacto energético europeo",
        section="España",
        url="https://elpais.com/espana/2026-03-22/pacto-energetico.html",
    )
    raw_only = _article(
        session,
        source="elpais",
        title="Crónica social del fin de semana",
        section="Gente",
        url="https://elpais.com/gente/2026-03-22/cronica-social.html",
        article_text="Texto corto",
    )

    MatchingCorpusPipeline(session).build(days_back=30, daily_cap=10)
    metrics = AnalysisPipeline(session).enrich_articles(days_back=30, limit=10, corpus="matching")

    analyses = session.execute(select(ArticleAnalysisORM)).scalars().all()

    assert metrics.article_count == 1
    assert len(analyses) == 1
    assert analyses[0].article_id == selected.id
    assert analyses[0].article_id != raw_only.id
