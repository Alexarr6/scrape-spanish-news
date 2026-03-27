from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analysis.ops.matching_rules import (
    GLOBAL_EXCLUDE_PATH_TERMS,
    GLOBAL_EXCLUDE_SECTION_TERMS,
    GLOBAL_EXCLUDE_TERMS,
    LOCALITY_TERMS,
    NATIONAL_TERMS,
    SOFT_LIFESTYLE_TERMS,
    SOURCE_EXCLUDE_SECTION_TERMS,
    SOURCE_EXCLUDE_TERMS,
    detect_bucket,
    local_published_date,
    text_blob,
)
from src.analysis.store.models import ArticleMatchingSelectionORM
from src.persistence.orm import ArticleORM

MATCHING_PROFILE_VERSION = "matching-v2"
MATCHING_DAILY_CAP = 0


@dataclass(frozen=True)
class MatchingDecision:
    eligible: bool
    eligibility_reason: str
    bucket: str
    score: float


@dataclass
class MatchingCorpusMetrics:
    profile_version: str = MATCHING_PROFILE_VERSION
    built_at: str = ""
    article_count: int = 0
    eligible_count: int = 0
    selected_count: int = 0
    bucket_counts: dict[str, int] | None = None
    source_counts: dict[str, int] | None = None
    audit_path: str = ""

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        del mode
        return {
            "profile_version": self.profile_version,
            "built_at": self.built_at,
            "article_count": self.article_count,
            "eligible_count": self.eligible_count,
            "selected_count": self.selected_count,
            "bucket_counts": self.bucket_counts or {},
            "source_counts": self.source_counts or {},
            "audit_path": self.audit_path,
        }


