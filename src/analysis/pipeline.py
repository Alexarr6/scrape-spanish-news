"""Pipelines for article enrichment and same-story cluster rebuilding."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
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
    EditorialAnalysisRunMetrics,
    EnrichmentRunMetrics,
    PairScoreArtifact,
    StoryClusterMemberReason,
)
from src.analysis.heuristics import heuristic_enrichment, title_similarity
from src.analysis.llm_client import (
    EDITORIAL_ANALYSIS_SCHEMA_VERSION,
    EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION,
    EditorialAnalysisResult,
    OpenRouterClient,
    OpenRouterSettings,
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
from src.persistence.contracts import ArticleRead
from src.persistence.orm_models import ArticleORM


@dataclass
class EnrichedArticle:
    article: ArticleRead
    analysis: ArticleAnalysisRead
    tag_codes: list[str]
    entity_slugs: list[str]
    key_phrases: list[str]


class AnalysisPipeline:
    """Enrich persisted articles with tags, entities, and analysis side tables."""

    def __init__(self, session: Session, *, llm_settings: OpenRouterSettings | None = None) -> None:
        self.session = session
        self.llm = OpenRouterClient(llm_settings) if llm_settings else None
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
            provider="openrouter" if settings else "heuristic",
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
            .limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()
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

    def __init__(self, session: Session, *, llm_settings: OpenRouterSettings | None = None) -> None:
        self.session = session
        self.llm = OpenRouterClient(llm_settings) if llm_settings else None

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
            raise RuntimeError("OpenRouter settings are required for editorial analysis")

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
        analysis.analysis_status = "pending"
        analysis.failure_reason = ""
        analysis.content_hash = content_hash
        analysis.model_provider = "openrouter"
        analysis.model_name = self.llm.settings.model
        analysis.model_version = self.llm.settings.model
        analysis.prompt_version = self.llm.settings.prompt_version
        analysis.schema_version = EDITORIAL_ANALYSIS_SCHEMA_VERSION
        analysis.source_text_version = EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION

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
        analysis.article_type = payload.article_type
        analysis.article_type_confidence = payload.article_type_confidence
        analysis.bias_label = payload.bias_label
        analysis.bias_score = payload.bias_score
        analysis.bias_confidence = payload.bias_confidence
        analysis.tone_emotional = payload.tone_emotional
        analysis.tone_target = payload.tone_target
        analysis.opinionatedness = payload.opinionatedness
        analysis.sensationalism = payload.sensationalism
        analysis.rhetorical_certainty = payload.rhetorical_certainty
        analysis.editorial_applicability = (
            diagnostics.editorial_applicability if diagnostics is not None else "full"
        )
        analysis.editorial_applicability_reason = (
            diagnostics.editorial_applicability_reason
            if diagnostics is not None
            else "general_editorial_content"
        )
        analysis.analysis_path = analysis_path
        analysis.framing_devices_json = json.dumps(payload.framing_devices, ensure_ascii=False)
        analysis.evidence_spans_json = json.dumps(
            [item.model_dump(mode="json") for item in payload.evidence_spans],
            ensure_ascii=False,
        )
        analysis.rationale = payload.rationale
        analysis.diagnostics_json = (
            json.dumps(diagnostics.model_dump(mode="json"), ensure_ascii=False)
            if diagnostics is not None
            else "{}"
        )
        analysis.analysis_status = "completed"
        analysis.failure_reason = ""
        analysis.content_hash = content_hash
        analysis.analyzed_at = datetime.now(UTC)
        analysis.updated_at = datetime.now(UTC)

    def _persist_editorial_failure(
        self,
        *,
        analysis: ArticleEditorialAnalysisORM,
        failure_class: str,
        failure_message: str,
        artifact_path: str,
    ) -> None:
        analysis.article_type = analysis.article_type or "unclear"
        analysis.bias_label = analysis.bias_label or "unclear"
        analysis.tone_emotional = analysis.tone_emotional or "unclear"
        analysis.tone_target = analysis.tone_target or "unclear"
        analysis.opinionatedness = analysis.opinionatedness or "unclear"
        analysis.sensationalism = analysis.sensationalism or "unclear"
        analysis.rhetorical_certainty = analysis.rhetorical_certainty or "unclear"
        analysis.editorial_applicability = analysis.editorial_applicability or "full"
        analysis.editorial_applicability_reason = (
            analysis.editorial_applicability_reason or "general_editorial_content"
        )
        analysis.analysis_path = analysis.analysis_path or failure_class
        analysis.diagnostics_json = analysis.diagnostics_json or "{}"
        analysis.analysis_status = "failed"
        summary = f"{failure_class}: {failure_message}".strip()
        if artifact_path:
            summary = f"{summary} [artifact={artifact_path}]"
        analysis.failure_reason = summary[:255]
        analysis.updated_at = datetime.now(UTC)

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
        keyphrase_overlap_score = jaccard_similarity(
            [normalize_lookup(v) for v in left.key_phrases],
            [normalize_lookup(v) for v in right.key_phrases],
        )
        days_delta = abs((left.article.published_at - right.article.published_at).days)
        temporal_proximity_score = max(0.0, 1 - (days_delta / 7))
        penalties: list[str] = []
        hard_block = None
        if {left.analysis.article_type, right.analysis.article_type} & {"opinion", "editorial"}:
            if left.analysis.article_type != right.analysis.article_type or {
                left.analysis.article_type,
                right.analysis.article_type,
            } != {"opinion"}:
                hard_block = "opinion_editorial_excluded_from_primary_clusters"
        if (
            "analysis" in {left.analysis.article_type, right.analysis.article_type}
            and title_sim < 0.55
        ):
            penalties.append("analysis_pair_penalty")
        if days_delta >= 3 and title_sim < 0.6:
            penalties.append("followup_penalty")
        score = (
            semantic_similarity * 0.30
            + title_sim * 0.20
            + shared_entity_score * 0.25
            + tag_overlap_score * 0.10
            + keyphrase_overlap_score * 0.10
            + temporal_proximity_score * 0.05
        )
        if "analysis_pair_penalty" in penalties:
            score -= 0.15
        if "followup_penalty" in penalties:
            score -= 0.12
        return StoryClusterMemberReason(
            score=max(0.0, round(score, 4)),
            semantic_similarity=round(semantic_similarity, 4),
            title_similarity=round(title_sim, 4),
            shared_entity_score=round(shared_entity_score, 4),
            tag_overlap_score=round(tag_overlap_score, 4),
            keyphrase_overlap_score=round(keyphrase_overlap_score, 4),
            temporal_proximity_score=round(temporal_proximity_score, 4),
            hard_block=hard_block,
            penalties=penalties,
        )

    def _connected_components(
        self,
        article_ids: list[int],
        accepted_edges: list[tuple[int, int, StoryClusterMemberReason]],
    ) -> list[list[int]]:
        parent = {article_id: article_id for article_id in article_ids}

        def find(node: int) -> int:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left: int, right: int) -> None:
            root_left = find(left)
            root_right = find(right)
            if root_left != root_right:
                parent[root_right] = root_left

        for left, right, _ in accepted_edges:
            union(left, right)
        grouped: dict[int, list[int]] = defaultdict(list)
        for article_id in article_ids:
            grouped[find(article_id)].append(article_id)
        return sorted((sorted(members) for members in grouped.values()), key=len, reverse=True)

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
                pair_scores = [
                    reason.score
                    for (left_id, right_id), reason in edge_map.items()
                    if article_id in {left_id, right_id}
                ]
                membership_score = sum(pair_scores) / len(pair_scores) if pair_scores else 1.0
                reason_payload = {"edge_scores": pair_scores}
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
