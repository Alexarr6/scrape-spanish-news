from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from src.core.export import export_articles
from src.core.models import Article


class ExportArticleTextTests(unittest.TestCase):
    def test_json_and_csv_include_article_text(self) -> None:
        root = Path("runs/20260314-1212-8ff9/data")
        root.mkdir(parents=True, exist_ok=True)

        items = [
            Article(
                source="elpais",
                title="t",
                url="https://example.com/a",
                published_at="2026-03-14T00:00:00+00:00",
                summary="s",
                article_text="full text",
            )
        ]

        json_out = root / "_tmp_article_text.json"
        csv_out = root / "_tmp_article_text.csv"
        export_articles(items, str(json_out))
        export_articles(items, str(csv_out))

        payload = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertEqual(payload[0]["article_text"], "full text")

        with csv_out.open("r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["article_text"], "full text")

        json_out.unlink(missing_ok=True)
        csv_out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
