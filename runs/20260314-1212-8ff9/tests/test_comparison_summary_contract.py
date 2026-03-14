import json
import unittest
from pathlib import Path

from src.core.comparison_summary import SourceSnapshot, build_comparison_summary


class ComparisonSummaryContractTests(unittest.TestCase):
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

    def test_builds_stable_v1_schema_for_all_sources(self):
        run_root = Path(__file__).resolve().parents[1]
        snapshots: list[SourceSnapshot] = []

        for source in self.sources:
            baseline_path = self._pick_existing(
                run_root,
                [
                    f"data/canon2_{source}_{self.date}.json",
                    f"data/canon_{source}_{self.date}.json",
                    f"data/news_{source}_{self.date}.json",
                ],
            )
            current_path = self._pick_existing(
                run_root,
                [
                    f"data/reg2_{source}_{self.date}.json",
                    f"data/reg_{source}_{self.date}.json",
                    f"data/news_{source}_{self.date}.json",
                ],
            )
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

            baseline = self._load_json(baseline_path)
            current = self._load_json(current_path)
            metrics = self._load_json(metrics_path)

            snapshots.append(
                SourceSnapshot(
                    source=source,
                    baseline_count=len(baseline),
                    current_count=len(current),
                    metrics=metrics,
                )
            )

        summary = build_comparison_summary(
            date=self.date,
            baseline_ref="canon2",
            current_ref="reg2",
            snapshots=snapshots,
        )

        self.assertEqual(summary["schema_version"], "comparison_summary.v1")
        self.assertEqual(summary["date"], self.date)
        self.assertEqual(summary["baseline_ref"], "canon2")
        self.assertEqual(summary["current_ref"], "reg2")
        self.assertEqual(len(summary["sources"]), len(self.sources))

        expected_row_keys = {
            "source",
            "baseline_count",
            "current_count",
            "delta_abs",
            "delta_pct",
            "status",
            "warnings",
            "metrics",
        }
        expected_metric_keys = {"discovered", "processed", "kept", "discarded_by_date", "stop_reason"}

        seen = set()
        for row in summary["sources"]:
            self.assertEqual(set(row.keys()), expected_row_keys)
            self.assertIn(row["source"], self.sources)
            self.assertNotIn(row["source"], seen)
            seen.add(row["source"])

            self.assertIsInstance(row["baseline_count"], int)
            self.assertIsInstance(row["current_count"], int)
            self.assertIsInstance(row["delta_abs"], int)
            self.assertIsInstance(row["delta_pct"], float)
            self.assertIsInstance(row["warnings"], list)

            self.assertEqual(set(row["metrics"].keys()), expected_metric_keys)
            self.assertIsInstance(row["metrics"]["discovered"], int)
            self.assertIsInstance(row["metrics"]["processed"], int)
            self.assertIsInstance(row["metrics"]["kept"], int)
            self.assertIsInstance(row["metrics"]["discarded_by_date"], int)
            self.assertIsInstance(row["metrics"]["stop_reason"], str)


if __name__ == "__main__":
    unittest.main()
