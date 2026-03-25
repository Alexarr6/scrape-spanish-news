from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.analysis.contracts import PairScoreArtifact
from src.analysis.pipeline import EnrichedArticle
from src.analysis.story_eval import (
    PairLabel,
    PairEvalSummary,
    build_pair_artifacts,
    evaluate_pair_labels,
)


@dataclass
class ReviewBatchRow:
    bucket: str
    left_article_id: int
    right_article_id: int
    predicted_label: str
    score: float
    candidate_rank: int | None
    candidate_origins: list[str]
    reason: dict
    left: dict
    right: dict
    label: str = ""
    labeler_notes: str = ""


@dataclass
class ThresholdSweepRow:
    threshold: float
    accepted_pair_count: int
    predicted_cluster_count: int
    singleton_count: int
    multi_article_cluster_count: int
    pair_summary: PairEvalSummary | None


def build_threshold_sweep(
    pipeline,
    articles: list[EnrichedArticle],
    labels: list[PairLabel] | None = None,
    *,
    thresholds: Iterable[float],
    max_days_delta: int = 7,
) -> list[ThresholdSweepRow]:
    rows: list[ThresholdSweepRow] = []
    for threshold in thresholds:
        artifacts, _, components = build_pair_artifacts(
            pipeline,
            articles,
            score_threshold=threshold,
            max_days_delta=max_days_delta,
        )
        pair_summary = evaluate_pair_labels(artifacts, labels or []) if labels is not None else None
        rows.append(
            ThresholdSweepRow(
                threshold=round(threshold, 4),
                accepted_pair_count=sum(1 for artifact in artifacts if artifact.accepted),
                predicted_cluster_count=len(components),
                singleton_count=sum(1 for component in components if len(component) == 1),
                multi_article_cluster_count=sum(1 for component in components if len(component) > 1),
                pair_summary=pair_summary,
            )
        )
    return rows


def build_review_batch(
    artifacts: list[PairScoreArtifact],
    articles: list[EnrichedArticle],
    *,
    score_threshold: float,
    batch_size: int = 10,
    accepted_share: float = 0.3,
    borderline_share: float = 0.4,
) -> list[ReviewBatchRow]:
    articles_by_id = {item.article.id: item.article for item in articles}
    accepted = sorted(
        [artifact for artifact in artifacts if artifact.accepted],
        key=lambda artifact: artifact.reason.score,
        reverse=True,
    )
    rejected = sorted(
        [artifact for artifact in artifacts if not artifact.accepted],
        key=lambda artifact: artifact.reason.score,
        reverse=True,
    )
    borderline = sorted(
        artifacts,
        key=lambda artifact: (abs(artifact.reason.score - score_threshold), -artifact.reason.score),
    )

    accepted_target = max(1, round(batch_size * accepted_share)) if accepted else 0
    borderline_target = max(1, round(batch_size * borderline_share)) if borderline else 0
    rejected_target = max(0, batch_size - accepted_target - borderline_target)

    picked: list[tuple[str, PairScoreArtifact]] = []
    picked.extend(("accepted_high", artifact) for artifact in accepted[:accepted_target])
    picked.extend(("borderline", artifact) for artifact in borderline[:borderline_target])
    picked.extend(("rejected_high", artifact) for artifact in rejected[:rejected_target])

    rows: list[ReviewBatchRow] = []
    seen: set[tuple[int, int]] = set()
    for bucket, artifact in picked:
        key = tuple(sorted((artifact.left_article_id, artifact.right_article_id)))
        if key in seen:
            continue
        seen.add(key)
        left = articles_by_id[artifact.left_article_id]
        right = articles_by_id[artifact.right_article_id]
        rows.append(
            ReviewBatchRow(
                bucket=bucket,
                left_article_id=artifact.left_article_id,
                right_article_id=artifact.right_article_id,
                predicted_label="same_event" if artifact.accepted else "different_event",
                score=artifact.reason.score,
                candidate_rank=artifact.candidate_rank,
                candidate_origins=list(artifact.candidate_origins),
                reason=artifact.reason.model_dump(mode="json"),
                left={
                    "source": left.source,
                    "published_at": left.published_at.isoformat(),
                    "title": left.title,
                    "summary": left.summary,
                },
                right={
                    "source": right.source,
                    "published_at": right.published_at.isoformat(),
                    "title": right.title,
                    "summary": right.summary,
                },
            )
        )
        if len(rows) >= batch_size:
            break
    return rows


