from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.clustering import ClusterPipeline  # noqa: E402
from src.analysis.ops.story_eval import build_pair_artifacts, load_fixture_dataset  # noqa: E402
from src.analysis.ops.story_review import (  # noqa: E402
    load_review_rows,
    summarize_review_labels,
    sweep_thresholds_against_review_labels,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize manual story-review feedback and sweep thresholds against it")
    parser.add_argument("--fixture", required=True, help="Path to fixture/export JSON dataset")
    parser.add_argument("--review-jsonl", required=True, help="Path to labeled review batch JSONL")
    parser.add_argument("--output-dir", default="artifacts/story-review-feedback")
    parser.add_argument("--score-threshold", type=float, default=0.68)
    parser.add_argument("--max-days-delta", type=int, default=7)
    parser.add_argument("--thresholds", default="0.45,0.55,0.60,0.68,0.72,0.78")
    return parser.parse_args()


def parse_thresholds(raw: str) -> list[float]:
    return [float(chunk.strip()) for chunk in raw.split(",") if chunk.strip()]


def main() -> int:
    args = parse_args()
    thresholds = parse_thresholds(args.thresholds)
    dataset = load_fixture_dataset(args.fixture)
    rows = load_review_rows(args.review_jsonl)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    artifacts, _, _ = build_pair_artifacts(
        pipeline,
        dataset.articles,
        score_threshold=args.score_threshold,
        max_days_delta=args.max_days_delta,
    )
    summary = summarize_review_labels(rows)
    threshold_sweep = sweep_thresholds_against_review_labels(artifacts, rows, thresholds=thresholds)
    output = {
        "fixture": str(Path(args.fixture)),
        "review_jsonl": str(Path(args.review_jsonl)),
        "summary": summary,
        "threshold_sweep": threshold_sweep,
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
