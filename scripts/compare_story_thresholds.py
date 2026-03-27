from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.clustering import ClusterPipeline  # noqa: E402
from src.analysis.ops.story_eval import load_fixture_dataset  # noqa: E402
from src.analysis.ops.story_review import build_threshold_sweep  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare story-matching thresholds on a fixture/export dataset"
    )
    parser.add_argument("--fixture", required=True, help="Path to fixture/export JSON dataset")
    parser.add_argument("--thresholds", default="0.45,0.55,0.60,0.68,0.72,0.78")
    parser.add_argument("--output-dir", default="artifacts/story-threshold-compare")
    parser.add_argument("--max-days-delta", type=int, default=7)
    return parser.parse_args()


def parse_thresholds(raw: str) -> list[float]:
    return [float(chunk.strip()) for chunk in raw.split(",") if chunk.strip()]


def render_markdown(rows: list) -> str:
    lines = [
        "# Threshold comparison",
        "",
        (
            "| threshold | accepted_pairs | clusters | singletons | multi_clusters | "
            "pair_precision | pair_recall | pair_f1 | cluster_precision | cluster_recall | "
            "cluster_f1 |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        pair = row.pair_summary
        cluster = row.cluster_summary
        lines.append(
            (
                "| {threshold:.2f} | {accepted_pair_count} | {predicted_cluster_count} | "
                "{singleton_count} | {multi_article_cluster_count} | {precision} | {recall} | "
                "{f1} | {cluster_precision} | {cluster_recall} | {cluster_f1} |"
            ).format(
                threshold=row.threshold,
                accepted_pair_count=row.accepted_pair_count,
                predicted_cluster_count=row.predicted_cluster_count,
                singleton_count=row.singleton_count,
                multi_article_cluster_count=row.multi_article_cluster_count,
                precision="-" if pair is None else pair.precision,
                recall="-" if pair is None else pair.recall,
                f1="-" if pair is None else pair.f1,
                cluster_precision="-" if cluster is None else cluster.precision,
                cluster_recall="-" if cluster is None else cluster.recall,
                cluster_f1="-" if cluster is None else cluster.f1,
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    thresholds = parse_thresholds(args.thresholds)
    dataset = load_fixture_dataset(args.fixture)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    rows = build_threshold_sweep(
        pipeline,
        dataset.articles,
        dataset.pair_labels,
        dataset.gold_clusters,
        thresholds=thresholds,
        max_days_delta=args.max_days_delta,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "fixture": str(Path(args.fixture)),
        "thresholds": thresholds,
        "rows": [
            {
                "threshold": row.threshold,
                "accepted_pair_count": row.accepted_pair_count,
                "predicted_cluster_count": row.predicted_cluster_count,
                "singleton_count": row.singleton_count,
                "multi_article_cluster_count": row.multi_article_cluster_count,
                "pair_summary": None if row.pair_summary is None else row.pair_summary.__dict__,
                "cluster_summary": (
                    None if row.cluster_summary is None else row.cluster_summary.__dict__
                ),
            }
            for row in rows
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(render_markdown(rows), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
