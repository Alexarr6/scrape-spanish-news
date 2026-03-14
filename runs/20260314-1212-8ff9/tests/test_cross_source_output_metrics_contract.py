import json
import unittest
from pathlib import Path


class CrossSourceOutputMetricsContractTests(unittest.TestCase):
    date = "2026-03-13"
    sources = ["20minutos", "abc", "eldiario", "elmundo", "elpais", "lavanguardia"]

    def _pick_existing(self, run_root: Path, candidates: list[str]) -> Path:
        for rel in candidates:
            path = run_root / rel
            if path.exists():
                return path
        self.fail(f"missing all candidates: {candidates}")

    def _load_json(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_output_item_shape_stable_for_each_source(self):
        run_root = Path(__file__).resolve().parents[1]
        required_article_keys = {
            "source",
            "title",
            "url",
            "published_at",
            "section",
            "author",
            "summary",
            "tags",
        }

        for source in self.sources:
            data_path = self._pick_existing(
                run_root,
                [
                    f"data/reg2_{source}_{self.date}.json",
                    f"data/reg_{source}_{self.date}.json",
                    f"data/news_{source}_{self.date}.json",
                ],
            )
            rows = self._load_json(data_path)
            self.assertIsInstance(rows, list)
            self.assertGreater(len(rows), 0, f"expected at least one row for {source}")
            first = rows[0]
            self.assertEqual(set(first.keys()), required_article_keys)
            for key in required_article_keys:
                self.assertIsInstance(first[key], str)

    def test_metrics_shape_stable_for_each_source(self):
        run_root = Path(__file__).resolve().parents[1]
        required_metric_keys = {
            "discovered",
            "processed",
            "kept",
            "discarded_by_date",
            "stop_reason",
        }

        for source in self.sources:
            metrics_path = self._pick_existing(
                run_root,
                [
                    f"logs/reg2_{source}_metrics.json",
                    f"logs/reg_{source}_metrics.json",
                    f"logs/news_{source}_metrics.json",
                    f"logs/canon2_{source}_metrics.json",
                    f"logs/canon_{source}_metrics.json",
                ],
            )
            metrics = self._load_json(metrics_path)
            self.assertTrue(required_metric_keys.issubset(metrics.keys()))
            self.assertIsInstance(metrics["discovered"], int)
            self.assertIsInstance(metrics["processed"], int)
            self.assertIsInstance(metrics["kept"], int)
            self.assertIsInstance(metrics["discarded_by_date"], int)
            self.assertIsInstance(metrics["stop_reason"], str)


if __name__ == "__main__":
    unittest.main()
