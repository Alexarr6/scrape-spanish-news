import json
import unittest
from pathlib import Path

from src.core.contracts import NewsItemModel, RunMetricsModel


class CrossSourceOutputMetricsContractTests(unittest.TestCase):
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

    def test_output_item_shape_stable_for_each_source(self):
        run_root = self.archived_run_root

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
            for row in rows[: min(10, len(rows))]:
                NewsItemModel.model_validate(row)

    def test_metrics_shape_stable_for_each_source(self):
        run_root = self.archived_run_root

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
            parsed = RunMetricsModel.model_validate(metrics)
            payload = parsed.model_dump()
            if source in {"elpais", "eldiario", "abc"} and "strategy_metrics" in payload:
                self.assertEqual(
                    payload["strategy_metrics"].get("schema_version"),
                    "discovery_strategy_metrics.v1",
                )
                self.assertIsInstance(payload["strategy_metrics"].get("strategies"), list)


if __name__ == "__main__":
    unittest.main()