def dump_review_batch_jsonl(rows: list[ReviewBatchRow], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.__dict__, ensure_ascii=False) + "\n")


def render_review_batch_markdown(rows: list[ReviewBatchRow]) -> str:
    lines = [
        "# Story matching review batch",
        "",
        "Labels válidos: `same_event`, `different_event`, `uncertain`.",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## Pair {index}: {row.left_article_id} ↔ {row.right_article_id}",
                f"- bucket: `{row.bucket}`",
                f"- predicted: `{row.predicted_label}` | score: `{row.score:.4f}` | candidate_rank: `{row.candidate_rank}`",
                f"- candidate_origins: {', '.join(row.candidate_origins) if row.candidate_origins else 'n/a'}",
                f"- penalties: {', '.join(row.reason.get('penalties', [])) if row.reason.get('penalties') else 'none'}",
                f"- risky_bridge_pair: `{row.reason.get('risky_bridge_pair', False)}`",
                "- left:",
                f"  - [{row.left['source']}] {row.left['published_at']}",
                f"  - title: {row.left['title']}",
                f"  - summary: {row.left['summary']}",
                "- right:",
                f"  - [{row.right['source']}] {row.right['published_at']}",
                f"  - title: {row.right['title']}",
                f"  - summary: {row.right['summary']}",
                "- reviewer_label: ``",
                "- reviewer_notes: " ,
                "",
            ]
        )
    return "\n".join(lines)


def load_review_rows(path: str | Path) -> list[ReviewBatchRow]:
    rows: list[ReviewBatchRow] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            rows.append(ReviewBatchRow(**payload))
    return rows


def summarize_review_labels(rows: list[ReviewBatchRow]) -> dict:
    label_counts = Counter(row.label or "unlabeled" for row in rows)
    labeled_rows = [row for row in rows if row.label]
    decided_rows = [row for row in labeled_rows if row.label != "uncertain"]
    agreement_counts = Counter()
    bucket_counts = Counter(row.bucket for row in decided_rows)
    for row in decided_rows:
        predicted_positive = row.predicted_label == "same_event"
        actual_positive = row.label == "same_event"
        if predicted_positive and actual_positive:
            agreement_counts["true_positive"] += 1
        elif predicted_positive and not actual_positive:
            agreement_counts["false_positive"] += 1
        elif not predicted_positive and actual_positive:
            agreement_counts["false_negative"] += 1
        else:
            agreement_counts["true_negative"] += 1
    precision_den = agreement_counts["true_positive"] + agreement_counts["false_positive"]
    recall_den = agreement_counts["true_positive"] + agreement_counts["false_negative"]
    precision = agreement_counts["true_positive"] / precision_den if precision_den else 0.0
    recall = agreement_counts["true_positive"] / recall_den if recall_den else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else 0.0
    return {
        "row_count": len(rows),
        "labeled_count": len(labeled_rows),
        "decided_count": len(decided_rows),
        "uncertain_count": label_counts.get("uncertain", 0),
        "label_counts": dict(label_counts),
        "bucket_counts": dict(bucket_counts),
        "confusion": dict(agreement_counts),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def sweep_thresholds_against_review_labels(
    artifacts: list[PairScoreArtifact],
    rows: list[ReviewBatchRow],
    *,
    thresholds: Iterable[float],
) -> list[dict]:
    decided = [row for row in rows if row.label in {"same_event", "different_event"}]
    if not decided:
        return []
    artifact_by_key = {
        tuple(sorted((artifact.left_article_id, artifact.right_article_id))): artifact
        for artifact in artifacts
    }
    output = []
    for threshold in thresholds:
        labels = []
        rescored_artifacts = []
        for row in decided:
            key = tuple(sorted((row.left_article_id, row.right_article_id)))
            artifact = artifact_by_key.get(key)
            if artifact is None:
                continue
            rescored = artifact.model_copy(deep=True)
            rescored.accepted = rescored.reason.score >= threshold and rescored.reason.hard_block is None
            rescored_artifacts.append(rescored)
            labels.append(
                PairLabel(
                    left_article_id=row.left_article_id,
                    right_article_id=row.right_article_id,
                    label=row.label,
                )
            )
        summary = evaluate_pair_labels(rescored_artifacts, labels)
        output.append(
            {
                "threshold": round(threshold, 4),
                "pair_summary": None if summary is None else summary.__dict__,
            }
        )
    return output
