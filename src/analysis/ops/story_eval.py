from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from src.analysis.clustering.service import ClusterPipeline
from src.analysis.shared.contracts import CandidateRecallSummary, PairScoreArtifact
from src.analysis.shared.types import EnrichedArticle


@dataclass
class PairLabel:
    left_article_id: int
    right_article_id: int
    label: str
    notes: str = ""

    @property
    def key(self) -> tuple[int, int]:
        return tuple(sorted((self.left_article_id, self.right_article_id)))

    @property
    def is_positive(self) -> bool:
        return self.label == "same_event"


@dataclass
class PairEvalSummary:
    labeled_pair_count: int
    positive_pair_count: int
    predicted_positive_count: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    precision: float
    recall: float
    f1: float


@dataclass
class ClusterEvalSummary:
    gold_cluster_count: int
    predicted_cluster_count: int
    gold_positive_pair_count: int
    predicted_positive_pair_count: int
    true_positive_pair_count: int
    precision: float
    recall: float
    f1: float


@dataclass
class EvalRunResult:
    pair_summary: PairEvalSummary | None
    cluster_summary: ClusterEvalSummary | None
    candidate_recall_summary: CandidateRecallSummary | None
    artifacts: list[PairScoreArtifact]
    predicted_components: list[list[int]]


@dataclass
class FixtureDataset:
    articles: list[EnrichedArticle]
    pair_labels: list[PairLabel]
    gold_clusters: list[list[int]]


def build_pair_artifacts(
    pipeline: ClusterPipeline,
    articles: list[EnrichedArticle],
    *,
    score_threshold: float = 0.68,
    max_days_delta: int = 7,
) -> tuple[list[PairScoreArtifact], list[tuple[int, int, object]], list[list[int]]]:
    artifacts: list[PairScoreArtifact] = []
    accepted_edges = []
    article_by_id = {article.article.id: article for article in articles}
    candidate_pairs, _ = pipeline._generate_candidate_pairs(  # noqa: SLF001
        articles,
        max_days_delta=max_days_delta,
    )
    for candidate in candidate_pairs:
        left = article_by_id[candidate.left_article_id]
        right = article_by_id[candidate.right_article_id]
        reason = pipeline.score_pair(left, right)
        accepted = reason.hard_block is None and reason.score >= score_threshold
        artifact = PairScoreArtifact(
            left_article_id=left.article.id,
            right_article_id=right.article.id,
            accepted=accepted,
            candidate_origins=sorted(candidate.origins),
            candidate_rank=candidate.rank,
            reason=reason,
        )
        artifacts.append(artifact)
        if accepted:
            accepted_edges.append((left.article.id, right.article.id, reason))
    components = pipeline._connected_components(  # noqa: SLF001
        [article.article.id for article in articles], accepted_edges
    )
    return artifacts, accepted_edges, components


def evaluate_fixture(
    pipeline: ClusterPipeline,
    dataset: FixtureDataset,
    *,
    score_threshold: float = 0.68,
    max_days_delta: int = 7,
) -> EvalRunResult:
    artifacts, _, components = build_pair_artifacts(
        pipeline,
        dataset.articles,
        score_threshold=score_threshold,
        max_days_delta=max_days_delta,
    )
    pair_summary = evaluate_pair_labels(artifacts, dataset.pair_labels)
    cluster_summary = evaluate_clusters(components, dataset.gold_clusters)
    candidate_recall_summary = evaluate_candidate_recall(artifacts, dataset.pair_labels)
    return EvalRunResult(
        pair_summary=pair_summary,
        cluster_summary=cluster_summary,
        candidate_recall_summary=candidate_recall_summary,
        artifacts=artifacts,
        predicted_components=components,
    )


