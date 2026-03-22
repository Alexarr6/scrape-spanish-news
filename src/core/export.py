from __future__ import annotations

import csv
import json
from pathlib import Path

from .contracts import validate_article_payload
from .models import Article

FIELDS = [
    "source",
    "title",
    "url",
    "published_at",
    "section",
    "author",
    "summary",
    "article_text",
    "tags",
]


def export_articles(articles: list[Article], out_path: str) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = [validate_article_payload(a.as_dict()) for a in articles]

    if out.suffix.lower() == ".csv":
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            for row in payload:
                writer.writerow(row)
    else:
        with out.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