class MatchingCorpusPipeline:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build(
        self,
        *,
        days_back: int = 3,
        daily_cap: int = MATCHING_DAILY_CAP,
        audit_path: str = "",
    ) -> MatchingCorpusMetrics:
        started_at = datetime.now(UTC)
        rows = self._load_recent_articles(days_back=days_back)
        decisions = {row.id: self._decide(row) for row in rows}
        selected = self._select_articles(rows, decisions=decisions, daily_cap=daily_cap)
        self._persist(rows, decisions=decisions, selected=selected)
        audit_payload = self._build_audit(rows, decisions=decisions, selected=selected)
        if audit_path:
            path = Path(audit_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(audit_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return MatchingCorpusMetrics(
            built_at=started_at.isoformat(),
            article_count=len(rows),
            eligible_count=sum(1 for decision in decisions.values() if decision.eligible),
            selected_count=len(selected),
            bucket_counts=dict(Counter(item["bucket"] for item in selected.values())),
            source_counts=dict(Counter(item["source"] for item in selected.values())),
            audit_path=audit_path,
        )

    def _load_recent_articles(self, *, days_back: int) -> list[ArticleORM]:
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        stmt = (
            select(ArticleORM)
            .where(ArticleORM.published_at.is_not(None), ArticleORM.published_at >= cutoff)
            .order_by(ArticleORM.published_at.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def _select_articles(
        self,
        rows: list[ArticleORM],
        *,
        decisions: dict[int, MatchingDecision],
        daily_cap: int,
    ) -> dict[int, dict[str, Any]]:
        grouped: dict[
            tuple[str, date], list[tuple[ArticleORM, MatchingDecision]]
        ] = defaultdict(list)
        for row in rows:
            local_date = local_published_date(row.published_at)
            if local_date is None:
                continue
            grouped[(row.source, local_date)].append((row, decisions[row.id]))

        selected: dict[int, dict[str, Any]] = {}
        uncapped = daily_cap <= 0
        for (source, local_date), items in grouped.items():
            eligible_items = [(row, decision) for row, decision in items if decision.eligible]
            eligible_items.sort(
                key=lambda item: (
                    -item[1].score,
                    item[0].published_at or datetime.min.replace(tzinfo=UTC),
                    item[0].url,
                )
            )
            rank = 1
            for row, decision in eligible_items:
                if not uncapped and rank > daily_cap:
                    break
                selected[row.id] = {
                    "source": source,
                    "local_date": local_date,
                    "bucket": decision.bucket,
                    "score": decision.score,
                    "rank": rank,
                }
                rank += 1
        return selected

    def _persist(
        self,
        rows: list[ArticleORM],
        *,
        decisions: dict[int, MatchingDecision],
        selected: dict[int, dict[str, Any]],
    ) -> None:
        existing = {
            row.article_id: row
            for row in self.session.execute(select(ArticleMatchingSelectionORM)).scalars()
        }
        for article in rows:
            selection = existing.get(article.id)
            if selection is None:
                selection = ArticleMatchingSelectionORM(article_id=article.id)
                self.session.add(selection)
            decision = decisions[article.id]
            chosen = selected.get(article.id)
            selection.eligible = decision.eligible
            selection.eligibility_reason = decision.eligibility_reason
            selection.bucket = chosen["bucket"] if chosen else decision.bucket
            selection.score = chosen["score"] if chosen else decision.score
            selection.local_published_date = (
                chosen["local_date"] if chosen else local_published_date(article.published_at)
            )
            selection.selection_rank = chosen["rank"] if chosen else None
            selection.profile_version = MATCHING_PROFILE_VERSION
        self.session.commit()

    def _build_audit(
        self,
        rows: list[ArticleORM],
        *,
        decisions: dict[int, MatchingDecision],
        selected: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        by_source: dict[str, dict[str, Any]] = {}
        for row in rows:
            source_bucket = by_source.setdefault(
                row.source,
                {
                    "raw_count": 0,
                    "eligible_count": 0,
                    "selected_count": 0,
                    "raw_sections": Counter(),
                    "selected_sections": Counter(),
                    "selected_buckets": Counter(),
                },
            )
            source_bucket["raw_count"] += 1
            source_bucket["raw_sections"][row.section or ""] += 1
            if decisions[row.id].eligible:
                source_bucket["eligible_count"] += 1
            if row.id in selected:
                source_bucket["selected_count"] += 1
                source_bucket["selected_sections"][row.section or ""] += 1
                source_bucket["selected_buckets"][selected[row.id]["bucket"]] += 1

        payload_sources: dict[str, Any] = {}
        for source, bucket in by_source.items():
            payload_sources[source] = {
                "raw_count": bucket["raw_count"],
                "eligible_count": bucket["eligible_count"],
                "selected_count": bucket["selected_count"],
                "raw_sections": dict(bucket["raw_sections"].most_common(10)),
                "selected_sections": dict(bucket["selected_sections"].most_common(10)),
                "selected_buckets": dict(bucket["selected_buckets"]),
            }
        return {
            "profile_version": MATCHING_PROFILE_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "sources": payload_sources,
        }

    def _decide(self, row: ArticleORM) -> MatchingDecision:
        local_date = local_published_date(row.published_at)
        if local_date is None:
            return MatchingDecision(False, "missing_local_date", "", 0.0)

        path = (urlparse(row.url).path or "").casefold()
        section = (row.section or "").casefold()
        text = text_blob(row)
        if any(term in path for term in GLOBAL_EXCLUDE_PATH_TERMS):
            return MatchingDecision(False, "excluded_non_article_path", "", 0.0)
        if any(term in section for term in GLOBAL_EXCLUDE_SECTION_TERMS):
            return MatchingDecision(False, "excluded_section", "", 0.0)
        if any(
            term in section for term in SOURCE_EXCLUDE_SECTION_TERMS.get(row.source, ())
        ):
            return MatchingDecision(False, "excluded_source_section", "", 0.0)
        if any(term in text for term in GLOBAL_EXCLUDE_TERMS):
            return MatchingDecision(False, "excluded_article_type", "", 0.0)
        if any(term in path or term in text for term in SOURCE_EXCLUDE_TERMS.get(row.source, ())):
            return MatchingDecision(False, "excluded_source_policy", "", 0.0)
        if any(term in text for term in SOFT_LIFESTYLE_TERMS):
            return MatchingDecision(False, "excluded_soft_lifestyle", "", 0.0)

        bucket = detect_bucket(text)
        if not bucket:
            return MatchingDecision(False, "excluded_no_hard_news_bucket", "", 0.0)

        score = 3.0
        score += 2.0 if len((row.article_text or "").strip()) >= 1200 else 0.5
        score += 1.5 if any(term in text for term in NATIONAL_TERMS) else 0.0
        score += 1.0 if row.source == "eldiario" and "/politica/" in path else 0.0
        score += 0.5 if row.source == "elpais" and "/internacional/" in path else 0.0
        score += 0.5 if row.source == "elmundo" and "/espana/" in path else 0.0

        if any(term in path for term in LOCALITY_TERMS) and not any(
            term in text for term in NATIONAL_TERMS
        ):
            score -= 2.0
        if score < 2.5:
            return MatchingDecision(False, "excluded_locality_bias", bucket, score)

        return MatchingDecision(True, "eligible_hard_news", bucket, score)
