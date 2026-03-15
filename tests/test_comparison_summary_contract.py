import json
import re
import unittest
from pathlib import Path

from src.core.comparison_summary import SourceSnapshot, build_comparison_summary
from src.core.contracts import ComparisonSummaryModel


class ComparisonSummaryContractTests(unittest.TestCase):
    date = "2026-03-13"
    sources = ["20minutos", "abc", "eldiario", "elmundo", "elpais", "lavanguardia"]

    @property
    def archived_run_root(self) -> Path:
        return Path(__file__).resolve().parents[1] / "runs" / "20260314-1212-8ff9"

    def _pick_existing(self, run_root: Path, candidates: list[str]) -> Path:
        for rel in candidates:
            path = run_root / rel
            if path.exists():
                return path
        self.fail(f"missing all candidates: {candidates}")

    def _load_json(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_fixture_summary(self) -> dict:
        run_root = self.archived_run_root
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

        return build_comparison_summary(
            date=self.date,
            baseline_ref="canon2",
            current_ref="reg2",
            snapshots=snapshots,
        )

    def test_builds_stable_v1_schema_for_all_sources(self):
        summary = self._build_fixture_summary()

        self.assertEqual(summary["schema_version"], "comparison_summary.v1")
        self.assertEqual(summary["date"], self.date)
        self.assertEqual(summary["baseline_ref"], "canon2")
        self.assertEqual(summary["current_ref"], "reg2")
        self.assertEqual(len(summary["sources"]), len(self.sources))

        ComparisonSummaryModel.model_validate(summary)

    def test_fixture_payload_respects_json_schema_constraints(self):
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "docs/contracts/comparison_summary.schema.json"
        )
        schema = self._load_json(schema_path)
        summary = self._build_fixture_summary()

        for key in schema["required"]:
            self.assertIn(key, summary)
        if schema.get("additionalProperties") is False:
            self.assertEqual(set(summary.keys()), set(schema["properties"].keys()))

        self.assertEqual(summary["schema_version"], schema["properties"]["schema_version"]["const"])
        self.assertRegex(summary["date"], re.compile(schema["properties"]["date"]["pattern"]))
        self.assertIn(summary["status"], schema["properties"]["status"]["enum"])

        sources_schema = schema["properties"]["sources"]
        self.assertGreaterEqual(len(summary["sources"]), sources_schema["minItems"])

        row_schema = sources_schema["items"]
        row_props = row_schema["properties"]
        for row in summary["sources"]:
            for key in row_schema["required"]:
                self.assertIn(key, row)
            if row_schema.get("additionalProperties") is False:
                self.assertEqual(set(row.keys()), set(row_props.keys()))

            self.assertGreaterEqual(row["baseline_count"], row_props["baseline_count"]["minimum"])
            self.assertGreaterEqual(row["current_count"], row_props["current_count"]["minimum"])
            self.assertIn(row["status"], row_props["status"]["enum"])
            self.assertIsInstance(row["warnings"], list)

            metrics = row["metrics"]
            metrics_schema = row_props["metrics"]
            for key in metrics_schema["required"]:
                self.assertIn(key, metrics)
            self.assertGreaterEqual(
                metrics["discovered"],
                metrics_schema["properties"]["discovered"]["minimum"],
            )
            self.assertGreaterEqual(
                metrics["processed"],
                metrics_schema["properties"]["processed"]["minimum"],
            )
            self.assertGreaterEqual(
                metrics["kept"],
                metrics_schema["properties"]["kept"]["minimum"],
            )
            self.assertGreaterEqual(
                metrics["discarded_by_date"],
                metrics_schema["properties"]["discarded_by_date"]["minimum"],
            )
            self.assertGreaterEqual(
                len(metrics["stop_reason"]),
                metrics_schema["properties"]["stop_reason"]["minLength"],
            )


if __name__ == "__main__":
    unittest.main()
