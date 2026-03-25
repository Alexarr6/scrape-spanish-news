from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.pipeline import ClusterPipeline  # noqa: E402
from src.analysis.story_eval import build_pair_artifacts, load_fixture_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a small manual labeling set from current story-matching decisions"
    )
    parser.add_argument("--fixture", required=True, help="Path to fixture JSON dataset")
    parser.add_argument("--output", default="artifacts/story-matching-eval/manual-gold-candidates.jsonl")
    parser.add_argument("--score-threshold", type=float, default=0.68)
    parser.add_argument("--max-days-delta", type=int, default=7)
    parser.add_argument("--top-accepted", type=int, default=10)
    parser.add_argument("--top-borderline", type=int, default=10)
    parser.add_argument("--top-rejected", type=int, default=10)
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
    articles_by_id = {item.article.id: item.article for item in dataset.articles}
    accepted = sorted([a for a in artifacts if a.accepted], key=lambda a: a.reason.score, reverse=True)
    rejected = sorted([a for a in artifacts if not a.accepted], key=lambda a: a.reason.score, reverse=True)
    borderline = sorted(artifacts, key=lambda a: abs(a.reason.score - args.score_threshold))
    picked = []
    picked.extend(("accepted_high", item) for item in accepted[: args.top_accepted])
    picked.extend(("borderline", item) for item in borderline[: args.top_borderline])
    picked.extend(("rejected_high", item) for item in rejected[: args.top_rejected])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    with output_path.open("w", encoding="utf-8") as handle:
        for bucket, artifact in picked:
            key = tuple(sorted((artifact.left_article_id, artifact.right_article_id)))
            if key in seen:
                continue
            seen.add(key)
            left = articles_by_id[artifact.left_article_id]
            right = articles_by_id[artifact.right_article_id]
            row = {
                "bucket": bucket,
                "left_article_id": artifact.left_article_id,
                "right_article_id": artifact.right_article_id,
                "predicted_label": "same_event" if artifact.accepted else "different_event",
                "score": artifact.reason.score,
                "reason": artifact.reason.model_dump(mode="json"),
                "left": {
                    "source": left.source,
                    "published_at": left.published_at.isoformat(),
                    "title": left.title,
                    "summary": left.summary,
                },
                "right": {
                    "source": right.source,
                    "published_at": right.published_at.isoformat(),
                    "title": right.title,
                    "summary": right.summary,
                },
                "label": "",
                "labeler_notes": "",
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output_path), "row_count": len(seen)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
