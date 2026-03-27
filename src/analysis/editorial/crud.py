from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.editorial.core import (
    EditorialCompletedPersistence,
    EditorialFailurePersistence,
)
from src.analysis.editorial.orm import ArticleEditorialAnalysisORM


class EditorialAnalysisCRUD:
    """Synchronous CRUD boundary for editorial analysis rows.

    FastCRUD is attractive here, but the current repository uses sync SQLAlchemy sessions
    end-to-end. This module establishes the target `core/orm/crud` shape first so the
    storage layer can be swapped later without reshaping the rest of the code again.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_article_id(self, article_id: int) -> ArticleEditorialAnalysisORM | None:
        return self.session.execute(
            select(ArticleEditorialAnalysisORM).where(
                ArticleEditorialAnalysisORM.article_id == article_id
            )
        ).scalar_one_or_none()

    def mark_pending(
        self,
        *,
        analysis: ArticleEditorialAnalysisORM,
        content_hash: str,
        model_provider: str,
        model_name: str,
        model_version: str,
        prompt_version: str,
        schema_version: str,
        source_text_version: str,
    ) -> ArticleEditorialAnalysisORM:
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
        analysis.rationale = analysis.rationale or "Pending editorial analysis."
        analysis.framing_devices_json = analysis.framing_devices_json or "[]"
        analysis.evidence_spans_json = analysis.evidence_spans_json or "[]"
        analysis.diagnostics_json = analysis.diagnostics_json or "{}"
        analysis.unclear_reasons_json = analysis.unclear_reasons_json or "[]"
        analysis.analysis_status = "pending"
        analysis.failure_reason = ""
        analysis.provider_failure_class = ""
        analysis.content_hash = content_hash
        analysis.model_provider = model_provider
        analysis.model_name = model_name
        analysis.model_version = model_version
        analysis.prompt_version = prompt_version
        analysis.schema_version = schema_version
        analysis.source_text_version = source_text_version
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def upsert_completed_analysis(
        self,
        *,
        analysis: ArticleEditorialAnalysisORM,
        command: EditorialCompletedPersistence,
    ) -> ArticleEditorialAnalysisORM:
        payload = command.payload
        diagnostics = command.diagnostics
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
        analysis.editorial_applicability = diagnostics.editorial_applicability
        analysis.editorial_applicability_reason = diagnostics.editorial_applicability_reason
        analysis.provider_failure_class = ""
        analysis.analysis_path = command.analysis_path
        analysis.unclear_reasons_json = json.dumps(diagnostics.unclear_reasons, ensure_ascii=False)
        analysis.article_type_status = self._dimension_status(diagnostics, "article_type")
        analysis.bias_status = self._dimension_status(diagnostics, "bias")
        analysis.tone_emotional_status = self._dimension_status(diagnostics, "tone_emotional")
        analysis.tone_target_status = self._dimension_status(diagnostics, "tone_target")
        analysis.opinionatedness_status = self._dimension_status(diagnostics, "opinionatedness")
        analysis.sensationalism_status = self._dimension_status(diagnostics, "sensationalism")
        analysis.rhetorical_certainty_status = self._dimension_status(
            diagnostics, "rhetorical_certainty"
        )
        analysis.framing_status = self._dimension_status(diagnostics, "framing")
        analysis.framing_devices_json = json.dumps(payload.framing_devices, ensure_ascii=False)
        analysis.evidence_spans_json = json.dumps(
            [item.model_dump(mode="json") for item in payload.evidence_spans],
            ensure_ascii=False,
        )
        analysis.rationale = payload.rationale
        analysis.diagnostics_json = json.dumps(
            diagnostics.model_dump(mode="json"), ensure_ascii=False
        )
        analysis.analysis_status = "completed"
        analysis.failure_reason = ""
        analysis.content_hash = command.content_hash
        analysis.analyzed_at = command.analyzed_at
        analysis.updated_at = command.analyzed_at
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def upsert_failed_analysis(
        self,
        *,
        analysis: ArticleEditorialAnalysisORM,
        command: EditorialFailurePersistence,
    ) -> ArticleEditorialAnalysisORM:
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
        analysis.provider_failure_class = command.failure_class
        analysis.analysis_path = (
            analysis.analysis_path or command.analysis_path or command.failure_class
        )
        analysis.unclear_reasons_json = analysis.unclear_reasons_json or "[]"
        analysis.diagnostics_json = analysis.diagnostics_json or "{}"
        analysis.analysis_status = "failed"
        analysis.content_hash = command.content_hash
        summary = f"{command.failure_class}: {command.failure_message}".strip()
        if command.artifact_path:
            summary = f"{summary} [artifact={command.artifact_path}]"
        analysis.failure_reason = summary[:255]
        analysis.updated_at = command.analyzed_at
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def _dimension_status(self, diagnostics, name: str) -> str:
        dimension = diagnostics.dimension_status.get(name)
        return "" if dimension is None else dimension.status
