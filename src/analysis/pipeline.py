"""Pipelines for article enrichment and same-story cluster rebuilding."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from src.analysis.canonicalization import EntityCanonicalizer
from src.analysis.contracts import (
    ArticleAnalysisExtractedEntity,
    ArticleAnalysisRead,
    ArticleEditorialAnalysisPayload,
    ArticleEnrichmentPayload,
    CandidateGenerationSummary,
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
from src.analysis.heuristics import (
    event_terms,
    followup_markers,
    heuristic_enrichment,
    lexical_signature,
    title_similarity,
)
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
class CandidatePair:
    left_article_id: int
    right_article_id: int
    origins: set[str] = field(default_factory=set)
    rank: int | None = None


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
        article_by_id = {article.article.id: article for article in articles}
        artifacts: list[PairScoreArtifact] = []
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]] = []
        candidate_pairs, candidate_summaries = self._generate_candidate_pairs(articles)
        for summary in candidate_summaries:
            for origin, count in summary.origin_counts.items():
                metrics.candidate_origin_counts[origin] = metrics.candidate_origin_counts.get(origin, 0) + count
            for origin, count in summary.overflow_counts.items():
                metrics.candidate_overflow_counts[origin] = metrics.candidate_overflow_counts.get(origin, 0) + count
        for candidate in candidate_pairs:
            left = article_by_id[candidate.left_article_id]
            right = article_by_id[candidate.right_article_id]
            metrics.candidate_pair_count += 1
            reason = self.score_pair(left, right)
            accepted = reason.hard_block is None and reason.score >= score_threshold
            artifacts.append(
                PairScoreArtifact(
                    left_article_id=left.article.id,
                    right_article_id=right.article.id,
                    accepted=accepted,
                    candidate_origins=sorted(candidate.origins),
                    candidate_rank=candidate.rank,
                    reason=reason,
                )
            )
            if accepted:
                metrics.accepted_pair_count += 1
                edge_class = self._classify_closure_edge(reason)
                if edge_class == "strong":
                    metrics.accepted_strong_pair_count += 1
                else:
                    metrics.accepted_medium_pair_count += 1
                if reason.risky_bridge_pair:
                    metrics.accepted_risky_pair_count += 1
                accepted_edges.append((left.article.id, right.article.id, reason))
            else:
                metrics.rejected_pair_count += 1
        raw_components = self._raw_connected_components(
            [article.article.id for article in articles], accepted_edges
        )
        metrics.raw_component_count = len(raw_components)
        metrics.raw_multi_article_component_count = len(
            [component for component in raw_components if len(component) > 1]
        )
        components, member_closure_meta = self._build_guarded_components(
            [article.article.id for article in articles], accepted_edges
        )
        try:
            self._persist_clusters(articles, components, accepted_edges, member_closure_meta)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        metrics.guarded_cluster_count = len(components)
        metrics.guarded_multi_article_cluster_count = len(
            [component for component in components if len(component) > 1]
        )
        metrics.cluster_count = metrics.guarded_cluster_count
        metrics.singleton_count = len([component for component in components if len(component) == 1])
        metrics.attached_singleton_count = sum(
            1
            for meta in member_closure_meta.values()
            if meta.get("closure_stage") == "attach"
        )
        metrics.unattached_singleton_count = sum(
            1
            for meta in member_closure_meta.values()
            if meta.get("closure_decision") == "no_support"
        )
        metrics.closure_decision_counts = dict(
            Counter(
                str(meta.get("closure_decision", "unknown"))
                for meta in member_closure_meta.values()
            )
        )
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


    def _generate_candidate_pairs(
        self,
        articles: list[EnrichedArticle],
        *,
        max_days_delta: int = 7,
        per_seed_limit: int = 40,
        per_origin_limit: int = 20,
    ) -> tuple[list[CandidatePair], list[CandidateGenerationSummary]]:
        ordered_articles = sorted(articles, key=lambda item: item.article.published_at)
        pair_map: dict[tuple[int, int], CandidatePair] = {}
        summaries: list[CandidateGenerationSummary] = []

        for seed in ordered_articles:
            summary = CandidateGenerationSummary(seed_article_id=seed.article.id)
            candidates: dict[str, list[tuple[int, float]]] = defaultdict(list)
            seed_time = seed.article.published_at
            seed_tags = set(seed.tag_codes)
            seed_entities = set(seed.entity_slugs)
            seed_keyphrases = {normalize_lookup(value) for value in seed.key_phrases if normalize_lookup(value)}
            for other in ordered_articles:
                if other.article.id == seed.article.id:
                    continue
                days_delta = abs((seed_time - other.article.published_at).days)
                if days_delta > max_days_delta:
                    continue
                score = max(0.0, 1 - (days_delta / max_days_delta))
                candidates['temporal_window'].append((other.article.id, score))

                shared_tags = seed_tags & set(other.tag_codes)
                if shared_tags:
                    candidates['shared_tag'].append((other.article.id, len(shared_tags) + score))

                shared_entities = seed_entities & set(other.entity_slugs)
                if shared_entities:
                    candidates['shared_entity'].append((other.article.id, len(shared_entities) + score))

                other_keyphrases = {normalize_lookup(value) for value in other.key_phrases if normalize_lookup(value)}
                lexical_overlap = len(seed_keyphrases & other_keyphrases)
                if lexical_overlap:
                    candidates['lexical_neighbor'].append((other.article.id, lexical_overlap + score))

            chosen_for_seed: list[int] = []
            seen_ids: set[int] = set()
            for origin, ranked_rows in candidates.items():
                ranked = sorted(ranked_rows, key=lambda item: (-item[1], item[0]))
                summary.origin_counts[origin] = min(len(ranked), per_origin_limit)
                overflow = max(0, len(ranked) - per_origin_limit)
                if overflow:
                    summary.overflow_counts[origin] = overflow
                for article_id, _ in ranked[:per_origin_limit]:
                    if article_id not in seen_ids and len(chosen_for_seed) >= per_seed_limit:
                        summary.overflow_counts[origin] = summary.overflow_counts.get(origin, 0) + 1
                        continue
                    pair_key = tuple(sorted((seed.article.id, article_id)))
                    pair = pair_map.setdefault(
                        pair_key,
                        CandidatePair(
                            left_article_id=pair_key[0],
                            right_article_id=pair_key[1],
                        ),
                    )
                    pair.origins.add(origin)
                    if article_id not in seen_ids:
                        seen_ids.add(article_id)
                        chosen_for_seed.append(article_id)
            summary.candidate_count = len(chosen_for_seed)
            for rank, article_id in enumerate(chosen_for_seed, start=1):
                pair_key = tuple(sorted((seed.article.id, article_id)))
                pair = pair_map[pair_key]
                if pair.rank is None or rank < pair.rank:
                    pair.rank = rank
            summaries.append(summary)

        pairs = sorted(pair_map.values(), key=lambda item: (item.rank or 999999, item.left_article_id, item.right_article_id))
        return pairs, summaries

    def score_pair(self, left: EnrichedArticle, right: EnrichedArticle) -> StoryClusterMemberReason:
        """Score whether two enriched articles should belong to the same story cluster."""

        left_keyphrases = [normalize_lookup(value) for value in left.key_phrases if normalize_lookup(value)]
        right_keyphrases = [normalize_lookup(value) for value in right.key_phrases if normalize_lookup(value)]
        left_signature = lexical_signature(left.article.title, left.article.summary)
        right_signature = lexical_signature(right.article.title, right.article.summary)
        lexical_overlap_score = jaccard_similarity(left_signature, right_signature)
        left_event_terms = event_terms(f"{left.article.title} {left.article.summary} {' '.join(left.key_phrases)}")
        right_event_terms = event_terms(f"{right.article.title} {right.article.summary} {' '.join(right.key_phrases)}")
        event_overlap_score = jaccard_similarity(left_event_terms, right_event_terms)
        left_followup_terms = followup_markers(f"{left.article.title} {left.article.summary}")
        right_followup_terms = followup_markers(f"{right.article.title} {right.article.summary}")
        followup_marker_overlap = jaccard_similarity(left_followup_terms, right_followup_terms)
        semantic_similarity = max(
            jaccard_similarity(left_keyphrases + left.entity_slugs, right_keyphrases + right.entity_slugs),
            round((lexical_overlap_score * 0.6) + (event_overlap_score * 0.4), 4),
        )
        title_sim = title_similarity(left.article.title, right.article.title)
        lede_sim = title_similarity(
            f"{left.article.title}. {left.article.summary}".strip(),
            f"{right.article.title}. {right.article.summary}".strip(),
        )
        shared_entity_score = jaccard_similarity(left.entity_slugs, right.entity_slugs)
        entity_salience_score = min(
            1.0,
            shared_entity_score * (1.0 if len(set(left.entity_slugs) & set(right.entity_slugs)) >= 2 else 0.72),
        )
        tag_overlap_score = jaccard_similarity(left.tag_codes, right.tag_codes)
        keyphrase_overlap_score = max(jaccard_similarity(left_keyphrases, right_keyphrases), lexical_overlap_score)
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
        has_followup_shape = (
            days_delta <= 4
            and shared_entity_score >= 0.5
            and (
                event_overlap_score >= 0.14
                or lexical_overlap_score >= 0.18
                or followup_marker_overlap > 0
                or (len(shared_entities) >= 2 and tag_overlap_score >= 0.33)
            )
        )
        event_continuity_score = min(
            1.0,
            (
                (0.45 if len(shared_entities) >= 2 else 0.0)
                + (0.2 if tag_overlap_score >= 0.33 else 0.0)
                + (0.2 if event_overlap_score >= 0.14 else 0.0)
                + (0.15 if followup_marker_overlap > 0 else 0.0)
            ),
        )
        if article_types & {"opinion", "editorial"}:
            if (
                left.analysis.article_type != right.analysis.article_type
                or article_types != {"opinion"}
            ):
                hard_block = "opinion_editorial_excluded_from_primary_clusters"
        if article_types & secondary_types and (
            lede_sim < 0.58 or keyphrase_overlap_score < 0.32
        ):
            penalties.append("secondary_form_penalty")
            if shared_entity_score >= 0.5 and keyphrase_overlap_score < 0.24 and event_overlap_score < 0.2:
                risky_bridge_pair = True
                penalties.append("entity_glue_penalty")
        if days_delta >= 2 and not has_followup_shape and lede_sim < 0.56 and keyphrase_overlap_score < 0.4:
            penalties.append("followup_penalty")
        if (
            shared_entity_score >= 0.5
            and not has_followup_shape
            and (lede_sim < 0.6 or article_types & secondary_types)
            and keyphrase_overlap_score < 0.24
            and event_overlap_score < 0.2
            and tag_overlap_score < 0.75
        ):
            penalties.append("entity_glue_penalty")
            risky_bridge_pair = True
        if days_delta >= 4 and semantic_similarity < 0.52 and lede_sim < 0.62 and event_overlap_score < 0.2:
            penalties.append("late_story_drift_penalty")
            risky_bridge_pair = True
        score = (
            semantic_similarity * 0.22
            + max(title_sim, lede_sim) * 0.16
            + lede_sim * 0.14
            + entity_salience_score * 0.16
            + tag_overlap_score * 0.07
            + keyphrase_overlap_score * 0.09
            + event_overlap_score * 0.04
            + event_continuity_score * 0.10
            + temporal_proximity_score * 0.02
        )
        if has_followup_shape:
            score += 0.06
        if "secondary_form_penalty" in penalties:
            score -= 0.14
        if "followup_penalty" in penalties:
            score -= 0.12
        if "entity_glue_penalty" in penalties:
            score -= 0.14
        if "late_story_drift_penalty" in penalties:
            score -= 0.12
        return StoryClusterMemberReason(
            score=max(0.0, round(score, 4)),
            semantic_similarity=round(semantic_similarity, 4),
            title_similarity=round(max(title_sim, lede_sim), 4),
            shared_entity_score=round(entity_salience_score, 4),
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
        components, _ = self._build_guarded_components(article_ids, accepted_edges)
        return components

    def _raw_connected_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> list[list[int]]:
        adjacency: dict[int, set[int]] = defaultdict(set)
        for left, right, _ in accepted_edges:
            adjacency[left].add(right)
            adjacency[right].add(left)

        remaining = set(article_ids)
        components: list[list[int]] = []
        while remaining:
            seed = remaining.pop()
            component = [seed]
            queue = deque([seed])
            while queue:
                node = queue.popleft()
                for neighbor in sorted(adjacency.get(node, set())):
                    if neighbor not in remaining:
                        continue
                    remaining.remove(neighbor)
                    component.append(neighbor)
                    queue.append(neighbor)
            components.append(sorted(component))
        return sorted(components, key=len, reverse=True)

    def _build_guarded_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> tuple[list[list[int]], dict[int, dict[str, object]]]:
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
        medium_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
        raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]] = defaultdict(dict)
        for left, right, reason in sorted(
            accepted_edges, key=lambda item: item[2].score, reverse=True
        ):
            edge_class = self._classify_closure_edge(reason)
            if edge_class == "discard":
                continue
            raw_adjacency[left][right] = reason
            raw_adjacency[right][left] = reason
            target = strong_adjacency if edge_class == "strong" else medium_adjacency
            target[left][right] = reason
            target[right][left] = reason

        remaining = set(article_ids)
        components: list[set[int]] = []
        member_meta: dict[int, dict[str, object]] = {}
        while remaining:
            seed = max(
                remaining,
                key=lambda article_id: max(
                    (
                        reason.score
                        for adjacency in (strong_adjacency, medium_adjacency)
                        for reason in adjacency.get(article_id, {}).values()
                    ),
                    default=0.0,
                ),
            )
            cluster = {seed}
            remaining.remove(seed)
            member_meta[seed] = {
                "closure_stage": "seed",
                "closure_decision": "seed",
                "closure_support_count": 0,
            }
            queue = deque([seed])
            while queue:
                node = queue.popleft()
                for neighbor in sorted(strong_adjacency.get(node, {})):
                    if neighbor not in remaining:
                        continue
                    remaining.remove(neighbor)
                    cluster.add(neighbor)
                    queue.append(neighbor)
                    support = [
                        strong_adjacency[neighbor][member]
                        for member in cluster
                        if member != neighbor and member in strong_adjacency.get(neighbor, {})
                    ]
                    member_meta[neighbor] = self._closure_attach_meta(
                        cluster_size=len(cluster),
                        support=support,
                        decision="strong_component",
                        stage="strong",
                    )
            components.append(cluster)

        self._preserve_medium_components(
            components=components,
            member_meta=member_meta,
            raw_adjacency=raw_adjacency,
            strong_adjacency=strong_adjacency,
        )

        singleton_cluster_by_id = {
            next(iter(component)): component for component in components if len(component) == 1
        }
        candidate_singletons = sorted(singleton_cluster_by_id)
        for candidate in candidate_singletons:
            own_cluster = singleton_cluster_by_id.get(candidate)
            if own_cluster is None or len(own_cluster) != 1:
                continue
            best_target: set[int] | None = None
            best_support: list[StoryClusterMemberReason] = []
            best_decision: str | None = None
            for cluster in components:
                if cluster is own_cluster or not cluster:
                    continue
                support = [
                    adjacency[candidate][member]
                    for adjacency in (strong_adjacency, medium_adjacency)
                    for member in cluster
                    if member in adjacency.get(candidate, {})
                ]
                attach_decision = self._should_attach_candidate(cluster, support)
                if attach_decision is None:
                    continue
                if not best_support or max(reason.score for reason in support) > max(reason.score for reason in best_support):
                    best_target = cluster
                    best_support = support
                    best_decision = attach_decision
            if best_target is None or best_decision is None:
                member_meta[candidate] = {
                    "closure_stage": "singleton",
                    "closure_decision": "no_support",
                    "closure_support_count": 0,
                }
                continue
            best_target.add(candidate)
            own_cluster.clear()
            singleton_cluster_by_id.pop(candidate, None)
            member_meta[candidate] = self._closure_attach_meta(
                cluster_size=len(best_target),
                support=best_support,
                decision=best_decision,
                stage="attach",
            )

        final_components = [component for component in components if component]
        normalized = [sorted(component) for component in final_components]
        return sorted(normalized, key=len, reverse=True), member_meta

    def _preserve_medium_components(
        self,
        *,
        components: list[set[int]],
        member_meta: dict[int, dict[str, object]],
        raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    ) -> None:
        singleton_cluster_by_id = {
            next(iter(component)): component for component in components if len(component) == 1
        }
        visited: set[int] = set()
        for article_id in sorted(raw_adjacency):
            if article_id in visited or article_id not in singleton_cluster_by_id:
                continue
            raw_component = []
            queue = deque([article_id])
            visited.add(article_id)
            while queue:
                node = queue.popleft()
                raw_component.append(node)
                for neighbor in sorted(raw_adjacency.get(node, {})):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    queue.append(neighbor)
            raw_component = sorted(raw_component)
            if not all(node in singleton_cluster_by_id for node in raw_component):
                continue
            audit = self._audit_medium_component(
                raw_component=raw_component,
                raw_adjacency=raw_adjacency,
                strong_adjacency=strong_adjacency,
            )
            if not audit["preserve"]:
                continue
            new_cluster = {node for node in raw_component}
            for node in raw_component:
                singleton_cluster_by_id[node].clear()
                singleton_cluster_by_id.pop(node, None)
                member_meta[node] = self._closure_attach_meta(
                    cluster_size=len(new_cluster),
                    support=audit["support_by_node"].get(node, []),
                    decision="preserved_medium_component",
                    stage="medium_component",
                )
            components.append(new_cluster)

    def _audit_medium_component(
        self,
        *,
        raw_component: list[int],
        raw_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
        strong_adjacency: dict[int, dict[int, StoryClusterMemberReason]],
    ) -> dict[str, object]:
        if len(raw_component) < 2 or len(raw_component) > 3:
            return {"preserve": False}
        if any(strong_adjacency.get(node, {}) for node in raw_component):
            return {"preserve": False}

        support_by_node: dict[int, list[StoryClusterMemberReason]] = defaultdict(list)
        edges: list[StoryClusterMemberReason] = []
        compatible_edge_count = 0
        non_entity_signal_count = 0
        max_days_delta = 0
        for index, left in enumerate(raw_component):
            for right in raw_component[index + 1 :]:
                reason = raw_adjacency.get(left, {}).get(right)
                if reason is None:
                    continue
                edges.append(reason)
                support_by_node[left].append(reason)
                support_by_node[right].append(reason)
                max_days_delta = max(max_days_delta, reason.days_delta)
                if reason.shared_tag_count >= 1 or reason.shared_keyphrase_count >= 1:
                    non_entity_signal_count += 1
                if self._is_medium_component_edge_compatible(reason):
                    compatible_edge_count += 1
        minimum_edges = 1 if len(raw_component) == 2 else 2
        if len(edges) < minimum_edges:
            return {"preserve": False}
        if compatible_edge_count != len(edges):
            return {"preserve": False}
        if non_entity_signal_count < 1:
            return {"preserve": False}
        if max_days_delta > 3:
            return {"preserve": False}
        mean_score = sum(reason.score for reason in edges) / len(edges)
        best_score = max(reason.score for reason in edges)
        if mean_score < 0.72 or best_score < 0.74:
            return {"preserve": False}
        return {
            "preserve": True,
            "support_by_node": dict(support_by_node),
        }

    def _is_medium_component_edge_compatible(self, reason: StoryClusterMemberReason) -> bool:
        if reason.risky_bridge_pair:
            return False
        if reason.article_type_pair_class == "secondary_form_pair":
            return False
        forbidden_penalties = {
            "entity_glue_penalty",
            "late_story_drift_penalty",
            "secondary_form_penalty",
        }
        if any(penalty in forbidden_penalties for penalty in reason.penalties):
            return False
        if reason.days_delta > 3:
            return False
        if reason.shared_entity_count < 2 and reason.shared_tag_count < 1 and reason.shared_keyphrase_count < 1:
            return False
        if reason.shared_tag_count < 1 and reason.shared_keyphrase_count < 1:
            return False
        return reason.score >= 0.72

    def _classify_closure_edge(self, reason: StoryClusterMemberReason) -> str:
        if reason.risky_bridge_pair and reason.score < 0.78:
            return "discard"
        if not reason.risky_bridge_pair and reason.score >= 0.78:
            return "strong"
        return "medium"

    def _closure_attach_meta(
        self,
        *,
        cluster_size: int,
        support: list[StoryClusterMemberReason],
        decision: str,
        stage: str,
    ) -> dict[str, object]:
        if not support:
            return {
                "closure_stage": stage,
                "closure_decision": decision,
                "closure_support_count": 0,
                "closure_cluster_size": cluster_size,
            }
        best = max(support, key=lambda reason: reason.score)
        return {
            "closure_stage": stage,
            "closure_decision": decision,
            "closure_support_count": len(support),
            "closure_cluster_size": cluster_size,
            "closure_best_score": round(best.score, 4),
            "closure_mean_score": round(sum(reason.score for reason in support) / len(support), 4),
            "closure_best_days_delta": best.days_delta,
            "closure_best_shared_entities": best.shared_entity_count,
            "closure_best_shared_tags": best.shared_tag_count,
            "closure_best_shared_keyphrases": best.shared_keyphrase_count,
            "closure_best_penalties": list(best.penalties),
        }

    def _should_attach_candidate(
        self,
        cluster: set[int],
        support: list[StoryClusterMemberReason],
    ) -> str | None:
        if not support:
            return None
        best = max(support, key=lambda reason: reason.score)
        best_score = best.score
        support_count = len(support)
        mean_score = sum(reason.score for reason in support) / support_count
        risky_support = any(reason.risky_bridge_pair for reason in support)
        has_guardrail_penalty = any(
            penalty in {"entity_glue_penalty", "late_story_drift_penalty", "secondary_form_penalty"}
            for reason in support
            for penalty in reason.penalties
        )
        has_secondary_form = any(
            reason.article_type_pair_class == "secondary_form_pair" for reason in support
        )
        if len(cluster) == 1:
            return (
                "seed_pair"
                if best_score >= 0.68
                and not risky_support
                and not has_guardrail_penalty
                and not has_secondary_form
                else None
            )
        if support_count >= 2 and mean_score >= 0.72 and best_score >= 0.74 and not risky_support:
            return "multi_support"
        pivot_compatible = (
            not best.risky_bridge_pair
            and best.days_delta <= 4
            and best_score >= 0.74
            and best.shared_entity_count >= 2
            and (best.shared_tag_count >= 1 or best.shared_keyphrase_count >= 1)
            and "entity_glue_penalty" not in best.penalties
            and "late_story_drift_penalty" not in best.penalties
        )
        if pivot_compatible:
            return "strong_pivot_attach"
        if best_score >= 0.82 and mean_score >= 0.76 and not risky_support:
            return "high_confidence_attach"
        return None

    def _persist_clusters(
        self,
        articles: list[EnrichedArticle],
        components: list[list[int]],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
        member_closure_meta: dict[int, dict[str, object]],
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
                    "closure": member_closure_meta.get(
                        article_id,
                        {
                            "closure_stage": "singleton",
                            "closure_decision": "no_support",
                            "closure_support_count": 0,
                        },
                    ),
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
