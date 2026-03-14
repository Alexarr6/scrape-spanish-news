from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.core.contracts import (
    ComparisonSummaryModel,
    NewsItemModel,
    RunMetricsModel,
)


class ContractModelsTests(unittest.TestCase):
    def _load_fixture(self, name: str):
        root = Path(__file__).resolve().parent
        return json.loads((root / "fixtures" / name).read_text(encoding="utf-8"))

    def test_news_item_positive_and_negative(self):
        valid = {
            "source": "abc",
            "title": "t",
            "url": "https://abc.es/x",
            "published_at": "2026-03-13T10:00:00+00:00",
            "section": "espana",
            "author": "",
            "summary": "",
            "article_text": "",
            "tags": "",
        }
        row = NewsItemModel.model_validate(valid)
        self.assertEqual(row.model_dump()["source"], "abc")

        invalid = dict(valid)
        invalid["title"] = 123
        with self.assertRaises(TypeError):
            NewsItemModel.model_validate(invalid)

        invalid_text = dict(valid)
        invalid_text["article_text"] = 123
        with self.assertRaises(TypeError):
            NewsItemModel.model_validate(invalid_text)

    def test_run_metrics_negative_cases(self):
        valid = {
            "discovered": 1,
            "processed": 1,
            "kept": 1,
            "discarded_by_date": 0,
            "errors": 0,
            "stop_reason": "completed",
            "last_url": "",
        }
        RunMetricsModel.model_validate(valid)

        missing = dict(valid)
        missing.pop("stop_reason")
        with self.assertRaises(ValueError):
            RunMetricsModel.model_validate(missing)

        wrong_type = dict(valid)
        wrong_type["processed"] = "1"
        with self.assertRaises(TypeError):
            RunMetricsModel.model_validate(wrong_type)

    def test_comparison_summary_fixture_and_negative(self):
        fixture = self._load_fixture("comparison_summary_valid.json")
        parsed = ComparisonSummaryModel.model_validate(fixture)
        self.assertEqual(parsed.model_dump()["schema_version"], "comparison_summary.v1")

        broken = self._load_fixture("comparison_summary_valid.json")
        broken["sources"][0]["metrics"]["stop_reason"] = 7
        with self.assertRaises(TypeError):
            ComparisonSummaryModel.model_validate(broken)

    def test_comparison_summary_json_schema_shape(self):
        schema = ComparisonSummaryModel.model_json_schema()
        self.assertEqual(schema["type"], "object")
        self.assertIn("sources", schema["required"])
        self.assertEqual(schema["properties"]["sources"]["type"], "array")


if __name__ == "__main__":
    unittest.main()
