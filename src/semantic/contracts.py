from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SemanticArticle:
    article_id: int
    source: str
    title: str
    url: str
    published_at: str
    section: str
    summary: str
    article_text: str

    @property
    def text_length(self) -> int:
        return len(self.article_text or "")


@dataclass
class EmbeddingArtifact:
    article_id: int
    source: str
    title: str
    url: str
    published_at: str
    section: str
    summary_snippet: str
    text_length: int
    embedding_model: str
    embedding: list[float]

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NeighborArtifact:
    article_id: int
    similarity: float
    source: str
    title: str
    url: str
    published_at: str
    published_date: str
    display_date: str
    section: str
    summary_snippet: str

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PointArtifact:
    article_id: int
    source: str
    title: str
    url: str
    published_at: str
    published_date: str = ""
    display_date: str = ""
    section: str = ""
    summary_snippet: str = ""
    text_length: int = 0
    embedding_model: str = ""
    x: float = 0.0
    y: float = 0.0
    neighbors: list[NeighborArtifact] = field(default_factory=list)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticMetrics:
    started_at: str = field(default_factory=lambda: _utc_now_iso())
    finished_at: str = ""
    article_limit: int = 0
    fetched_rows: int = 0
    eligible_rows: int = 0
    skipped_empty_text: int = 0
    embedding_model: str = ""
    embedding_dimensions: int = 0
    embedding_batch_size: int = 0
    embedding_requests: int = 0
    projection_method: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)

    def finish(self) -> None:
        self.finished_at = _utc_now_iso()

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticBuildConfig:
    database_url: str
    limit: int = 200
    embedding_model: str = "text-embedding-3-small"
    batch_size: int = 20
    max_chars: int = 12000
    stamp: str = ""
    out_dir: Path = Path("data/semantic")
    log_dir: Path = Path("logs")

    def __post_init__(self) -> None:
        if not self.stamp:
            self.stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
