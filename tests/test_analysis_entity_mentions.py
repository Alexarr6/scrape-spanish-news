from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.analysis.shared.contracts import ArticleAnalysisExtractedEntity, ArticleEnrichmentPayload
from src.analysis.store.models import ArticleAnalysisORM, EntityMentionORM
from src.analysis.enrichment import AnalysisPipeline
from src.persistence.core import ArticleRead
from src.persistence.orm import ArticleORM, Base


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_persist_article_analysis_merges_duplicate_normalized_entity_mentions() -> None:
    session = _session()
    article_row = ArticleORM(
        source="elpais",
        title="Lázaro Báez vuelve a escena",
        url="https://elpais.com/lazaro-baez",
        published_at=datetime(2026, 3, 18, 12, 0),
        scraped_at=datetime(2026, 3, 18, 12, 5),
        section="politica",
        author="Reporter",
        summary="Lazaro Baez reaparece en el sumario.",
        article_text="La investigación cita a Lázaro Báez y también a Lazaro Baez varias veces.",
        tags="",
    )
    session.add(article_row)
    session.flush()

    article = ArticleRead.model_validate(article_row)
    payload = ArticleEnrichmentPayload(
        article_type="news_report",
        article_type_confidence=0.91,
        is_event_coverage=True,
        language="es",
        entities=[
            ArticleAnalysisExtractedEntity(
                entity_type="person",
                canonical_name="Lázaro Báez",
                relevance_score=0.55,
                role_hint=None,
            ),
            ArticleAnalysisExtractedEntity(
                entity_type="person",
                canonical_name="Lazaro Baez",
                relevance_score=0.93,
                role_hint="businessman",
            ),
        ],
        key_phrases=["caso judicial"],
        claims=["El artículo menciona al empresario en varias grafías."],
    )

    pipeline = AnalysisPipeline(session)
    pipeline._persist_article_analysis(
        article=article,
        payload=payload,
        tag_by_code={},
        content_hash="hash",
    )
    session.commit()

    mentions = session.execute(select(EntityMentionORM)).scalars().all()
    assert len(mentions) == 1
    mention = mentions[0]
    assert mention.mention_text_normalized == "lazaro baez"
    assert mention.surface_form == "Lázaro Báez"
    assert mention.mention_count == 4
    assert mention.title_hits == 1
    assert mention.summary_hits == 1
    assert mention.body_hits == 2
    assert mention.relevance_score == 0.93
    assert mention.role_hint == "businessman"

    analysis = session.execute(select(ArticleAnalysisORM)).scalar_one()
    assert analysis.article_id == article.id
