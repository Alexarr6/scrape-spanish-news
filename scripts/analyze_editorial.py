"""CLI entrypoint for dedicated article-level editorial analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.llm_client import LLMSettings  # noqa: E402
from src.analysis.pipeline import EditorialAnalysisPipeline  # noqa: E402
from src.persistence.db import (  # noqa: E402
    create_postgres_engine,
    init_schema,
    make_session,
    resolve_db_url,
)


def _csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run dedicated editorial analysis for persisted articles"
    )
    parser.add_argument("--db-url", default="")
    parser.add_argument("--days-back", type=int, default=2)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument(
        "--status", choices=["pending", "failed", "completed", "any"], default="pending"
    )
    parser.add_argument("--failed-only", action="store_true")
    parser.add_argument("--article-ids", type=_csv_ints, default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--published-from", default=None)
    parser.add_argument("--published-to", default=None)
    parser.add_argument("--reprocess", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = create_postgres_engine(resolve_db_url(args.db_url))
    init_schema(engine)
    session = make_session(engine)
    try:
        settings = None if args.dry_run else LLMSettings.from_env()
        pipeline = EditorialAnalysisPipeline(session, llm_settings=settings)
        status = "failed" if args.failed_only else args.status
        effective_status = pipeline.effective_status(
            status=status,
            reprocess=args.reprocess,
            article_ids=args.article_ids,
        )
        metrics = pipeline.analyze_articles(
            days_back=args.days_back,
            limit=args.limit,
            reprocess=args.reprocess,
            status=status,
            article_ids=args.article_ids,
            source=args.source,
            published_from=(
                None
                if not args.published_from
                else __import__("datetime").date.fromisoformat(args.published_from)
            ),
            published_to=(
                None
                if not args.published_to
                else __import__("datetime").date.fromisoformat(args.published_to)
            ),
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
        payload = metrics.model_dump(mode="json")
        payload["diagnostic_summary"] = {
            "top_unclear_reasons": sorted(
                payload.get("unclear_reason_counts", {}).items(),
                key=lambda item: item[1],
                reverse=True,
            )[:5],
            "top_preserved_signals": {
                key: sorted(values.items(), key=lambda item: item[1], reverse=True)[:5]
                for key, values in payload.get("preserved_signal_counts", {}).items()
            },
        }
        payload["selection"] = {
            "status": status,
            "effective_status": effective_status,
            "reprocess": args.reprocess,
            "reprocess_widened_status": effective_status != status,
            "article_ids": args.article_ids or [],
            "source": args.source,
            "published_from": args.published_from,
            "published_to": args.published_to,
            "dry_run": args.dry_run,
            "batch_size": args.batch_size,
            "status_counts": pipeline.selection_status_counts(
                days_back=args.days_back,
                limit=args.limit,
                article_ids=args.article_ids,
                source=args.source,
                published_from=(
                    None
                    if not args.published_from
                    else __import__("datetime").date.fromisoformat(args.published_from)
                ),
                published_to=(
                    None
                    if not args.published_to
                    else __import__("datetime").date.fromisoformat(args.published_to)
                ),
                batch_size=args.batch_size,
            ),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
