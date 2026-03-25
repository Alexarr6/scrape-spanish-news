from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.pipeline import ClusterPipeline  # noqa: E402
from src.analysis.story_eval import (  # noqa: E402
    dump_pair_artifacts_jsonl,
    evaluate_fixture,
    load_fixture_dataset,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate current same-event matching baseline on a fixture gold set"
    )
    parser.add_argument("--fixture", required=True, help="Path to fixture JSON dataset")
    parser.add_argument("--output-dir", default="artifacts/story-matching-eval")
    parser.add_argument("--score-threshold", type=float, default=0.68)
    parser.add_argument("--max-days-delta", type=int, default=7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset = load_fixture_dataset(args.fixture)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    result = evaluate_fixture(
        pipeline,
        dataset,
        score_threshold=args.score_threshold,
        max_days_delta=args.max_days_delta,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_pair_artifacts_jsonl(result.artifacts, output_dir / "pair-artifacts.jsonl")
    summary = {
        "fixture": str(Path(args.fixture)),
        "score_threshold": args.score_threshold,
        "max_days_delta": args.max_days_delta,
        "article_count": len(dataset.articles),
        "predicted_components": result.predicted_components,
        "pair_summary": None
        if result.pair_summary is None
        else result.pair_summary.__dict__,
        "cluster_summary": None
        if result.cluster_summary is None
        else result.cluster_summary.__dict__,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
