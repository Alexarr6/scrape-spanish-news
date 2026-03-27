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
    build_review_batch,
    dump_review_batch_jsonl,
    render_review_batch_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a human-review batch for same-event matching")
    parser.add_argument("--fixture", required=True, help="Path to fixture/export JSON dataset")
    parser.add_argument("--output-dir", default="artifacts/story-review-batch")
    parser.add_argument("--score-threshold", type=float, default=0.68)
    parser.add_argument("--max-days-delta", type=int, default=7)
    parser.add_argument("--batch-size", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset = load_fixture_dataset(args.fixture)
    pipeline = ClusterPipeline(session=None)  # type: ignore[arg-type]
    artifacts, _, _ = build_pair_artifacts(
        pipeline,
        dataset.articles,
        score_threshold=args.score_threshold,
        max_days_delta=args.max_days_delta,
    )
    rows = build_review_batch(
        artifacts,
        dataset.articles,
        score_threshold=args.score_threshold,
        batch_size=args.batch_size,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_review_batch_jsonl(rows, output_dir / "review-batch.jsonl")
    (output_dir / "review-batch.md").write_text(render_review_batch_markdown(rows), encoding="utf-8")
    manifest = {
        "fixture": str(Path(args.fixture)),
        "score_threshold": args.score_threshold,
        "max_days_delta": args.max_days_delta,
        "batch_size": len(rows),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
