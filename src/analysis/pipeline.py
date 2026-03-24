"""Pipelines for article enrichment and same-story cluster rebuilding."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from src.analysis.canonicalization import EntityCanonicalizer
from src.analysis.contracts import (
    ArticleAnalysisExtractedEntity,
    ArticleAnalysisRead,
    ArticleEditorialAnalysisPayload,
    ArticleEnrichmentPayload,
    ClusterRebuildMetrics,
    EditorialAnalysisDiagnostics,
    EditorialAnalysisRunMetrics,
    EditorialCompletedPersistence,
    EditorialFailurePersistence,
    EnrichmentRunMetrics,
    PairScoreArtifact,
    StoryClusterMemberReason,
)
from src.analysis.editorial.crud import EditorialAnalysisCRUD
from src.analysis.editorial_normalization import build_editorial_diagnostics_from_payload
from src.analysis.heuristics import heuristic_enrichment, title_similarity
from src.analysis.llm_client import (
    EDITORIAL_ANALYSIS_SCHEMA_VERSION,
    EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION,
    EditorialAnalysisResult,
    LLMClient,
    LLMSettings,
    build_editorial_analysis_prompt,
    build_prompt,
    editorial_analysis_json_schema,
    editorial_debug_artifact_dir,
    enrichment_json_schema,
)
from src.analysis.normalization import jaccard_similarity, normalize_lookup, slugify
from src.analysis.orm_models import (
    ArticleAnalysisORM,
    ArticleEditorialAnalysisORM,
    ArticleEnrichmentRunORM,
    ArticleTagORM,
    ClusterEntityORM,
    ClusterMemberORM,
    EntityAliasORM,
    EntityMentionORM,
    EntityORM,
    StoryClusterORM,
    TagORM,
)
from src.analysis.taxonomy import CANONICAL_TAGS
from src.persistence.core import ArticleRead
from src.persistence.orm import ArticleORM


@dataclass
class EnrichedArticle:
    article: ArticleRead
    analysis: ArticleAnalysisRead
    tag_codes: list[str]
    entity_slugs: list[str]
    key_phrases: list[str]


class AnalysisPipeline:
    """Enrich persisted articles with tags, entities, and analysis side tables."""

    def __init__(self, session: Session, *, llm_settings: LLMSettings | None = None) -> None:
        self.session = session
        self.llm = LLMClient(llm_settings) if llm_settings else None
        self.canonicalizer = EntityCanonicalizer()

    def seed_tags(self) -> None:
        existing = {row.tag_code: row for row in self.session.execute(select(TagORM)).scalars()}
        for tag in CANONICAL_TAGS:
            row = existing.get(tag.code)
            if row is None:
                self.session.add(
                    TagORM(
                        tag_code=tag.code,
                        display_name=tag.display_name,
                        tag_group=tag.group,
                        description=tag.description,
                        sort_order=tag.sort_order,
                    )
                )
            else:
                row.display_name = tag.display_name
                row.tag_group = tag.group
                row.description = tag.description
                row.sort_order = tag.sort_order
                row.is_active = True
        self.session.commit()

    def enrich_articles(self, *, days_back: int = 2, limit: int = 150) -> EnrichmentRunMetrics:
        """Enrich a bounded recent article window and persist the resulting analysis.

        The pipeline always starts with heuristic extraction so there is a stable
        fallback path even when the optional OpenRouter call is unavailable or
        returns unusable data. Existing rows are skipped when the content hash has
        not changed.
        """

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
        cutoff = started_at - timedelta(days=days_back)
        stmt = (
            select(ArticleORM)
            .where(ArticleORM.published_at.is_not(None), ArticleORM.published_at >= cutoff)
            .order_by(ArticleORM.published_at.desc())
            .limit(limit * 4)
        )
        rows = self._select_source_balanced_enrichment_rows(
            self.session.execute(stmt).scalars().all(),
            limit=limit,
        )
        metrics.article_count = len(rows)
        tag_by_code = {
            row.tag_code: row.id for row in self.session.execute(select(TagORM)).scalars()
        }
        for row in rows:
            article = ArticleRead.model_validate(row)
            content_hash = self._content_hash(article)
            existing = self.session.execute(
                select(ArticleAnalysisORM).where(ArticleAnalysisORM.article_id == article.id)
            ).scalar_one_or_none()
            if existing and existing.content_hash == content_hash:
                metrics.skipped_count += 1
                continue
            payload = heuristic_enrichment(article)
            if self.llm:
                candidate_entities = [entity.model_dump(mode="json") for entity in payload.entities]
                allowed_tags = [
                    {"tag_code": code, "display_name": tag.display_name}
                    for code, tag in (
                        (tag.tag_code, tag)
                        for tag in self.session.execute(select(TagORM)).scalars()
                    )
                ]
                prompt = build_prompt(
                    article_title=article.title,
                    article_summary=article.summary,
                    article_text=article.article_text,
                    candidate_entities=candidate_entities,
                    allowed_tags=allowed_tags,
                )
                try:
                    payload, usage = self.llm.enrich_article(
                        article_prompt=prompt, schema=enrichment_json_schema()
                    )
                    metrics.request_count += 1
                    run.request_count += 1
                    run.estimated_input_tokens += usage.prompt_tokens
                    run.estimated_output_tokens += usage.completion_tokens
                except Exception:
                    metrics.invalid_schema_count += 1
            self._persist_article_analysis(
                article=article, payload=payload, tag_by_code=tag_by_code, content_hash=content_hash
            )
            metrics.enriched_count += 1
        run.article_count = metrics.article_count
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        self.session.commit()
        metrics.finished_at = run.finished_at
        return metrics

    def _persist_article_analysis(
        self,
        *,
        article: ArticleRead,
        payload: ArticleEnrichmentPayload,
        tag_by_code: dict[str, int],
        content_hash: str,
    ) -> None:
        analysis = self.session.execute(
            select(ArticleAnalysisORM).where(ArticleAnalysisORM.article_id == article.id)
        ).scalar_one_or_none()
        if analysis is None:
            analysis = ArticleAnalysisORM(article_id=article.id)
            self.session.add(analysis)
        analysis.article_type = payload.article_type
        analysis.article_type_confidence = payload.article_type_confidence
        analysis.is_event_coverage = payload.is_event_coverage
        analysis.language = payload.language
        analysis.primary_topic_tag_id = (
            tag_by_code.get(payload.primary_tag_code) if payload.primary_tag_code else None
        )
        analysis.key_phrases_json = json.dumps(payload.key_phrases, ensure_ascii=False)
        analysis.claims_json = json.dumps(payload.claims, ensure_ascii=False)
        analysis.extraction_version = "v1"
        analysis.content_hash = content_hash
        self.session.flush()
        self.session.execute(delete(ArticleTagORM).where(ArticleTagORM.article_id == article.id))
        all_tag_codes = [
            code for code in [payload.primary_tag_code, *payload.secondary_tag_codes] if code
        ]
        for idx, code in enumerate(all_tag_codes):
            self.session.add(
                ArticleTagORM(
                    article_id=article.id,
                    tag_id=tag_by_code[code],
                    assignment_source="llm" if self.llm else "hybrid",
                    confidence=payload.article_type_confidence,
                    is_primary=idx == 0,
                )
            )
        self.session.execute(
            delete(EntityMentionORM).where(EntityMentionORM.article_id == article.id)
        )
        merged_mentions: dict[tuple[int, int, str], dict[str, int | float | str | None]] = {}
        for entity_payload in payload.entities[:12]:
            canonical = self.canonicalizer.canonicalize(entity_payload)
            entity_row = self.session.execute(
                select(EntityORM).where(
                    EntityORM.entity_type == canonical.entity_type,
                    EntityORM.normalized_name == canonical.normalized_name,
                )
            ).scalar_one_or_none()
            if entity_row is None:
                entity_row = EntityORM(
                    entity_type=canonical.entity_type,
                    canonical_name=canonical.canonical_name,
                    normalized_name=canonical.normalized_name,
                    slug=canonical.slug,
                    canonical_source=canonical.canonical_source,
                )
                self.session.add(entity_row)
                self.session.flush()
            aliases = {
                alias.normalized_alias
                for alias in self.session.execute(
                    select(EntityAliasORM).where(EntityAliasORM.entity_id == entity_row.id)
                ).scalars()
            }
            for alias in canonical.aliases + (entity_payload.canonical_name,):
                normalized_alias = normalize_lookup(alias)
                if not normalized_alias or normalized_alias in aliases:
                    continue
                self.session.add(
                    EntityAliasORM(
                        entity_id=entity_row.id,
                        alias=alias,
                        normalized_alias=normalized_alias,
                        alias_type="surface",
                    )
                )
                aliases.add(normalized_alias)

            mention = self._build_entity_mention(
                article=article,
                entity_id=entity_row.id,
                entity_payload=entity_payload,
            )
            mention_key = (
                mention["article_id"],
                mention["entity_id"],
                mention["mention_text_normalized"],
            )
            merged = merged_mentions.get(mention_key)
            if merged is None:
                merged_mentions[mention_key] = mention
                continue
            merged["mention_count"] += mention["mention_count"]
            merged["title_hits"] += mention["title_hits"]
            merged["summary_hits"] += mention["summary_hits"]
            merged["body_hits"] += mention["body_hits"]
            merged["relevance_score"] = max(merged["relevance_score"], mention["relevance_score"])
            if not merged["role_hint"] and mention["role_hint"]:
                merged["role_hint"] = mention["role_hint"]
            if len(mention["surface_form"]) > len(merged["surface_form"]):
                merged["surface_form"] = mention["surface_form"]

        for mention in merged_mentions.values():
            self.session.add(EntityMentionORM(**mention))

    def _build_entity_mention(
        self,
        *,
        article: ArticleRead,
        entity_id: int,
        entity_payload: ArticleAnalysisExtractedEntity,
    ) -> dict[str, int | float | str | None]:
        surface = entity_payload.canonical_name.strip()
        article_title = article.title.lower()
        article_summary = article.summary.lower()
        article_body = article.article_text.lower()
        combined_text = " ".join([article.title, article.summary, article.article_text]).lower()
        return {
            "article_id": article.id,
            "entity_id": entity_id,
            "surface_form": surface,
            "mention_text_normalized": normalize_lookup(surface),
            "mention_count": combined_text.count(surface.lower()) or 1,
            "title_hits": article_title.count(surface.lower()),
            "summary_hits": article_summary.count(surface.lower()),
            "body_hits": article_body.count(surface.lower()),
            "relevance_score": entity_payload.relevance_score,
            "role_hint": entity_payload.role_hint,
        }

    def _content_hash(self, article: ArticleRead) -> str:
        raw = "\n".join(
            [article.title, article.summary, article.article_text, article.section, article.tags]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


    def _select_source_balanced_enrichment_rows(
        self, rows: list[ArticleORM], *, limit: int
    ) -> list[ArticleORM]:
        """Round-robin recent enrichment work across sources after recency filtering.

        This keeps the enrichment window broader than a raw top-N recent slice, so
        one loud publisher cannot monopolize the bounded run and starve cluster
        formation for other sources.
        """

        if limit <= 0 or not rows:
            return []
        buckets: dict[str, deque[ArticleORM]] = defaultdict(deque)
        source_order: list[str] = []
        for row in rows:
            source = row.source or ""
            if source not in buckets:
                source_order.append(source)
            buckets[source].append(row)

        selected: list[ArticleORM] = []
        while len(selected) < limit and source_order:
            next_round: list[str] = []
            for source in source_order:
                bucket = buckets[source]
                if bucket:
                    selected.append(bucket.popleft())
                    if len(selected) >= limit:
                        break
                if bucket:
                    next_round.append(source)
            source_order = next_round
        return selected


@dataclass
class EditorialSelectionFilters:
    days_back: int = 2
    limit: int = 100
    status: str = "pending"
    article_ids: list[int] | None = None
    source: str | None = None
    published_from: date | None = None
    published_to: date | None = None
    batch_size: int | None = None


class EditorialAnalysisPipeline:
    """Run bounded LLM-driven editorial analysis as a separate first-pass pipeline."""

    def __init__(self, session: Session, *, llm_settings: LLMSettings | None = None) -> None:
        self.session = session
        self.llm = LLMClient(llm_settings) if llm_settings else None
        self.repo = EditorialAnalysisCRUD(session)

    def effective_status(
        self, *, status: str, reprocess: bool, article_ids: list[int] | None
    ) -> str:
        return "any" if reprocess and status == "pending" and not article_ids else status

    def analyze_articles(
        self,
        *,
        days_back: int = 2,
        limit: int = 100,
        reprocess: bool = False,
        status: str = "pending",
        article_ids: list[int] | None = None,
        source: str | None = None,
        published_from: date | None = None,
        published_to: date | None = None,
        dry_run: bool = False,
        batch_size: int | None = None,
    ) -> EditorialAnalysisRunMetrics:
        if self.llm is None and not dry_run:
            raise RuntimeError("LLM settings are required for editorial analysis")

        started_at = datetime.now(UTC)
        metrics = EditorialAnalysisRunMetrics(started_at=started_at)
        effective_status = self.effective_status(
            status=status,
            reprocess=reprocess,
            article_ids=article_ids,
        )
        filters = EditorialSelectionFilters(
            days_back=days_back,
            limit=limit,
            status=effective_status,
            article_ids=article_ids,
            source=source,
            published_from=published_from,
            published_to=published_to,
            batch_size=batch_size,
        )
        rows = self._select_candidate_articles(filters)
        if batch_size:
            rows = rows[:batch_size]
        metrics.article_count = len(rows)
        if dry_run:
            metrics.finished_at = datetime.now(UTC)
            return metrics
        for row in rows:
            article = ArticleRead.model_validate(row)
            content_hash = AnalysisPipeline(self.session)._content_hash(article)
            analysis = self.session.execute(
                select(ArticleEditorialAnalysisORM).where(
                    ArticleEditorialAnalysisORM.article_id == article.id
                )
            ).scalar_one_or_none()
            if self._should_skip_existing(analysis, content_hash=content_hash, reprocess=reprocess):
                metrics.skipped_count += 1
                continue
            analysis = analysis or ArticleEditorialAnalysisORM(article_id=article.id)
            if analysis.id is None:
                self.session.add(analysis)
            self._prepare_pending_analysis(analysis=analysis, content_hash=content_hash)
            published_at = article.published_at.isoformat() if article.published_at else ""
            prompt = build_editorial_analysis_prompt(
                source=article.source,
                section=article.section,
                published_at=published_at,
                url=str(article.url),
                title=article.title,
                summary=article.summary,
                body=article.article_text,
            )
            result = self.llm.analyze_editorial(
                article_prompt=prompt,
                schema=editorial_analysis_json_schema(),
            )
            metrics.request_count += sum(
                1 for attempt in result.attempts if attempt.request_accepted
            )
            metrics.provider_rejected_count += sum(
                1
                for attempt in result.attempts
                if attempt.failure_class == "provider_schema_rejected"
            )
            metrics.parse_failed_count += sum(
                1
                for attempt in result.attempts
                if attempt.failure_class
                in {
                    "empty_content",
                    "non_json_content",
                    "json_parse_failed",
                    "unknown_response_shape",
                }
            )
            metrics.validation_failed_count += sum(
                1
                for attempt in result.attempts
                if attempt.failure_class == "payload_validation_failed"
            )
            success_attempt = result.successful_attempt
            if success_attempt and success_attempt.payload is not None:
                self._persist_editorial_analysis(
                    analysis=analysis,
                    payload=success_attempt.payload,
                    content_hash=content_hash,
                    diagnostics=success_attempt.diagnostics,
                    analysis_path=self._analysis_path_for_result(result),
                )
                metrics.analyzed_count += 1
                if success_attempt.mode == "strict_json_schema":
                    metrics.strict_success_count += 1
                else:
                    metrics.fallback_success_count += 1
                if (
                    any(a.failure_class == "provider_schema_rejected" for a in result.attempts[:-1])
                    and success_attempt.mode == "fallback_json_text"
                ):
                    metrics.fallback_after_strict_reject_count += 1
                if (
                    success_attempt.repair_warnings
                    or success_attempt.normalization_warnings
                    or success_attempt.truncated_fields
                    or success_attempt.dropped_fields
                ):
                    metrics.rows_with_warnings_count += 1
                if "evidence_spans" in success_attempt.truncated_fields:
                    metrics.rows_with_truncated_evidence_count += 1
                if success_attempt.dropped_fields:
                    metrics.rows_with_dropped_fields_count += 1
                if success_attempt.payload.bias_label == "unclear":
                    metrics.unclear_bias_count += 1
                diagnostics = success_attempt.diagnostics
                if diagnostics is not None:
                    if diagnostics.editorial_applicability == "out_of_domain":
                        metrics.out_of_domain_count += 1
                    elif diagnostics.editorial_applicability == "limited":
                        metrics.limited_applicability_count += 1
                    if diagnostics.preserved_signals:
                        metrics.rows_with_unmapped_signals_count += 1
                    for reason in diagnostics.unclear_reasons:
                        metrics.unclear_reason_counts[reason] = (
                            metrics.unclear_reason_counts.get(reason, 0) + 1
                        )
                    for name, diag in diagnostics.dimension_status.items():
                        bucket = metrics.dimension_status_counts.setdefault(name, {})
                        bucket[diag.status] = bucket.get(diag.status, 0) + 1
                        if name == "bias" and diag.status == "weak_signal_abstain":
                            metrics.bias_weak_signal_count += 1
                        if name == "bias" and diag.status == "mapping_loss":
                            metrics.bias_mapping_loss_count += 1
                        if name == "framing" and diag.status == "mapping_loss":
                            metrics.framing_mapping_loss_count += 1
                        if diag.status == "provider_missing":
                            metrics.provider_missing_dimension_count += 1
                    for group, values in diagnostics.preserved_signals.items():
                        bucket = metrics.preserved_signal_counts.setdefault(group, {})
                        for value in values:
                            bucket[value] = bucket.get(value, 0) + 1
                if (
                    "mapping_loss" in success_attempt.unclear_reasons
                    or "repair_data_loss" in success_attempt.unclear_reasons
                ):
                    metrics.unclear_due_to_mapping_count += 1
                self.session.commit()
                continue
            final_attempt = result.final_attempt
            artifact_path = self._write_failure_artifact(
                article=article,
                analysis=analysis,
                prompt=prompt,
                result=result,
            )
            self._persist_editorial_failure(
                analysis=analysis,
                failure_class=final_attempt.failure_class or "provider_request_failed",
                failure_message=final_attempt.failure_message,
                artifact_path=artifact_path,
            )
            self.session.commit()
            metrics.failed_count += 1
        metrics.finished_at = datetime.now(UTC)
        return metrics

    def _prepare_pending_analysis(
        self, *, analysis: ArticleEditorialAnalysisORM, content_hash: str
    ) -> None:
        self.repo.mark_pending(
            analysis=analysis,
            content_hash=content_hash,
            model_provider=self.llm.settings.provider_label,
            model_name=self.llm.settings.model,
            model_version=self.llm.settings.model,
            prompt_version=self.llm.settings.prompt_version,
            schema_version=EDITORIAL_ANALYSIS_SCHEMA_VERSION,
            source_text_version=EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION,
        )

    def selection_status_counts(
        self,
        *,
        days_back: int,
        limit: int,
        article_ids: list[int] | None = None,
        source: str | None = None,
        published_from: date | None = None,
        published_to: date | None = None,
        batch_size: int | None = None,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for status in ("pending", "failed", "completed", "any"):
            rows = self._select_candidate_articles(
                EditorialSelectionFilters(
                    days_back=days_back,
                    limit=limit,
                    status=status,
                    article_ids=article_ids,
                    source=source,
                    published_from=published_from,
                    published_to=published_to,
                    batch_size=batch_size,
                )
            )
            counts[status] = len(rows[:batch_size] if batch_size else rows)
        return counts

    def _select_candidate_articles(self, filters: EditorialSelectionFilters) -> list[ArticleORM]:
        stmt = select(ArticleORM).outerjoin(
            ArticleEditorialAnalysisORM, ArticleEditorialAnalysisORM.article_id == ArticleORM.id
        )
        if filters.article_ids:
            stmt = stmt.where(ArticleORM.id.in_(filters.article_ids))
        else:
            cutoff = datetime.now(UTC) - timedelta(days=filters.days_back)
            stmt = stmt.where(
                ArticleORM.published_at.is_not(None), ArticleORM.published_at >= cutoff
            )
            if filters.source:
                stmt = stmt.where(ArticleORM.source == filters.source)
            if filters.published_from:
                stmt = stmt.where(
                    ArticleORM.published_at
                    >= datetime.combine(filters.published_from, datetime.min.time())
                )
            if filters.published_to:
                stmt = stmt.where(
                    ArticleORM.published_at
                    <= datetime.combine(filters.published_to, datetime.max.time())
                )
            if filters.status == "pending":
                stmt = stmt.where(
                    or_(
                        ArticleEditorialAnalysisORM.id.is_(None),
                        ArticleEditorialAnalysisORM.analysis_status == "pending",
                    )
                )
            elif filters.status == "failed":
                stmt = stmt.where(ArticleEditorialAnalysisORM.analysis_status == "failed")
            elif filters.status == "completed":
                stmt = stmt.where(ArticleEditorialAnalysisORM.analysis_status == "completed")
            elif filters.status == "any":
                pass
            else:
                raise ValueError(f"Unsupported editorial analysis status: {filters.status}")
        return (
            self.session.execute(stmt.order_by(ArticleORM.published_at.desc()).limit(filters.limit))
            .scalars()
            .all()
        )

    def _should_skip_existing(
        self,
        analysis: ArticleEditorialAnalysisORM | None,
        *,
        content_hash: str,
        reprocess: bool,
    ) -> bool:
        return bool(
            analysis
            and not reprocess
            and analysis.content_hash == content_hash
            and analysis.analysis_status == "completed"
        )

    def _persist_editorial_analysis(
        self,
        *,
        analysis: ArticleEditorialAnalysisORM,
        payload: ArticleEditorialAnalysisPayload,
        content_hash: str,
        diagnostics=None,
        analysis_path: str = "",
    ) -> None:
        diagnostics = diagnostics or self._default_diagnostics_for_payload(payload)
        self.repo.upsert_completed_analysis(
            analysis=analysis,
            command=EditorialCompletedPersistence(
                article_id=analysis.article_id,
                content_hash=content_hash,
                payload=payload,
                diagnostics=diagnostics,
                analysis_path=analysis_path,
            ),
        )

    def _default_diagnostics_for_payload(
        self, payload: ArticleEditorialAnalysisPayload
    ) -> EditorialAnalysisDiagnostics:
        return build_editorial_diagnostics_from_payload(
            payload,
            provider_path="pipeline_default",
        )

    def _persist_editorial_failure(
        self,
        *,
        analysis: ArticleEditorialAnalysisORM,
        failure_class: str,
        failure_message: str,
        artifact_path: str,
    ) -> None:
        self.repo.upsert_failed_analysis(
            analysis=analysis,
            command=EditorialFailurePersistence(
                article_id=analysis.article_id,
                content_hash=analysis.content_hash,
                failure_class=failure_class,
                failure_message=failure_message,
                artifact_path=artifact_path,
                analysis_path=failure_class,
            ),
        )

    def _analysis_path_for_result(self, result: EditorialAnalysisResult) -> str:
        parts = []
        for attempt in result.attempts:
            if attempt.payload is not None:
                parts.append("strict" if attempt.mode == "strict_json_schema" else "fallback")
            elif attempt.failure_class:
                parts.append(f"{attempt.mode}:{attempt.failure_class}")
            else:
                parts.append(attempt.mode)
        return " -> ".join(parts)

    def _write_failure_artifact(
        self,
        *,
        article: ArticleRead,
        analysis: ArticleEditorialAnalysisORM,
        prompt: str,
        result: EditorialAnalysisResult,
    ) -> str:
        artifact_dir = editorial_debug_artifact_dir()
        artifact_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        artifact_path = artifact_dir / f"{timestamp}-article-{article.id}.json"
        artifact = {
            "article_id": article.id,
            "model_provider": analysis.model_provider,
            "model_name": analysis.model_name,
            "prompt_version": analysis.prompt_version,
            "schema_version": analysis.schema_version,
            "source_text_version": analysis.source_text_version,
            "attempts": [
                {
                    "mode": attempt.mode,
                    "request_accepted": attempt.request_accepted,
                    "failure_class": attempt.failure_class,
                    "failure_message": attempt.failure_message,
                    "usage": None
                    if attempt.usage is None
                    else attempt.usage.model_dump(mode="json"),
                    "raw_message": attempt.raw_message,
                    "raw_content": attempt.raw_content,
                    "parsed_json": attempt.parsed_json,
                    "repair_warnings": list(attempt.repair_warnings),
                    "normalization_warnings": list(attempt.normalization_warnings),
                    "dropped_fields": list(attempt.dropped_fields),
                    "truncated_fields": list(attempt.truncated_fields),
                    "final_unclear_reasons": list(attempt.unclear_reasons),
                    "diagnostics": None
                    if attempt.diagnostics is None
                    else attempt.diagnostics.model_dump(mode="json"),
                    "fallback_success": attempt.mode == "fallback_json_text"
                    and attempt.payload is not None,
                    "raw_response": attempt.raw_response,
                }
                for attempt in result.attempts
            ],
            "prompt_excerpt": prompt[:1200],
            "article_metadata": {
                "source": article.source,
                "section": article.section,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "url": str(article.url),
                "title": article.title,
            },
        }
        artifact_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(artifact_path)


class ClusterPipeline:
    """Rebuild same-story clusters from enriched article state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def build_clusters(
        self, *, days_back: int = 3, limit: int = 200, score_threshold: float = 0.68
    ) -> tuple[ClusterRebuildMetrics, list[PairScoreArtifact]]:
        """Score candidate pairs, accept qualifying edges, and persist components.

        The rebuild is bounded by recency, article count, and threshold so the
        operator can trade completeness for predictable runtime during repeated
        refreshes.
        """

        started = datetime.now(UTC)
        articles = self._load_enriched_articles(days_back=days_back, limit=limit)
        metrics = ClusterRebuildMetrics(article_count=len(articles), started_at=started)
        artifacts: list[PairScoreArtifact] = []
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]] = []
        for idx, left in enumerate(articles):
            for right in articles[idx + 1 :]:
                if abs((left.article.published_at - right.article.published_at).days) > 7:
                    continue
                metrics.candidate_pair_count += 1
                reason = self.score_pair(left, right)
                accepted = reason.hard_block is None and reason.score >= score_threshold
                artifacts.append(
                    PairScoreArtifact(
                        left_article_id=left.article.id,
                        right_article_id=right.article.id,
                        accepted=accepted,
                        reason=reason,
                    )
                )
                if accepted:
                    metrics.accepted_pair_count += 1
                    accepted_edges.append((left.article.id, right.article.id, reason))
                else:
                    metrics.rejected_pair_count += 1
        components = self._connected_components(
            [article.article.id for article in articles], accepted_edges
        )
        try:
            self._persist_clusters(articles, components, accepted_edges)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        metrics.cluster_count = len(components)
        metrics.finished_at = datetime.now(UTC)
        return metrics, artifacts

    def _load_enriched_articles(self, *, days_back: int, limit: int) -> list[EnrichedArticle]:
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        stmt = (
            select(ArticleORM, ArticleAnalysisORM)
            .join(ArticleAnalysisORM, ArticleAnalysisORM.article_id == ArticleORM.id)
            .where(ArticleORM.published_at.is_not(None), ArticleORM.published_at >= cutoff)
            .order_by(ArticleORM.published_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).all()
        tag_lookup = {
            row.id: row.tag_code for row in self.session.execute(select(TagORM)).scalars()
        }
        result: list[EnrichedArticle] = []
        for article_row, analysis_row in rows:
            article = ArticleRead.model_validate(article_row)
            analysis = ArticleAnalysisRead.model_validate(analysis_row)
            article_tags = (
                self.session.execute(
                    select(ArticleTagORM).where(ArticleTagORM.article_id == article.id)
                )
                .scalars()
                .all()
            )
            tag_codes = [tag_lookup[tag.tag_id] for tag in article_tags if tag.tag_id in tag_lookup]
            mentions = self.session.execute(
                select(EntityMentionORM, EntityORM.slug)
                .join(EntityORM, EntityORM.id == EntityMentionORM.entity_id)
                .where(EntityMentionORM.article_id == article.id)
            ).all()
            entity_slugs = [slug for _, slug in mentions]
            key_phrases = json.loads(analysis.key_phrases_json)
            result.append(
                EnrichedArticle(
                    article=article,
                    analysis=analysis,
                    tag_codes=tag_codes,
                    entity_slugs=entity_slugs,
                    key_phrases=key_phrases,
                )
            )
        return result

    def score_pair(self, left: EnrichedArticle, right: EnrichedArticle) -> StoryClusterMemberReason:
        """Score whether two enriched articles should belong to the same story cluster."""

        left_keyphrases = [normalize_lookup(value) for value in left.key_phrases]
        right_keyphrases = [normalize_lookup(value) for value in right.key_phrases]
        semantic_similarity = (
            1.0
            if jaccard_similarity(left.key_phrases, right.key_phrases) > 0.8
            else jaccard_similarity(
                left.key_phrases + left.entity_slugs, right.key_phrases + right.entity_slugs
            )
        )
        title_sim = title_similarity(left.article.title, right.article.title)
        shared_entity_score = jaccard_similarity(left.entity_slugs, right.entity_slugs)
        tag_overlap_score = jaccard_similarity(left.tag_codes, right.tag_codes)
        keyphrase_overlap_score = jaccard_similarity(left_keyphrases, right_keyphrases)
        shared_entities = sorted(set(left.entity_slugs) & set(right.entity_slugs))
        shared_keyphrases = sorted(set(left_keyphrases) & set(right_keyphrases))
        shared_tags = sorted(set(left.tag_codes) & set(right.tag_codes))
        days_delta = abs((left.article.published_at - right.article.published_at).days)
        temporal_proximity_score = max(0.0, 1 - (days_delta / 7))
        penalties: list[str] = []
        hard_block = None
        secondary_types = {"analysis", "explainer", "feature", "interview"}
        article_types = {left.analysis.article_type, right.analysis.article_type}
        article_type_pair_class = (
            "secondary_form_pair" if article_types & secondary_types else "primary_pair"
        )
        risky_bridge_pair = False
        if article_types & {"opinion", "editorial"}:
            if (
                left.analysis.article_type != right.analysis.article_type
                or article_types != {"opinion"}
            ):
                hard_block = "opinion_editorial_excluded_from_primary_clusters"
        if article_types & secondary_types and (
            title_sim < 0.58 or keyphrase_overlap_score < 0.34
        ):
            penalties.append("secondary_form_penalty")
        if days_delta >= 2 and title_sim < 0.58 and keyphrase_overlap_score < 0.45:
            penalties.append("followup_penalty")
        if shared_entity_score >= 0.5 and title_sim < 0.52 and keyphrase_overlap_score < 0.34:
            penalties.append("entity_glue_penalty")
            risky_bridge_pair = True
        if days_delta >= 3 and semantic_similarity < 0.78 and title_sim < 0.7:
            penalties.append("late_story_drift_penalty")
            risky_bridge_pair = True
        score = (
            semantic_similarity * 0.30
            + title_sim * 0.20
            + shared_entity_score * 0.25
            + tag_overlap_score * 0.10
            + keyphrase_overlap_score * 0.10
            + temporal_proximity_score * 0.05
        )
        if "secondary_form_penalty" in penalties:
            score -= 0.14
        if "followup_penalty" in penalties:
            score -= 0.14
        if "entity_glue_penalty" in penalties:
            score -= 0.12
        if "late_story_drift_penalty" in penalties:
            score -= 0.10
        return StoryClusterMemberReason(
            score=max(0.0, round(score, 4)),
            semantic_similarity=round(semantic_similarity, 4),
            title_similarity=round(title_sim, 4),
            shared_entity_score=round(shared_entity_score, 4),
            tag_overlap_score=round(tag_overlap_score, 4),
            keyphrase_overlap_score=round(keyphrase_overlap_score, 4),
            temporal_proximity_score=round(temporal_proximity_score, 4),
            days_delta=days_delta,
            shared_entity_count=len(shared_entities),
            shared_keyphrase_count=len(shared_keyphrases),
            shared_tag_count=len(shared_tags),
            article_type_pair_class=article_type_pair_class,
            risky_bridge_pair=risky_bridge_pair,
            hard_block=hard_block,
            penalties=penalties,
        )

    def _connected_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> list[list[int]]:
        adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
        for left, right, reason in sorted(
            accepted_edges, key=lambda item: item[2].score, reverse=True
        ):
            if reason.risky_bridge_pair and reason.score < 0.78:
                continue
            adjacency[left][right] = reason
            adjacency[right][left] = reason

        unassigned = set(article_ids)
        components: list[list[int]] = []
        while unassigned:
            seed = max(
                unassigned,
                key=lambda article_id: max(
                    (reason.score for reason in adjacency.get(article_id, {}).values()),
                    default=0.0,
                ),
            )
            cluster = {seed}
            unassigned.remove(seed)
            added = True
            while added:
                added = False
                for candidate in sorted(unassigned):
                    support = [
                        adjacency[candidate][member]
                        for member in cluster
                        if member in adjacency.get(candidate, {})
                    ]
                    if self._should_attach_candidate(cluster, support):
                        cluster.add(candidate)
                        unassigned.remove(candidate)
                        added = True
            components.append(sorted(cluster))
        return sorted(components, key=len, reverse=True)

    def _should_attach_candidate(
        self,
        cluster: set[int],
        support: list[StoryClusterMemberReason],
    ) -> bool:
        if not support:
            return False
        best_score = max(reason.score for reason in support)
        support_count = len(support)
        mean_score = sum(reason.score for reason in support) / support_count
        risky_support = any(reason.risky_bridge_pair for reason in support)
        if len(cluster) == 1:
            return best_score >= 0.68 and not risky_support
        if support_count >= 2 and mean_score >= 0.72 and best_score >= 0.74 and not risky_support:
            return True
        return best_score >= 0.82 and mean_score >= 0.76 and not risky_support

    def _persist_clusters(
        self,
        articles: list[EnrichedArticle],
        components: list[list[int]],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> None:
        edge_map = {
            (min(left, right), max(left, right)): reason for left, right, reason in accepted_edges
        }
        article_by_id = {item.article.id: item for item in articles}
        self.session.execute(delete(ClusterEntityORM))
        self.session.execute(delete(ClusterMemberORM))
        self.session.execute(delete(StoryClusterORM))
        self.session.flush()
        for index, members in enumerate(components, start=1):
            member_articles = [article_by_id[article_id] for article_id in members]
            ordered = sorted(
                member_articles, key=lambda item: item.article.published_at or datetime.now(UTC)
            )
            primary_tags = [tag for item in member_articles for tag in item.tag_codes]
            tag_code = Counter(primary_tags).most_common(1)[0][0] if primary_tags else None
            primary_tag_row = (
                self.session.execute(
                    select(TagORM).where(TagORM.tag_code == tag_code)
                ).scalar_one_or_none()
                if tag_code
                else None
            )
            representative = ordered[0]
            cluster = StoryClusterORM(
                cluster_key=f"story-{representative.article.published_at.date().isoformat()}-{slugify(representative.article.title)[:48]}-{index}",
                status="active",
                event_date_start=ordered[0].article.published_at.date()
                if ordered[0].article.published_at
                else None,
                event_date_end=ordered[-1].article.published_at.date()
                if ordered[-1].article.published_at
                else None,
                first_article_published_at=ordered[0].article.published_at,
                last_article_published_at=ordered[-1].article.published_at,
                cluster_type="breaking_event",
                summary_headline=representative.article.title,
                summary_text=" | ".join(
                    dict.fromkeys(
                        item.article.summary.strip()
                        for item in ordered
                        if item.article.summary.strip()
                    )
                )[:1000],
                primary_tag_id=primary_tag_row.id if primary_tag_row else None,
                article_count=len(members),
                source_count=len({item.article.source for item in member_articles}),
                clustering_version="v1",
            )
            self.session.add(cluster)
            self.session.flush()
            entity_counts: dict[int, tuple[int, int, float]] = defaultdict(lambda: (0, 0, 0.0))
            for article_id in members:
                supporting_edges = [
                    (left_id, right_id, reason)
                    for (left_id, right_id), reason in edge_map.items()
                    if (
                        article_id in {left_id, right_id}
                        and left_id in members
                        and right_id in members
                    )
                ]
                pair_scores = [reason.score for _, _, reason in supporting_edges]
                membership_score = sum(pair_scores) / len(pair_scores) if pair_scores else 1.0
                supporting_article_ids = sorted(
                    {
                        right_id if left_id == article_id else left_id
                        for left_id, right_id, _ in supporting_edges
                    }
                )
                reason_payload = {
                    "support_edge_count": len(pair_scores),
                    "best_support_score": round(max(pair_scores), 4) if pair_scores else 1.0,
                    "mean_support_score": round(membership_score, 4),
                    "supporting_article_ids": supporting_article_ids,
                    "accepted_via_guarded_merge": len(members) > 1,
                    "risky_bridge_support": any(
                        reason.risky_bridge_pair for _, _, reason in supporting_edges
                    ),
                    "penalties": sorted(
                        {
                            penalty
                            for _, _, reason in supporting_edges
                            for penalty in reason.penalties
                        }
                    ),
                    "edge_scores": pair_scores,
                }
                self.session.add(
                    ClusterMemberORM(
                        cluster_id=cluster.id,
                        article_id=article_id,
                        membership_score=membership_score,
                        membership_reason_json=json.dumps(reason_payload),
                    )
                )
                mentions = (
                    self.session.execute(
                        select(EntityMentionORM).where(EntityMentionORM.article_id == article_id)
                    )
                    .scalars()
                    .all()
                )
                seen_entities: set[int] = set()
                for mention in mentions:
                    coverage, mention_count, relevance = entity_counts[mention.entity_id]
                    entity_counts[mention.entity_id] = (
                        coverage + (0 if mention.entity_id in seen_entities else 1),
                        mention_count + mention.mention_count,
                        relevance + mention.relevance_score,
                    )
                    seen_entities.add(mention.entity_id)
            for entity_id, (coverage, mention_count, relevance) in entity_counts.items():
                self.session.add(
                    ClusterEntityORM(
                        cluster_id=cluster.id,
                        entity_id=entity_id,
                        article_coverage_count=coverage,
                        mention_count=mention_count,
                        aggregate_relevance_score=round(relevance, 4),
                    )
                )