def evaluate_pair_labels(
    artifacts: list[PairScoreArtifact], labels: list[PairLabel]
) -> PairEvalSummary | None:
    if not labels:
        return None
    artifact_by_key = {
        tuple(sorted((artifact.left_article_id, artifact.right_article_id))): artifact
        for artifact in artifacts
    }
    tp = fp = fn = predicted_positive = positives = 0
    for label in labels:
        artifact = artifact_by_key.get(label.key)
        predicted_same = bool(artifact.accepted) if artifact is not None else False
        actual_same = label.is_positive
        if actual_same:
            positives += 1
        if predicted_same:
            predicted_positive += 1
        if predicted_same and actual_same:
            tp += 1
        elif predicted_same and not actual_same:
            fp += 1
        elif actual_same and not predicted_same:
            fn += 1
    precision = tp / predicted_positive if predicted_positive else 0.0
    recall = tp / positives if positives else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else 0.0
    return PairEvalSummary(
        labeled_pair_count=len(labels),
        positive_pair_count=positives,
        predicted_positive_count=predicted_positive,
        true_positive_count=tp,
        false_positive_count=fp,
        false_negative_count=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
    )


def evaluate_clusters(
    predicted_components: list[list[int]], gold_clusters: list[list[int]]
) -> ClusterEvalSummary | None:
    if not gold_clusters:
        return None
    predicted_pairs = _cluster_pairs(predicted_components)
    gold_pairs = _cluster_pairs(gold_clusters)
    tp = len(predicted_pairs & gold_pairs)
    predicted_positive = len(predicted_pairs)
    positives = len(gold_pairs)
    precision = tp / predicted_positive if predicted_positive else 0.0
    recall = tp / positives if positives else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else 0.0
    return ClusterEvalSummary(
        gold_cluster_count=len(gold_clusters),
        predicted_cluster_count=len(predicted_components),
        gold_positive_pair_count=positives,
        predicted_positive_pair_count=predicted_positive,
        true_positive_pair_count=tp,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
    )


def dump_pair_artifacts_jsonl(artifacts: list[PairScoreArtifact], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for artifact in artifacts:
            handle.write(json.dumps(artifact.model_dump(mode="json"), ensure_ascii=False) + "\n")


def load_fixture_dataset(path: str | Path) -> FixtureDataset:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    from src.analysis.shared.contracts import ArticleAnalysisRead
    from src.persistence.core import ArticleRead

    articles = []
    for row in payload.get("articles", []):
        article = ArticleRead(**row["article"])
        analysis = ArticleAnalysisRead(**row["analysis"])
        articles.append(
            EnrichedArticle(
                article=article,
                analysis=analysis,
                tag_codes=row.get("tag_codes", []),
                entity_slugs=row.get("entity_slugs", []),
                key_phrases=row.get("key_phrases", []),
            )
        )
    labels = [PairLabel(**row) for row in payload.get("pair_labels", [])]
    return FixtureDataset(
        articles=articles,
        pair_labels=labels,
        gold_clusters=payload.get("gold_clusters", []),
    )


def _cluster_pairs(clusters: list[list[int]]) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    for cluster in clusters:
        for left, right in combinations(sorted(cluster), 2):
            pairs.add((left, right))
    return pairs


def evaluate_candidate_recall(
    artifacts: list[PairScoreArtifact],
    labels: list[PairLabel],
    *,
    ks: tuple[int, ...] = (5, 10, 20, 50),
) -> CandidateRecallSummary | None:
    positive_labels = [label for label in labels if label.is_positive]
    if not positive_labels:
        return None
    artifact_by_key = {
        tuple(sorted((artifact.left_article_id, artifact.right_article_id))): artifact
        for artifact in artifacts
    }
    covered_counts = {str(k): 0 for k in ks}
    for label in positive_labels:
        artifact = artifact_by_key.get(label.key)
        rank = artifact.candidate_rank if artifact is not None else None
        for k in ks:
            if rank is not None and rank <= k:
                covered_counts[str(k)] += 1
    total = len(positive_labels)
    return CandidateRecallSummary(
        positive_pair_count=total,
        covered_pair_count_by_k=covered_counts,
        recall_at_k={str(k): round(covered_counts[str(k)] / total, 4) for k in ks},
    )
