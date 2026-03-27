from __future__ import annotations

from dataclasses import dataclass, field

from src.analysis.shared.contracts import ArticleAnalysisRead
from src.persistence.core import ArticleRead


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
