from __future__ import annotations

import argparse
import json
from datetime import datetime
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
    parser.add_argument("--max-articles-to-extract", type=int, default=120)
    parser.add_argument("--max-runtime-seconds", type=int, default=180)
    parser.add_argument("--metrics-out", default="", help="Optional path for metrics JSON")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist scraped articles into PostgreSQL (opt-in, off by default)",
    )
    parser.add_argument(
        "--db-url",
        default="",
        help="PostgreSQL SQLAlchemy URL. Used only when --persist is enabled.",
    )
    return parser.parse_args()


def _validate_date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d")
    return value


def _persist_articles(articles: list, db_url: str) -> dict[str, int]:
    from src.persistence.contracts import ArticleCreate
    from src.persistence.crud import ArticleCRUD
    from src.persistence.db import create_postgres_engine, init_schema, make_session, resolve_db_url

    engine = create_postgres_engine(resolve_db_url(db_url))
    init_schema(engine)

    rows = [ArticleCreate.model_validate(a.as_dict()) for a in articles]
    with make_session(engine) as session:
        result = ArticleCRUD(session).ingest_many(rows)
    return result.model_dump()


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

    persistence_result: dict[str, int] | None = None
    if args.persist:
        persistence_result = _persist_articles(articles, args.db_url)

    if args.metrics_out:
        path = Path(args.metrics_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

    summary = f"source={args.source} date={date_utc} kept={len(articles)} stop_reason={metrics['stop_reason']}"
    if persistence_result is not None:
        summary += (
            " persist="
            f"inserted:{persistence_result['inserted']},"
            f"updated:{persistence_result['updated']},"
            f"unchanged:{persistence_result['unchanged']},"
            f"errors:{persistence_result['errors']}"
        )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
