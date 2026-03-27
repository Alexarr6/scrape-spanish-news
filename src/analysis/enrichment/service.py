"""Article enrichment orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.shared.canonicalization import EntityCanonicalizer
from src.analysis.shared.contracts import ArticleEnrichmentPayload, EnrichmentRunMetrics
from src.analysis.editorial.llm import LLMClient, LLMSettings, build_prompt, enrichment_json_schema
from src.analysis.enrichment.persistence import (
    ArticleAnalysisPersister,
    seed_tags,
)
from src.analysis.enrichment.utils import content_hash, select_source_balanced_enrichment_rows
from src.analysis.shared.heuristics import heuristic_enrichment
from src.analysis.store.models import (
    ArticleAnalysisORM,
    ArticleEnrichmentRunORM,
    ArticleMatchingSelectionORM,
    TagORM,
)
from src.persistence.core import ArticleRead
from src.persistence.orm import ArticleORM


class AnalysisPipeline:
    """Enrich persisted articles with tags, entities, and analysis side tables."""

    def __init__(self, session: Session, *, llm_settings: LLMSettings | None = None) -> None:
        self.session = session
        self.llm = LLMClient(llm_settings) if llm_settings else None
        self.canonicalizer = EntityCanonicalizer()
        self._persister = ArticleAnalysisPersister(session, canonicalizer=self.canonicalizer)
        self._latest_usage = None

    def seed_tags(self) -> None:
        seed_tags(self.session)

    def enrich_articles(
        self,
        *,
        days_back: int = 2,
        limit: int = 150,
        corpus: Literal["raw", "matching"] = "matching",
    ) -> EnrichmentRunMetrics:
        self.seed_tags()
        started_at = datetime.now(UTC)
        settings = self.llm.settings if self.llm else None
        run = ArticleEnrichmentRunORM(
            started_at=started_at,
            window_date_from=(started_at - timedelta(days=days_back - 1)).date(),
            window_date_to=started_at.date(),
            provider=settings.provider_label if settings else "heuristic",
            model=settings.model if settings else "heuristic-only",
            prompt_version=settings.prompt_version if settings else "v0",
        )
        self.session.add(run)
        self.session.flush()
        metrics = EnrichmentRunMetrics(article_count=0, started_at=started_at)
        rows = self._load_candidate_rows(days_back=days_back, limit=limit, corpus=corpus)
        metrics.article_count = len(rows)
        tag_rows = list(self.session.execute(select(TagORM)).scalars())
        tag_by_code = {row.tag_code: row.id for row in tag_rows}
        allowed_tags = [
            {"tag_code": tag.tag_code, "display_name": tag.display_name} for tag in tag_rows
        ]
        for row in rows:
            article = ArticleRead.model_validate(row)
            article_content_hash = self._content_hash(article)
            existing = self.session.execute(
                select(ArticleAnalysisORM).where(ArticleAnalysisORM.article_id == article.id)
            ).scalar_one_or_none()
            if existing and existing.content_hash == article_content_hash:
                metrics.skipped_count += 1
                continue
            payload, invalid_schema = self._build_enrichment_payload(
                article=article,
                allowed_tags=allowed_tags,
            )
            if invalid_schema:
                metrics.invalid_schema_count += 1
            if self.llm and self._latest_usage is not None:
                metrics.request_count += 1
                run.request_count += 1
                run.estimated_input_tokens += self._latest_usage.prompt_tokens
                run.estimated_output_tokens += self._latest_usage.completion_tokens
            self._persister.persist_article_analysis(
                article=article,
                payload=payload,
                tag_by_code=tag_by_code,
                content_hash=article_content_hash,
                assignment_source="llm" if self.llm else "hybrid",
            )
            metrics.enriched_count += 1
        run.article_count = metrics.article_count
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        self.session.commit()
        metrics.finished_at = run.finished_at
        return metrics

    def _build_enrichment_payload(
        self,
        *,
        article: ArticleRead,
        allowed_tags: list[dict[str, str]],
    ) -> tuple[ArticleEnrichmentPayload, bool]:
        payload = heuristic_enrichment(article)
        if self.llm is None:
            return payload, False
        candidate_entities = [entity.model_dump(mode="json") for entity in payload.entities]
        prompt = build_prompt(
            article_title=article.title,
            article_summary=article.summary,
            article_text=article.article_text,
            candidate_entities=candidate_entities,
            allowed_tags=allowed_tags,
        )
        try:
            llm_payload, usage = self.llm.enrich_article(
                article_prompt=prompt,
                schema=enrichment_json_schema(),
            )
            self._latest_usage = usage
            return llm_payload, False
        except Exception:
            self._latest_usage = None
            return payload, True

    def _load_candidate_rows(
        self,
        *,
        days_back: int,
        limit: int,
        corpus: Literal["raw", "matching"],
    ) -> list[ArticleORM]:
        started_at = datetime.now(UTC)
        cutoff = started_at - timedelta(days=days_back)
        stmt = (
            select(ArticleORM)
            .where(ArticleORM.published_at.is_not(None), ArticleORM.published_at >= cutoff)
        )
        if corpus == "matching":
            stmt = (
                stmt.join(
                    ArticleMatchingSelectionORM,
                    ArticleMatchingSelectionORM.article_id == ArticleORM.id,
                )
                .where(ArticleMatchingSelectionORM.selection_rank.is_not(None))
                .order_by(
                    ArticleMatchingSelectionORM.local_published_date.desc().nullslast(),
                    ArticleMatchingSelectionORM.selection_rank.asc().nullslast(),
                    ArticleORM.published_at.desc(),
                )
                .limit(limit * 4)
            )
        else:
            stmt = stmt.order_by(ArticleORM.published_at.desc()).limit(limit * 4)
        return self._select_source_balanced_enrichment_rows(
            self.session.execute(stmt).scalars().all(),
            limit=limit,
        )

    def _content_hash(self, article: ArticleRead) -> str:
        return content_hash(article)

    def _persist_article_analysis(
        self,
        *,
        article: ArticleRead,
        payload: ArticleEnrichmentPayload,
        tag_by_code: dict[str, int],
        content_hash: str,
    ) -> None:
        self._persister.persist_article_analysis(
            article=article,
            payload=payload,
            tag_by_code=tag_by_code,
            content_hash=content_hash,
            assignment_source="llm" if self.llm else "hybrid",
        )

    def _select_source_balanced_enrichment_rows(
        self,
        rows: list[ArticleORM],
        *,
        limit: int,
    ) -> list[ArticleORM]:
        return select_source_balanced_enrichment_rows(rows, limit=limit)
