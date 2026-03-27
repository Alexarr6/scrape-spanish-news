from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.analysis.shared.contracts import (
    ArticleEditorialAnalysisPayload,
    EditorialAnalysisDiagnostics,
    EditorialAnalysisRunMetrics,
    EditorialCompletedPersistence,
    EditorialFailurePersistence,
)
from src.analysis.editorial.artifacts import analysis_path_for_result, write_failure_artifact
from src.analysis.editorial.crud import EditorialAnalysisCRUD
from src.analysis.editorial.llm import (
    EDITORIAL_ANALYSIS_SCHEMA_VERSION,
    EDITORIAL_ANALYSIS_SOURCE_TEXT_VERSION,
    EditorialAnalysisResult,
    LLMClient,
    LLMSettings,
    build_editorial_analysis_prompt,
    editorial_analysis_json_schema,
    editorial_debug_artifact_dir,
)
from src.analysis.editorial.normalization import build_editorial_diagnostics_from_payload
from src.analysis.editorial.orm import ArticleEditorialAnalysisORM
from src.analysis.editorial.selection import (
    EditorialSelectionFilters,
    effective_status,
    select_candidate_articles,
    selection_status_counts,
    should_skip_existing,
)
from src.analysis.enrichment.utils import content_hash
from src.persistence.core import ArticleRead


class EditorialAnalysisPipeline:
    """Run bounded LLM-driven editorial analysis as a separate first-pass pipeline."""

    def __init__(self, session: Session, *, llm_settings: LLMSettings | None = None) -> None:
        self.session = session
        self.llm = LLMClient(llm_settings) if llm_settings else None
        self.repo = EditorialAnalysisCRUD(session)
        self._artifact_dir_factory = self._default_artifact_dir

    def effective_status(
        self,
        *,
        status: str,
        reprocess: bool,
        article_ids: list[int] | None,
    ) -> str:
        return effective_status(status=status, reprocess=reprocess, article_ids=article_ids)

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
        effective = self.effective_status(
            status=status,
            reprocess=reprocess,
            article_ids=article_ids,
        )
        filters = EditorialSelectionFilters(
            days_back=days_back,
            limit=limit,
            status=effective,
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
            article_content_hash = content_hash(article)
            analysis = self.repo.get_by_article_id(article.id)
            if self._should_skip_existing(
                analysis,
                content_hash=article_content_hash,
                reprocess=reprocess,
            ):
                metrics.skipped_count += 1
                continue
            analysis = analysis or ArticleEditorialAnalysisORM(article_id=article.id)
            if analysis.id is None:
                self.session.add(analysis)
            self._prepare_pending_analysis(analysis=analysis, content_hash=article_content_hash)
            prompt = build_editorial_analysis_prompt(
                source=article.source,
                section=article.section,
                published_at=article.published_at.isoformat() if article.published_at else "",
                url=str(article.url),
                title=article.title,
                summary=article.summary,
                body=article.article_text,
            )
            result = self.llm.analyze_editorial(
                article_prompt=prompt,
                schema=editorial_analysis_json_schema(),
            )
            self._update_attempt_metrics(metrics, result)
            success_attempt = result.successful_attempt
            if success_attempt and success_attempt.payload is not None:
                self._persist_editorial_analysis(
                    analysis=analysis,
                    payload=success_attempt.payload,
                    content_hash=article_content_hash,
                    diagnostics=success_attempt.diagnostics,
                    analysis_path=self._analysis_path_for_result(result),
                )
                self._update_success_metrics(metrics, result, success_attempt)
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

    def _update_attempt_metrics(
        self,
        metrics: EditorialAnalysisRunMetrics,
        result: EditorialAnalysisResult,
    ) -> None:
        metrics.request_count += sum(1 for attempt in result.attempts if attempt.request_accepted)
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

    def _update_success_metrics(self, metrics, result, success_attempt):  # type: ignore[no-untyped-def]
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

    def _prepare_pending_analysis(
        self,
        *,
        analysis: ArticleEditorialAnalysisORM,
        content_hash: str,
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
        return selection_status_counts(
            self.session,
            days_back=days_back,
            limit=limit,
            article_ids=article_ids,
            source=source,
            published_from=published_from,
            published_to=published_to,
            batch_size=batch_size,
        )

    def _select_candidate_articles(self, filters: EditorialSelectionFilters):
        return select_candidate_articles(self.session, filters)

    def _should_skip_existing(
        self,
        analysis: ArticleEditorialAnalysisORM | None,
        *,
        content_hash: str,
        reprocess: bool,
    ) -> bool:
        return should_skip_existing(analysis, content_hash=content_hash, reprocess=reprocess)

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
        self,
        payload: ArticleEditorialAnalysisPayload,
    ) -> EditorialAnalysisDiagnostics:
        return build_editorial_diagnostics_from_payload(payload, provider_path="pipeline_default")

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
        return analysis_path_for_result(result)

    def _write_failure_artifact(
        self,
        *,
        article: ArticleRead,
        analysis: ArticleEditorialAnalysisORM,
        prompt: str,
        result: EditorialAnalysisResult,
    ) -> str:
        return write_failure_artifact(
            article=article,
            analysis=analysis,
            prompt=prompt,
            result=result,
            artifact_dir_factory=self._artifact_dir_factory,
        )

    def _default_artifact_dir(self) -> Path:
        return editorial_debug_artifact_dir()
