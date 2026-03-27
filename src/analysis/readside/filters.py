from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class ClusterListFilters:
    limit: int = 20
    offset: int = 0
    source: str | None = None
    tag_code: str | None = None
    entity_slug: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None


@dataclass
class EditorialAnalysisListFilters:
    limit: int = 20
    offset: int = 0
    source: str | None = None
    bias_label: str | None = None
    article_type: str | None = None
    analysis_status: str | None = None
    tone_emotional: str | None = None
    opinionatedness: str | None = None
    min_bias_confidence: float | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort: str = "published_at_desc"
