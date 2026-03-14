from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.adapters.registry import ADAPTERS, build_adapter
from src.core.adapter import RunConfig
from src.core.export import export_articles


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spain news scraper (core + adapters)")
    parser.add_argument("--source", required=True, choices=sorted(ADAPTERS.keys()))
    parser.add_argument("--date", required=True, help="UTC date as YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="Output .json or .csv path")
    parser.add_argument("--max-discovery-urls", type=int, default=300)
    parser.add_argument("--max-articles-to-extract", type=int, default=100)
    parser.add_argument("--max-runtime-seconds", type=int, default=180)
    parser.add_argument("--metrics-out", default="", help="Optional path for metrics JSON")
    return parser.parse_args()


def _validate_date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d")
    return value


def main() -> int:
    args = _parse_args()
    date_utc = _validate_date(args.date)
    cfg = RunConfig(
        max_discovery_urls=args.max_discovery_urls,
        max_articles_to_extract=args.max_articles_to_extract,
        max_runtime_seconds=args.max_runtime_seconds,
    )

    adapter = build_adapter(args.source)
    articles, metrics = adapter.run(target_date=date_utc, cfg=cfg)
    export_articles(articles, args.out)

    if args.metrics_out:
        path = Path(args.metrics_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"source={args.source} date={date_utc} kept={len(articles)} stop_reason={metrics['stop_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
