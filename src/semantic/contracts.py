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
class PointAnalysisArtifact:
    article_id: int
    cluster_id: int | None = None
    cluster_size: int = 0
    is_outlier: bool = False
    local_density_distance: float = 0.0
    source_neighbor_diversity: int = 0
    nearby_sources: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClusterArtifact:
    cluster_id: int
    size: int
    article_ids: list[int] = field(default_factory=list)
    representative_article_ids: list[int] = field(default_factory=list)
    top_sources: dict[str, int] = field(default_factory=dict)
    source_count: int = 0
    source_dominance: float = 0.0
    date_min: str = ""
    date_max: str = ""
    centroid_x: float = 0.0
    centroid_y: float = 0.0

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisMetadataArtifact:
    distance_basis: str = "embedding_cosine_distance"
    article_ids: list[int] = field(default_factory=list)
    article_count: int = 0
    config: dict[str, Any] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticAnalysisArtifact:
    points: list[PointAnalysisArtifact] = field(default_factory=list)
    clusters: list[ClusterArtifact] = field(default_factory=list)
    unclustered_article_ids: list[int] = field(default_factory=list)
    density_baseline: float = 0.0
    outlier_count: int = 0
    metadata: AnalysisMetadataArtifact = field(default_factory=AnalysisMetadataArtifact)

    def model_dump(self) -> dict[str, Any]:
        return {
            "points": [point.model_dump() for point in self.points],
            "clusters": [cluster.model_dump() for cluster in self.clusters],
            "unclustered_article_ids": self.unclustered_article_ids,
            "density_baseline": self.density_baseline,
            "outlier_count": self.outlier_count,
            "metadata": self.metadata.model_dump(),
        }


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
    analysis: PointAnalysisArtifact = field(
        default_factory=lambda: PointAnalysisArtifact(article_id=0)
    )

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
